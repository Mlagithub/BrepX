import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/GLTFLoader.js';

import {
  container, scene, renderer, activeCamera, perspCamera, orthoCamera, controls,
  gridHelper, axesHelper, fitCameraToObject, setStandardView, startAnimationLoop, setActiveCamera
} from './js/viewport.js';

import {
  transformControls, resetAxesConstraints, toggleXrayMode, setTransformFinishedCallback, getIsXrayMode
} from './js/gizmo.js';

import {
  performSelectionPick, clearHighlights
} from './js/selection.js';

import {
  setBoundaryMode, setBoundaryPatches, markFaceSemantic, updateBoundaryVisuals, getIsBoundaryMode
} from './js/boundary.js';

import {
  openToolModal, setToolExecuteCallback, RIGHT_TOOLS_SCHEMA
} from './js/tools.js';

import {
  initAgentUI, sendAgentMessage, appendChatBubble
} from './js/agent.js';

// --- 全局应用状态 ---
export const state = {
  template: 'flange',
  params: {},
  cameraType: 'perspective',
  showGrid: true,
  showAxes: true,
  showEdges: true,
  currentPartGroup: null,
  isBuilding: false,
  selectionMode: 'solid',
  currentHitFace: null,
};

// 预设参数化模板定义
const TEMPLATE_CONFIGS = {
  flange: {
    name: '带孔圆角板 / 机械法兰',
    params: [
      { key: 'length', label: '基板长度 X (mm)', min: 40, max: 200, step: 2, default: 100 },
      { key: 'width', label: '基板宽度 Y (mm)', min: 30, max: 160, step: 2, default: 80 },
      { key: 'thickness', label: '厚度 Z (mm)', min: 4, max: 50, step: 1, default: 12 },
      { key: 'fillet_r', label: '四角圆角半径 (mm)', min: 0, max: 30, step: 1, default: 10 },
      { key: 'center_hole_r', label: '中心通孔半径 (mm)', min: 0, max: 40, step: 1, default: 15 },
      { key: 'bolt_holes', label: '安装螺栓孔', type: 'boolean', default: true },
      { key: 'bolt_hole_r', label: '螺栓孔径 (mm)', min: 2, max: 12, step: 0.5, default: 4 },
      { key: 'bolt_offset_x', label: '螺栓 X 偏移 (mm)', min: 10, max: 90, step: 1, default: 35 },
      { key: 'bolt_offset_y', label: '螺栓 Y 偏移 (mm)', min: 10, max: 70, step: 1, default: 25 },
    ]
  },
  bracket: {
    name: 'L型加筋角码 / 结构支架',
    params: [
      { key: 'length', label: '长度 X (mm)', min: 40, max: 150, step: 2, default: 80 },
      { key: 'width', label: '宽度 Y (mm)', min: 30, max: 120, step: 2, default: 50 },
      { key: 'height', label: '高度 Z (mm)', min: 40, max: 150, step: 2, default: 60 },
      { key: 'thickness', label: '壁厚 (mm)', min: 4, max: 25, step: 1, default: 10 },
      { key: 'fillet_r', label: '过渡圆角半径 (mm)', min: 0, max: 15, step: 1, default: 6 },
      { key: 'hole_r', label: '安装孔半径 (mm)', min: 0, max: 15, step: 1, default: 6 },
    ]
  },
  bushing: {
    name: '法兰轴套 / 衬套',
    params: [
      { key: 'od', label: '主体外径 (mm)', min: 20, max: 100, step: 2, default: 40 },
      { key: 'id', label: '内孔直径 (mm)', min: 10, max: 80, step: 2, default: 20 },
      { key: 'length', label: '总长度 (mm)', min: 20, max: 150, step: 2, default: 60 },
      { key: 'flange_od', label: '台阶法兰外径 (mm)', min: 30, max: 140, step: 2, default: 60 },
      { key: 'flange_len', label: '法兰厚度 (mm)', min: 4, max: 30, step: 1, default: 12 },
    ]
  },
  csg_demo: {
    name: '经典 CSG 球芯布尔体',
    params: [
      { key: 'box_size', label: '立方体边长 (mm)', min: 30, max: 120, step: 2, default: 50 },
      { key: 'sphere_r', label: '球体半径 (mm)', min: 20, max: 80, step: 1, default: 32 },
      { key: 'cyl_r', label: '三向贯穿孔半径 (mm)', min: 8, max: 35, step: 1, default: 18 },
    ]
  }
};

