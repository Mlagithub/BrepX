/**
 * Fusion 360 style Timeline component managing parametric command history,
 * in-place parameter bubble editing, incremental rebuild, and rollback bar.
 */

import { fetchScene, undo, updateCommandParams } from './api.js';
import { context } from './context.js';
import { OPERATOR_METADATA } from './operator_meta.js';

let timelineTrackEl = null;
let rollbackBarEl = null;
let activeBubbleEl = null;
let currentRollbackIdx = -1;

export function initTimeline(containerEl) {
  if (!containerEl) return;
  containerEl.innerHTML = `
    <div class="timeline-container">
      <div class="timeline-header">
        <span class="timeline-title">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:4px; vertical-align:middle;"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          特征时间线 (Timeline)
        </span>
        <span class="timeline-hint">双击卡片改参 · 拖动黄色滑块历史回退</span>
      </div>
      <div class="timeline-track-wrap">
        <div id="timeline-track" class="timeline-track"></div>
        <div id="timeline-rollback-bar" class="timeline-rollback-bar" title="拖动历史回退重构棒"></div>
      </div>
    </div>
  `;

  timelineTrackEl = containerEl.querySelector('#timeline-track');
  rollbackBarEl = containerEl.querySelector('#timeline-rollback-bar');

  context.on('snapshot:changed', () => renderTimelineNodes());
  context.on('lastCommand:changed', () => renderTimelineNodes());
  context.on('journal:changed', () => renderTimelineNodes());

  window.addEventListener('click', (e) => {
    if (activeBubbleEl && !activeBubbleEl.contains(e.target) && !e.target.closest('.timeline-node')) {
      closeParamBubble();
    }
  });

  _bindRollbackDrag();
}

export function renderTimelineNodes() {
  if (!timelineTrackEl) return;
  timelineTrackEl.innerHTML = '';

  const journal = context.journal || [];
  if (!journal.length && context.lastCommand) {
    journal.push({
      command: context.lastCommand,
      version: context.version,
    });
  }

  if (!journal.length) {
    timelineTrackEl.innerHTML = '<div class="timeline-empty">暂无历史建模工步</div>';
    return;
  }

  journal.forEach((rec, idx) => {
    const cmd = rec.command;
    const meta = OPERATOR_METADATA[cmd.op] || { title: cmd.op };
    const nodeEl = document.createElement('div');
    nodeEl.className = 'timeline-node';
    nodeEl.dataset.cmdId = cmd.command_id;
    nodeEl.dataset.index = idx;

    const isRolledBack = currentRollbackIdx >= 0 && idx > currentRollbackIdx;
    if (isRolledBack) nodeEl.classList.add('rolled-back');

    const paramSummary = Object.entries(cmd.params || {})
      .map(([k, v]) => `${k}=${v}`)
      .slice(0, 2)
      .join(', ');

    nodeEl.innerHTML = `
      <div class="node-badge">#${idx + 1}</div>
      <div class="node-op">${meta.title.split(' ')[0]}</div>
      <div class="node-params">${paramSummary || '-'}</div>
    `;

    nodeEl.addEventListener('dblclick', (e) => {
      e.stopPropagation();
      openParamBubble(cmd, nodeEl);
    });

    timelineTrackEl.appendChild(nodeEl);
  });
}

