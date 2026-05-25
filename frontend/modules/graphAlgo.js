import { edgeKey } from "./graphState.js";

export function buildSpanningTreeEdges(nodeCount, edges) {
  if (nodeCount === 0) return [];

  const adjacency = Array.from({ length: nodeCount }, () => []);
  for (const key of edges) {
    const [aStr, bStr] = key.split("-");
    const a = parseInt(aStr, 10);
    const b = parseInt(bStr, 10);
    adjacency[a].push(b);
    adjacency[b].push(a);
  }

  const visited = new Array(nodeCount).fill(false);
  const treeEdges = [];
  const queue = [0];
  visited[0] = true;

  while (queue.length) {
    const current = queue.shift();
    for (const next of adjacency[current]) {
      if (visited[next]) continue;
      visited[next] = true;
      treeEdges.push([current, next]);
      queue.push(next);
    }
  }

  return treeEdges;
}

export function normalizeEdgesForPayload(edges, zeroBased) {
  const base = zeroBased ? 0 : 1;
  return Array.from(edges).map((key) => {
    const [aStr, bStr] = key.split("-");
    const a = parseInt(aStr, 10) + base;
    const b = parseInt(bStr, 10) + base;
    return [a, b];
  });
}

export function edgeCount(edges) {
  return edges instanceof Set ? edges.size : edges.length;
}