// UI 元素引用
const loadingOverlay = document.getElementById('loading-overlay');
const loadingMsg = document.getElementById('loading-msg');
const statusText = document.getElementById('status-text');
const scriptEditor = document.getElementById('script-editor');
const paramForm = document.getElementById('parametric-form');
const templateSelect = document.getElementById('template-select');
const selBadgeMode = document.getElementById('sel-badge-mode');
const selSubInfo = document.getElementById('sel-sub-info');
const selectionFields = document.getElementById('selection-fields');
const hudModeTag = document.getElementById('hud-mode-tag');
const addMenuPopup = document.getElementById('add-menu-popup');
const btnToggleBoundary = document.getElementById('btn-toggle-boundary-mode');

export function showLoading(msg = '正在调用 SMLib 几何内核计算…') {
  if (loadingMsg) loadingMsg.textContent = msg;
  if (loadingOverlay) loadingOverlay.classList.remove('hidden');
}

export function hideLoading() {
  if (loadingOverlay) loadingOverlay.classList.add('hidden');
}

export function showStatus(text, isError = false) {
  if (!statusText) return;
  statusText.textContent = text;
  statusText.style.color = isError ? '#e06c75' : '';
}

// --- GLTF 几何解析与视口刷新 ---
const gltfLoader = new GLTFLoader();

export function renderModelGLTF(gltfContent) {
  gltfLoader.parse(gltfContent, '', (gltf) => {
    if (state.currentPartGroup) {
      scene.remove(state.currentPartGroup);
      state.currentPartGroup.traverse((child) => {
        if (child.geometry) child.geometry.dispose();
        if (child.material) {
          if (Array.isArray(child.material)) child.material.forEach(m => m.dispose());
          else child.material.dispose();
        }
      });
      state.currentPartGroup = null;
    }

    const group = gltf.scene;

    // 解除 smlibpy 默认的 0.001 缩放，还原真实毫米尺寸
    group.traverse((child) => {
      if (child.scale && Math.abs(child.scale.x - 0.001) < 0.0001) {
        child.scale.set(1, 1, 1);
      }
    });

    let triangleCount = 0;
    group.traverse((child) => {
      if (child.isMesh) {
        triangleCount += child.geometry.index ? child.geometry.index.count / 3 : child.geometry.attributes.position.count / 3;
        child.material = new THREE.MeshStandardMaterial({
          color: 0x80baff,
          metalness: 0.15,
          roughness: 0.4,
          side: THREE.DoubleSide,
          polygonOffset: true,
          polygonOffsetFactor: 1,
          polygonOffsetUnits: 1
        });
        child.castShadow = true;
        child.receiveShadow = true;

        if (state.showEdges) {
          const edges = new THREE.EdgesGeometry(child.geometry, 28);
          const lineMaterial = new THREE.LineBasicMaterial({ color: 0x111c2e, linewidth: 2 });
          const lineSegments = new THREE.LineSegments(edges, lineMaterial);
          lineSegments.name = 'cad-edge-line';
          child.add(lineSegments);
        }
      } else if (child.isLineSegments) {
        child.material = new THREE.LineBasicMaterial({ color: 0x111c2e, linewidth: 2 });
        child.name = 'cad-edge-line';
      }
    });

    const triEl = document.getElementById('stat-triangles');
    if (triEl) triEl.textContent = Math.round(triangleCount).toLocaleString();

    scene.add(group);
    state.currentPartGroup = group;

    // 手柄重新挂载到新模型
    transformControls.attach(group);
    transformControls.visible = true;

    // 辅助网格对齐底面
    const box = new THREE.Box3().setFromObject(group);
    if (!box.isEmpty()) {
      gridHelper.position.y = box.min.y - 0.2;
    }

    fitCameraToObject(group);
    clearHighlights();
    updateTopologyView();
    updateBoundaryVisuals(group);
  }, (err) => {
    console.error('Failed to parse glTF:', err);
    showStatus('GLTF 解析失败: ' + err.message, true);
  });
}

