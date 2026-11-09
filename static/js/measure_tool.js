/**
 * Two-element measurement caliper tool displaying 3D leader dimensions and delta coordinates.
 */

import * as THREE from 'three';
import { scene } from './viewport.js';
import { interactionLock } from './interaction_lock.js';

export const measureGroup = new THREE.Group();
measureGroup.name = 'measure-tool-root';
scene.add(measureGroup);

let isMeasureActive = false;
let pickedPoints = [];

export function toggleMeasureTool(active) {
  isMeasureActive = active !== undefined ? active : !isMeasureActive;
  if (isMeasureActive) {
    interactionLock.acquire('measure_tool');
    clearMeasurements();
  } else {
    interactionLock.release('measure_tool');
    clearMeasurements();
  }
  return isMeasureActive;
}

export function handleMeasurePick(point) {
  if (!isMeasureActive || !point) return;

  pickedPoints.push(point.clone());
  if (pickedPoints.length === 2) {
    _renderMeasurementLine(pickedPoints[0], pickedPoints[1]);
    pickedPoints = [];
  }
}

export function clearMeasurements() {
  while (measureGroup.children.length > 0) {
    const c = measureGroup.children[0];
    measureGroup.remove(c);
    if (c.geometry) c.geometry.dispose();
    if (c.material) c.material.dispose();
  }
  pickedPoints = [];
}

function _renderMeasurementLine(p1, p2) {
  clearMeasurements();

  const geom = new THREE.BufferGeometry().setFromPoints([p1, p2]);
  const mat = new THREE.LineDashedMaterial({
    color: 0xffd885,
    dashSize: 3,
    gapSize: 1.5,
    linewidth: 2,
    depthTest: false,
  });
  const line = new THREE.Line(geom, mat);
  line.computeLineDistances();
  measureGroup.add(line);

  const dist = p1.distanceTo(p2);
  const statusEl = document.getElementById('status-text');
  if (statusEl) {
    const dx = Math.abs(p2.x - p1.x).toFixed(2);
    const dy = Math.abs(p2.y - p1.y).toFixed(2);
    const dz = Math.abs(p2.z - p1.z).toFixed(2);
    statusEl.textContent = `📏 空间测距: ${dist.toFixed(2)} mm (ΔX=${dx}, ΔY=${dy}, ΔZ=${dz})`;
    statusEl.style.color = '#ffd885';
  }
}
