import { setModelingHTML, setModelingText } from './modeling-i18n.js';
import { isPrimitive, MODEL_NAMES } from "./modeling-state.js";
const icons = {
  open: '<path d="M3 8h7l2 3h12l-3 12H3z" fill="#ebf1f9"/><path d="M3 8V5h8l3 3h8v3"/>',
  save: '<path d="M4 3h17l3 3v19H4z" fill="#ebf1f9"/><path d="M9 3v8h11V3M8 25V15h12v10M17 4v5"/>',
  export: '<path d="M5 3h11l5 5v6M16 3v6h5M5 3v22h16v-6"/><path d="M13 17h12m-4-4 4 4-4 4" stroke="#3787c8"/>',
  undo: '<path d="m10 5-6 6 6 5M4 11h12a7 7 0 0 1 0 14"/>',
  redo: '<path d="m18 5 6 6-6 5M24 11H12a7 7 0 0 0 0 14"/>',
  select: '<path d="M6 3v21l5-6 5 8 4-2-5-8h8z" fill="#ebf1f9"/>',
  move: '<path d="M14 2v24M2 14h24m-16-8 4-4 4 4M10 22l4 4 4-4M6 10l-4 4 4 4M22 10l4 4-4 4"/>',
  resize: '<path d="M7 7h13v13H7z" fill="#ebf1f9"/><path d="m3 3 5 1-4 4-1-5M25 25l-5-1 4-4 1 5M5 5l18 18" stroke="#3787c8"/>',
  height: '<path d="M4 24h14V12H4z" fill="#ebf1f9"/><path d="M23 3v21m-4-17 4-4 4 4m-8 13 4 4 4-4"/>',
  rotate: '<path d="M6 9a10 10 0 1 1-1 10M6 3v7H0"/><path d="M10 11h8v8h-8z" fill="#ebf1f9"/>',
  scale: '<path d="M3 18h7v7H3zM13 3h12v12H13z" fill="#ebf1f9"/><path d="m9 17 10-9m-5 0h5v5"/>',
  delete: '<path d="M5 7h18M10 3h8v4M7 7l1 18h12l1-18M11 11v10M17 11v10"/>',
  box: '<path d="m4 9 10-6 10 6v13l-10 5-10-5z" fill="#ebf1f9"/><path d="m4 9 10 5 10-5M14 14v13"/>',
  cylinder: '<path d="M5 7v15c0 5 18 5 18 0V7" fill="#ebf1f9"/><ellipse cx="14" cy="7" rx="9" ry="4"/><path d="M5 22c0-5 18-5 18 0" stroke-dasharray="2 2"/>',
  sphere: '<circle cx="14" cy="14" r="11" fill="#ebf1f9"/><ellipse cx="14" cy="14" rx="5" ry="11"/><ellipse cx="14" cy="14" rx="11" ry="4"/>',
  cone: '<path d="m14 3-10 19c0 5 20 5 20 0L14 3z" fill="#ebf1f9"/><path d="M4 22c0-5 20-5 20 0" stroke-dasharray="2 2"/>',
  torus: '<path d="M3 12v3a11 6 0 0 0 22 0v-3M9 12v2c0 2 10 2 10 0v-2"/><path d="M25 12a11 6 0 1 1-22 0 11 6 0 1 1 22 0ZM19 12a5 2.5 0 1 1-10 0 5 2.5 0 1 1 10 0Z" fill="#ebf1f9" fill-rule="evenodd"/>',
  hole: '<path d="M3 6h22v19H3z" fill="#ebf1f9"/><ellipse cx="14" cy="14" rx="6" ry="4"/><path d="M8 14v5c0 4 12 4 12 0v-5"/>',
  fit: '<path d="M3 10V3h7M18 3h7v7M25 18v7h-7M10 25H3v-7M9 9h10v10H9z"/>',
};
export function installModelingUI({ getState, restore, selectModel, setTool, fitView, onSettingsVisibilityChange }) {
  installDockResizing();
  for (const button of document.querySelectorAll("[data-icon]")) {
    const label = button.textContent;
    setModelingHTML(button,`<svg class="tool-icon" viewBox="0 0 28 28" aria-hidden="true" fill="none" stroke="#466eaa" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${icons[button.dataset.icon]}</svg><span>${label}</span>`);
  }
  const select = document.querySelector("#mouse-tool");
  const names = { box: "长方体", cylinder: "圆柱", sphere: "球体" };
  const context = document.querySelector("#viewport-context");
  const canvas = document.querySelector("canvas");
  let rightStart;
  let lastHistory = "";
  function closeMenus() { context.hidden = true; }
  function syncPanelButtons() {
    for (const button of document.querySelectorAll("[data-panel-toggle]")) {
      button.setAttribute("aria-controls", button.dataset.panelToggle);
      button.setAttribute("aria-expanded", String(!document.getElementById(button.dataset.panelToggle).hidden));
    }
  }
  function markTools() {
    for (const button of document.querySelectorAll("[data-tool]")) button.setAttribute("aria-pressed", String(button.dataset.tool === select.value));
  }
  function refresh() {
    const s = getState(), disabled = s.busy || !s.initialized;
    const solidSelection = s.selections.filter((item) => item.type === "solid"), editable = solidSelection.length === 1 && s.selections.length === 1;
    for (const button of document.querySelectorAll("[data-transform]")) button.disabled = disabled || !solidSelection.length || solidSelection.length !== s.selections.length;
    for (const button of document.querySelectorAll("[data-select-tool]")) { button.disabled = disabled; button.setAttribute("aria-pressed", String(s.boxSelection && button.dataset.selectTool === "box")); }
    for (const button of document.querySelectorAll("[data-tool]")) button.disabled = disabled || (["move", "resize", "height", "hole"].includes(button.dataset.tool) && ((button.dataset.tool === "move" ? !solidSelection.length || solidSelection.length !== s.selections.length : !editable) || !s.model || (button.dataset.tool === "hole" && s.model.kind !== "box") || (["resize", "height", "hole"].includes(button.dataset.tool) && !isPrimitive(s.model)) || (button.dataset.tool === "height" && s.model.kind === "sphere")));
    for (const button of document.querySelectorAll("[data-view-action], [data-focus], #show-modeling-settings")) button.disabled = disabled;
    document.querySelector("#delete-model").disabled = disabled || !solidSelection.length || solidSelection.length !== s.selections.length;
    for (const button of document.querySelectorAll("[data-action]")) {
      const original = document.getElementById(button.dataset.action);
      if (original) button.disabled = original.disabled;
    }
    const tree = document.querySelector("#tree-model");
    document.querySelector("#tree-empty").hidden = !!s.project.objects.length;
    const branch = document.querySelector("#project-tree");
    for (const extra of branch.querySelectorAll("[data-object-id]")) if (extra !== tree) extra.remove();
    tree.hidden = !s.project.objects.length;
    s.project.objects.forEach((object, index) => {
      const row = index === 0 ? tree : document.createElement("button");
      row.setAttribute("role", "treeitem"); row.dataset.objectId = object.id;
      const objectName = document.createElement("span"), visibility = document.createElement("span");
      objectName.dataset.modelingUserText = ""; objectName.textContent = object.name;
      setModelingText(visibility, object.visible ? "" : " · 隐藏");
      row.replaceChildren("◇ ", objectName, visibility);
      row.setAttribute("aria-selected", String(s.selections.some((item) => item.objectId === object.id)));
      row.disabled = disabled;
      if (index) branch.append(row);
    });
    setModelingText(document.querySelector("#property-selection"),s.selections.length > 1 ? `已选 ${s.selections.length} 项` : s.selectedEdgeId ? `边 ${s.selectedEdgeId}` : s.selectedFaceId ? `面 ${s.selectedFaceId}` : s.selected && s.model ? s.project.objects.find((o) => o.id === s.activeId)?.name : "未选择",{preserve:s.selected&&!s.selectedFaceId&&!s.selectedEdgeId&&s.selections.length===1});
    for (const button of document.querySelectorAll("[data-selection-mode]")) {
      button.disabled = disabled; button.setAttribute("aria-pressed", String(button.dataset.selectionMode === s.selectionMode));
    }
    const format = (value) => value==null?'—':Array.isArray(value) ? value.map((v) => v.toFixed(6)).join(", ") : typeof value === "number" ? value.toFixed(6) : String(value);
    let properties = [["选择", "未选择对象"]];
    const face = s.faces.find((f) => f.id === s.selectedFaceId), edge = s.topology.edges.find((e) => e.id === s.selectedEdgeId);
    if (edge) {
      properties = [["对象", `边 ${edge.id}`], ["曲线类型", edge.kind === "line" ? "直线" : edge.kind === "circle" ? "圆弧" : "曲线（边捕捉采用采样）"], ["长度 (mm)", edge.length], ["中点 (mm)", edge.midpoint], ["相邻面", edge.faceIds.join(", ")], ["接缝", edge.isSeam ? "是" : "否"]];
      if (edge.radius) properties.push(["半径 (mm)", edge.radius]);
      if (edge.start) properties.push(["起点 (mm)", edge.start], ["终点 (mm)", edge.end]);
    } else if (face) {
      properties = [["对象", `面 ${face.id}`], ["曲面类型", face.surfaceType], ["面积 (mm²)", face.area], ["形心 (mm)", face.center]];
      if (face.surface.radius) properties.push(["半径 (mm)", face.surface.radius]);
    } else if (s.selected && s.model && s.metrics) {
      properties = [["对象", s.project.objects.find((o) => o.id === s.activeId)?.name], ["类型", s.metrics.dimension === 0 ? "点集" : s.metrics.dimension === 1 ? "曲线" : s.metrics.dimension === 2 ? "曲面" : "实体"], ["体积 (mm³)", s.metrics.volume], ["表面积 (mm²)", s.metrics.area], ["质心 (mm)", s.metrics.center], ["面数", s.faces.length], ["边数", s.topology.edges.length], ["拓扑指针检查", s.metrics.valid ? "通过" : "失败"], ["位置 (mm)", [s.model.x, s.model.y, s.model.z]], ["旋转 (°)", s.model.angle], ["缩放", s.model.scale]];
      if (s.metrics.dimension === 1) properties.push(["总长度 (mm)", s.metrics.length]);
      if (s.model.kind === "box") properties.push(["长宽高 (mm)", [s.model.length, s.model.width, s.model.height]]);
      else if (isPrimitive(s.model)) { properties.push(["半径 (mm)", s.model.radius]); if (s.model.kind === "cylinder") properties.push(["高度 (mm)", s.model.height]); }
      else {
        properties.push(["建模特征", MODEL_NAMES[s.model.kind]]);
        if (s.model.kind === "boolean") properties.push(["运算", { fuse: "并集", cut: "差集", common: "交集", xor: "异或" }[s.model.operation]], ["输入实体数", s.model.operands.length]);
        if (s.model.kind === "sweep") properties.push(["截面", s.model.profile.kind === "circle" ? `圆形 R${s.model.profile.radius}` : `矩形 ${s.model.profile.width} × ${s.model.profile.height}`], ["路径点数", s.model.path.length]);
        if (["chamfer", "fillet"].includes(s.model.kind)) properties.push([s.model.kind === "chamfer" ? "倒角距离 (mm)" : "圆角半径 (mm)", s.model.size], ["基体边编号", s.model.edges.join(", ")]);
      }
      if (s.model.hole) properties.push(["孔径 (mm)", s.model.diameter], ["孔中心偏移 (mm)", [s.model.holeX, s.model.holeY]]);
    }
    if (s.selections.length > 1) {
      properties = [["选择", `${s.selections.length} 项`], ["对象数", solidSelection.length]];
      if (solidSelection.length === s.selections.length && s.objects.filter(o=>solidSelection.some(item=>item.objectId===o.object.id)).every(o=>o.metrics.dimension===3)) properties.push(["总体积 (mm³)", s.objects.filter((o) => solidSelection.some((item) => item.objectId === o.object.id)).reduce((sum, o) => sum + o.metrics.volume, 0)]);
    }
    const attributes = document.querySelector("#object-appearance"); attributes.disabled = disabled || !editable;
    const object = editable && s.project.objects.find((o) => o.id === solidSelection[0].objectId);
    // Keep submitted values in place while the previous history is still displayed.
    if (object && !s.busy) {
      document.querySelector("#object-name").value = object.name; document.querySelector("#object-color").value = object.color;
      document.querySelector("#object-opacity").value = 1 - object.opacity; document.querySelector("#object-visible").checked = object.visible;
    } else if (!s.busy) {
      document.querySelector("#object-name").value = "";
      document.querySelector("#object-color").value = document.querySelector("#object-color").defaultValue;
      document.querySelector("#object-opacity").value = document.querySelector("#object-opacity").defaultValue;
      document.querySelector("#object-visible").checked = document.querySelector("#object-visible").defaultChecked;
    }
    document.querySelector("#selection-properties").replaceChildren(...properties.flatMap(([name, value]) => {
      const term = document.createElement("dt"), description = document.createElement("dd");
      setModelingText(term,name); setModelingText(description,format(value),{preserve:name==="对象"}); description.dataset.property = name; return [term, description];
    }));
    setModelingText(document.querySelector("#document-state"),s.project.objects.length ? `${s.project.objects.length} 个对象` : "空场景");
    const signature = JSON.stringify([s.history.index, s.history.version, disabled]);
    if (signature !== lastHistory) {
      lastHistory = signature;
      const list = document.querySelector("#history-list");
      list.replaceChildren(...s.history.entries.map((entry, index) => {
        const row = document.createElement("li"), button = document.createElement("button"), detail = document.createElement("small");
        setModelingText(button,`${index + 1}. ${entry.objects.length ? `${entry.objects.length} 个对象` : "空场景"}`);
        setModelingText(detail,index === s.history.index ? "当前" : index > s.history.index ? "待重做" : "");
        button.append(detail); button.dataset.historyIndex = String(index);
        button.setAttribute("aria-current", index === s.history.index ? "step" : "false");
        button.classList.toggle("history-future", index > s.history.index);
        button.disabled = disabled || index === s.history.index;
        button.addEventListener("click", () => restore(index)); row.append(button); return row;
      }));
      list.querySelector('[aria-current="step"]')?.scrollIntoView({ block: "nearest" });
    }
    markTools(); syncPanelButtons();
  }
  for (const button of document.querySelectorAll("[data-tool]")) button.addEventListener("click", () => { closeMenus(); setTool(button.dataset.tool); markTools(); });
  for (const button of document.querySelectorAll("[data-action]")) button.addEventListener("click", () => { closeMenus(); document.getElementById(button.dataset.action)?.click(); });
  for (const button of document.querySelectorAll("[data-view-action]")) button.addEventListener("click", () => { closeMenus(); fitView(button.dataset.viewAction); });
  const settingsDialog = document.querySelector("#modeling-settings-dialog");
  function openSettings(id = "workplane-z") {
    closeMenus();
    if (!settingsDialog.open) settingsDialog.showModal();
    onSettingsVisibilityChange();
    const input = settingsDialog.querySelector(`#${id}`);
    input?.focus(); input?.select();
  }
  document.querySelector("#show-modeling-settings").addEventListener("click", () => openSettings());
  document.querySelector("#close-modeling-settings").addEventListener("click", () => settingsDialog.close());
  settingsDialog.addEventListener("close", onSettingsVisibilityChange);
  for (const button of document.querySelectorAll("[data-focus]")) button.addEventListener("click", () => openSettings(button.dataset.focus));
  for (const button of document.querySelectorAll("[data-panel-toggle]")) button.addEventListener("click", () => {
    closeMenus(); const panel = document.getElementById(button.dataset.panelToggle); panel.hidden = !panel.hidden; syncPanelButtons();
  });
  for (const tablist of document.querySelectorAll('.dock-tabs[role="tablist"]')) {
    const tabs = [...tablist.querySelectorAll('[role="tab"]')];
    for (const tab of tabs) {
      tab.addEventListener("click", () => {
        for (const candidate of tabs) {
          const active = candidate === tab;
          candidate.setAttribute("aria-selected", String(active));
          candidate.tabIndex = active ? 0 : -1;
          document.getElementById(candidate.getAttribute("aria-controls")).hidden = !active;
        }
      });
      tab.addEventListener("keydown", (event) => {
        const index = tabs.indexOf(tab);
        const next = { ArrowRight: (index + 1) % tabs.length, ArrowLeft: (index + tabs.length - 1) % tabs.length, Home: 0, End: tabs.length - 1 }[event.key];
        if (next === undefined) return;
        event.preventDefault(); tabs[next].click(); tabs[next].focus();
      });
    }
  }
  document.querySelector("#project-tree").addEventListener("click", (event) => { const row = event.target.closest("[data-object-id]"); if (row) selectModel(row.dataset.objectId, event.ctrlKey || event.metaKey); });
  document.querySelector("#clear-messages").addEventListener("click", () => document.querySelector("#message-log").replaceChildren());
  document.addEventListener("pointerdown", (event) => { if (!event.target.closest("#viewport-context")) closeMenus(); });
  document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeMenus(); });
  canvas.addEventListener("pointerdown", (event) => { if (event.button === 2) rightStart = { x: event.clientX, y: event.clientY }; });
  canvas.addEventListener("pointerup", (event) => {
    if (event.button !== 2 || !rightStart) return;
    const start = rightStart; rightStart = null;
    if (Math.hypot(event.clientX - start.x, event.clientY - start.y) > 4 || document.querySelector("dialog[open]")) return;
    // State changes already refresh controls; opening a menu must preserve input drafts.
    const rect = canvas.getBoundingClientRect();
    context.hidden = false;
    context.style.left = `${Math.max(0, Math.min(event.clientX - rect.left, rect.width - context.offsetWidth))}px`;
    context.style.top = `${Math.max(0, Math.min(event.clientY - rect.top, rect.height - context.offsetHeight))}px`;
  });
  // The menu opened on pointerup can receive the subsequent contextmenu event.
  // Capture it for the entire viewport, including the menu and other overlays.
  document.querySelector("#viewport").addEventListener("contextmenu", (event) => event.preventDefault(), { capture: true });
  for (const button of context.querySelectorAll("[data-selection-mode], [data-select-tool], [data-clear-selection]")) button.addEventListener("click", () => { context.hidden = true; });
  document.addEventListener("modeling-toolchange", markTools);
  document.querySelector("#close-help").addEventListener("click", () => document.querySelector("#help-dialog").close());
  document.querySelector("#show-help").addEventListener("click", () => document.querySelector("#help-dialog").showModal());
  refresh();
  return { refresh, appendMessage(text, error) {
    const list = document.querySelector("#message-log"), row = document.createElement("li");
    setModelingText(row,text); row.dataset.error = String(error); list.append(row);
    while (list.children.length > 100) list.firstElementChild.remove();
    list.scrollTop = list.scrollHeight;
    if (error) document.querySelector("#messages").hidden = false;
  } };
}

