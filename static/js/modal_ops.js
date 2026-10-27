/**
 * Blender-Style Modal Operator State Machine for BrepX.
 * Implements interactive Face Extrude (E), Edge Fillet/Chamfer (Ctrl+B),
 * G/R/S transforms, X deletion, and Blender F9 Adjust Last Operation panel.
 */

import * as THREE from 'three';
import { TransformControls } from 'three/addons/TransformControls.js';
import { activeCamera, container, controls, modelGroup, previewGroup, renderer, scene } from './viewport.js';
import { ctx } from './context.js';
import { renderAdjustLastPanel, adjustLastOperation } from './adjust_last.js';

export { renderAdjustLastPanel, adjustLastOperation };

// Top banner indicator in viewport
const modalStatusBar = document.getElementById('modal-status-bar');

// 空间交互变换手柄集成与约束轴配置
export const transformControls = new TransformControls(activeCamera, renderer.domElement);
transformControls.size = 0.85;
scene.add(transformControls.getHelper ? transformControls.getHelper() : transformControls);

let transformStartPos = new THREE.Vector3();
let transformStartRot = new THREE.Euler();
let transformStartScale = new THREE.Vector3();

transformControls.addEventListener('dragging-changed', (event) => {
  controls.enabled = !event.value;
  const obj = transformControls.object;
  if (event.value && obj) {
    transformStartPos.copy(obj.position);
    transformStartRot.copy(obj.rotation);
    transformStartScale.copy(obj.scale);
  }
});

export function attachGizmoToActiveModel() {
  if (modelGroup.children.length > 0) {
    transformControls.attach(modelGroup.children[0]);
    transformControls.visible = ctx.mode === 'OBJECT';
  } else {
    transformControls.detach();
  }
}

export function resetAxesConstraints() {
  transformControls.showX = true;
  transformControls.showY = true;
  transformControls.showZ = true;
}

// Gizmo mouse release triggers exact backend execution
transformControls.addEventListener('mouseUp', async () => {
  const obj = transformControls.object;
  if (!obj) return;

  const dx = obj.position.x - transformStartPos.x;
  const dy = obj.position.y - transformStartPos.y;
  const dz = obj.position.z - transformStartPos.z;

  const mode = transformControls.getMode();
  obj.position.copy(transformStartPos);
  obj.rotation.copy(transformStartRot);
  obj.scale.copy(transformStartScale);

  if (mode === 'translate' && (Math.abs(dx) > 0.05 || Math.abs(dy) > 0.05 || Math.abs(dz) > 0.05)) {
    await executeOperator('translate', { dx: round2(dx), dy: round2(dy), dz: round2(dz) });
  } else if (mode === 'rotate') {
    const dangle = THREE.MathUtils.radToDeg(obj.rotation.z - transformStartRot.z);
    if (Math.abs(dangle) > 0.1) {
      await executeOperator('rotate', { axis: 'Z', angle: round2(dangle) });
    }
  } else if (mode === 'scale') {
    const factor = obj.scale.x / (transformStartScale.x || 1.0);
    if (Math.abs(factor - 1.0) > 0.01) {
      await executeOperator('scale', { factor: round2(factor) });
    }
  }
});

// 视口模态交互操作符运行时状态与临时网格预览容器
let activeModalOp = null; // { type, startPointer, normal, baseCenter, previewMesh, value, ... }

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

/**
 * Invoke interactive Face Extrude (E Key)
 */
export function invokeExtrudeModal() {
  const selectedFaces = ctx.selections.filter(s => s.type === 'face');
  if (!selectedFaces.length) {
    alert('请先在视口中选择一个要拉伸的拓扑面 (快捷键: 3 进入面模式)');
    return;
  }

  const faceData = selectedFaces[0];
  controls.enabled = false;

  const normal = new THREE.Vector3(...(faceData.meta.normal || [0, 0, 1])).normalize();
  const center = new THREE.Vector3(...(faceData.meta.center || [0, 0, 0]));

  // Build a visual arrow preview along face normal
  const arrow = new THREE.ArrowHelper(normal, center, 30, 0xffd885, 6, 4);
  previewGroup.add(arrow);

  activeModalOp = {
    type: 'extrude',
    faceData,
    normal,
    center,
    value: 15.0,
    startClientY: 0,
    initialized: false,
    arrow,
  };

  showModalStatus(`[拉伸模态] 移动鼠标调整高度 · 当前: +15.0 mm · Enter/左键 确认 · Esc 取消`);
}

