const canvas = document.getElementById("graphCanvas");
const ctx = canvas.getContext("2d");

const addNodeBtn = document.getElementById("addNodeBtn");
const removeNodeBtn = document.getElementById("removeNodeBtn");
const addEdgeBtn = document.getElementById("addEdgeBtn");
const removeEdgeBtn = document.getElementById("removeEdgeBtn");
const evaluateBtn = document.getElementById("evaluateBtn");
const zeroBasedToggle = document.getElementById("zeroBasedToggle");
const pMaxInput = document.getElementById("pMax");
const pMaxValue = document.getElementById("pMaxValue");
const shotsInput = document.getElementById("shots");
const maxIterInput = document.getElementById("maxIter");
const statusText = document.getElementById("statusText");
const resultStatus = document.getElementById("resultStatus");

const starTree = document.getElementById("starTree");
const heurTree = document.getElementById("heurTree");
const starHist = document.getElementById("starHist");
const heurHist = document.getElementById("heurHist");
const starRatio = document.getElementById("starRatio");
const heurRatio = document.getElementById("heurRatio");

const state = {
  nodes: [],
  edges: new Set(),
  selected: [],
  zeroBased: true,
};

const nodeRadius = 18;

function resizeCanvas(canvasEl, heightFallback) {
  const ratio = window.devicePixelRatio || 1;
  const cssWidth = canvasEl.clientWidth || canvasEl.width;
  const cssHeight = canvasEl.clientHeight || heightFallback || canvasEl.height;
  canvasEl.width = Math.floor(cssWidth * ratio);
  canvasEl.height = Math.floor(cssHeight * ratio);
  const ctx = canvasEl.getContext("2d");
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  return ctx;
}

function edgeKey(a, b) {
  const [u, v] = a < b ? [a, b] : [b, a];
  return `${u}-${v}`;
}

function labelFor(index) {
  return index + (state.zeroBased ? 0 : 1);
}

function updateStatus() {
  statusText.textContent = `${state.nodes.length} nodes, ${state.edges.size} edges.`;
}

function addNode() {
  const padding = 40;
  const x = padding + Math.random() * (canvas.width - padding * 2);
  const y = padding + Math.random() * (canvas.height - padding * 2);
  state.nodes.push({ x, y });
  updateStatus();
  draw();
}

function removeNode() {
  if (state.selected.length !== 1) {
    resultStatus.textContent = "Select one node to remove.";
    return;
  }
  const idx = state.selected[0];
  state.nodes.splice(idx, 1);

  const newEdges = new Set();
  for (const key of state.edges) {
    const [aStr, bStr] = key.split("-");
    let a = parseInt(aStr, 10);
    let b = parseInt(bStr, 10);
    if (a === idx || b === idx) {
      continue;
    }
    if (a > idx) a -= 1;
    if (b > idx) b -= 1;
    newEdges.add(edgeKey(a, b));
  }
  state.edges = newEdges;
  state.selected = [];
  updateStatus();
  draw();
}

function addEdge() {
  if (state.selected.length !== 2) {
    resultStatus.textContent = "Select two nodes to add an edge.";
    return;
  }
  const [a, b] = state.selected;
  if (a === b) return;
  state.edges.add(edgeKey(a, b));
  updateStatus();
  draw();
}

function removeEdge() {
  if (state.selected.length !== 2) {
    resultStatus.textContent = "Select two nodes to remove an edge.";
    return;
  }
  const [a, b] = state.selected;
  state.edges.delete(edgeKey(a, b));
  updateStatus();
  draw();
}

function getNodeAt(x, y) {
  for (let i = 0; i < state.nodes.length; i += 1) {
    const n = state.nodes[i];
    const dx = n.x - x;
    const dy = n.y - y;
    if (Math.sqrt(dx * dx + dy * dy) <= nodeRadius) {
      return i;
    }
  }
  return null;
}

function toggleSelection(idx) {
  const exists = state.selected.indexOf(idx);
  if (exists >= 0) {
    state.selected.splice(exists, 1);
  } else {
    if (state.selected.length === 2) {
      state.selected.shift();
    }
    state.selected.push(idx);
  }
}

function drawEdges(targetCtx, edges, nodes, color) {
  targetCtx.strokeStyle = color;
  targetCtx.lineWidth = 2;
  for (const key of edges) {
    const [aStr, bStr] = key.split("-");
    const a = parseInt(aStr, 10);
    const b = parseInt(bStr, 10);
    const na = nodes[a];
    const nb = nodes[b];
    if (!na || !nb) continue;
    targetCtx.beginPath();
    targetCtx.moveTo(na.x, na.y);
    targetCtx.lineTo(nb.x, nb.y);
    targetCtx.stroke();
  }
}

