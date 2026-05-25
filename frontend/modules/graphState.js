export const nodeRadius = 18;

export const state = {
  nodes: [],
  edges: new Set(),
  selected: [],
  zeroBased: true,
  mode: "draw",
};

export function edgeKey(a, b) {
  const [u, v] = a < b ? [a, b] : [b, a];
  return `${u}-${v}`;
}

export function labelFor(index, zeroBased) {
  return index + (zeroBased ? 0 : 1);
}

export function setGraph(nodes, edges) {
  state.nodes = nodes;
  state.edges = new Set(edges);
  state.selected = [];
}

export function clearSelection() {
  state.selected = [];
}
