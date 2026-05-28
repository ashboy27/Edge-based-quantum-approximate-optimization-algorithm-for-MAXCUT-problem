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
