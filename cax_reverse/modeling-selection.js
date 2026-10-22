// Rectangle selection uses projected geometry, so empty corners of a curved
// object's bounding rectangle do not count as crossing the object itself.
export function intersectsRectangle(polygon, rectangle) {
  let clipped = polygon.map((p) => [...p]);
  const { left, right, top, bottom } = rectangle;
  for (const [axis, boundary, sign] of [[0, left, 1], [0, right, -1], [1, top, 1], [1, bottom, -1]]) {
    const input = clipped; clipped = [];
    if (!input.length) return false;
    for (let i = 0; i < input.length; i++) {
      const a = input[i], b = input[(i + 1) % input.length];
      const insideA = sign * (a[axis] - boundary) >= -1e-8, insideB = sign * (b[axis] - boundary) >= -1e-8;
      if (insideA) clipped.push(a);
      if (insideA !== insideB) {
        const t = (boundary - a[axis]) / (b[axis] - a[axis]);
        clipped.push(a.map((v, j) => v + (b[j] - v) * t));
      }
    }
  }
  return clipped.length > 0;
}
export function selectProjected(points, rectangle, windowMode, polyline = false) {
  if (!points.length) return false;
  const inside = ([x, y]) => x >= rectangle.left && x <= rectangle.right && y >= rectangle.top && y <= rectangle.bottom;
  if (windowMode) return points.every(inside);
  if (points.some(inside)) return true;
  for (let i = 0; i + (polyline ? 1 : 2) < points.length; i += polyline ? 1 : 3) {
    if (intersectsRectangle(points.slice(i, i + (polyline ? 2 : 3)), rectangle)) return true;
  }
  return false;
}
