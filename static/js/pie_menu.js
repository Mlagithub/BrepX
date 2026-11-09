/**
 * Blender-style 4-direction radial Pie Menu (Z key) for display mode switching.
 */

import { context } from './context.js';

let pieEl = null;
let isOpen = false;

function ensurePieElement() {
  if (!pieEl) {
    pieEl = document.createElement('div');
    pieEl.id = 'cad-pie-menu';
    pieEl.className = 'cad-pie-menu hidden';
    document.body.appendChild(pieEl);

    window.addEventListener('click', () => closePieMenu());
    window.addEventListener('keyup', (e) => {
      if (e.key === 'z' || e.key === 'Z') {
        closePieMenu();
      }
    });
  }
}

export function openPieMenu(clientX, clientY) {
  ensurePieElement();
  pieEl.innerHTML = '';
  isOpen = true;

  const sectors = [
    { label: '带边着色 (8)', mode: 'shaded_edges', key: '8', angle: 270 },
    { label: '实体着色 (6)', mode: 'shaded', key: '6', angle: 0 },
    { label: '纯线框 (4)', mode: 'wireframe', key: '4', angle: 180 },
    { label: '斑马线分析 (2)', mode: 'zebra', key: '2', angle: 90 },
  ];

  sectors.forEach((sec) => {
    const btn = document.createElement('div');
    btn.className = `pie-sector-btn pie-pos-${sec.key}`;
    btn.textContent = sec.label;
    btn.onclick = (e) => {
      e.stopPropagation();
      selectDisplayMode(sec.mode);
    };
    pieEl.appendChild(btn);
  });

  pieEl.style.left = `${clientX}px`;
  pieEl.style.top = `${clientY}px`;
  pieEl.classList.remove('hidden');
}

export function closePieMenu() {
  if (pieEl) {
    pieEl.classList.add('hidden');
    isOpen = false;
  }
}

export function isPieMenuOpen() {
  return isOpen;
}

function selectDisplayMode(mode) {
  context.setDisplayMode(mode);
  closePieMenu();
}
