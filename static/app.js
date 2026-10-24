/**
 * SMLib Studio Next · Main Controller (< 250 lines)
 * Assembles viewport, selection, modal ops, sketcher, boundary, and agent modules.
 */

import { ctx } from './js/context.js';
import {
  buildBrepScene, container, setCameraType, setStandardView, setXrayMode, startAnimationLoop,
} from './js/viewport.js';
import {
  handlePointerClick, handlePointerMove,
} from './js/selection.js';
import {
  attachGizmoToActiveModel, executeOperator, handleModalMouseMove, isModalActive,
  renderAdjustLastPanel, resetAxesConstraints, transformControls,
} from './js/modal_ops.js';
import {
  handleSketchClick, handleSketchMouseMove, isSketchingActive, startSketchSession,
} from './js/sketcher.js';
import {
  assignFacePatch, toggleBoundaryMode, updateBoundaryVisuals,
} from './js/boundary.js';
import {
  initAgentPanel,
} from './js/agent_panel.js';

// --- 1. Global Viewport Interaction Dispatcher ---
let pointerDownPos = { x: 0, y: 0 };

container.addEventListener('pointerdown', (e) => {
  pointerDownPos = { x: e.clientX, y: e.clientY };
  // Hide Shift+A add menu if clicked outside
  const menu = document.getElementById('add-menu-popup');
  if (menu && !menu.contains(e.target)) {
    menu.classList.add('hidden');
  }
});

container.addEventListener('pointermove', (e) => {
  if (isModalActive()) {
    handleModalMouseMove(e);
  } else if (isSketchingActive()) {
    handleSketchMouseMove(e.clientX, e.clientY);
  } else {
    handlePointerMove(e.clientX, e.clientY);
  }
});

container.addEventListener('pointerup', async (e) => {
  const dist = Math.hypot(e.clientX - pointerDownPos.x, e.clientY - pointerDownPos.y);
  if (dist > 5) return; // Orbiting camera, ignore click

  if (isSketchingActive()) {
    await handleSketchClick(e.clientX, e.clientY);
  } else if (!isModalActive()) {
    handlePointerClick(e.clientX, e.clientY, e.shiftKey);
  }
});

// --- 2. Top Toolbar & Shortcut Keymaps ---
const statusText = document.getElementById('status-text');
export function setStatus(msg, isErr = false) {
  if (statusText) {
    statusText.textContent = msg;
    statusText.style.color = isErr ? '#e06c75' : '';
  }
}

// Mode & Selection Level Switching
document.querySelectorAll('#selection-mode-group button[data-sel-mode]').forEach((btn) => {
  btn.onclick = () => {
    document.querySelectorAll('#selection-mode-group button').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const mode = btn.dataset.selMode;
    ctx.setMode(mode === 'solid' ? 'OBJECT' : 'EDIT');
    ctx.setSelectionLevel(mode);
    attachGizmoToActiveModel();
    updateHudText();
  };
});

function updateHudText() {
  const tag = document.getElementById('hud-mode-tag');
  if (tag) {
    if (ctx.mode === 'OBJECT') {
      tag.textContent = '模式: 对象模式 [Tab 切换]';
      tag.style.color = '#ffd885';
    } else {
      tag.textContent = `模式: 编辑模式 (${ctx.selectionLevel.toUpperCase()}) [Tab 切换]`;
      tag.style.color = '#61afef';
    }
  }
}