// 更新总体积、面积与外形包围盒
async function updateTopologyView() {
  if (!state.currentPartGroup) return;
  const box = new THREE.Box3().setFromObject(state.currentPartGroup);
  if (!box.isEmpty()) {
    const size = box.getSize(new THREE.Vector3());
    const bboxEl = document.getElementById('stat-bbox');
    if (bboxEl) bboxEl.textContent = `${size.x.toFixed(1)} × ${size.y.toFixed(1)} × ${size.z.toFixed(1)} mm`;
  }

  try {
    const res = await fetch('/api/model/topology');
    const data = await res.json();
    if (data.ok) {
      const areaEl = document.getElementById('stat-area');
      if (areaEl) areaEl.textContent = `${data.area.toLocaleString()} mm²`;
      if (data.size && document.getElementById('stat-bbox')) {
        document.getElementById('stat-bbox').textContent = `${data.size[0]} × ${data.size[1]} × ${data.size[2]} mm`;
      }
    }
  } catch (err) {
    console.warn('Topology fetch error:', err);
  }
}

// 手柄拖拽松手回调
setTransformFinishedCallback(async (kind, params) => {
  showLoading(`正在执行【${kind}】几何变换…`);
  try {
    const res = await fetch('/api/transform', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        kind,
        dx: params.dx || 0,
        dy: params.dy || 0,
        dz: params.dz || 0,
        axis: params.axis || 'Z',
        angle: params.angle || 0,
        factor: params.factor || 1.0
      })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || '变换失败');
    renderModelGLTF(data.gltf);
    if (scriptEditor) scriptEditor.value = data.code;
    showStatus(`${data.explanation} · 耗时: ${data.stats.compute_ms} ms`);
  } catch (err) {
    showStatus(`变换失败: ${err.message}`, true);
  } finally {
    hideLoading();
  }
});

// 右侧工具弹窗执行回调
setToolExecuteCallback(async (toolKey, params, baseOnCurrent, schema) => {
  showLoading(`SMLib 正在执行【${schema.title}】运算…`);
  let res;
  if (['move', 'rotate', 'scale'].includes(toolKey)) {
    res = await fetch('/api/transform', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        kind: toolKey === 'move' ? 'translate' : toolKey,
        dx: params.dx || 0,
        dy: params.dy || 0,
        dz: params.dz || 0,
        axis: params.axis || 'Z',
        angle: params.angle || 0,
        factor: params.factor || 1.0
      })
    });
  } else {
    res = await fetch('/api/tools/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tool: toolKey, params, base_on_current: baseOnCurrent })
    });
  }

  const data = await res.json();
  if (!res.ok) {
    let msg = '工具运算失败';
    if (typeof data.detail === 'string') msg = data.detail;
    else if (Array.isArray(data.detail)) msg = data.detail.map(d => d.msg || JSON.stringify(d)).join('; ');
    throw new Error(msg);
  }

  renderModelGLTF(data.gltf);
  if (scriptEditor) scriptEditor.value = data.code;

  if (data.stats) {
    document.getElementById('stat-volume').textContent = `${data.stats.volume.toLocaleString()} mm³`;
    document.getElementById('stat-time').textContent = `${data.stats.compute_ms} ms`;
    showStatus(`${data.explanation} · 耗时: ${data.stats.compute_ms} ms`);
  }

  appendChatBubble('assistant', `🛠️ 执行工具【${schema.title}】：${data.explanation}`, {
    code: data.code,
    compute_ms: data.stats ? data.stats.compute_ms : null
  });
});

// Agent 回调绑定
initAgentUI(showLoading, hideLoading, showStatus);

// --- 模式与分级选择控制器 ---
let currentAppMode = 'OBJECT';
let lastCursorPos = { x: 300, y: 200 };

container.addEventListener('mousemove', (e) => {
  const rect = container.getBoundingClientRect();
  lastCursorPos = { x: e.clientX - rect.left, y: e.clientY - rect.top };
});

container.addEventListener('pointerdown', (e) => {
  if (addMenuPopup && !addMenuPopup.contains(e.target)) {
    addMenuPopup.classList.add('hidden');
  }
});

if (addMenuPopup) {
  addMenuPopup.querySelectorAll('.add-menu-item').forEach(item => {
    item.onclick = (e) => {
      e.stopPropagation();
      const tool = item.dataset.tool;
      addMenuPopup.classList.add('hidden');
      if (tool) openToolModal(tool);
    };
  });
}

