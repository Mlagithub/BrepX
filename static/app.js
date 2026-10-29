import { ctx } from './js/context.js';
import {
  buildBrepScene, container, resizeViewport, scene, setCameraType, setXrayMode, startAnimationLoop,
} from './js/viewport.js';
import { setStandardViewSmooth } from './js/view_cube.js';
import { handlePointerClick, handlePointerMove } from './js/selection.js';
import {
  attachGizmoToActiveModel, confirmModalOperation, executeOperator, handleModalMouseMove, isModalActive,
  resetAxesConstraints, transformControls,
} from './js/modal_ops.js';
import {
  handleSketchClick, handleSketchMouseMove, isSketchingActive, startSketchSession,
} from './js/sketcher.js';
import { assignFacePatch, toggleBoundaryMode } from './js/boundary.js';
import { initAgentPanel } from './js/agent_panel.js';

let pointerDownPos = { x: 0, y: 0 };

// 全局视口交互事件分发与模态/草图状态路由
container.addEventListener('pointerdown', (e) => {
  pointerDownPos = { x: e.clientX, y: e.clientY };
  const menu = document.getElementById('add-menu-popup');
  if (menu && !menu.contains(e.target)) menu.classList.add('hidden');
});

container.addEventListener('pointermove', (e) => {
  if (isModalActive()) handleModalMouseMove(e);
  else if (isSketchingActive()) handleSketchMouseMove(e.clientX, e.clientY);
  else handlePointerMove(e.clientX, e.clientY);
});

container.addEventListener('pointerup', async (e) => {
  if (Math.hypot(e.clientX - pointerDownPos.x, e.clientY - pointerDownPos.y) > 5) return;
  if (isModalActive()) await confirmModalOperation();
  else if (isSketchingActive()) await handleSketchClick(e.clientX, e.clientY);
  else handlePointerClick(e.clientX, e.clientY, e.shiftKey);
});

// 状态提示与模式标签同步
const statusText = document.getElementById('status-text');
export function setStatus(msg, isErr = false) {
  if (statusText) {
    statusText.textContent = msg;
    statusText.style.color = isErr ? '#e06c75' : '';
  }
}

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
  if (!tag) return;
  if (ctx.isBoundaryMode) {
    tag.innerHTML = '<span class="hud-pill hud-pill-cfd">🌊 物理边界模式</span>';
  } else if (ctx.mode === 'OBJECT') {
    tag.innerHTML = '<span class="hud-pill hud-pill-object">● 对象模式 [Tab]</span>';
  } else {
    const levelMap = { face: '面 [3]', edge: '边 [2]', vertex: '点 [1]', solid: '实体' };
    tag.innerHTML = `<span class="hud-pill hud-pill-edit">● 编辑模式: ${levelMap[ctx.selectionLevel] || ctx.selectionLevel} [Tab]</span>`;
  }
}

function syncSelectionNavButtons() {
  document.querySelectorAll('#selection-mode-group button').forEach((b) => {
    b.classList.toggle('active', b.dataset.selMode === ctx.selectionLevel);
  });
}