// Blender Standard Shortcuts
window.addEventListener('keydown', (e) => {
  const tag = (e.target.tagName || '').toLowerCase();
  if (tag === 'input' || tag === 'textarea') return;

  if (e.key === 'Tab') {
    e.preventDefault();
    const nextMode = ctx.mode === 'OBJECT' ? 'EDIT' : 'OBJECT';
    ctx.setMode(nextMode);
    if (nextMode === 'EDIT' && ctx.selectionLevel === 'solid') {
      ctx.setSelectionLevel('face');
    } else if (nextMode === 'OBJECT') {
      ctx.setSelectionLevel('solid');
    }
    syncSelectionNavButtons();
    attachGizmoToActiveModel();
    updateHudText();
    return;
  }

  if (ctx.mode === 'EDIT') {
    if (e.key === '1') { ctx.setSelectionLevel('vertex'); syncSelectionNavButtons(); updateHudText(); return; }
    if (e.key === '2') { ctx.setSelectionLevel('edge'); syncSelectionNavButtons(); updateHudText(); return; }
    if (e.key === '3') { ctx.setSelectionLevel('face'); syncSelectionNavButtons(); updateHudText(); return; }
  }

  // Shift + A: Add Menu popup at mouse cursor
  if (e.shiftKey && (e.key === 'a' || e.key === 'A')) {
    e.preventDefault();
    const menu = document.getElementById('add-menu-popup');
    if (menu) {
      menu.style.left = `${Math.min(pointerDownPos.x || 300, window.innerWidth - 200)}px`;
      menu.style.top = `${Math.min(pointerDownPos.y || 200, window.innerHeight - 340)}px`;
      menu.classList.remove('hidden');
    }
    return;
  }

  // Alt + Z: X-Ray toggle
  if (e.altKey && (e.key === 'z' || e.key === 'Z')) {
    e.preventDefault();
    ctx.isXrayMode = !ctx.isXrayMode;
    setXrayMode(ctx.isXrayMode);
    setStatus(ctx.isXrayMode ? '已开启 X-Ray 半透明透视' : '已恢复实体着色');
    return;
  }

  // G / R / S Transform Shortcuts in Object Mode
  if (ctx.mode === 'OBJECT') {
    if (e.key === 'g' || e.key === 'G') {
      e.preventDefault();
      transformControls.setMode('translate');
      resetAxesConstraints();
      transformControls.visible = true;
      setStatus('变换: 平移 (G) · 拖动手柄移动，按 X/Y/Z 可锁定轴向');
    } else if (e.key === 'r' || e.key === 'R') {
      e.preventDefault();
      transformControls.setMode('rotate');
      resetAxesConstraints();
      transformControls.visible = true;
      setStatus('变换: 旋转 (R) · 拖动手柄旋转');
    } else if (e.key === 's' || e.key === 'S') {
      e.preventDefault();
      transformControls.setMode('scale');
      resetAxesConstraints();
      transformControls.visible = true;
      setStatus('变换: 缩放 (S)');
    }
  }

  // X / Y / Z axis constraints during transform
  if (transformControls.visible) {
    if (e.key === 'x' || e.key === 'X') { transformControls.showX = true; transformControls.showY = false; transformControls.showZ = false; setStatus('锁定 X 轴向'); }
    if (e.key === 'y' || e.key === 'Y') { transformControls.showX = false; transformControls.showY = true; transformControls.showZ = false; setStatus('锁定 Y 轴向'); }
    if (e.key === 'z' || e.key === 'Z') { transformControls.showX = false; transformControls.showY = false; transformControls.showZ = true; setStatus('锁定 Z 轴向'); }
  }
});

function syncSelectionNavButtons() {
  document.querySelectorAll('#selection-mode-group button').forEach((b) => {
    b.classList.toggle('active', b.dataset.selMode === ctx.selectionLevel);
  });
}

// Camera views
document.getElementById('btn-iso').onclick = () => setStandardView('iso');
document.getElementById('btn-front').onclick = () => setStandardView('front');
document.getElementById('btn-top').onclick = () => setStandardView('top');
document.getElementById('btn-right').onclick = () => setStandardView('right');
document.getElementById('btn-fit').onclick = () => setStandardView('fit');

// Camera & Layer Toggles
document.getElementById('btn-camera-toggle').onclick = (e) => {
  const isOrtho = e.currentTarget.classList.toggle('active');
  e.currentTarget.textContent = isOrtho ? '正交' : '透视';
  setCameraType(isOrtho ? 'orthographic' : 'perspective');
};
document.getElementById('btn-grid-toggle').onclick = (e) => {
  const active = e.currentTarget.classList.toggle('active');
  const gh = scene.getObjectByName('GridHelper');
  if (gh) gh.visible = active;
};
document.getElementById('btn-axes-toggle').onclick = (e) => {
  const active = e.currentTarget.classList.toggle('active');
  const ax = scene.getObjectByName('AxesHelper');
  if (ax) ax.visible = active;
};
document.getElementById('btn-xray-toggle').onclick = () => {
  ctx.isXrayMode = !ctx.isXrayMode;
  setXrayMode(ctx.isXrayMode);
};
document.getElementById('btn-toggle-boundary-mode').onclick = (e) => {
  const active = toggleBoundaryMode();
  e.currentTarget.classList.toggle('active', active);
  setStatus(active ? '已开启【🌊 物理边界模式】：高亮显示各边界补丁' : '已退出边界模式：恢复标准 CAD 天蓝外观');
};