function setAppMode(mode) {
  currentAppMode = mode;
  if (hudModeTag) {
    hudModeTag.textContent = mode === 'OBJECT' ? '模式: 对象模式 [Tab 切换]' : '模式: 编辑模式 (1点 2边 3面) [Tab 切换]';
    hudModeTag.style.color = mode === 'OBJECT' ? '#ffd885' : '#61afef';
  }
  showStatus(`已切换至: ${mode === 'OBJECT' ? '对象模式 (Object Mode)' : '编辑模式 (Edit Mode)'}`);
}

function switchSelectionModeTo(modeKey) {
  document.querySelectorAll('#selection-mode-group button').forEach(b => b.classList.remove('active'));
  const targetBtn = document.querySelector(`#selection-mode-group button[data-sel-mode="${modeKey}"]`);
  if (targetBtn) targetBtn.classList.add('active');
  state.selectionMode = modeKey;
  clearHighlights();

  const modeLabels = { solid: '实体 (Solid)', face: '面 (Face)', edge: '边 (Edge)', vertex: '点 (Vertex)' };
  if (selBadgeMode) selBadgeMode.textContent = `拾取: ${modeLabels[modeKey] || modeKey}`;
  if (selSubInfo) selSubInfo.textContent = '点击 3D 视图中相应部位进行高亮与分析';
  showStatus(`选择模式: ${modeLabels[modeKey]}`);
}

document.querySelectorAll('#selection-mode-group button[data-sel-mode]').forEach(btn => {
  btn.onclick = () => switchSelectionModeTo(btn.dataset.selMode);
});

// 画布点击触发分级拾取
let pointerDownCoord = { x: 0, y: 0 };
container.addEventListener('pointerdown', (e) => {
  pointerDownCoord = { x: e.clientX, y: e.clientY };
});

