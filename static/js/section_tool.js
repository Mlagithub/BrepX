/**
 * Dynamic Section Clipping tool enabling real-time internal flow channel inspection.
 */

import * as THREE from 'three';
import { renderer, scene } from './viewport.js';

let clippingPlane = null;
let isSectionActive = false;
let currentOffset = 0.0;
let currentAxis = 'Z';

export function initSectionTool() {
  renderer.localClippingEnabled = true;
  clippingPlane = new THREE.Plane(new THREE.Vector3(0, 0, -1), 0);
}

export function toggleSectionTool(active, axis = 'Z') {
  isSectionActive = active !== undefined ? active : !isSectionActive;
  currentAxis = axis;

  if (isSectionActive) {
    _updatePlaneNormal();
    renderer.clippingPlanes = [clippingPlane];
  } else {
    renderer.clippingPlanes = [];
  }
  return isSectionActive;
}

export function setSectionOffset(offsetVal) {
  currentOffset = offsetVal;
  if (clippingPlane) {
    clippingPlane.constant = currentOffset;
  }
}

export function setSectionAxis(axis) {
  currentAxis = axis;
  _updatePlaneNormal();
}

function _updatePlaneNormal() {
  if (!clippingPlane) return;
  const normalMap = {
    X: new THREE.Vector3(-1, 0, 0),
    Y: new THREE.Vector3(0, -1, 0),
    Z: new THREE.Vector3(0, 0, -1),
  };
  const norm = normalMap[currentAxis] || normalMap.Z;
  clippingPlane.normal.copy(norm);
  clippingPlane.constant = currentOffset;
}

export function isSectionToolActive() {
  return isSectionActive;
}
