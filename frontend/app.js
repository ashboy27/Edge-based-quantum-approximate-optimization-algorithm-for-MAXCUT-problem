import { state, edgeKey, setGraph, clearSelection } from "./modules/graphState.js";
import {
  buildCircularLayout,
  drawGraph,
  drawLineChart,
  drawTree,
  renderHistogram,
  resizeCanvas,
} from "./modules/graphRender.js";
import { parseEdgeList } from "./modules/graphParser.js";
import {
  buildSpanningTreeEdges,
  edgeCount,
  normalizeEdgesForPayload,
} from "./modules/graphAlgo.js";

const canvas = document.getElementById("graphCanvas");
const addNodeBtn = document.getElementById("addNodeBtn");
const removeNodeBtn = document.getElementById("removeNodeBtn");
const addEdgeBtn = document.getElementById("addEdgeBtn");
const removeEdgeBtn = document.getElementById("removeEdgeBtn");
const trainBtn = document.getElementById("trainBtn");
const zeroBasedToggle = document.getElementById("zeroBasedToggle");
const pMaxInput = document.getElementById("pMax");
const pMaxValue = document.getElementById("pMaxValue");
const shotsInput = document.getElementById("shots");
const maxIterInput = document.getElementById("maxIter");
const statusText = document.getElementById("statusText");
const resultStatus = document.getElementById("resultStatus");
const previewStatus = document.getElementById("previewStatus");
const edgeListInput = document.getElementById("edgeList");
const modeButtons = document.querySelectorAll(".mode-btn");
const modePanels = document.querySelectorAll(".mode-panel");
const previewSection = document.getElementById("previewSection");
const resultsSection = document.getElementById("resultsSection");
const previewTree = document.getElementById("previewTree");

const confirmModal = document.getElementById("confirmModal");
const cancelConfirm = document.getElementById("cancelConfirm");
const confirmTrain = document.getElementById("confirmTrain");
const loadingOverlay = document.getElementById("loadingOverlay");

const summaryMode = document.getElementById("summaryMode");
const summaryNodes = document.getElementById("summaryNodes");
const summaryEdges = document.getElementById("summaryEdges");
const summaryP = document.getElementById("summaryP");
const summaryShots = document.getElementById("summaryShots");

const starTree = document.getElementById("starTree");
const heurTree = document.getElementById("heurTree");
const starHist = document.getElementById("starHist");
const heurHist = document.getElementById("heurHist");
const starRatio = document.getElementById("starRatio");
const heurRatio = document.getElementById("heurRatio");

function updateStatus(message) {
  statusText.textContent =
    message || `${state.nodes.length} nodes, ${state.edges.size} edges.`;
}

function updatePreviewStatus(message) {
  previewStatus.textContent = message;
}

function refreshCanvas() {
  drawGraph(canvas, state.nodes, state.edges, state.selected, state.zeroBased);
}

function addNode() {
  const ctx = resizeCanvas(canvas, 520);
  const padding = 40;
  const x = padding + Math.random() * (ctx.canvas.clientWidth - padding * 2);
  const y = padding + Math.random() * (ctx.canvas.clientHeight - padding * 2);
  state.nodes.push({ x, y });
  updateStatus();
  refreshCanvas();
}

function removeNode() {
  if (state.selected.length !== 1) {
    updateStatus("Select one node to remove.");
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
  clearSelection();
  updateStatus();
  refreshCanvas();
}

function addEdge() {
  if (state.selected.length !== 2) {
    updateStatus("Select two nodes to add an edge.");
    return;
  }
  const [a, b] = state.selected;
  if (a === b) return;
  state.edges.add(edgeKey(a, b));
  updateStatus();
  refreshCanvas();
}

function removeEdge() {
  if (state.selected.length !== 2) {
    updateStatus("Select two nodes to remove an edge.");
    return;
  }
  const [a, b] = state.selected;
  state.edges.delete(edgeKey(a, b));
  updateStatus();
  refreshCanvas();
}

function getNodeAt(x, y) {
  const nodeRadius = 18;
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

function applyEdgeList() {
  const { edges, nodeCount, errors } = parseEdgeList(
    edgeListInput.value,
    state.zeroBased,
  );

  if (nodeCount === 0) {
    setGraph([], edges);
    updateStatus("Paste edges to build a graph.");
    refreshCanvas();
    return;
  }

  const nodes = buildCircularLayout(nodeCount, canvas);
  setGraph(nodes, edges);
  updateStatus(errors.length ? errors[0] : undefined);
  refreshCanvas();
}

function setMode(mode) {
  state.mode = mode;
  modeButtons.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.mode === mode);
  });
  modePanels.forEach((panel) => {
    panel.classList.toggle("is-hidden", panel.dataset.modePanel !== mode);
  });

  if (mode === "paste") {
    applyEdgeList();
  } else {
    updateStatus();
    refreshCanvas();
  }
}