container.addEventListener('pointerup', (e) => {
  const dist = Math.hypot(e.clientX - pointerDownCoord.x, e.clientY - pointerDownCoord.y);
  if (dist > 5) return; // 拖拽旋转相机，忽略

  performSelectionPick(e.clientX, e.clientY, container, state.currentPartGroup, state.selectionMode, {
    onClear: () => {
      if (selSubInfo) selSubInfo.textContent = '未选中目标（点击空白处清除选择）';
      updateTopologyView();
    },
    onSolidPick: () => {
      if (selBadgeMode) selBadgeMode.textContent = '拾取: 实体 (Solid)';
      if (selSubInfo) selSubInfo.textContent = '已选择完整三维实体模型';
      updateTopologyView();
      showStatus('已选择实体模型');
    },
    onFacePick: (res) => {
      state.currentHitFace = res;
      if (selBadgeMode) selBadgeMode.textContent = `拾取: 面 (Face #${res.index})`;
      if (selSubInfo) selSubInfo.textContent = res.orient;
      if (selectionFields) {
        selectionFields.innerHTML = `
          <div class="stat-row"><span class="stat-name">法向量 (X,Y,Z):</span><span class="stat-value">[${res.normal[0]}, ${res.normal[1]}, ${res.normal[2]}]</span></div>
          <div class="stat-row"><span class="stat-name">面取向特征:</span><span class="stat-value">${res.orient}</span></div>
          <div class="stat-row"><span class="stat-name">击中坐标 (XYZ):</span><span class="stat-value">${res.point.x.toFixed(1)}, ${res.point.y.toFixed(1)}, ${res.point.z.toFixed(1)}</span></div>
          <div style="margin-top:6px;font-size:10px;color:#abb2bf">物理边界标注 (CFD):</div>
          <div class="cfd-patch-toolbar" style="margin-top:4px;display:flex;flex-wrap:wrap;gap:4px;">
            <button class="btn-text-sm btn-mark-patch" data-ptype="inlet" style="color:#3a86ff;border:1px solid #3a86ff;border-radius:3px;padding:2px 5px;background:rgba(58,134,255,0.1)">+ 入口 (Inlet)</button>
            <button class="btn-text-sm btn-mark-patch" data-ptype="outlet" style="color:#ff006e;border:1px solid #ff006e;border-radius:3px;padding:2px 5px;background:rgba(255,0,110,0.1)">+ 出口 (Outlet)</button>
            <button class="btn-text-sm btn-mark-patch" data-ptype="wall" style="color:#a0aab8;border:1px solid #a0aab8;border-radius:3px;padding:2px 5px;background:rgba(160,170,184,0.1)">+ 壁面 (Wall)</button>
            <button class="btn-text-sm btn-mark-patch" data-ptype="interface" style="color:#fb5607;border:1px solid #fb5607;border-radius:3px;padding:2px 5px;background:rgba(251,86,7,0.1)">+ 交界 (Interface)</button>
          </div>
        `;
        selectionFields.querySelectorAll('.btn-mark-patch').forEach(b => {
          b.onclick = async () => {
            try {
              const patch = await markFaceSemantic(res.index, b.dataset.ptype, res.normal, state.currentPartGroup);
              if (btnToggleBoundary) btnToggleBoundary.classList.add('active');
              showStatus(`已将面 #${res.index} 标记为【${patch.name}】(${b.dataset.ptype})`);
              appendChatBubble('assistant', `🌊 物理边界标注：已将面 #${res.index} 设为 **${patch.name}** [类型: ${b.dataset.ptype.toUpperCase()}]`);
            } catch (err) {
              showStatus(`打标失败: ${err.message}`, true);
            }
          };
        });
      }
      showStatus(`选中面 #${res.index} · 法向: [${res.normal[0]}, ${res.normal[1]}, ${res.normal[2]}] · ${res.orient}`);
    },
    onEdgePick: (res) => {
      if (selBadgeMode) selBadgeMode.textContent = '拾取: 边 (Edge)';
      if (selSubInfo) selSubInfo.textContent = `特征线段 (长 ${res.length.toFixed(2)} mm)`;
      if (selectionFields) {
        selectionFields.innerHTML = `
          <div class="stat-row"><span class="stat-name">特征边长度:</span><span class="stat-value">${res.length.toFixed(2)} mm</span></div>
          <div class="stat-row"><span class="stat-name">端点 1 (XYZ):</span><span class="stat-value">${res.p1.x.toFixed(1)}, ${res.p1.y.toFixed(1)}, ${res.p1.z.toFixed(1)}</span></div>
          <div class="stat-row"><span class="stat-name">端点 2 (XYZ):</span><span class="stat-value">${res.p2.x.toFixed(1)}, ${res.p2.y.toFixed(1)}, ${res.p2.z.toFixed(1)}</span></div>
        `;
      }
      showStatus(`选中边 · 长度: ${res.length.toFixed(2)} mm`);
    },
    onVertexPick: (res) => {
      if (selBadgeMode) selBadgeMode.textContent = '拾取: 顶点 (Vertex)';
      if (selSubInfo) selSubInfo.textContent = '几何特征顶点坐标已锁定';
      if (selectionFields) {
        selectionFields.innerHTML = `
          <div class="stat-row"><span class="stat-name">绝对空间 X:</span><span class="stat-value">${res.vertex.x.toFixed(2)} mm</span></div>
          <div class="stat-row"><span class="stat-name">绝对空间 Y:</span><span class="stat-value">${res.vertex.y.toFixed(2)} mm</span></div>
          <div class="stat-row"><span class="stat-name">绝对空间 Z:</span><span class="stat-value">${res.vertex.z.toFixed(2)} mm</span></div>
        `;
      }
      showStatus(`选中顶点 · 空间坐标: (${res.vertex.x.toFixed(2)}, ${res.vertex.y.toFixed(2)}, ${res.vertex.z.toFixed(2)}) mm`);
    }
  });
});

