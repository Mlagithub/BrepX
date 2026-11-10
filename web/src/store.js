const listeners = new Set();

export const state = {
  doc: null,
  catalog: [],
  scene: null,
  selected: null,
  selection: null,
  preview: null,
  busy: false,
  error: false,
  status: "ready",
};

export function update(patch) {
  Object.assign(state, patch);
  for (const listener of listeners) listener(state);
}

export function subscribe(listener) {
  listeners.add(listener);
  listener(state);
  return () => listeners.delete(listener);
}

export function featureById(id) {
  return state.doc?.features.find((feature) => feature.id === id) ?? null;
}

export function catalogEntry(type) {
  return state.catalog.find((entry) => entry.type === type) ?? null;
}
