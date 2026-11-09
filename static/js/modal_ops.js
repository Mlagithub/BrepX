/**
 * Blender-Style Modal Operator State Machine for BrepX.
 * Implements interactive Face Extrude (E), Edge Fillet/Chamfer (Ctrl+B),
 * G/R/S transforms, and keyboard direct numeric confirmation.
 */

import * as THREE from 'three';
import { fetchScene, submitCommand } from './api.js';
import { context } from './context.js';
import {
  activateHudInput,
  deactivateHudInput,
  getTypedNumericValue,
  hasUserTyped,
  updateHudPosition,
  updateHudValue,
} from './hud_input.js';
import { interactionLock } from './interaction_lock.js';
import { activeCamera, controls, previewGroup } from './viewport.js';
import { renderAdjustLastPanel } from './adjust_last.js';

const modalStatusBar = document.getElementById('modal-status-bar');

let activeModalOp = null;

export function isModalActive() {
  return activeModalOp !== null;
}

let modalStatusRaf = null;
let pendingStatusText = null;

function showModalStatus(text) {
  pendingStatusText = text;
  if (!modalStatusRaf) {
    modalStatusRaf = requestAnimationFrame(() => {
      modalStatusRaf = null;
      if (modalStatusBar && pendingStatusText) {
        modalStatusBar.textContent = pendingStatusText;
        modalStatusBar.classList.remove('hidden');
      }
    });
  }
}

function hideModalStatus() {
  if (modalStatusBar) {
    modalStatusBar.classList.add('hidden');
  }
}

function clearPreviewGeometry() {
  while (previewGroup.children.length > 0) {
    const c = previewGroup.children[0];
    previewGroup.remove(c);
    if (c.geometry) c.geometry.dispose();
    if (c.material) c.material.dispose();
  }
}

function round2(v) {
  return Math.round(v * 100) / 100;
}

export function invokeExtrudeModal() {
  const selections = context.getSelection();
  if (!selections.length) {
    alert('请先在视口中选择一个要拉伸的拓扑面 (快捷键: 3 进入面模式)');
    return;
  }

  const targetExpr = selections[0];
  interactionLock.acquire('modal_operator');

  activeModalOp = {
    type: 'extrude',
    targetExpr,
    value: 15.0,
    startClientY: 0,
    initialized: false,
  };

  activateHudInput(15.0, (typedVal) => {
    if (activeModalOp) {
      activeModalOp.value = typedVal;
      showModalStatus(`[拉伸模态] 键入数值: ${typedVal} mm · Enter 确认 · Esc 取消`);
    }
  });

  showModalStatus(`[拉伸模态] 拖动鼠标或直接敲键盘数字 · 当前: +15.0 mm · Enter 确认 · Esc 取消`);
}

export function invokeFilletModal(mode = 'fillet') {
  const selections = context.getSelection();
  if (!selections.length) {
    alert('请先在视口中选择一条特征边 (快捷键: 2 进入边模式)');
    return;
  }

  const targetExpr = selections[0];
  interactionLock.acquire('modal_operator');

  activeModalOp = {
    type: mode,
    targetExpr,
    value: 4.0,
    startClientX: 0,
    initialized: false,
  };

  activateHudInput(4.0, (typedVal) => {
    if (activeModalOp) {
      activeModalOp.value = Math.max(0.1, typedVal);
      const title = activeModalOp.type === 'fillet' ? '圆角 R' : '倒角 D';
      showModalStatus(`[${title}模态] 键入大小: ${activeModalOp.value} mm · M 切换 · Enter 确认 · Esc 取消`);
    }
  });

  const title = mode === 'fillet' ? '倒圆角' : '倒角';
  showModalStatus(`[${title}模态] 拖动鼠标或敲数字 · 当前: R4.0 mm · M 切换 · Enter 确认 · Esc 取消`);
}

