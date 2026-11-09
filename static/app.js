/**
 * BrepX Viewport Application Controller.
 * Assembles reactive context, viewport rendering, modal operators, and toolbar actions.
 */

import { fetchQuery, fetchScene, redo, undo } from './js/api.js?v=10';
import { initBodiesTree, renderBodiesList } from './js/bodies_tree.js?v=10';
import { handleBooleanTopologyPick, isBooleanWorkflowActive } from './js/boolean_workflow.js?v=10';
import { initCommandPalette } from './js/command_palette.js?v=10';
import { showContextMenu } from './js/context_menu.js?v=10';
import { context } from './js/context.js?v=10';
import { toggleDatumPlanes } from './js/datum_planes.js?v=10';
import { setDisplayMode } from './js/display_modes.js?v=10';
import { initMeasureInspector } from './js/measure_inspector.js?v=10';
import { handleMeasurePick, toggleMeasureTool } from './js/measure_tool.js?v=10';
import {
  confirmModalOperation,
  handleModalMouseMove,
  isModalActive,
} from './js/modal_ops.js?v=10';
import { openPieMenu } from './js/pie_menu.js?v=10';
import { initPythonViewer } from './js/python_viewer.js?v=10';
import { toggleSectionTool } from './js/section_tool.js?v=10';
import { handlePointerClick, handlePointerMove, rebuildRaycastCache } from './js/selection.js?v=10';
import { initTimeline } from './js/timeline.js?v=10';
import { renderToolbar } from './js/toolbar.js?v=10';
import { setStandardViewSmooth } from './js/view_cube.js?v=10';
import {
  alignCameraNormalTo,
  buildBrepScene,
  container,
  resizeViewport,
  setCameraType,
  setXrayMode,
  startAnimationLoop,
} from './js/viewport.js?v=10';
import { initAgentPanel } from './js/agent_panel.js?v=10';

window.context = context;

let pointerDownPos = { x: 0, y: 0 };

container.addEventListener('pointerdown', (e) => {
  pointerDownPos = { x: e.clientX, y: e.clientY };
});

container.addEventListener('pointermove', (e) => {
  if (isModalActive()) handleModalMouseMove(e);
  else handlePointerMove(e.clientX, e.clientY);
});

container.addEventListener('pointerup', async (e) => {
  if (Math.hypot(e.clientX - pointerDownPos.x, e.clientY - pointerDownPos.y) > 5) return;

  if (isModalActive()) {
    await confirmModalOperation();
  } else if (isBooleanWorkflowActive()) {
    const sel = context.getSelection()[0];
    if (sel) handleBooleanTopologyPick(sel);
  } else {
    handlePointerClick(e.clientX, e.clientY, e.shiftKey);
  }
});

container.addEventListener('contextmenu', (e) => {
  e.preventDefault();
  const sels = context.getSelection();
  const targetType = sels.length > 0 ? (sels[0].startsWith('faces()') ? 'face' : 'edge') : 'empty';
  showContextMenu(e.clientX, e.clientY, targetType, null);
});

document.querySelectorAll('#selection-mode-group button[data-sel-mode]').forEach((btn) => {
  btn.onclick = () => {
    document.querySelectorAll('#selection-mode-group button').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const mode = btn.dataset.selMode;
    context.setSelectionLevel(mode);
    updateHudText();
  };
});

function updateHudText() {
  const tag = document.getElementById('hud-mode-tag');
  if (!tag) return;
  const levelMap = { face: '面 [3]', edge: '边 [2]', vertex: '点 [1]' };
  tag.innerHTML = `<span class="hud-pill hud-pill-edit">● 编辑模式: ${levelMap[context.selectionLevel] || context.selectionLevel}</span>`;
}

// Side panels toggle with raycast bounds update
const toggleSidebar = (btnId, barId) => {
  const btn = document.getElementById(btnId);
  const bar = document.getElementById(barId);
  if (btn && bar) {
    btn.onclick = () => {
      btn.classList.toggle('active', bar.classList.toggle('collapsed'));
      setTimeout(() => {
        resizeViewport();
        rebuildRaycastCache();
      }, 220);
    };
  }
};
toggleSidebar('btn-toggle-left-panel', 'left-sidebar');
toggleSidebar('btn-toggle-right-panel', 'right-sidebar');

