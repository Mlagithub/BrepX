import { state } from "./store.js";

export function renderPreview(root, handlers) {
  root.hidden = !state.preview;
  root.innerHTML = "";
  if (!state.preview) return;

  const result = state.preview.result;
  const heading = document.createElement("h3");
  heading.textContent = "Pending edit";
  root.append(heading);

  const diff = result.diff ?? {};
  const parts = [];
  if (diff.added?.length) parts.push(`added ${diff.added.join(", ")}`);
  if (diff.removed?.length) parts.push(`removed ${diff.removed.join(", ")}`);
  if (diff.changed?.length) parts.push(`changed ${diff.changed.join(", ")}`);

  const line = document.createElement("div");
  line.className = "diff";
  line.textContent = parts.length ? parts.join(" · ") : "no structural change";
  const timing = document.createElement("div");
  timing.className = "diff";
  timing.textContent = `build ${(result.build?.seconds ?? 0).toFixed(2)}s`;
  root.append(line, timing);

  const actions = document.createElement("div");
  actions.className = "param-actions";
  const apply = document.createElement("button");
  apply.className = "primary";
  apply.textContent = "Apply";
  apply.addEventListener("click", handlers.apply);
  const cancel = document.createElement("button");
  cancel.textContent = "Cancel";
  cancel.addEventListener("click", handlers.cancel);
  actions.append(apply, cancel);
  root.append(actions);
}
