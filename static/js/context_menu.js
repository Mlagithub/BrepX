/**
 * Contextual right-click popup menu for CAD entities, timeline nodes, and viewport.
 */

import { context } from './context.js';
import { invokeExtrudeModal, invokeFilletModal } from './modal_ops.js';
import { fitCameraToObject, modelGroup, setCameraType } from './viewport.js';

let menuEl = null;

function ensureContextMenuElement() {
  if (!menuEl) {
    menuEl = document.createElement('div');
    menuEl.id = 'cad-context-menu';
    menuEl.className = 'cad-context-menu hidden';
    document.body.appendChild(menuEl);

    window.addEventListener('click', () => hideContextMenu());
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') hideContextMenu();
    });
  }
}

export function hideContextMenu() {
  if (menuEl) {
    menuEl.classList.add('hidden');
    menuEl.innerHTML = '';
  }
}

export function showContextMenu(clientX, clientY, targetType = 'empty', meta = null) {
  ensureContextMenuElement();
  menuEl.innerHTML = '';

  const items = [];

  if (targetType === 'face') {
    items.push({ label: '📐 选面拉伸 [E]', action: () => invokeExtrudeModal() });
    items.push({ label: '⚡ 面法向对齐 [Ctrl+8]', action: () => context.emit('camera:normal_to', meta) });
    items.push({ label: '🌊 标记为入口 (Inlet)', action: () => context.emit('tag:inlet', meta) });
    items.push({ label: '🌊 标记为出口 (Outlet)', action: () => context.emit('tag:outlet', meta) });
    items.push({ label: '🌊 标记为壁面 (Wall)', action: () => context.emit('tag:wall', meta) });
  } else if (targetType === 'edge') {
    items.push({ label: '⭕ 选边倒圆角 [Ctrl+B]', action: () => invokeFilletModal('fillet') });
    items.push({ label: '📐 选边倒斜角', action: () => invokeFilletModal('chamfer') });
  } else {
    items.push({ label: '📦 添加长方体', action: () => context.emit('operator:run', { op: 'box' }) });
    items.push({ label: '🌀 添加圆柱体', action: () => context.emit('operator:run', { op: 'cylinder' }) });
    items.push({ label: '🔍 全景居中适应', action: () => fitCameraToObject(modelGroup) });
    items.push({ label: '📐 切换透视/正交', action: () => context.emit('camera:toggle_type') });
    items.push({ label: '✖ 全部取消选择', action: () => context.clearSelections() });
  }

  items.forEach((item) => {
    const row = document.createElement('div');
    row.className = 'ctx-menu-item';
    row.textContent = item.label;
    row.onclick = (e) => {
      e.stopPropagation();
      hideContextMenu();
      item.action();
    };
    menuEl.appendChild(row);
  });

  const maxX = window.innerWidth - 180;
  const maxY = window.innerHeight - (items.length * 32 + 20);

  menuEl.style.left = `${Math.min(clientX, maxX)}px`;
  menuEl.style.top = `${Math.min(clientY, maxY)}px`;
  menuEl.classList.remove('hidden');
}