window.addEventListener('keydown', async (e) => {
  const tag = (e.target.tagName || '').toLowerCase();
  if (tag === 'input' || tag === 'textarea' || tag === 'select' || e.target.isContentEditable) return;

  if (['1', '2', '3'].includes(e.key)) {
    const m = { '1': 'vertex', '2': 'edge', '3': 'face' };
    context.setSelectionLevel(m[e.key]);
    document.querySelectorAll('#selection-mode-group button').forEach((b) => {
      b.classList.toggle('active', b.dataset.selMode === context.selectionLevel);
    });
    updateHudText();
    return;
  }

  if (e.key === 't' || e.key === 'T') {
    document.getElementById('left-sidebar')?.classList.toggle('collapsed');
    setTimeout(resizeViewport, 200);
    return;
  }

  if (e.key === 'n' || e.key === 'N') {
    document.getElementById('right-sidebar')?.classList.toggle('collapsed');
    setTimeout(resizeViewport, 200);
    return;
  }

  if (e.key === 'z' || e.key === 'Z') {
    if (!e.ctrlKey && !e.metaKey && !e.altKey) {
      e.preventDefault();
      openPieMenu(pointerDownPos.x || window.innerWidth / 2, pointerDownPos.y || window.innerHeight / 2);
      return;
    }
  }

  if ((e.ctrlKey || e.metaKey) && (e.key === '8')) {
    e.preventDefault();
    const sels = context.getSelection();
    if (sels.length > 0) {
      alignCameraNormalTo({ normal: [0, 0, 1] });
    }
    return;
  }

  if ((e.ctrlKey || e.metaKey) && (e.key === 'z' || e.key === 'Z')) {
    e.preventDefault();
    await handleUndo();
    return;
  }

  if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || e.key === 'Y')) {
    e.preventDefault();
    await handleRedo();
    return;
  }
});

['iso', 'front', 'top', 'right', 'fit'].forEach((v) => {
  const btn = document.getElementById(`btn-${v}`);
  if (btn) btn.onclick = () => setStandardViewSmooth(v);
});

document.getElementById('btn-normal-to').onclick = () => {
  alignCameraNormalTo({ normal: [0, 0, 1] });
};

document.getElementById('btn-datum-toggle').onclick = (e) => {
  const active = toggleDatumPlanes();
  e.currentTarget.classList.toggle('active', active);
};

document.getElementById('btn-section-toggle').onclick = (e) => {
  const active = toggleSectionTool();
  e.currentTarget.classList.toggle('active', active);
};

document.getElementById('btn-measure-toggle').onclick = (e) => {
  const active = toggleMeasureTool();
  e.currentTarget.classList.toggle('active', active);
};

document.getElementById('btn-xray-toggle').onclick = (e) => {
  const active = e.currentTarget.classList.toggle('active');
  setXrayMode(active);
};

const download = (url) => { const a = document.createElement('a'); a.href = url; a.download = ''; a.click(); };
document.getElementById('btn-export-step').onclick = () => download('/api/export/step');
document.getElementById('btn-export-stl').onclick = () => download('/api/export/stl');
document.getElementById('btn-export-dxf').onclick = () => download('/api/export/dxf');
document.getElementById('btn-export-cfd').onclick = () => download('/api/export/cfd-dict');

async function handleUndo() {
  try {
    const res = await undo();
    const sceneData = await fetchScene();
    if (res.journal) context.setJournal(res.journal);
    context.setSnapshot(res.version, res.body, sceneData);
  } catch (err) {
    console.warn('Undo error:', err);
  }
}

async function handleRedo() {
  try {
    const res = await redo();
    const sceneData = await fetchScene();
    if (res.journal) context.setJournal(res.journal);
    context.setSnapshot(res.version, res.body, sceneData);
  } catch (err) {
    console.warn('Redo error:', err);
  }
}

document.getElementById('btn-undo').onclick = handleUndo;
document.getElementById('btn-redo').onclick = handleRedo;

document.querySelectorAll('.tab-btn[data-tab]').forEach((btn) => {
  btn.onclick = () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(`tab-${btn.dataset.tab}`)?.classList.add('active');
  };
});

context.on('snapshot:changed', ({ version, body, scene: sceneData }) => {
  if (sceneData) {
    buildBrepScene(sceneData);
    renderBodiesList();
    rebuildRaycastCache();
  }
  if (body) {
    const statusEl = document.getElementById('status-text');
    if (statusEl && !statusEl.textContent.includes('执行')) {
      statusEl.textContent = `就绪 · v${version} (${(body.volume || 0).toLocaleString()} mm³)`;
    }
  }
});

async function initApp() {
  startAnimationLoop();
  renderToolbar(document.getElementById('toolbar-container'));
  initBodiesTree(document.getElementById('bodies-tree-container'));
  initTimeline(document.getElementById('timeline-bar-root'));
  initAgentPanel(document.getElementById('agent-panel-container'));
  initMeasureInspector(document.getElementById('measure-inspector-container'));
  initPythonViewer(document.getElementById('python-viewer-textarea'));
  try {
    const [qData, sData] = await Promise.all([fetchQuery(), fetchScene()]);
    if (qData.journal) context.setJournal(qData.journal);
    context.setSnapshot(qData.version, qData.body, sData);
  } catch (err) {
    console.warn('Initial fetch error:', err);
  }
}

initApp();