// 全局 Blender 常用快捷键映射
window.addEventListener('keydown', async (e) => {
  const tag = (e.target.tagName || '').toLowerCase();
  if (tag === 'input' || tag === 'textarea' || tag === 'select' || e.target.isContentEditable) return;

  if (e.key === 'Tab') {
    e.preventDefault();
    const nextMode = ctx.mode === 'OBJECT' ? 'EDIT' : 'OBJECT';
    ctx.setMode(nextMode);
    ctx.setSelectionLevel(nextMode === 'EDIT' && ctx.selectionLevel === 'solid' ? 'face' : nextMode === 'OBJECT' ? 'solid' : ctx.selectionLevel);
    syncSelectionNavButtons();
    attachGizmoToActiveModel();
    updateHudText();
    return;
  }

  if (ctx.mode === 'EDIT' && ['1', '2', '3'].includes(e.key)) {
    const m = { '1': 'vertex', '2': 'edge', '3': 'face' };
    ctx.setSelectionLevel(m[e.key]);
    syncSelectionNavButtons();
    updateHudText();
    return;
  }

  // T / N 侧边栏折叠
  if (e.key === 't' || e.key === 'T') {
    document.getElementById('left-sidebar')?.classList.toggle('collapsed');
    setTimeout(resizeViewport, 220);
    return;
  }
  if (e.key === 'n' || e.key === 'N') {
    document.getElementById('right-sidebar')?.classList.toggle('collapsed');
    setTimeout(resizeViewport, 220);
    return;
  }

  // 特征面快速擦除填平
  if (e.key === 'Delete' || ((e.key === 'x' || e.key === 'X') && !transformControls.visible)) {
    if (ctx.selections.length > 0 && ctx.selections[0].type === 'face') {
      e.preventDefault();
      try {
        await executeOperator('remove_faces');
        setStatus('已执行特征面消除并缝合');
      } catch (err) {
        setStatus(`消除失败: ${err.message}`, true);
      }
      return;
    }
  }

  // Shift + A 添加菜单
  if (e.shiftKey && (e.key === 'a' || e.key === 'A')) {
    e.preventDefault();
    const menu = document.getElementById('add-menu-popup');
    if (menu) {
      menu.style.left = `${Math.min(pointerDownPos.x || 300, window.innerWidth - 220)}px`;
      menu.style.top = `${Math.min(pointerDownPos.y || 200, window.innerHeight - 360)}px`;
      menu.classList.remove('hidden');
    }
    return;
  }

  // Alt + Z 透视视图
  if (e.altKey && (e.key === 'z' || e.key === 'Z')) {
    e.preventDefault();
    ctx.isXrayMode = !ctx.isXrayMode;
    setXrayMode(ctx.isXrayMode);
    document.getElementById('btn-xray-toggle')?.classList.toggle('active', ctx.isXrayMode);
    setStatus(ctx.isXrayMode ? '已开启 X-Ray 半透明透视' : '已恢复实体着色');
    return;
  }

  // G / R / S 空间变换手柄
  if (ctx.mode === 'OBJECT' && ['g', 'r', 's'].includes(e.key.toLowerCase())) {
    e.preventDefault();
    const tMap = { g: 'translate', r: 'rotate', s: 'scale' };
    transformControls.setMode(tMap[e.key.toLowerCase()]);
    resetAxesConstraints();
    transformControls.visible = true;
    setStatus(`已启用变换手柄 [${e.key.toUpperCase()}]`);
  }

  if (transformControls.visible && ['x', 'y', 'z'].includes(e.key.toLowerCase())) {
    const k = e.key.toLowerCase();
    transformControls.showX = k === 'x';
    transformControls.showY = k === 'y';
    transformControls.showZ = k === 'z';
    setStatus(`锁定 ${k.toUpperCase()} 轴向`);
  }
});

// 标准视角平滑切换
['iso', 'front', 'top', 'right', 'fit'].forEach((v) => {
  const btn = document.getElementById(`btn-${v}`);
  if (btn) btn.onclick = () => setStandardViewSmooth(v);
});

