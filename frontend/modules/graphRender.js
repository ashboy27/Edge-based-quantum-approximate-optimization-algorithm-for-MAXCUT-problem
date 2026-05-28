import { edgeKey, labelFor, nodeRadius } from "./graphState.js";

export function resizeCanvas(canvasEl, heightFallback) {
  const ratio = window.devicePixelRatio || 1;
  const cssWidth = canvasEl.clientWidth || canvasEl.width;
  const cssHeight = canvasEl.clientHeight || heightFallback || canvasEl.height;
  canvasEl.width = Math.floor(cssWidth * ratio);
  canvasEl.height = Math.floor(cssHeight * ratio);
  const ctx = canvasEl.getContext("2d");
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  return ctx;
}

export function drawEdges(targetCtx, edges, nodes, color) {
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

export function drawNodes(targetCtx, nodes, selected, zeroBased) {
  targetCtx.font = "600 13px 'Space Grotesk', sans-serif";
  targetCtx.textAlign = "center";
  targetCtx.textBaseline = "middle";

  nodes.forEach((n, i) => {
    const isSelected = selected.includes(i);
    const label = labelFor(i, zeroBased).toString();
    targetCtx.fillStyle = isSelected ? "#121111" : "#ffffff";
    targetCtx.strokeStyle = "#121111";
    targetCtx.lineWidth = isSelected ? 3 : 2;
    targetCtx.beginPath();
    targetCtx.arc(n.x, n.y, nodeRadius, 0, Math.PI * 2);
    targetCtx.fill();
    targetCtx.stroke();

    targetCtx.fillStyle = isSelected ? "#ffffff" : "#121111";
    targetCtx.fillText(label, n.x, n.y + 1);
  });
}

export function drawGraph(canvasEl, nodes, edges, selected, zeroBased) {
  const ctx = resizeCanvas(canvasEl, 520);
  ctx.clearRect(0, 0, canvasEl.clientWidth, canvasEl.clientHeight);
  drawEdges(ctx, edges, nodes, "#121111");
  drawNodes(ctx, nodes, selected, zeroBased);
}

export function drawTree(canvasEl, nodes, treeEdges, zeroBased) {
  const tctx = resizeCanvas(canvasEl, 240);
  const width = canvasEl.clientWidth;
  const height = canvasEl.clientHeight;
  tctx.clearRect(0, 0, width, height);

  if (!nodes.length) return;

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
  drawEdges(tctx, edges, mapped, "#121111");

  tctx.font = "600 12px 'Space Grotesk', sans-serif";
  tctx.textAlign = "center";
  tctx.textBaseline = "middle";

  mapped.forEach((n, i) => {
    tctx.fillStyle = "#ffffff";
    tctx.strokeStyle = "#121111";
    tctx.lineWidth = 2;
    tctx.beginPath();
    tctx.arc(n.x, n.y, 10, 0, Math.PI * 2);
    tctx.fill();
    tctx.stroke();

    tctx.fillStyle = "#121111";
    tctx.fillText(labelFor(i, zeroBased).toString(), n.x, n.y + 1);
  });
}

export function drawLineChart(canvasEl, values) {
  const lctx = resizeCanvas(canvasEl, 160);
  lctx.clearRect(0, 0, canvasEl.clientWidth, canvasEl.clientHeight);

  const padding = 32;
  const pointRadius = 4.5;
  const w = canvasEl.clientWidth - padding * 2;
  const h = canvasEl.clientHeight - padding * 2;
  const vals = values.map((v) => (v === null ? 0 : v));

  const clamp = (val, min, max) => Math.min(Math.max(val, min), max);

  lctx.strokeStyle = "#121111";
  lctx.lineWidth = 1;
  lctx.beginPath();
  // left axis
  lctx.moveTo(padding, padding);
  lctx.lineTo(padding, padding + h);
  // bottom axis
  lctx.moveTo(padding, padding + h);
  lctx.lineTo(padding + w, padding + h);
  lctx.stroke();

  // Y-axis ticks and labels (0.00 .. 1.00)
  lctx.fillStyle = "#121111";
  lctx.font = "500 11px 'Space Grotesk', sans-serif";
  lctx.textAlign = "right";
  lctx.textBaseline = "middle";
  const tickCount = 4; // will show 0,0.25,0.5,0.75,1
  for (let ti = 0; ti <= tickCount; ti += 1) {
    const v = ti / tickCount;
    const yy = padding + h - v * h;
    // small tick
    lctx.beginPath();
    lctx.moveTo(padding - 6, yy);
    lctx.lineTo(padding, yy);
    lctx.stroke();
    // label
    lctx.fillText(v.toFixed(2), padding - 8, yy);
  }

  lctx.beginPath();
  vals.forEach((v, i) => {
    // clamp input values to [0,1]
    const vv = Math.min(Math.max(v, 0), 1);
    const x = padding + (w * i) / (vals.length - 1 || 1);
    const y = padding + h - (vv - 0) / (1 - 0 || 1) * h;
    const safeX = clamp(x, padding + pointRadius, padding + w - pointRadius);
    const safeY = clamp(y, padding + pointRadius, padding + h - pointRadius);
    if (i === 0) lctx.moveTo(safeX, safeY);
    else lctx.lineTo(safeX, safeY);
  });

  lctx.strokeStyle = "#d18c6c";
  lctx.lineWidth = 2.5;
  lctx.stroke();

  lctx.fillStyle = "#1b4b7a";
  lctx.font = "600 11px 'Space Grotesk', sans-serif";
  vals.forEach((v, i) => {
    const vv = Math.min(Math.max(v, 0), 1);
    const x = padding + (w * i) / (vals.length - 1 || 1);
    const y = padding + h - (vv - 0) / (1 - 0 || 1) * h;
    const safeX = clamp(x, padding + pointRadius, padding + w - pointRadius);
    const safeY = clamp(y, padding + pointRadius, padding + h - pointRadius);
    lctx.beginPath();
    lctx.arc(safeX, safeY, pointRadius, 0, Math.PI * 2);
    lctx.fill();

    const label = `p${i + 1}`;
    lctx.textAlign = "center";
    lctx.textBaseline = "top";
    lctx.fillText(label, safeX, padding + h + 6);
  });
}

export function renderHistogram(container, histogram) {
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

export function buildCircularLayout(count, canvasEl) {
  const width = canvasEl.clientWidth || canvasEl.width;
  const height = canvasEl.clientHeight || canvasEl.height;
  const radius = Math.max(40, Math.min(width, height) / 2 - 40);
  const centerX = width / 2;
  const centerY = height / 2;
  const nodes = [];

  for (let i = 0; i < count; i += 1) {
    const angle = (Math.PI * 2 * i) / Math.max(count, 1) - Math.PI / 2;
    nodes.push({
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
    });
  }

  return nodes;
}
