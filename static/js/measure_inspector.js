/**
 * Real-time topology geometry inspector displaying dimensions, normal, and area.
 */

import { context } from './context.js';

let inspectorContainerEl = null;

export function initMeasureInspector(containerEl) {
  inspectorContainerEl = containerEl;
  context.on('selections:changed', () => renderInspectorData());
  renderInspectorData();
}

export function renderInspectorData() {
  if (!inspectorContainerEl) return;
  inspectorContainerEl.innerHTML = '';

  const selections = context.getSelection() || [];
  if (!selections.length) {
    inspectorContainerEl.innerHTML = '<div class="inspector-hint">未选中任何拓扑几何（点击面或边查看参数）</div>';
    return;
  }

  const title = document.createElement('div');
  title.className = 'inspector-title';
  title.innerHTML = `
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:4px; vertical-align:middle;"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="4"/></svg>
    选区几何度量 (${selections.length})
  `;
  inspectorContainerEl.appendChild(title);

  selections.forEach((expr) => {
    const card = document.createElement('div');
    card.className = 'inspector-card';

    const isFace = expr.startsWith('faces()');
    card.innerHTML = `
      <div class="inspector-expr" title="${expr}">${expr}</div>
      <div class="inspector-badge">${isFace ? '曲面 (Face)' : '特征边 (Edge)'}</div>
    `;
    inspectorContainerEl.appendChild(card);
  });
}