// --- Blender 快捷键流体系 (Shift+A, Tab, 1/2/3, G/R/S/X/Y/Z, Alt+Z) ---
window.addEventListener('keydown', (e) => {
  const tag = (e.target.tagName || '').toLowerCase();
  if (tag === 'input' || tag === 'textarea') {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      runScript();
    }
    return;
  }

  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    e.preventDefault();
    runScript();
    return;
  }

  if (e.shiftKey && (e.key === 'a' || e.key === 'A')) {
    e.preventDefault();
    if (addMenuPopup) {
      const maxX = container.clientWidth - 180;
      const maxY = container.clientHeight - 340;
      addMenuPopup.style.left = `${Math.max(10, Math.min(lastCursorPos.x, maxX))}px`;
      addMenuPopup.style.top = `${Math.max(10, Math.min(lastCursorPos.y, maxY))}px`;
      addMenuPopup.classList.remove('hidden');
    }
    return;
  }

  if (e.key === 'Tab') {
    e.preventDefault();
    setAppMode(currentAppMode === 'OBJECT' ? 'EDIT' : 'OBJECT');
    switchSelectionModeTo(currentAppMode === 'EDIT' ? 'face' : 'solid');
    return;
  }

  if (e.key === '1') {
    e.preventDefault();
    setAppMode('EDIT');
    switchSelectionModeTo('vertex');
    return;
  } else if (e.key === '2') {
    e.preventDefault();
    setAppMode('EDIT');
    switchSelectionModeTo('edge');
    return;
  } else if (e.key === '3') {
    e.preventDefault();
    setAppMode('EDIT');
    switchSelectionModeTo('face');
    return;
  }

  if (e.altKey && (e.key === 'z' || e.key === 'Z')) {
    e.preventDefault();
    const xActive = toggleXrayMode(state.currentPartGroup);
    showStatus(xActive ? '已开启 X-Ray 半透明透视模式 (Alt+Z)' : '已恢复实体着色模式 (Alt+Z)');
    return;
  }

  if (e.key === 'g' || e.key === 'G') {
    e.preventDefault();
    transformControls.setMode('translate');
    resetAxesConstraints();
    transformControls.visible = true;
    showStatus('变换手柄: 平移 (G) · 拖拽手柄移动，按 X/Y/Z 可锁定单轴');
  } else if (e.key === 'r' || e.key === 'R') {
    e.preventDefault();
    transformControls.setMode('rotate');
    resetAxesConstraints();
    transformControls.visible = true;
    showStatus('变换手柄: 旋转 (R) · 拖拽手柄旋转，按 X/Y/Z 可锁定单轴');
  } else if (e.key === 's' || e.key === 'S') {
    e.preventDefault();
    transformControls.setMode('scale');
    resetAxesConstraints();
    transformControls.visible = true;
    showStatus('变换手柄: 缩放 (S) · 拖拽手柄缩放');
  } else if (e.key === 'x' || e.key === 'X') {
    if (transformControls.visible) {
      e.preventDefault();
      transformControls.showX = true; transformControls.showY = false; transformControls.showZ = false;
      showStatus('已锁定 X 轴向约束');
    }
  } else if (e.key === 'y' || e.key === 'Y') {
    if (transformControls.visible) {
      e.preventDefault();
      transformControls.showX = false; transformControls.showY = true; transformControls.showZ = false;
      showStatus('已锁定 Y 轴向约束');
    }
  } else if (e.key === 'z' || e.key === 'Z') {
    if (transformControls.visible) {
      e.preventDefault();
      transformControls.showX = false; transformControls.showY = false; transformControls.showZ = true;
      showStatus('已锁定 Z 轴向约束');
    }
  } else if (e.key === 'Escape') {
    resetAxesConstraints();
    showStatus('已重置轴向约束');
  }
});

// --- 顶部导航与视角控制 ---
document.getElementById('btn-iso').onclick = () => setStandardView('iso', state.currentPartGroup);
document.getElementById('btn-front').onclick = () => setStandardView('front', state.currentPartGroup);
document.getElementById('btn-top').onclick = () => setStandardView('top', state.currentPartGroup);
document.getElementById('btn-right').onclick = () => setStandardView('right', state.currentPartGroup);
document.getElementById('btn-fit').onclick = () => setStandardView('fit', state.currentPartGroup);

document.getElementById('btn-camera-toggle').onclick = (e) => {
  const btn = e.currentTarget;
  if (state.cameraType === 'perspective') {
    state.cameraType = 'orthographic';
    orthoCamera.position.copy(perspCamera.position);
    orthoCamera.quaternion.copy(perspCamera.quaternion);
    setActiveCamera(orthoCamera);
    transformControls.camera = orthoCamera;
    btn.textContent = '正交';
    btn.classList.add('active');
  } else {
    state.cameraType = 'perspective';
    perspCamera.position.copy(orthoCamera.position);
    perspCamera.quaternion.copy(orthoCamera.quaternion);
    setActiveCamera(perspCamera);
    transformControls.camera = perspCamera;
    btn.textContent = '透视';
    btn.classList.remove('active');
  }
  controls.update();
};

document.getElementById('btn-grid-toggle').onclick = (e) => {
  state.showGrid = !state.showGrid;
  gridHelper.visible = state.showGrid;
  e.currentTarget.classList.toggle('active', state.showGrid);
};

document.getElementById('btn-axes-toggle').onclick = (e) => {
  state.showAxes = !state.showAxes;
  axesHelper.visible = state.showAxes;
  e.currentTarget.classList.toggle('active', state.showAxes);
};

