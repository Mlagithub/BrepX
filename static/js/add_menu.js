/**
 * Blender-style Shift + A popup menu at cursor position for rapid entity creation.
 */

import { runOperator } from './operator_runner.js';
import { OPERATOR_METADATA } from './operator_meta.js';

let menuEl = null;

function ensureAddMenuElement() {
  if (!menuEl) {
    menuEl = document.createElement('div');
    menuEl.id = 'shift-a-add-menu';
    menuEl.className = 'add-menu-popup hidden';
    document.body.appendChild(menuEl);

    window.addEventListener('click', () => closeAddMenu());
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closeAddMenu();
    });
  }
}

export function openAddMenu(clientX, clientY) {
  ensureAddMenuElement();
  menuEl.innerHTML = '';

  const header = document.createElement('div');
  header.className = 'add-menu-header';
  header.textContent = '快速添加 (Shift + A)';
  menuEl.appendChild(header);

  const sections = [
    { title: '3D 基础实体', ops: ['box', 'cylinder', 'sphere', 'cone', 'torus', 'wedge'] },
    { title: '流体机械核心', ops: ['blade_runner', 'volute'] },
    { title: '特征成型', ops: ['extrude', 'hole', 'shell', 'revolve', 'sweep', 'loft'] },
  ];

  sections.forEach((sec) => {
    const secTitle = document.createElement('div');
    secTitle.className = 'add-menu-section';
    secTitle.textContent = sec.title;
    menuEl.appendChild(secTitle);

    sec.ops.forEach((opName) => {
      const meta = OPERATOR_METADATA[opName];
      if (!meta) return;

      const item = document.createElement('div');
      item.className = 'add-menu-item';
      item.textContent = meta.title;
      item.onclick = (e) => {
        e.stopPropagation();
        closeAddMenu();
        runOperator(opName);
      };
      menuEl.appendChild(item);
    });
  });

  const maxX = window.innerWidth - 220;
  const maxY = window.innerHeight - 340;
  menuEl.style.left = `${Math.min(clientX, maxX)}px`;
  menuEl.style.top = `${Math.min(clientY, maxY)}px`;
  menuEl.classList.remove('hidden');
}

export function closeAddMenu() {
  if (menuEl) {
    menuEl.classList.add('hidden');
  }
}

window.addEventListener('keydown', (e) => {
  const tag = (e.target.tagName || '').toLowerCase();
  if (tag === 'input' || tag === 'textarea') return;

  if (e.shiftKey && (e.key === 'a' || e.key === 'A')) {
    e.preventDefault();
    openAddMenu(window.innerWidth / 2 - 100, window.innerHeight / 2 - 150);
  }
});
