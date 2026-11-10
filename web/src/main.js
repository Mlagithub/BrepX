import { api } from "./api.js";
import { state, update, subscribe, featureById, catalogEntry } from "./store.js";
import { initViewport, setScene } from "./viewport.js";
import { renderTree, renderAddMenu } from "./tree.js";
import { renderParams } from "./params.js";
import { renderPreview } from "./review.js";

const el = (id) => document.getElementById(id);

function statusText() {
  let text = state.status;
  if (state.selection) {
    text += ` · face ${state.selection.index} · area ${state.selection.area.toFixed(1)}`;
  }
  return text;
}

function describe(error) {
  const hint = error.hint ? ` — ${error.hint}` : "";
  return `${error.code ?? "ERROR"}: ${error.message}${hint}`;
}

async function refresh() {
  state.doc = await api.getDoc(state.doc.id);
  state.selected = featureById(state.selected)
    ? state.selected
    : (state.doc.features[0]?.id ?? null);
  state.preview = null;
  state.scene = await api.scene(state.doc.id);
  setScene(state.scene);
  update({});
}

async function run(action, success = "ok") {
  update({ busy: true });
  try {
    await action();
    await refresh();
    update({ status: success, error: false, busy: false });
  } catch (error) {
    if (error.status === 409) {
      try { await refresh(); } catch { /* keep the original error */ }
    }
    update({ status: describe(error), error: true, busy: false });
  }
}

async function applyOps(ops) {
  await run(() => api.edit(state.doc.id, state.doc.version, ops));
}

function defaultParams(type) {
  const entry = catalogEntry(type);
  if (!entry) return {};
  const params = {};
  for (const [name, spec] of Object.entries(entry.params)) params[name] = spec.default;
  return params;
}

function ref(source, select, filters = []) {
  return { source, select, filters };
}

function autoRefs(type) {
  const features = state.doc.features.filter((feature) => feature.enabled);
  const last = features[features.length - 1];
  switch (type) {
    case "pattern_circular":
      return last ? { target: ref(last.id, "self") } : null;
    case "boolean":
      if (features.length < 2) return null;
      return { target: ref(features[0].id, "self"), tool: ref(last.id, "self") };
    case "fillet":
      return last ? {
        target: ref(last.id, "self"),
        edges: ref(last.id, "edges", [{ method: "nearest", args: [[44, 0, 20]] }]),
      } : null;
    case "tag_boundary":
      return last ? {
        target: ref(last.id, "self"),
        faces: ref(last.id, "faces", [{ method: "largest" }]),
      } : null;
    case "cavity_extraction":
      return last ? { target: ref(last.id, "self") } : null;
    default:
      return {};
  }
}

function nextId(features) {
  let value = 0;
  for (const feature of features) {
    const match = /^f(\d+)$/.exec(feature.id);
    if (match) value = Math.max(value, Number(match[1]));
  }
  return `f${value + 1}`;
}

async function addFeature(type) {
  const refs = autoRefs(type);
  if (refs === null) {
    update({ status: `${type} needs at least two features first`, error: true });
    return;
  }
  const feature = {
    id: nextId(state.doc.features),
    type,
    params: defaultParams(type),
    refs,
  };
  await applyOps([{ op: "add", feature }]);
}

async function toggle(feature) {
  await applyOps([{ op: "update", id: feature.id, enabled: !feature.enabled }]);
}

async function remove(feature) {
  await applyOps([{ op: "remove", id: feature.id }]);
}

async function move(feature, delta) {
  const features = state.doc.features;
  const index = features.findIndex((item) => item.id === feature.id);
  const target = index + delta;
  if (target < 0 || target >= features.length) return;
  const before = delta < 0 ? features[target].id : (features[target + 1]?.id ?? null);
  await applyOps([{ op: "reorder", id: feature.id, before }]);
}

async function preview(op) {
  update({ busy: true });
  try {
    const result = await api.preview(state.doc.id, [op]);
    update({ preview: { ops: [op], result }, status: "preview ready", error: false, busy: false });
  } catch (error) {
    update({ status: describe(error), error: true, busy: false });
  }
}

async function applyPreview() {
  if (!state.preview) return;
  const ops = state.preview.ops;
  await applyOps(ops);
}

function renderChecks(root) {
  root.innerHTML = "";
  const features = state.doc.build?.features ?? [];
  let failures = 0;
  for (const item of features) {
    for (const check of item.checks ?? []) {
      const row = document.createElement("div");
      row.className = "check " + (check.ok ? "ok" : "bad");
      row.textContent = `${item.id} ${check.name} ${check.ok ? "ok" : "FAILED"}`;
      if (!check.ok) failures += 1;
      root.append(row);
    }
  }
  if (!features.length) {
    root.textContent = "Nothing built.";
    return;
  }
  if (!failures) {
    const row = document.createElement("div");
    row.className = "check ok";
    row.textContent = "all checks pass";
    root.prepend(row);
  }
}

function render(stateNow) {
  const doc = stateNow.doc;
  if (!doc) return;
  el("doc-meta").textContent = `${doc.name} · v${doc.version} · ${doc.features.length} features`;
  el("btn-step").href = api.exportUrl(doc.id, "step");
  el("btn-cfd").href = api.exportUrl(doc.id, "cfd");
  el("btn-render").href = api.renderUrl(doc.id);
  renderTree(el("feature-list"), {
    select: (id) => update({ selected: id }),
    toggle,
    remove,
    move,
  });
  renderParams(el("params"), { preview, apply: (op) => applyOps([op]) });
  renderPreview(el("preview"), {
    apply: applyPreview,
    cancel: () => update({ preview: null }),
  });
  renderChecks(el("checks"));
  el("status").textContent = statusText();
  el("status").classList.toggle("error", Boolean(stateNow.error));
  el("btn-undo").disabled = stateNow.busy;
  el("btn-add").disabled = stateNow.busy;
  el("btn-new").disabled = stateNow.busy;
  el("btn-sample").disabled = stateNow.busy;
}

async function boot() {
  const docs = await api.listDocs();
  state.doc = docs.length ? await api.getDoc(docs[0].id) : await api.createDoc("Workbench");
  state.catalog = await api.catalog();
  state.selected = state.doc.features[0]?.id ?? null;
  window.cadwork = { state, api };

  initViewport(el("viewport"), (hit) => {
    state.selection = hit;
    el("status").textContent = statusText();
  });
  renderAddMenu(el("add-type"), state.catalog);

  el("btn-add").addEventListener("click", () => addFeature(el("add-type").value));
  el("btn-new").addEventListener("click", () => run(async () => {
    state.doc = await api.createDoc("Workbench");
    state.selected = null;
    state.preview = null;
  }, "new document"));
  el("btn-sample").addEventListener("click", () => run(
    () => api.loadImpeller(state.doc.id), "impeller loaded",
  ));
  el("btn-undo").addEventListener("click", () => run(
    () => api.undo(state.doc.id), "undone",
  ));

  subscribe(render);
  state.scene = await api.scene(state.doc.id);
  setScene(state.scene);
  update({ status: `ready · smlibpy-backed document ${state.doc.id}` });
}

boot().catch((error) => {
  update({ status: describe(error), error: true });
  subscribe(render);
});