document.getElementById('btn-edges-toggle').onclick = (e) => {
  state.showEdges = !state.showEdges;
  e.currentTarget.classList.toggle('active', state.showEdges);
  if (state.currentPartGroup) {
    state.currentPartGroup.traverse((child) => {
      if (child.name === 'cad-edge-line') child.visible = state.showEdges;
    });
  }
};

if (btnToggleBoundary) {
  btnToggleBoundary.onclick = () => {
    const next = !getIsBoundaryMode();
    btnToggleBoundary.classList.toggle('active', next);
    setBoundaryMode(next, state.currentPartGroup);
    showStatus(next ? '已开启【🌊 物理边界模式】：高亮显示各物理边界补丁颜色' : '已退出边界模式：恢复标准 CAD 天蓝色实体外观');
  };
}

// 顶部变换按钮绑定
const btnToolMove = document.getElementById('btn-tool-move');
const btnToolRotate = document.getElementById('btn-tool-rotate');
const btnToolScale = document.getElementById('btn-tool-scale');
if (btnToolMove) btnToolMove.onclick = () => openToolModal('move');
if (btnToolRotate) btnToolRotate.onclick = () => openToolModal('rotate');
if (btnToolScale) btnToolScale.onclick = () => openToolModal('scale');

// 右侧工具栏按钮绑定
document.querySelectorAll('.right-tools button[data-tool]').forEach(btn => {
  btn.onclick = () => {
    const tool = btn.dataset.tool;
    if (tool) openToolModal(tool);
  };
});

// --- 参数化模板表单逻辑 ---
function renderParamForm(templateKey) {
  const config = TEMPLATE_CONFIGS[templateKey];
  if (!config) return;

  state.template = templateKey;
  state.params = {};
  paramForm.innerHTML = '';

  config.params.forEach((p) => {
    state.params[p.key] = p.default;
    const group = document.createElement('div');
    group.className = 'param-group';

    if (p.type === 'boolean') {
      group.innerHTML = `
        <div class="param-header"><label class="param-label" for="param-${p.key}">${p.label}</label><input type="checkbox" id="param-${p.key}" ${p.default ? 'checked' : ''}></div>
      `;
      const checkbox = group.querySelector('input');
      checkbox.onchange = () => {
        state.params[p.key] = checkbox.checked;
        triggerParametricBuild();
      };
    } else {
      group.innerHTML = `
        <div class="param-header"><label class="param-label" for="param-${p.key}">${p.label}</label><span class="param-val-preview">${p.default}</span></div>
        <div class="param-inputs"><input type="range" class="param-slider" id="slider-${p.key}" min="${p.min}" max="${p.max}" step="${p.step}" value="${p.default}"><input type="number" class="param-num" id="num-${p.key}" min="${p.min}" max="${p.max}" step="${p.step}" value="${p.default}"></div>
      `;
      const slider = group.querySelector('.param-slider');
      const numInput = group.querySelector('.param-num');
      const preview = group.querySelector('.param-val-preview');

      const updateVal = (val) => {
        state.params[p.key] = parseFloat(val);
        slider.value = val;
        numInput.value = val;
        preview.textContent = val;
      };

      slider.oninput = (e) => { updateVal(e.target.value); debounceBuild(); };
      numInput.onchange = (e) => { updateVal(e.target.value); triggerParametricBuild(); };
    }
    paramForm.appendChild(group);
  });
}

let debounceTimer = null;
let needRebuild = false;

function debounceBuild() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => triggerParametricBuild(), 120);
}

export async function triggerParametricBuild() {
  if (state.isBuilding) {
    needRebuild = true;
    return;
  }
  state.isBuilding = true;
  showLoading('SMLib 正在重构参数化特征…');

  try {
    const res = await fetch('/api/build/parametric', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ template: state.template, params: state.params })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || '建模错误');

    renderModelGLTF(data.gltf);
    if (scriptEditor) scriptEditor.value = data.script;

    document.getElementById('stat-volume').textContent = `${data.stats.volume.toLocaleString()} mm³`;
    document.getElementById('stat-time').textContent = `${data.stats.compute_ms} ms`;
    showStatus(`建模完成 · 体积: ${data.stats.volume} mm³ · 耗时: ${data.stats.compute_ms} ms`);
  } catch (err) {
    showStatus(`构建失败: ${err.message}`, true);
  } finally {
    state.isBuilding = false;
    hideLoading();
    if (needRebuild) {
      needRebuild = false;
      triggerParametricBuild();
    }
  }
}

