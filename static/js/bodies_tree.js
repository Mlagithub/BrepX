/**
 * Solid bodies list component managing multi-body tree visibility and isolation.
 */

import { context } from './context.js';
import { modelGroup } from './viewport.js';

let bodiesContainerEl = null;

const eyeOpenSvg = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`;
const eyeClosedSvg = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>`;
const targetSvg = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="4"/><line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="2" y1="12" x2="6" y2="12"/><line x1="18" y1="12" x2="22" y2="12"/></svg>`;

export function initBodiesTree(containerEl) {
  bodiesContainerEl = containerEl;
  renderBodiesList();
}

export function renderBodiesList() {
  if (!bodiesContainerEl) return;
  bodiesContainerEl.innerHTML = '';

  const bodies = modelGroup.children || [];
  if (!bodies.length) {
    bodiesContainerEl.innerHTML = '<div class="tree-empty">无活跃几何实体</div>';
    return;
  }

  const title = document.createElement('div');
  title.className = 'tree-section-title';
  title.innerHTML = `
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:5px; vertical-align:middle;"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
    实体列表 (${bodies.length})
  `;
  bodiesContainerEl.appendChild(title);

  bodies.forEach((bodyRoot, idx) => {
    const item = document.createElement('div');
    item.className = 'tree-item';
    item.dataset.bodyIdx = idx;

    const name = bodyRoot.name || `Body_${idx + 1}`;
    const isVisible = bodyRoot.visible !== false;

    item.innerHTML = `
      <span class="tree-eye-btn" title="显示/隐藏实体">${isVisible ? eyeOpenSvg : eyeClosedSvg}</span>
      <span class="tree-item-name">${name}</span>
      <span class="tree-isolate-btn" title="孤立显示此实体">${targetSvg}</span>
    `;

    const eyeBtn = item.querySelector('.tree-eye-btn');
    eyeBtn.onclick = (e) => {
      e.stopPropagation();
      bodyRoot.visible = !bodyRoot.visible;
      eyeBtn.innerHTML = bodyRoot.visible ? eyeOpenSvg : eyeClosedSvg;
    };

    const isolateBtn = item.querySelector('.tree-isolate-btn');
    isolateBtn.onclick = (e) => {
      e.stopPropagation();
      const allBodies = modelGroup.children;
      const anyOtherVisible = Array.from(allBodies).some(b => b !== bodyRoot && b.visible);
      if (anyOtherVisible) {
        allBodies.forEach(b => { b.visible = (b === bodyRoot); });
      } else {
        allBodies.forEach(b => { b.visible = true; });
      }
      renderBodiesList();
    };

    bodiesContainerEl.appendChild(item);
  });
}
