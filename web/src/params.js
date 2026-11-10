import { state, featureById, catalogEntry } from "./store.js";

function field(name, spec, current) {
  const row = document.createElement("div");
  row.className = "param";

  const label = document.createElement("label");
  const title = document.createElement("span");
  title.textContent = name;
  const unit = document.createElement("span");
  unit.textContent = spec.unit ?? "";
  label.append(title, unit);

  let input;
  if (spec.kind === "bool") {
    input = document.createElement("input");
    input.type = "checkbox";
    input.checked = Boolean(current);
  } else if (spec.choices?.length) {
    input = document.createElement("select");
    for (const choice of spec.choices) {
      const option = document.createElement("option");
      option.value = choice;
      option.textContent = choice;
      input.append(option);
    }
    input.value = current;
  } else {
    input = document.createElement("input");
    input.type = spec.kind === "str" ? "text" : "number";
    if (spec.kind !== "str") input.step = "any";
    input.value = current;
  }
  input.dataset.name = name;
  row.append(label, input);
  return { row, input, spec };
}

function collect(fields) {
  const params = {};
  for (const [name, entry] of Object.entries(fields)) {
    const { input, spec } = entry;
    if (spec.kind === "bool") params[name] = input.checked;
    else if (spec.kind === "int") params[name] = parseInt(input.value, 10);
    else if (spec.kind === "float") params[name] = parseFloat(input.value);
    else params[name] = input.value;
  }
  return params;
}

export function renderParams(root, handlers) {
  root.innerHTML = "";
  const feature = featureById(state.selected);
  if (!feature) {
    root.textContent = "Select a feature.";
    return;
  }
  const entry = catalogEntry(feature.type);
  if (!entry) {
    root.textContent = `No schema for ${feature.type}.`;
    return;
  }

  const form = document.createElement("form");
  form.addEventListener("submit", (event) => event.preventDefault());
  const fields = {};
  for (const [name, spec] of Object.entries(entry.params)) {
    const current = feature.params[name] ?? spec.default;
    const built = field(name, spec, current);
    fields[name] = built;
    form.append(built.row);
  }

  const actions = document.createElement("div");
  actions.className = "param-actions";
  const preview = document.createElement("button");
  preview.type = "button";
  preview.textContent = "Preview";
  preview.addEventListener("click", () => handlers.preview({
    op: "update", id: feature.id, params: collect(fields),
  }));
  const apply = document.createElement("button");
  apply.type = "button";
  apply.className = "primary";
  apply.textContent = "Apply";
  apply.addEventListener("click", () => handlers.apply({
    op: "update", id: feature.id, params: collect(fields),
  }));
  actions.append(preview, apply);
  form.append(actions);
  root.append(form);
}