function drawNodes(targetCtx, nodes) {
  targetCtx.font = "600 13px 'Space Grotesk', sans-serif";
  targetCtx.textAlign = "center";
  targetCtx.textBaseline = "middle";

  nodes.forEach((n, i) => {
    const isSelected = state.selected.includes(i);
    const label = labelFor(i).toString();
    targetCtx.fillStyle = isSelected ? "#000" : "#fff";
    targetCtx.strokeStyle = "#000";
    targetCtx.lineWidth = isSelected ? 3 : 2;
    targetCtx.beginPath();
    targetCtx.arc(n.x, n.y, nodeRadius, 0, Math.PI * 2);
    targetCtx.fill();
    targetCtx.stroke();

    targetCtx.fillStyle = isSelected ? "#fff" : "#000";
    targetCtx.fillText(label, n.x, n.y + 1);
  });
}

function draw() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  drawEdges(ctx, state.edges, state.nodes, "#000");
  drawNodes(ctx, state.nodes);
}

function normalizeEdgesForPayload() {
  const base = state.zeroBased ? 0 : 1;
  return Array.from(state.edges).map((key) => {
    const [aStr, bStr] = key.split("-");
    const a = parseInt(aStr, 10) + base;
    const b = parseInt(bStr, 10) + base;
    return { u: a, v: b };
  });
}

function renderHistogram(container, histogram) {
  container.innerHTML = "";
  const entries = Object.entries(histogram).sort((a, b) => b[1] - a[1]);
  const maxCount = entries.reduce((acc, [, count]) => Math.max(acc, count), 0) || 1;
  const slice = entries.length > 16 ? entries.slice(0, 16) : entries;

  slice.forEach(([bitstring, count]) => {
    const row = document.createElement("div");
    row.className = "hist-bar";

    const label = document.createElement("div");
    label.className = "hist-label";
    label.textContent = bitstring;

    const bar = document.createElement("div");
    bar.className = "hist-value";
    const span = document.createElement("span");
    span.style.width = `${(count / maxCount) * 100}%`;
    bar.appendChild(span);

    const countEl = document.createElement("div");
    countEl.className = "hist-count";
    countEl.textContent = count.toString();

    row.appendChild(label);
    row.appendChild(bar);
    row.appendChild(countEl);
    container.appendChild(row);
  });

  if (entries.length > 16) {
    const note = document.createElement("div");
    note.className = "hist-count";
    note.textContent = `Showing top 16 of ${entries.length} outcomes.`;
    container.appendChild(note);
  }
}

function drawTree(canvasEl, nodes, treeEdges) {
  const tctx = resizeCanvas(canvasEl, 240);
  const width = canvasEl.clientWidth;
  const height = canvasEl.clientHeight;
  tctx.clearRect(0, 0, width, height);

  const xs = nodes.map((n) => n.x);
  const ys = nodes.map((n) => n.y);
  const minX = Math.min(...xs, 0);
  const maxX = Math.max(...xs, 1);
  const minY = Math.min(...ys, 0);
  const maxY = Math.max(...ys, 1);
  const pad = 18;
  const scaleX = (width - pad * 2) / (maxX - minX || 1);
  const scaleY = (height - pad * 2) / (maxY - minY || 1);
  const scale = Math.min(scaleX, scaleY);

  const mapped = nodes.map((n) => ({
    x: pad + (n.x - minX) * scale,
    y: pad + (n.y - minY) * scale,
  }));

  const edges = new Set(treeEdges.map(([u, v]) => edgeKey(u, v)));
  drawEdges(tctx, edges, mapped, "#000");

  tctx.font = "600 12px 'Space Grotesk', sans-serif";
  tctx.textAlign = "center";
  tctx.textBaseline = "middle";

  mapped.forEach((n, i) => {
    tctx.fillStyle = "#fff";
    tctx.strokeStyle = "#000";
    tctx.lineWidth = 2;
    tctx.beginPath();
    tctx.arc(n.x, n.y, 10, 0, Math.PI * 2);
    tctx.fill();
    tctx.stroke();

    tctx.fillStyle = "#000";
    tctx.fillText(labelFor(i).toString(), n.x, n.y + 1);
  });
}

