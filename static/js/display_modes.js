/**
 * Display modes switcher (Shaded with edges, Shaded, Wireframe, Zebra analysis).
 */

import * as THREE from 'three';
import { modelGroup } from './viewport.js';
import { context } from './context.js';

let currentMode = 'shaded_edges';

export function setDisplayMode(mode) {
  currentMode = mode;

  modelGroup.traverse((child) => {
    if (child.isMesh && child.userData.type === 'face') {
      if (mode === 'wireframe') {
        child.material.wireframe = true;
      } else {
        child.material.wireframe = false;
      }

      if (mode === 'zebra') {
        child.material.color = new THREE.Color(0xffffff);
        child.material.roughness = 0.05;
        child.material.metalness = 0.95;
      } else {
        child.material.color = new THREE.Color(0x5b9be6);
        child.material.roughness = 0.45;
        child.material.metalness = 0.1;
      }
    } else if (child.isLine && child.userData.type === 'edge') {
      child.visible = (mode === 'shaded_edges' || mode === 'wireframe');
    }
  });

  context.setDisplayMode(mode);
}

context.on('displayMode:changed', (mode) => {
  if (mode !== currentMode) setDisplayMode(mode);
});