// Left T-Panel Tool Chips & Shift+A menu items
document.querySelectorAll('.tool-chip[data-op], .add-menu-item[data-op]').forEach((btn) => {
  btn.onclick = async () => {
    const op = btn.dataset.op;
    document.getElementById('add-menu-popup').classList.add('hidden');
    if (['line', 'rectangle', 'circle', 'arc', 'polyline', 'spline'].includes(op)) {
      startSketchSession(op);
    } else {
      try {
        await executeOperator(op);
        setStatus(`已执行: ${op}`);
      } catch (err) {
        setStatus(`执行失败: ${err.message}`, true);
      }
    }
  };
});

// Floating Face Action Pill (Inlet/Outlet/Wall/Interface)
document.querySelectorAll('.face-action-pill .pill-btn').forEach((btn) => {
  btn.onclick = async () => {
    if (ctx.selections.length === 1 && ctx.selections[0].type === 'face') {
      const fIdx = ctx.selections[0].index;
      const ptype = btn.dataset.ptype;
      try {
        const patch = await assignFacePatch(fIdx, ptype);
        document.getElementById('btn-toggle-boundary-mode').classList.add('active');
        setStatus(`已标记 Face #${fIdx} 为【${patch.name}】(${ptype})`);
      } catch (err) {
        setStatus(`标注失败: ${err.message}`, true);
      }
    }
  };
});

// Right Tab Switcher
document.querySelectorAll('.tab-btn').forEach((btn) => {
  btn.onclick = () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    const pane = document.getElementById(`tab-${btn.dataset.tab}`);
    if (pane) pane.classList.add('active');
  };
});

// Script editor actions & Undo / Redo
const scriptEditor = document.getElementById('script-editor');
document.getElementById('btn-run-script').onclick = async () => {
  const code = scriptEditor.value.trim();
  if (!code) return;
  const res = await fetch('/api/workspace/run_script', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ script: code, replace_all: true }),
  });
  const data = await res.json();
  if (res.ok) {
    ctx.setSceneData(data.scene);
    ctx.setPatches(data.patches);
    setStatus(`脚本执行成功 · 体积: ${data.scene.summary.volume} mm³`);
  } else {
    alert(`脚本执行失败:\n${data.detail}`);
  }
};
document.getElementById('btn-undo').onclick = async () => {
  const res = await fetch('/api/workspace/undo', { method: 'POST' });
  const data = await res.json();
  if (res.ok) { ctx.setSceneData(data.scene); ctx.setPatches(data.patches); }
};
document.getElementById('btn-redo').onclick = async () => {
  const res = await fetch('/api/workspace/redo', { method: 'POST' });
  const data = await res.json();
  if (res.ok) { ctx.setSceneData(data.scene); ctx.setPatches(data.patches); }
};

// Exports
function download(url) {
  const a = document.createElement('a'); a.href = url; a.download = ''; a.click();
}
document.getElementById('btn-export-step').onclick = () => download('/api/export/step');
document.getElementById('btn-export-cfd').onclick = () => download('/api/export/cfd_meta');
document.getElementById('btn-export-stl').onclick = () => download('/api/export/stl');
document.getElementById('btn-export-gltf').onclick = () => download('/api/export/gltf');
document.getElementById('btn-export-py').onclick = () => download('/api/export/py');

// --- 3. Scene State Listener ---
ctx.on('scene:updated', (sceneData) => {
  buildBrepScene(sceneData);
  attachGizmoToActiveModel();
  if (scriptEditor && sceneData.script) {
    scriptEditor.value = sceneData.script;
  }
  const sum = sceneData.summary || {};
  document.getElementById('stat-volume').textContent = `${(sum.volume || 0).toLocaleString()} mm³`;
  document.getElementById('stat-area').textContent = `${(sum.area || 0).toLocaleString()} mm²`;
  document.getElementById('stat-faces').textContent = sum.faces_count || 0;
  document.getElementById('stat-edges').textContent = sum.edges_count || 0;
});

// Bootstrapping
async function initApp() {
  startAnimationLoop();
  initAgentPanel();
  const res = await fetch('/api/workspace/state');
  const data = await res.json();
  if (data.ok) {
    ctx.setSceneData(data.scene);
    ctx.setPatches(data.patches);
    if (scriptEditor) scriptEditor.value = data.script;
  }
}

initApp();

// Globals for automated browser verification
window.ctx = ctx;
window.transformControls = transformControls;
