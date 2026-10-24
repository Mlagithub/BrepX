/**
 * Native B-Rep Topological Raycaster & Multi-Selection System.
 * Supports Hover Pre-highlighting, Shift Multi-selection, and topological HUD inspection.
 */

import * as THREE from 'three';
import { activeCamera, container, modelGroup, scene } from './viewport.js';
import { ctx } from './context.js';

const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();

// Group for active selection and hover highlights
export const selectionGroup = new THREE.Group();
selectionGroup.name = 'selection-highlight-root';
scene.add(selectionGroup);

// Highlight materials
const hoverFaceMat = new THREE.MeshBasicMaterial({
  color: 0xffd885,
  side: THREE.DoubleSide,
  transparent: true,
  opacity: 0.35,
  depthTest: true,
  polygonOffset: true,
  polygonOffsetFactor: -2,
  polygonOffsetUnits: -2,
});

const selectedFaceMat = new THREE.MeshBasicMaterial({
  color: 0xffa116,
  side: THREE.DoubleSide,
  transparent: true,
  opacity: 0.7,
  depthTest: true,
  polygonOffset: true,
  polygonOffsetFactor: -3,
  polygonOffsetUnits: -3,
});

const hoverEdgeMat = new THREE.LineBasicMaterial({
  color: 0xffea00,
  linewidth: 3,
  depthTest: false,
});

const selectedEdgeMat = new THREE.LineBasicMaterial({
  color: 0xff9900,
  linewidth: 4,
  depthTest: false,
});

let hoveredMesh = null;
let hoverHighlightObj = null;

// Track selection objects for fast toggle
const activeSelectionVisuals = new Map(); // expr -> Object3D

export function clearSelectionVisuals() {
  activeSelectionVisuals.forEach((obj) => {
    selectionGroup.remove(obj);
    if (obj.geometry) obj.geometry.dispose();
  });
  activeSelectionVisuals.clear();
  clearHoverHighlight();
}

function clearHoverHighlight() {
  if (hoverHighlightObj) {
    selectionGroup.remove(hoverHighlightObj);
    if (hoverHighlightObj.geometry) hoverHighlightObj.geometry.dispose();
    hoverHighlightObj = null;
  }
  hoveredMesh = null;
}

function updateMouseCoords(clientX, clientY) {
  const rect = container.getBoundingClientRect();
  mouse.x = ((clientX - rect.left) / rect.width) * 2 - 1;
  mouse.y = -((clientY - rect.top) / rect.height) * 2 + 1;
}

/**
 * Handle hover motion to pre-highlight B-Rep faces or edges.
 */
export function handlePointerMove(clientX, clientY) {
  if (ctx.mode === 'OBJECT') {
    clearHoverHighlight();
    return;
  }
  updateMouseCoords(clientX, clientY);
  raycaster.setFromCamera(mouse, activeCamera);

  const level = ctx.selectionLevel;
  const targets = [];
  modelGroup.traverse((child) => {
    if (level === 'face' && child.isMesh && child.userData.type === 'face') {
      targets.push(child);
    } else if (level === 'edge' && child.isLine && child.userData.type === 'edge') {
      targets.push(child);
    }
  });

  const intersects = raycaster.intersectObjects(targets, false);
  if (!intersects.length) {
    clearHoverHighlight();
    return;
  }

  const hit = intersects[0].object;
  if (hit === hoveredMesh) return;

  clearHoverHighlight();
  hoveredMesh = hit;

  if (level === 'face') {
    const cloneGeom = hit.geometry.clone();
    cloneGeom.applyMatrix4(hit.matrixWorld);
    hoverHighlightObj = new THREE.Mesh(cloneGeom, hoverFaceMat);
    hoverHighlightObj.renderOrder = 9;
    selectionGroup.add(hoverHighlightObj);
  } else if (level === 'edge') {
    const cloneGeom = hit.geometry.clone();
    cloneGeom.applyMatrix4(hit.matrixWorld);
    hoverHighlightObj = new THREE.Line(cloneGeom, hoverEdgeMat);
    hoverHighlightObj.renderOrder = 10;
    selectionGroup.add(hoverHighlightObj);
  }
}

