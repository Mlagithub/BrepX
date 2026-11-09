/**
 * Unified operator execution runner with automatic topological target binding,
 * snapshot syncing, and F9 Adjust Last Operation panel invocation.
 */

import { fetchScene, submitCommand } from './api.js';
import { handleBooleanTopologyPick, isBooleanWorkflowActive, startBooleanWorkflow } from './boolean_workflow.js';
import { context } from './context.js';
import { OPERATOR_METADATA } from './operator_meta.js';
import { renderAdjustLastPanel } from './adjust_last.js';

export async function runOperator(opName, customParams = {}) {
  const meta = OPERATOR_METADATA[opName];
  if (!meta) {
    console.warn(`Operator '${opName}' metadata not defined.`);
    return;
  }

  // Handle two-phase boolean workflow if operator needs both target and tool
  if (meta.needsTarget && meta.needsTool) {
    startBooleanWorkflow(opName, async (workflowResult) => {
      await _dispatchCommand({
        command_id: `c_${Date.now()}`,
        op: workflowResult.op,
        target: workflowResult.target,
        tool: workflowResult.tool,
        params: customParams,
        idempotency_key: `cmd_${opName}_${Date.now()}`,
      });
    });
    return;
  }

  let targetRef = null;
  if (meta.needsTarget) {
    const selections = context.getSelection();
    if (!selections.length) {
      const targetHint = meta.targetType === 'edge' ? '特征边 (按 2 进入边模式)' : '拓扑面 (按 3 进入面模式)';
      alert(`【${meta.title}】需要先在视口中选择一个${targetHint}`);
      return;
    }
    targetRef = { base: 'prev', expr: selections[0] };
  }

  const mergedParams = { ...(meta.defaultParams || {}), ...customParams };
  const cmdId = `c_${Date.now()}`;
  const cmdPayload = {
    command_id: cmdId,
    op: opName,
    target: targetRef,
    tool: null,
    params: mergedParams,
    idempotency_key: `cmd_${opName}_${Date.now()}`,
  };

  await _dispatchCommand(cmdPayload);
}

async function _dispatchCommand(cmdPayload) {
  const statusEl = document.getElementById('status-text');
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

    if (statusEl) {
      statusEl.textContent = `成功执行: ${cmdPayload.op} (v${res.version})`;
      statusEl.style.color = '#98c379';
    }
  } catch (err) {
    if (statusEl) {
      statusEl.textContent = `执行受限: ${err.message}`;
      statusEl.style.color = '#e06c75';
    }
  }
}

context.on('operator:run', ({ op, params }) => {
  runOperator(op, params || {});
});
