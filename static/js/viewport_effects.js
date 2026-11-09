/**
 * Viewport visual effects for CAD topology feedback, including face normal arrows,
 * contour edges, and memory-safe resource disposal.
 */

import * as THREE from 'three';
import { scene } from './viewport.js';
import { context } from './context.js';

export const effectsGroup = new THREE.Group();
effectsGroup.name = 'viewport-effects-root';
scene.add(effectsGroup);

let activeNormalArrow = null;

export function clearViewportEffects() {
  if (activeNormalArrow) {
    effectsGroup.remove(activeNormalArrow);
    if (activeNormalArrow.line && activeNormalArrow.line.geometry) {
      activeNormalArrow.line.geometry.dispose();
    }
    if (activeNormalArrow.cone && activeNormalArrow.cone.geometry) {
      activeNormalArrow.cone.geometry.dispose();
    }
    activeNormalArrow = null;
  }
}

export function updateFaceNormalIndicator(faceMesh) {
  clearViewportEffects();
  if (!faceMesh || !faceMesh.userData || faceMesh.userData.type !== 'face') return;

  const meta = faceMesh.userData.meta;
  if (!meta) return;

  const normalArr = meta.normal || [0, 0, 1];
  const centerArr = meta.center || [0, 0, 0];

  const normal = new THREE.Vector3(normalArr[0], normalArr[1], normalArr[2]).normalize();
  const center = new THREE.Vector3(centerArr[0], centerArr[1], centerArr[2]);

  const length = 20.0;
  const hexColor = 0xffd885;
  const headLength = 5.0;
  const headWidth = 3.0;

  activeNormalArrow = new THREE.ArrowHelper(normal, center, length, hexColor, headLength, headWidth);
  activeNormalArrow.renderOrder = 20;
  effectsGroup.add(activeNormalArrow);
}

context.on('selections:changed', (selections) => {
  if (!selections.length) {
    clearViewportEffects();
  }
});