function openConfirmModal() {
  summaryMode.textContent = state.mode === "draw" ? "Draw graph" : "Paste edges";
  summaryNodes.textContent = state.nodes.length.toString();
  summaryEdges.textContent = edgeCount(state.edges).toString();
  summaryP.textContent = pMaxInput.value;
  summaryShots.textContent = shotsInput.value;
  confirmModal.classList.add("is-open");
  confirmModal.setAttribute("aria-hidden", "false");
}

function closeConfirmModal() {
  confirmModal.classList.remove("is-open");
  confirmModal.setAttribute("aria-hidden", "true");
}

function setLoading(isLoading) {
  loadingOverlay.classList.toggle("is-open", isLoading);
  loadingOverlay.setAttribute("aria-hidden", isLoading ? "false" : "true");
}

function validateGraph() {
  if (state.nodes.length < 2) return "Add at least two nodes before training.";
  if (state.edges.size === 0) return "Add at least one edge before training.";
  return null;
}

function showPreviewTree() {
  const treeEdges = buildSpanningTreeEdges(state.nodes.length, state.edges);
  previewSection.hidden = false;
  updatePreviewStatus("Preview ready.");
  drawTree(previewTree, state.nodes, treeEdges, state.zeroBased);
}

async function trainGraph() {
  const payload = {
    nodeCount: state.nodes.length,
    edges: normalizeEdgesForPayload(state.edges, state.zeroBased),
    zeroBased: state.zeroBased,
    pMax: parseInt(pMaxInput.value, 10),
    shots: parseInt(shotsInput.value, 10),
    maxIter: parseInt(maxIterInput.value, 10),
  };

  trainBtn.disabled = true;
  resultStatus.textContent = "Training QAOA...";
  setLoading(true);

  try {
    const res = await fetch("/evaluate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Training failed.");
    }

    const data = await res.json();
    resultsSection.hidden = false;
    resultStatus.textContent = `Results ready. Max-cut ${data.maxCut ?? "(n>12)"}`;

    data.results.forEach((result) => {
      if (result.mode === "star") {
        drawTree(starTree, state.nodes, result.treeEdges, state.zeroBased);
        renderHistogram(starHist, result.histogram);
        drawLineChart(starRatio, result.approxRatios);
      } else {
        drawTree(heurTree, state.nodes, result.treeEdges, state.zeroBased);
        renderHistogram(heurHist, result.histogram);
        drawLineChart(heurRatio, result.approxRatios);
      }
    });
  } catch (err) {
    resultsSection.hidden = false;
    resultStatus.textContent = err.message;
  } finally {
    trainBtn.disabled = false;
    setLoading(false);
  }
}

canvas.addEventListener("click", (event) => {
  if (state.mode !== "draw") return;
  const rect = canvas.getBoundingClientRect();
  const x = ((event.clientX - rect.left) / rect.width) * canvas.width;
  const y = ((event.clientY - rect.top) / rect.height) * canvas.height;
  const idx = getNodeAt(x, y);
  if (idx !== null) {
    toggleSelection(idx);
    refreshCanvas();
  }
});

addNodeBtn.addEventListener("click", addNode);
removeNodeBtn.addEventListener("click", removeNode);
addEdgeBtn.addEventListener("click", addEdge);
removeEdgeBtn.addEventListener("click", removeEdge);

modeButtons.forEach((button) => {
  button.addEventListener("click", () => setMode(button.dataset.mode));
});

edgeListInput.addEventListener("input", () => {
  if (state.mode === "paste") applyEdgeList();
});

zeroBasedToggle.addEventListener("change", (event) => {
  state.zeroBased = event.target.checked;
  if (state.mode === "paste") {
    applyEdgeList();
  } else {
    refreshCanvas();
  }
});

pMaxInput.addEventListener("input", (event) => {
  pMaxValue.textContent = event.target.value;
});

trainBtn.addEventListener("click", () => {
  const error = validateGraph();
  if (error) {
    updateStatus(error);
    return;
  }
  openConfirmModal();
});

cancelConfirm.addEventListener("click", closeConfirmModal);
confirmTrain.addEventListener("click", () => {
  closeConfirmModal();
  showPreviewTree();
  trainGraph();
});

setMode("paste");
updateStatus("Paste edges to build a graph.");
