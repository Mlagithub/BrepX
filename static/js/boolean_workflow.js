/**
 * Two-phase interactive workflow for Boolean operators (Target + Tool selection).
 * Guides user to pick the base body first, then select the cutting or joining tool.
 */

import { context } from './context.js';
import { interactionLock } from './interaction_lock.js';

let activeBooleanOp = null; // { opName, targetExpr, stage: 1 | 2 }

export function isBooleanWorkflowActive() {
  return activeBooleanOp !== null;
}

export function startBooleanWorkflow(opName, onCompleteCallback) {
  interactionLock.acquire('boolean_workflow');
  activeBooleanOp = {
    opName,
    targetExpr: null,
    toolExpr: null,
    stage: 1,
    callback: onCompleteCallback,
  };

  const statusEl = document.getElementById('status-text');
  if (statusEl) {
    statusEl.textContent = `[${opName.toUpperCase()}] 步骤 1/2: 请点击选择基准工件 (Target)`;
    statusEl.style.color = '#ffd885';
  }
}

export function handleBooleanTopologyPick(selectorExpr) {
  if (!activeBooleanOp) return false;

  const statusEl = document.getElementById('status-text');

  if (activeBooleanOp.stage === 1) {
    activeBooleanOp.targetExpr = selectorExpr;
    activeBooleanOp.stage = 2;
    if (statusEl) {
      statusEl.textContent = `[${activeBooleanOp.opName.toUpperCase()}] 步骤 2/2: 请点击选择工具体 (Tool)`;
      statusEl.style.color = '#ffd885';
    }
    return true;
  }

  if (activeBooleanOp.stage === 2) {
    activeBooleanOp.toolExpr = selectorExpr;
    const completed = {
      op: activeBooleanOp.opName,
      target: { base: 'prev', expr: activeBooleanOp.targetExpr },
      tool: { base: 'prev', expr: activeBooleanOp.toolExpr },
    };

    const cb = activeBooleanOp.callback;
    cancelBooleanWorkflow();

    if (cb) cb(completed);
    return true;
  }

  return false;
}

export function cancelBooleanWorkflow() {
  activeBooleanOp = null;
  interactionLock.release('boolean_workflow');

  const statusEl = document.getElementById('status-text');
  if (statusEl) {
    statusEl.textContent = '就绪 · BrepX 已加载';
    statusEl.style.color = '';
  }
}

window.addEventListener('keydown', (e) => {
  if (isBooleanWorkflowActive() && e.key === 'Escape') {
    e.preventDefault();
    cancelBooleanWorkflow();
  }
});
