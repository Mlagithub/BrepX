import { state } from "./store.js";

export function renderAddMenu(select, catalog) {
  select.innerHTML = "";
  for (const entry of catalog) {
    const option = document.createElement("option");
    option.value = entry.type;
    option.textContent = entry.type;
    select.append(option);
  }
}

function button(label, title, handler) {
  const element = document.createElement("button");
  element.textContent = label;
  element.title = title;
  element.addEventListener("click", (event) => {
    event.stopPropagation();
    handler();
  });
  return element;
}

export function renderTree(root, handlers) {
  root.innerHTML = "";
  const features = state.doc?.features ?? [];

  features.forEach((feature) => {
    const item = document.createElement("li");
    item.className = "feature";
    if (state.selected === feature.id) item.classList.add("selected");
    if (!feature.enabled) item.classList.add("disabled");

    const info = document.createElement("div");
    const name = document.createElement("div");
    name.className = "name";
    name.textContent = feature.id;
    const type = document.createElement("div");
    type.className = "type";
    type.textContent = feature.type + (feature.note ? ` · ${feature.note}` : "");
    info.append(name, type);

    const buttons = document.createElement("div");
    buttons.className = "buttons";
    buttons.append(
      button(feature.enabled ? "○" : "●", "Toggle enabled", () => handlers.toggle(feature)),
      button("↑", "Move up", () => handlers.move(feature, -1)),
      button("↓", "Move down", () => handlers.move(feature, 1)),
      button("×", "Remove", () => handlers.remove(feature)),
    );

    item.append(info, buttons);
    item.addEventListener("click", () => handlers.select(feature.id));
    root.append(item);
  });

  if (!features.length) {
    const empty = document.createElement("li");
    empty.className = "type";
    empty.textContent = "No features yet. Add one or load the impeller sample.";
    root.append(empty);
  }
}