export function handleModalMouseMove(e) {
  if (!activeModalOp) return;

  updateHudPosition(e.clientX, e.clientY);

  if (hasUserTyped()) return;

  if (!activeModalOp.initialized) {
    activeModalOp.startClientX = e.clientX;
    activeModalOp.startClientY = e.clientY;
    activeModalOp.initialized = true;
    return;
  }

  if (activeModalOp.type === 'extrude') {
    const dy = activeModalOp.startClientY - e.clientY;
    const amount = round2(dy * 0.4);
    activeModalOp.value = amount === 0 ? 0.5 : amount;
    updateHudValue(activeModalOp.value);
    const sign = amount >= 0 ? '+' : '';
    showModalStatus(`[拉伸模态] 移动鼠标或敲数字 · 当前: ${sign}${amount} mm · Enter 确认 · Esc 取消`);
  } else if (activeModalOp.type === 'fillet' || activeModalOp.type === 'chamfer') {
    const dx = e.clientX - activeModalOp.startClientX;
    const r = Math.max(0.2, round2(4.0 + dx * 0.1));
    activeModalOp.value = r;
    updateHudValue(activeModalOp.value);
    const tag = activeModalOp.type === 'fillet' ? '圆角 R' : '倒角 D';
    showModalStatus(`[${tag}模态] 移动鼠标或敲数字 · 当前: ${r} mm · M 切换 · Enter 确认 · Esc 取消`);
  }
}

export async function confirmModalOperation() {
  if (!activeModalOp) return;
  const op = activeModalOp;
  const finalValue = getTypedNumericValue(op.value);

  cancelModalOperation();

  const cmdId = `c_${Date.now()}`;
  let cmdPayload = null;

  if (op.type === 'extrude') {
    cmdPayload = {
      command_id: cmdId,
      op: 'extrude',
      target: { base: 'prev', expr: op.targetExpr },
      params: { height: finalValue },
      idempotency_key: `extrude_${cmdId}`,
    };
  } else if (op.type === 'fillet') {
    cmdPayload = {
      command_id: cmdId,
      op: 'fillet',
      target: { base: 'prev', expr: op.targetExpr },
      params: { radius: finalValue },
      idempotency_key: `fillet_${cmdId}`,
    };
  } else if (op.type === 'chamfer') {
    cmdPayload = {
      command_id: cmdId,
      op: 'chamfer',
      target: { base: 'prev', expr: op.targetExpr },
      params: { distance: finalValue },
      idempotency_key: `chamfer_${cmdId}`,
    };
  }

  if (cmdPayload) {
    try {
      const res = await submitCommand(cmdPayload);
      const sceneData = await fetchScene();
      context.setSnapshot(res.version, res.body, sceneData);

      if (res.journal) {
        context.setJournal(res.journal);
      } else {
        const currentJournal = context.journal || [];
        currentJournal.push({ command: cmdPayload, version: res.version });
        context.setJournal(currentJournal);
      }

      context.setLastCommand(cmdPayload);
      renderAdjustLastPanel(cmdPayload);
      context.clearSelections();
    } catch (err) {
      alert(`操作失败: ${err.message}`);
    }
  }
}

export function cancelModalOperation() {
  activeModalOp = null;
  deactivateHudInput();
  interactionLock.release('modal_operator');
  clearPreviewGeometry();
  hideModalStatus();
}

window.addEventListener('keydown', (e) => {
  const tag = (e.target.tagName || '').toLowerCase();
  if (tag === 'input' || tag === 'textarea') return;

  if (isModalActive()) {
    if (e.key === 'Enter') {
      e.preventDefault();
      confirmModalOperation();
      return;
    }
    if (e.key === 'Escape') {
      e.preventDefault();
      cancelModalOperation();
      return;
    }
    if ((e.key === 'm' || e.key === 'M') && (activeModalOp.type === 'fillet' || activeModalOp.type === 'chamfer')) {
      e.preventDefault();
      activeModalOp.type = activeModalOp.type === 'fillet' ? 'chamfer' : 'fillet';
      const tag = activeModalOp.type === 'fillet' ? '圆角 R' : '倒角 D';
      showModalStatus(`[${tag}模态] 切换完成 · 当前: ${activeModalOp.value} mm · Enter 确认 · Esc 取消`);
      return;
    }
    return;
  }

  if (e.key === 'e' || e.key === 'E') {
    if (!e.ctrlKey && !e.metaKey && !e.altKey) {
      e.preventDefault();
      invokeExtrudeModal();
      return;
    }
  }

  if ((e.ctrlKey || e.metaKey) && (e.key === 'b' || e.key === 'B')) {
    e.preventDefault();
    invokeFilletModal('fillet');
    return;
  }
});