function openParamBubble(cmd, anchorEl) {
  closeParamBubble();

  activeBubbleEl = document.createElement('div');
  activeBubbleEl.className = 'timeline-param-bubble';
  activeBubbleEl.innerHTML = `
    <div class="bubble-header">
      <span>修改工步: ${cmd.op}</span>
      <button class="bubble-close">✕</button>
    </div>
    <div class="bubble-body"></div>
    <div class="bubble-actions">
      <button class="btn btn-primary btn-sm bubble-save">应用增量重算</button>
    </div>
  `;

  const bodyEl = activeBubbleEl.querySelector('.bubble-body');
  Object.entries(cmd.params || {}).forEach(([k, v]) => {
    const row = document.createElement('div');
    row.className = 'bubble-row';
    row.innerHTML = `
      <label>${k}</label>
      <input type="${typeof v === 'number' ? 'number' : 'text'}" data-param="${k}" value="${v}" step="any" />
    `;
    bodyEl.appendChild(row);
  });

  activeBubbleEl.querySelector('.bubble-close').onclick = () => closeParamBubble();
  activeBubbleEl.querySelector('.bubble-save').onclick = async () => {
    const newParams = {};
    let hasInvalid = false;
    activeBubbleEl.querySelectorAll('input[data-param]').forEach((inp) => {
      const key = inp.dataset.param;
      if (inp.type === 'number') {
        const val = parseFloat(inp.value);
        if (isNaN(val)) {
          hasInvalid = true;
        } else {
          newParams[key] = val;
        }
      } else {
        newParams[key] = inp.value;
      }
    });

    if (hasInvalid) {
      alert('参数输入有误，请输入有效数值');
      return;
    }

    try {
      const res = await updateCommandParams(cmd.command_id, newParams);
      const sceneData = await fetchScene();

      cmd.params = { ...cmd.params, ...newParams };

      if (res.journal) {
        context.setJournal(res.journal);
      } else {
        const j = context.journal || [];
        const targetRec = j.find(r => r.command.command_id === cmd.command_id);
        if (targetRec) {
          targetRec.command.params = { ...targetRec.command.params, ...newParams };
          context.setJournal([...j]);
        }
      }

      if (context.lastCommand && context.lastCommand.command_id === cmd.command_id) {
        context.setLastCommand({ ...context.lastCommand, params: { ...context.lastCommand.params, ...newParams } });
      }

      context.setSnapshot(res.version, res.body, sceneData);
      closeParamBubble();

      const rebuiltCount = (res.rebuilt || []).length;
      const statusEl = document.getElementById('status-text');
      if (statusEl) {
        const downstreamMsg = rebuiltCount > 0 ? ` · 已自动增量重算下游 ${rebuiltCount} 个特征` : '';
        statusEl.textContent = `特征参数已更新 (v${res.version})${downstreamMsg}`;
        statusEl.style.color = 'var(--success-color)';
      }
    } catch (err) {
      const diag = err.diagnostic;
      let msg = err.message;
      if (diag && diag.error) {
        const errType = diag.error.error || diag.error.type || '';
        const detail = diag.error.message || diag.error.suggestion || JSON.stringify(diag.error);
        msg = `${errType ? `[${errType}] ` : ''}${detail}`;
      }
      alert(`增量重算失败: ${msg}`);
    }
  };

  document.body.appendChild(activeBubbleEl);
  const rect = anchorEl.getBoundingClientRect();
  activeBubbleEl.style.left = `${Math.max(10, rect.left - 40)}px`;
  activeBubbleEl.style.bottom = `${window.innerHeight - rect.top + 8}px`;
}

function closeParamBubble() {
  if (activeBubbleEl) {
    activeBubbleEl.remove();
    activeBubbleEl = null;
  }
}

function _bindRollbackDrag() {
  if (!rollbackBarEl) return;
  let isDragging = false;

  rollbackBarEl.addEventListener('mousedown', (e) => {
    isDragging = true;
    e.preventDefault();
  });

  window.addEventListener('mousemove', (e) => {
    if (!isDragging || !timelineTrackEl) return;
    const trackRect = timelineTrackEl.getBoundingClientRect();
    const nodes = timelineTrackEl.querySelectorAll('.timeline-node');
    if (!nodes.length) return;

    let targetIdx = -1;
    nodes.forEach((n, idx) => {
      const nr = n.getBoundingClientRect();
      if (e.clientX >= nr.left) {
        targetIdx = idx;
      }
    });

    if (targetIdx !== currentRollbackIdx) {
      currentRollbackIdx = targetIdx;
      context.setRollbackIndex(currentRollbackIdx);
      renderTimelineNodes();
    }
  });

  window.addEventListener('mouseup', () => {
    isDragging = false;
  });
}
