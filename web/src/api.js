const BASE = "/api";

export class ApiError extends Error {
  constructor(payload, status) {
    super(payload?.message || `HTTP ${status}`);
    this.code = payload?.code || "HTTP_ERROR";
    this.status = status;
    this.hint = payload?.hint || null;
    this.detail = payload || {};
  }
}

async function request(path, options = {}) {
  const response = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) throw new ApiError(data?.error, response.status);
  return data;
}

export const api = {
  catalog: () => request("/catalog"),
  listDocs: () => request("/docs"),
  createDoc: (name) => request("/docs", {
    method: "POST", body: JSON.stringify({ name }),
  }),
  getDoc: (id) => request(`/docs/${id}`),
  scene: (id) => request(`/docs/${id}/scene`),
  edit: (id, baseVersion, ops) => request(`/docs/${id}`, {
    method: "PUT",
    body: JSON.stringify({ base_version: baseVersion, ops }),
  }),
  preview: (id, ops) => request(`/docs/${id}/preview`, {
    method: "POST", body: JSON.stringify({ ops }),
  }),
  undo: (id) => request(`/docs/${id}/undo`, { method: "POST" }),
  loadImpeller: (id, count = 9) => request(
    `/docs/${id}/sample/impeller?count=${count}`, { method: "POST" },
  ),
  exportUrl: (id, fmt) => `${BASE}/docs/${id}/export/${fmt}`,
  renderUrl: (id) => `${BASE}/docs/${id}/render.png`,
};