/**
 * Invoke interactive Edge Fillet / Chamfer (Ctrl + B)
 */
export function invokeFilletModal(mode = 'fillet') {
  const selectedEdges = ctx.selections.filter(s => s.type === 'edge');
  if (!selectedEdges.length) {
    alert('请先在视口中选择至少一条特征边进行倒角 (快捷键: 2 进入边模式，按住 Shift 可多选)');
    return;
  }

  controls.enabled = false;
  activeModalOp = {
    type: mode, // 'fillet' | 'chamfer'
    edges: selectedEdges,
    value: 4.0,
    startClientX: 0,
    initialized: false,
  };

  const title = mode === 'fillet' ? '倒圆角' : '倒角';
  showModalStatus(`[${title}模态] 移动鼠标调整半径 · 当前: R4.0 mm · M 切换圆角/倒角 · Enter/左键 确认 · Esc 取消`);
}

/**
 * Handle mouse motion in active modal operator
 */
export function handleModalMouseMove(e) {
  if (!activeModalOp) return;

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
    if (activeModalOp.arrow) {
      activeModalOp.arrow.setLength(Math.max(10, Math.abs(amount) * 1.5));
    }
    const sign = amount >= 0 ? '+' : '';
    showModalStatus(`[拉伸模态] 移动鼠标调整高度 · 当前: ${sign}${amount} mm · Enter/左键 确认 · Esc 取消`);
  } else if (activeModalOp.type === 'fillet' || activeModalOp.type === 'chamfer') {
    const dx = e.clientX - activeModalOp.startClientX;
    const r = Math.max(0.2, round2(4.0 + dx * 0.1));
    activeModalOp.value = r;
    const tag = activeModalOp.type === 'fillet' ? '圆角 R' : '倒角 D';
    showModalStatus(`[${tag}模态] 移动鼠标调整大小 · 当前: ${r} mm · M 切换 · Enter/左键 确认 · Esc 取消`);
  }
}

/**
 * Confirm and execute modal operator
 */
export async function confirmModalOperation() {
  if (!activeModalOp) return;
  const op = activeModalOp;
  cancelModalOperation();

  if (op.type === 'extrude') {
    await executeOperator('extrude', { height: op.value }, [op.faceData.expr]);
  } else if (op.type === 'fillet') {
    await executeOperator('fillet', { radius: op.value }, op.edges.map(e => e.expr));
  } else if (op.type === 'chamfer') {
    await executeOperator('chamfer', { distance: op.value }, op.edges.map(e => e.expr));
  }
}

/**
 * Cancel modal operator
 */
export function cancelModalOperation() {
  activeModalOp = null;
  controls.enabled = true;
  clearPreviewGeometry();
  hideModalStatus();
}

/**
 * Core operator executor connecting to backend
 */
export async function executeOperator(opName, params = {}, selections = null) {
  const reqSels = selections || ctx.getSelectedExpressions();
  const res = await fetch('/api/workspace/execute_operator', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      operator: opName,
      params,
      selections: reqSels,
    }),
  });

  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || '运算错误');

  ctx.setSceneData(data.scene);
  ctx.setPatches(data.patches);
  ctx.setLastOperation(data.last_operation);
  renderAdjustLastPanel(data.last_operation);
  return data;
}

// Global modal hotkeys: E, Ctrl+B, M, Enter, Esc
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
      showModalStatus(`[${tag}模态] 移动鼠标调整大小 · 当前: ${activeModalOp.value} mm · M 切换 · Enter 确认 · Esc 取消`);
      return;
    }
    return;
  }

  // E key: Extrude selected face
  if (e.key === 'e' || e.key === 'E') {
    if (!e.ctrlKey && !e.metaKey && !e.altKey) {
      e.preventDefault();
      invokeExtrudeModal();
      return;
    }
  }

  // Ctrl + B: Fillet selected edge
  if ((e.ctrlKey || e.metaKey) && (e.key === 'b' || e.key === 'B')) {
    e.preventDefault();
    invokeFilletModal('fillet');
    return;
  }
});
