import { edgeKey } from "./graphState.js";

export function parseEdgeList(text, zeroBased) {
  const edges = new Set();
  let maxLabel = -1;
  const errors = [];

  const lines = text.split(/\r?\n/);
  lines.forEach((line, index) => {
    const trimmed = line.trim();
    if (!trimmed) return;

    const matches = trimmed.match(/\d+/g);
    if (!matches || matches.length < 2) {
      errors.push(`Line ${index + 1}: expected two node labels.`);
      return;
    }

    const rawA = parseInt(matches[0], 10);
    const rawB = parseInt(matches[1], 10);

    if (!zeroBased && (rawA === 0 || rawB === 0)) {
      errors.push(`Line ${index + 1}: 1-based labels start at 1.`);
      return;
    }

    const a = zeroBased ? rawA : rawA - 1;
    const b = zeroBased ? rawB : rawB - 1;

    if (a < 0 || b < 0) {
      errors.push(`Line ${index + 1}: labels must be non-negative.`);
      return;
    }

    if (a === b) {
      errors.push(`Line ${index + 1}: self loops are not supported.`);
      return;
    }

    maxLabel = Math.max(maxLabel, a, b);
    edges.add(edgeKey(a, b));
  });

  const nodeCount = maxLabel + 1;
  return { edges, nodeCount, errors };
}
