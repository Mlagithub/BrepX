/**
 * Floating lightweight CFD boundary condition tagging pill bar on selected faces.
 */

import { runOperator } from './operator_runner.js';
import { context } from './context.js';

let pillEl = null;

function ensurePillElement() {
  if (!pillEl) {
    pillEl = document.createElement('div');
    pillEl.id = 'boundary-tag-pill-bar';
    pillEl.className = 'face-action-pill hidden';
    pillEl.innerHTML = `
      <span class="pill-label">🌊 CFD 边界</span>
      <button class="pill-btn pill-inlet" data-ptype="inlet">+ Inlet 入口</button>
      <button class="pill-btn pill-outlet" data-ptype="outlet">+ Outlet 出口</button>
      <button class="pill-btn pill-wall" data-ptype="wall">+ Wall 壁面</button>
      <button class="pill-btn pill-symmetry" data-ptype="symmetry">+ 对称面</button>
      <button class="pill-btn pill-interface" data-ptype="interface">+ 交界面</button>
    `;
    document.body.appendChild(pillEl);

    pillEl.querySelectorAll('.pill-btn').forEach((btn) => {
      btn.onclick = (e) => {
        e.stopPropagation();
        const ptype = btn.dataset.ptype;
        const sels = context.getSelection();
        if (sels.length > 0) {
          runOperator('tag_boundary', {
            semantic_type: ptype,
            name: `${ptype}_${Date.now() % 1000}`,
          });
        }
      };
    });
  }
}

export function updateBoundaryPillState() {
  ensurePillElement();
  const sels = context.getSelection() || [];
  const faceSels = sels.filter(s => s.startsWith('faces()'));

  if (faceSels.length > 0) {
    pillEl.classList.remove('hidden');
  } else {
    pillEl.classList.add('hidden');
  }
}

context.on('selections:changed', updateBoundaryPillState);