function drawLineChart(canvasEl, values) {
  const lctx = resizeCanvas(canvasEl, 160);
  lctx.clearRect(0, 0, canvasEl.clientWidth, canvasEl.clientHeight);

  const padding = 32;
  const pointRadius = 4.5;
  const w = canvasEl.clientWidth - padding * 2;
  const h = canvasEl.clientHeight - padding * 2;
  const vals = values.map((v) => (v === null ? 0 : v));
  const maxV = Math.max(...vals, 1);

  const clamp = (val, min, max) => Math.min(Math.max(val, min), max);

  lctx.strokeStyle = "#000";
  lctx.lineWidth = 1;
  lctx.strokeRect(padding, padding, w, h);

  lctx.beginPath();
  vals.forEach((v, i) => {
    const x = padding + (w * i) / (vals.length - 1 || 1);
    const y = padding + h - (v / maxV) * h;
    const safeX = clamp(x, padding + pointRadius, padding + w - pointRadius);
    const safeY = clamp(y, padding + pointRadius, padding + h - pointRadius);
    if (i === 0) lctx.moveTo(safeX, safeY);
    else lctx.lineTo(safeX, safeY);
  });

  lctx.strokeStyle = "#d4866c";
  lctx.lineWidth = 2.5;
  lctx.stroke();

  lctx.fillStyle = "#1b4b7a";
  lctx.font = "600 11px 'Space Grotesk', sans-serif";
  vals.forEach((v, i) => {
    const x = padding + (w * i) / (vals.length - 1 || 1);
    const y = padding + h - (v / maxV) * h;
    const safeX = clamp(x, padding + pointRadius, padding + w - pointRadius);
    const safeY = clamp(y, padding + pointRadius, padding + h - pointRadius);
    lctx.beginPath();
    lctx.arc(safeX, safeY, pointRadius, 0, Math.PI * 2);
    lctx.fill();

    const label = `p${i + 1}`;
    lctx.fillText(label, safeX, canvasEl.clientHeight - 8);
  });
}

async function evaluateGraph() {
  if (state.nodes.length < 2) {
    resultStatus.textContent = "Add at least two nodes before evaluating.";
    return;
  }
  if (state.edges.size === 0) {
    resultStatus.textContent = "Add at least one edge to evaluate.";
    return;
  }

  const payload = {
    nodeCount: state.nodes.length,
    edges: normalizeEdgesForPayload(),
    zeroBased: state.zeroBased,
    pMax: parseInt(pMaxInput.value, 10),
    shots: parseInt(shotsInput.value, 10),
    maxIter: parseInt(maxIterInput.value, 10),
  };

  evaluateBtn.disabled = true;
  resultStatus.textContent = "Running QAOA evaluation...";

  try {
    const res = await fetch("/evaluate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Evaluation failed.");
    }

    const data = await res.json();
    resultStatus.textContent = `Results ready. Max-cut ${data.maxCut ?? "(n>12)"}`;

    data.results.forEach((result) => {
      if (result.mode === "star") {
        drawTree(starTree, state.nodes, result.treeEdges);
        renderHistogram(starHist, result.histogram);
        drawLineChart(starRatio, result.approxRatios);
      } else {
        drawTree(heurTree, state.nodes, result.treeEdges);
        renderHistogram(heurHist, result.histogram);
        drawLineChart(heurRatio, result.approxRatios);
      }
    });
  } catch (err) {
    resultStatus.textContent = err.message;
  } finally {
    evaluateBtn.disabled = false;
  }
}

canvas.addEventListener("click", (event) => {
  const rect = canvas.getBoundingClientRect();
  const x = ((event.clientX - rect.left) / rect.width) * canvas.width;
  const y = ((event.clientY - rect.top) / rect.height) * canvas.height;
  const idx = getNodeAt(x, y);
  if (idx !== null) {
    toggleSelection(idx);
    draw();
  }
});

addNodeBtn.addEventListener("click", addNode);
removeNodeBtn.addEventListener("click", removeNode);
addEdgeBtn.addEventListener("click", addEdge);
removeEdgeBtn.addEventListener("click", removeEdge);

evaluateBtn.addEventListener("click", evaluateGraph);

zeroBasedToggle.addEventListener("change", (event) => {
  state.zeroBased = event.target.checked;
  draw();
});

pMaxInput.addEventListener("input", (event) => {
  pMaxValue.textContent = event.target.value;
});

updateStatus();
