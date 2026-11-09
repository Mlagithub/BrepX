import * as THREE from 'three';
import { activeCamera, container, controls, modelGroup } from './viewport.js';

let gizmoCanvas = null;
let gizmoCtx = null;
let isTransitioning = false;
let transitionStartTime = 0;
let transitionDuration = 260;
let startPos = new THREE.Vector3();
let endPos = new THREE.Vector3();
let startTarget = new THREE.Vector3();
let endTarget = new THREE.Vector3();
const lastQuat = new THREE.Quaternion();
let hasRenderedOnce = false;

// 轴向配置：坐标轴颜色与对应投影方向
const AXES = [
  { name: '+X', dir: new THREE.Vector3(1, 0, 0), color: '#e06c75', label: 'X' },
  { name: '-X', dir: new THREE.Vector3(-1, 0, 0), color: '#7a3b40', label: '-X' },
  { name: '+Y', dir: new THREE.Vector3(0, 1, 0), color: '#98c379', label: 'Y' },
  { name: '-Y', dir: new THREE.Vector3(0, -1, 0), color: '#4a6b35', label: '-Y' },
  { name: '+Z', dir: new THREE.Vector3(0, 0, 1), color: '#61afef', label: 'Z' },
  { name: '-Z', dir: new THREE.Vector3(0, 0, -1), color: '#2d5a88', label: '-Z' },
];

/**
 * 平滑缓动插值函数 (Cubic Out)
 */
function easeOutCubic(t) {
  return 1 - Math.pow(1 - t, 3);
}

/**
 * 平滑过渡相机到指定空间位置与注视目标点
 * @param {THREE.Vector3} toPos 目标相机位置
 * @param {THREE.Vector3} toTarget 目标相机注视点
 * @param {number} duration 过渡时长 (毫秒)
 */
export function smoothTransitionCamera(toPos, toTarget, duration = 260) {
  if (isTransitioning) return;
  isTransitioning = true;
  transitionStartTime = performance.now();
  transitionDuration = duration;

  startPos.copy(activeCamera.position);
  endPos.copy(toPos);
  startTarget.copy(controls.target);
  endTarget.copy(toTarget);
}

/**
 * 切换标准正交视图并启动平滑过渡
 * @param {'iso'|'front'|'top'|'right'|'fit'} type 目标视图类型
 */
export function setStandardViewSmooth(type) {
  const box = new THREE.Box3().setFromObject(modelGroup);
  const center = box.isEmpty() ? new THREE.Vector3() : box.getCenter(new THREE.Vector3());
  const size = box.isEmpty() ? 60 : box.getSize(new THREE.Vector3()).length();
  const dist = Math.max(size * 1.5, 90);

  const targetPos = new THREE.Vector3();
  if (type === 'iso') {
    targetPos.set(center.x + dist * 0.7, center.y + dist * 0.6, center.z + dist * 0.7);
  } else if (type === 'front') {
    targetPos.set(center.x, center.y, center.z + dist);
  } else if (type === 'top') {
    targetPos.set(center.x, center.y + dist, center.z);
  } else if (type === 'right') {
    targetPos.set(center.x + dist, center.y, center.z);
  } else if (type === 'fit') {
    const dir = new THREE.Vector3().subVectors(activeCamera.position, controls.target).normalize();
    if (dir.lengthSq() < 0.001) dir.set(1, 0.8, 1).normalize();
    targetPos.copy(center).addScaledVector(dir, dist);

    if (activeCamera.isOrthographicCamera) {
      const asp = container.clientWidth / container.clientHeight;
      const maxDim = Math.max(size, 40);
      activeCamera.left = -maxDim * asp * 0.8;
      activeCamera.right = maxDim * asp * 0.8;
      activeCamera.top = maxDim * 0.8;
      activeCamera.bottom = -maxDim * 0.8;
      activeCamera.updateProjectionMatrix();
    }
  }

  smoothTransitionCamera(targetPos, center);
}

/**
 * 初始化视口右上角 3D 视角罗盘
 */