// 相机与图层开关
document.getElementById('btn-camera-toggle').onclick = (e) => {
  const isOrtho = e.currentTarget.classList.toggle('active');
  e.currentTarget.textContent = isOrtho ? '📐 正交' : '📐 透视';
  setCameraType(isOrtho ? 'orthographic' : 'perspective');
  setStatus(isOrtho ? '已切换至正交投影模式' : '已切换至透视投影模式');
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
document.getElementById('btn-xray-toggle').onclick = (e) => {
  ctx.isXrayMode = !ctx.isXrayMode;
  e.currentTarget.classList.toggle('active', ctx.isXrayMode);
  setXrayMode(ctx.isXrayMode);
  setStatus(ctx.isXrayMode ? '已开启 X-Ray 半透明透视' : '已恢复实体着色');
};
document.getElementById('btn-toggle-boundary-mode').onclick = (e) => {
  const active = toggleBoundaryMode();
  e.currentTarget.classList.toggle('active', active);
  updateHudText();
  setStatus(active ? '已开启【🌊 物理边界模式】' : '已退出边界模式');
};

// 侧边栏折叠按钮
const toggleSide = (btnId, barId) => {
  const btn = document.getElementById(btnId);
  const bar = document.getElementById(barId);
  if (btn && bar) {
    btn.onclick = () => {
      btn.classList.toggle('active', bar.classList.toggle('collapsed'));
      setTimeout(resizeViewport, 220);
    };
  }
};
toggleSide('btn-toggle-left-panel', 'left-sidebar');
toggleSide('btn-toggle-right-panel', 'right-sidebar');

// 算子芯片与 Shift+A 菜单事件绑定
document.querySelectorAll('.tool-chip[data-op], .add-menu-item[data-op]').forEach((btn) => {
  btn.onclick = async () => {
    const op = btn.dataset.op;
    document.getElementById('add-menu-popup')?.classList.add('hidden');
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

// 选定面浮动打标条（支持单面与多选批量打标）
document.querySelectorAll('.face-action-pill .pill-btn').forEach((btn) => {
  btn.onclick = async () => {
    const faceSels = ctx.selections.filter(s => s.type === 'face');
    if (!faceSels.length) return;
    const indices = faceSels.map(f => f.index);
    const ptype = btn.dataset.ptype;
    try {
      const patch = await assignFacePatch(indices, ptype);
      document.getElementById('btn-toggle-boundary-mode')?.classList.add('active');
      setStatus(`已批量标记 [${indices.join(', ')}] 为【${patch.name}】(${ptype})`);
    } catch (err) {
      setStatus(`标注失败: ${err.message}`, true);
    }
  };
});

// 右侧 Tab 切换
document.querySelectorAll('.tab-btn').forEach((btn) => {
  btn.onclick = () => {
    document.querySelectorAll('.tab-btn').forEach(b => {
      b.classList.remove('active');
      b.setAttribute('aria-selected', 'false');
    });
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    btn.setAttribute('aria-selected', 'true');
    document.getElementById(`tab-${btn.dataset.tab}`)?.classList.add('active');
  };
});

// 脚本编辑器与撤销重做
const scriptEditor = document.getElementById('script-editor');
document.getElementById('btn-run-script').onclick = async () => {
  const code = scriptEditor?.value.trim();
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
['undo', 'redo'].forEach((action) => {
  const btn = document.getElementById(`btn-${action}`);
  if (btn) btn.onclick = async () => {
    const res = await fetch(`/api/workspace/${action}`, { method: 'POST' });
    const data = await res.json();
    if (res.ok) {
      ctx.setSceneData(data.scene);
      ctx.setPatches(data.patches);
      if (data.can_undo !== undefined) {
        document.getElementById('btn-undo')?.toggleAttribute('disabled', !data.can_undo);
        document.getElementById('btn-redo')?.toggleAttribute('disabled', !data.can_redo);
      }
    }
  };
});

// 交付导出
const download = (url) => { const a = document.createElement('a'); a.href = url; a.download = ''; a.click(); };
const exportMap = { step: '/api/export/step', cfd: '/api/export/cfd_meta', stl: '/api/export/stl', gltf: '/api/export/gltf', py: '/api/export/py' };
Object.keys(exportMap).forEach((t) => {
  document.getElementById(`btn-export-${t}`)?.addEventListener('click', () => download(exportMap[t]));
});

// 响应全局上下文场景状态同步三维渲染与数据看板
ctx.on('scene:updated', (sceneData) => {
  buildBrepScene(sceneData);
  attachGizmoToActiveModel();
  if (scriptEditor && sceneData.script) scriptEditor.value = sceneData.script;
  const sum = sceneData.summary || {};
  document.getElementById('stat-volume').textContent = `${(sum.volume || 0).toLocaleString()} mm³`;
  document.getElementById('stat-area').textContent = `${(sum.area || 0).toLocaleString()} mm²`;
  document.getElementById('stat-faces').textContent = sum.faces_count || 0;
  document.getElementById('stat-edges').textContent = sum.edges_count || 0;
  if (sum.bbox) {
    const s = sum.bbox.size || [0, 0, 0];
    document.getElementById('stat-bbox').textContent = `${Math.round(s[0])}×${Math.round(s[1])}×${Math.round(s[2])}`;
  }
});

// 系统启动引导
async function initApp() {
  startAnimationLoop();
  initAgentPanel();
  const res = await fetch('/api/workspace/state');
  const data = await res.json();
  if (data.ok) {
    ctx.setSceneData(data.scene);
    ctx.setPatches(data.patches);
    if (scriptEditor) scriptEditor.value = data.script;
    if (data.can_undo !== undefined) {
      document.getElementById('btn-undo')?.toggleAttribute('disabled', !data.can_undo);
      document.getElementById('btn-redo')?.toggleAttribute('disabled', !data.can_redo);
    }
  }
}

initApp();

window.ctx = ctx;
window.transformControls = transformControls;