async function runScript() {
  const code = (scriptEditor ? scriptEditor.value : '').trim();
  if (!code) return;

  showLoading('SMLib 正在执行自定义 Python 脚本…');
  try {
    const res = await fetch('/api/build/script', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ script: code, name: 'custom_part' })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || '执行失败');

    renderModelGLTF(data.gltf);
    document.getElementById('stat-volume').textContent = `${data.stats.volume.toLocaleString()} mm³`;
    document.getElementById('stat-time').textContent = `${data.stats.compute_ms} ms`;
    showStatus(`脚本构建完成 · 体积: ${data.stats.volume} mm³ · 耗时: ${data.stats.compute_ms} ms`);
  } catch (err) {
    alert('脚本执行出错:\n' + err.message);
    showStatus(`执行失败: ${err.message}`, true);
  } finally {
    hideLoading();
  }
}

if (templateSelect) {
  templateSelect.onchange = (e) => {
    renderParamForm(e.target.value);
    triggerParametricBuild();
  };
}

const btnRebuild = document.getElementById('btn-rebuild-param');
const btnRunScript = document.getElementById('btn-run-script');
const btnFormatScript = document.getElementById('btn-format-script');
if (btnRebuild) btnRebuild.onclick = () => triggerParametricBuild();
if (btnRunScript) btnRunScript.onclick = () => runScript();
if (btnFormatScript) btnFormatScript.onclick = () => triggerParametricBuild();

// 快捷代码插入与复制
document.querySelectorAll('.snip-btn').forEach((btn) => {
  btn.onclick = () => {
    if (!scriptEditor) return;
    const code = btn.dataset.code;
    const pos = scriptEditor.selectionStart;
    const prev = scriptEditor.value;
    scriptEditor.value = prev.slice(0, pos) + '\n' + code + prev.slice(pos);
    scriptEditor.focus();
  };
});

const btnCopy = document.getElementById('btn-copy-script');
if (btnCopy) {
  btnCopy.onclick = () => {
    if (!scriptEditor) return;
    navigator.clipboard.writeText(scriptEditor.value).then(() => {
      showStatus('Python 脚本已复制到剪贴板！');
    });
  };
}

// 侧栏 Tab 切换
document.querySelectorAll('.tab-btn').forEach((btn) => {
  btn.onclick = () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    const tabId = `tab-${btn.dataset.tab}`;
    const pane = document.getElementById(tabId);
    if (pane) pane.classList.add('active');
  };
});

// 文件下载与导出
function downloadFile(url) {
  const link = document.createElement('a');
  link.href = url;
  link.download = '';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

document.getElementById('btn-export-step').onclick = () => {
  downloadFile('/api/export/step');
  showStatus('正在生成并下载工业标准 STEP 文件…');
};
document.getElementById('btn-export-stl').onclick = () => {
  downloadFile('/api/export/stl');
  showStatus('正在生成并下载 3D 打印 STL 文件…');
};
document.getElementById('btn-export-gltf').onclick = () => {
  downloadFile('/api/export/gltf');
  showStatus('正在下载 glTF 3D 文件…');
};
document.getElementById('btn-export-py').onclick = () => {
  downloadFile('/api/export/py');
  showStatus('正在下载 Python 独立建模脚本…');
};

const btnExportCfd = document.getElementById('btn-export-cfd');
if (btnExportCfd) {
  btnExportCfd.onclick = () => {
    downloadFile('/api/export/cfd_meta');
    showStatus('正在生成并下载 CFD 物理边界字典 (JSON)…');
  };
}

async function fetchInfo() {
  try {
    const res = await fetch('/api/info');
    const info = await res.json();
    document.getElementById('info-kernel').textContent = info.kernel;
    document.getElementById('info-pyver').textContent = `smlibpy ${info.smlibpy_version}`;
  } catch (err) {
    console.warn('Failed to fetch info:', err);
  }
}

// 初始化启动
startAnimationLoop();
renderParamForm('flange');
triggerParametricBuild();
fetchInfo();

// 暴露全局变量供测试
window.transformControls = transformControls;
window.state = state;
window.__getIsXray = () => getIsXrayMode();
window.__getIsBoundaryMode = () => getIsBoundaryMode();
