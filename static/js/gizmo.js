import * as THREE from 'three';
import { TransformControls } from 'three/addons/TransformControls.js';
import { activeCamera, renderer, scene, controls } from './viewport.js';

export const transformControls = new TransformControls(activeCamera, renderer.domElement);
transformControls.size = 0.85;
scene.add(transformControls.getHelper ? transformControls.getHelper() : transformControls);

let transformStartPos = new THREE.Vector3();
let transformStartRot = new THREE.Euler();
let transformStartScale = new THREE.Vector3();

let isXrayMode = false;
let onTransformFinishedCallback = null;

export function setTransformFinishedCallback(cb) {
  onTransformFinishedCallback = cb;
}

export function getIsXrayMode() {
  return isXrayMode;
}

transformControls.addEventListener('dragging-changed', (event) => {
  controls.enabled = !event.value;
  const obj = transformControls.object;
  if (event.value && obj) {
    transformStartPos.copy(obj.position);
    transformStartRot.copy(obj.rotation);
    transformStartScale.copy(obj.scale);
  }
});

export function resetAxesConstraints() {
  transformControls.showX = true;
  transformControls.showY = true;
  transformControls.showZ = true;
}

function round2(v) {
  return Math.round(v * 100) / 100;
}

// 手柄松开时执行最终提交
transformControls.addEventListener('mouseUp', async () => {
  const obj = transformControls.object;
  if (!obj) return;

  const curPos = obj.position;
  const dx = curPos.x - transformStartPos.x;
  const dy = curPos.y - transformStartPos.y;
  const dz = curPos.z - transformStartPos.z;

  const mode = transformControls.getMode();
  if (mode === 'translate' && (Math.abs(dx) > 0.01 || Math.abs(dy) > 0.01 || Math.abs(dz) > 0.01)) {
    obj.position.copy(transformStartPos);
    if (onTransformFinishedCallback) {
      await onTransformFinishedCallback('translate', { dx: round2(dx), dy: round2(dy), dz: round2(dz) });
    }
  } else if (mode === 'rotate') {
    const curRot = obj.rotation;
    const dangle = THREE.MathUtils.radToDeg(curRot.z - transformStartRot.z);
    if (Math.abs(dangle) > 0.1) {
      obj.rotation.copy(transformStartRot);
      if (onTransformFinishedCallback) {
        await onTransformFinishedCallback('rotate', { axis: 'Z', angle: round2(dangle) });
      }
    }
  } else if (mode === 'scale') {
    const curScale = obj.scale;
    const factor = curScale.x / (transformStartScale.x || 1.0);
    if (Math.abs(factor - 1.0) > 0.01) {
      obj.scale.copy(transformStartScale);
      if (onTransformFinishedCallback) {
        await onTransformFinishedCallback('scale', { factor: round2(factor) });
      }
    }
  }
});

// 切换 X-Ray
export function toggleXrayMode(currentPartGroup) {
  isXrayMode = !isXrayMode;
  if (currentPartGroup) {
    currentPartGroup.traverse((child) => {
      if (child.isMesh && child.name !== 'cad-edge-line') {
        child.material.transparent = isXrayMode;
        child.material.opacity = isXrayMode ? 0.35 : 1.0;
        child.material.depthWrite = !isXrayMode;
      }
    });
  }
  return isXrayMode;
}