/**
 * Handle click selection with optional Shift multi-selection.
 */
export function handlePointerClick(clientX, clientY, isShiftKey = false) {
  updateMouseCoords(clientX, clientY);
  raycaster.setFromCamera(mouse, activeCamera);

  if (ctx.selectionLevel === 'solid') {
    const meshes = [];
    modelGroup.traverse(c => { if (c.isMesh) meshes.push(c); });
    const hits = raycaster.intersectObjects(meshes, true);
    if (!hits.length) {
      ctx.clearSelections();
      return;
    }
    const hitObj = hits[0].object;
    let rootBody = hitObj;
    while (rootBody.parent && rootBody.parent !== modelGroup) {
      rootBody = rootBody.parent;
    }
    ctx.setSelections([{
      type: 'solid',
      body: rootBody.userData.bodyName || 'part',
      expr: rootBody.userData.bodyExpr || 'part',
      meta: rootBody.userData,
    }]);
    return;
  }

  const level = ctx.selectionLevel;
  const targets = [];
  modelGroup.traverse((child) => {
    if (level === 'face' && child.isMesh && child.userData.type === 'face') {
      targets.push(child);
    } else if (level === 'edge' && child.isLine && child.userData.type === 'edge') {
      targets.push(child);
    }
  });

  const intersects = raycaster.intersectObjects(targets, false);
  if (!intersects.length) {
    if (!isShiftKey) {
      ctx.clearSelections();
    }
    return;
  }

  const hit = intersects[0].object;
  const data = {
    type: hit.userData.type,
    body: hit.userData.bodyName,
    index: hit.userData.index,
    expr: hit.userData.expr,
    meta: hit.userData.meta,
  };

  if (isShiftKey) {
    ctx.toggleSelection(data);
  } else {
    ctx.setSelections([data]);
  }
}

// React to context selection changes and rebuild visual highlight meshes
ctx.on('selections:changed', (selections) => {
  clearSelectionVisuals();
  selections.forEach((sel) => {
    let targetObj = null;
    modelGroup.traverse((c) => {
      if (c.userData.expr === sel.expr) targetObj = c;
    });
    if (!targetObj) return;

    if (sel.type === 'face' && targetObj.isMesh) {
      const g = targetObj.geometry.clone();
      g.applyMatrix4(targetObj.matrixWorld);
      const mesh = new THREE.Mesh(g, selectedFaceMat);
      mesh.renderOrder = 10;
      selectionGroup.add(mesh);
      activeSelectionVisuals.set(sel.expr, mesh);
    } else if (sel.type === 'edge' && targetObj.isLine) {
      const g = targetObj.geometry.clone();
      g.applyMatrix4(targetObj.matrixWorld);
      const line = new THREE.Line(g, selectedEdgeMat);
      line.renderOrder = 11;
      selectionGroup.add(line);
      activeSelectionVisuals.set(sel.expr, line);
    }
  });

  // Update floating face action pill in DOM
  const pill = document.getElementById('face-action-pill');
  if (pill) {
    if (selections.length === 1 && selections[0].type === 'face') {
      const s = selections[0];
      document.getElementById('pill-face-title').textContent = `Face #${s.index} (${s.meta.geom_type})`;
      pill.classList.remove('hidden');
    } else {
      pill.classList.add('hidden');
    }
  }

  // Update selection context bar in Right Panel
  const ctxSummary = document.getElementById('ctx-summary');
  const ctxPills = document.getElementById('ctx-pills');
  if (ctxSummary && ctxPills) {
    if (!selections.length) {
      ctxSummary.textContent = '未选中（点击视口中的面或边）';
      ctxPills.innerHTML = '';
    } else {
      ctxSummary.textContent = `已选 ${selections.length} 项 (Shift 可多选)`;
      ctxPills.innerHTML = selections.map(s => `
        <span class="sel-tag" title="${s.expr}">${s.type.toUpperCase()} #${s.index}</span>
      `).join('');
    }
  }
});