function installDockResizing() {
  const workspace = document.querySelector("#modeling-workspace");
  const sidebar = document.querySelector("#modeling-sidebar");
  const project = document.querySelector("#project-dock");
  const widthHandle = document.querySelector("#modeling-sidebar-resizer");
  const heightHandle = document.querySelector("#modeling-dock-resizer");
  const storageKey = "smlib-modeling-docks-v1";
  const desktop = matchMedia("(min-width: 701px)");
  const preferred = { width: null, height: null };
  try {
    const stored = JSON.parse(localStorage.getItem(storageKey));
    for (const dimension of ["width", "height"]) if (Number.isFinite(stored?.[dimension])) preferred[dimension] = stored[dimension];
  } catch { /* Resizing also works when browser storage is unavailable. */ }
  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
  function limits(dimension) {
    return dimension === "width"
      ? { min: 220, max: Math.max(220, Math.min(560, workspace.clientWidth - document.querySelector(".right-tools").offsetWidth - widthHandle.offsetWidth - 320)) }
      : { min: 88, max: Math.max(88, sidebar.clientHeight - heightHandle.offsetHeight - 160) };
  }
  function apply() {
    if (!desktop.matches) return;
    const width = limits("width"), height = limits("height");
    const defaultWidth = Number.parseFloat(getComputedStyle(workspace).getPropertyValue("--modeling-left-default")) || 280;
    for (const [dimension, node, handle, bounds, fallback, variable] of [
      ["width", workspace, widthHandle, width, defaultWidth, "--modeling-left-width"],
      ["height", sidebar, heightHandle, height, 156, "--modeling-project-height"],
    ]) {
      const value = Math.round(clamp(preferred[dimension] ?? fallback, bounds.min, bounds.max));
      if (node.style.getPropertyValue(variable) !== `${value}px`) node.style.setProperty(variable, `${value}px`);
      for (const [name, number] of [["min", bounds.min], ["max", bounds.max], ["now", value]]) handle.setAttribute(`aria-value${name}`, String(Math.round(number)));
      handle.setAttribute("aria-valuetext", `${value} 像素`);
    }
  }
  function save() {
    try { localStorage.setItem(storageKey, JSON.stringify(preferred)); } catch { /* Keep current sizes in memory. */ }
  }
  for (const [handle, dimension, pane, coordinate, negative, positive] of [
    [widthHandle, "width", sidebar, "clientX", "ArrowLeft", "ArrowRight"],
    [heightHandle, "height", project, "clientY", "ArrowUp", "ArrowDown"],
  ]) {
    let drag = null;
    handle.addEventListener("pointerdown", (event) => {
      if (!desktop.matches || event.button !== 0) return;
      event.preventDefault(); handle.focus();
      drag = { id: event.pointerId, coordinate: event[coordinate], size: pane.getBoundingClientRect()[dimension], previous: preferred[dimension] };
      handle.setPointerCapture(event.pointerId); handle.classList.add("is-dragging"); document.body.dataset.modelingResize = dimension;
    });
    handle.addEventListener("pointermove", (event) => {
      if (!drag || drag.id !== event.pointerId) return;
      const bounds = limits(dimension);
      preferred[dimension] = clamp(drag.size + event[coordinate] - drag.coordinate, bounds.min, bounds.max); apply();
    });
    function finish(event, cancelled = false) {
      if (!drag || drag.id !== event.pointerId) return;
      if (cancelled) { preferred[dimension] = drag.previous; apply(); } else save();
      drag = null; handle.classList.remove("is-dragging"); delete document.body.dataset.modelingResize;
      if (handle.hasPointerCapture(event.pointerId)) handle.releasePointerCapture(event.pointerId);
    }
    handle.addEventListener("pointerup", (event) => finish(event));
    handle.addEventListener("pointercancel", (event) => finish(event, true));
    handle.addEventListener("lostpointercapture", (event) => finish(event, true));
    handle.addEventListener("keydown", (event) => {
      if (!desktop.matches || ![negative, positive, "Home", "End"].includes(event.key)) return;
      event.preventDefault(); const bounds = limits(dimension);
      preferred[dimension] = event.key === "Home" ? bounds.min : event.key === "End" ? bounds.max : clamp(pane.getBoundingClientRect()[dimension] + (event.key === negative ? -16 : 16), bounds.min, bounds.max);
      apply(); save();
    });
    handle.addEventListener("dblclick", () => { preferred[dimension] = null; apply(); save(); });
  }
  const observer = new ResizeObserver(apply);
  observer.observe(workspace); observer.observe(sidebar);
  desktop.addEventListener("change", apply);
  apply();
}