export function initViewCube() {
  const wrapper = document.createElement('div');
  wrapper.className = 'viewport-gizmo-wrapper';
  wrapper.setAttribute('title', '3D 视图罗盘: 点击圆球切换对应正视/侧视/俯视');

  gizmoCanvas = document.createElement('canvas');
  gizmoCanvas.width = 96;
  gizmoCanvas.height = 96;
  gizmoCanvas.className = 'viewport-gizmo-canvas';
  wrapper.appendChild(gizmoCanvas);

  container.appendChild(wrapper);
  gizmoCtx = gizmoCanvas.getContext('2d');

  // 点击罗盘轴球平滑对齐视角
  gizmoCanvas.addEventListener('click', (e) => {
    const rect = gizmoCanvas.getBoundingClientRect();
    const cx = rect.width / 2;
    const cy = rect.height / 2;
    const clickX = e.clientX - rect.left - cx;
    const clickY = e.clientY - rect.top - cy;

    const projected = getProjectedAxes();
    // 优先匹配最靠近屏幕表面且命中半径内的轴球
    let closestAxis = null;
    let minDistance = 16;

    projected.forEach((p) => {
      const dist = Math.hypot(p.screenX - clickX, p.screenY - clickY);
      if (dist < minDistance) {
        minDistance = dist;
        closestAxis = p.axis;
      }
    });

    if (closestAxis) {
      const box = new THREE.Box3().setFromObject(modelGroup);
      const center = box.isEmpty() ? new THREE.Vector3() : box.getCenter(new THREE.Vector3());
      const dist = Math.max((box.isEmpty() ? 60 : box.getSize(new THREE.Vector3()).length()) * 1.5, 90);
      const targetPos = new THREE.Vector3().copy(center).addScaledVector(closestAxis.dir, dist);
      smoothTransitionCamera(targetPos, center);
    }
  });
}

/**
 * 计算三维轴线在当前相机视角矩阵下的二维屏幕投影
 */
function getProjectedAxes() {
  const rotMatrix = new THREE.Matrix4().extractRotation(activeCamera.matrixWorldInverse);
  const radius = 34;

  const list = AXES.map((axis) => {
    const v = axis.dir.clone().applyMatrix4(rotMatrix);
    return {
      axis,
      screenX: v.x * radius,
      screenY: -v.y * radius,
      depth: v.z,
    };
  });

  // 深度排序，先绘制背向轴，再绘制朝向轴
  list.sort((a, b) => a.depth - b.depth);
  return list;
}

/**
 * 实时绘制 3D 罗盘姿态并驱动平滑动画插值
 */
export function updateViewCube() {
  if (isTransitioning) {
    const now = performance.now();
    const elapsed = now - transitionStartTime;
    const t = Math.min(1.0, elapsed / transitionDuration);
    const ease = easeOutCubic(t);

    activeCamera.position.lerpVectors(startPos, endPos, ease);
    controls.target.lerpVectors(startTarget, endTarget, ease);
    activeCamera.lookAt(controls.target);
    controls.update();

    if (t >= 1.0) {
      isTransitioning = false;
    }
  }

  if (!gizmoCtx || !gizmoCanvas) return;

  const currentQuat = activeCamera.quaternion;
  const isDirty = isTransitioning || !currentQuat.equals(lastQuat);
  if (!isDirty && hasRenderedOnce) return;
  lastQuat.copy(currentQuat);
  hasRenderedOnce = true;

  const ctx2d = gizmoCtx;
  const w = gizmoCanvas.width;
  const h = gizmoCanvas.height;
  const cx = w / 2;
  const cy = h / 2;

  ctx2d.clearRect(0, 0, w, h);

  // 绘制半透明圆盘底座
  ctx2d.beginPath();
  ctx2d.arc(cx, cy, 42, 0, Math.PI * 2);
  ctx2d.fillStyle = 'rgba(24, 26, 31, 0.45)';
  ctx2d.fill();
  ctx2d.lineWidth = 1;
  ctx2d.strokeStyle = 'rgba(255, 255, 255, 0.08)';
  ctx2d.stroke();

  const projected = getProjectedAxes();

  projected.forEach((p) => {
    const isFront = p.depth >= -0.1;
    const alpha = isFront ? 1.0 : 0.35;
    const endX = cx + p.screenX;
    const endY = cy + p.screenY;

    // 绘制连线
    if (isFront) {
      ctx2d.beginPath();
      ctx2d.moveTo(cx, cy);
      ctx2d.lineTo(endX, endY);
      ctx2d.strokeStyle = p.axis.color;
      ctx2d.globalAlpha = 0.8;
      ctx2d.lineWidth = 2;
      ctx2d.stroke();
    }

    // 绘制轴端球体与文本标签
    ctx2d.beginPath();
    ctx2d.arc(endX, endY, isFront ? 7.5 : 5, 0, Math.PI * 2);
    ctx2d.fillStyle = p.axis.color;
    ctx2d.globalAlpha = alpha;
    ctx2d.fill();

    if (isFront && p.axis.label.length === 1) {
      ctx2d.fillStyle = '#ffffff';
      ctx2d.globalAlpha = 1.0;
      ctx2d.font = 'bold 9px sans-serif';
      ctx2d.textAlign = 'center';
      ctx2d.textBaseline = 'middle';
      ctx2d.fillText(p.axis.label, endX, endY);
    }
  });

  ctx2d.globalAlpha = 1.0;
}
