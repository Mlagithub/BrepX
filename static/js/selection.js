import * as THREE from 'three';
import { activeCamera, container, modelGroup, scene } from './viewport.js';
import { context } from './context.js';

const raycaster = new THREE.Raycaster();
raycaster.params.Line.threshold = 4.0;
const mouse = new THREE.Vector2();

export const selectionGroup = new THREE.Group();
selectionGroup.name = 'selection-highlight-root';
scene.add(selectionGroup);

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
const activeSelectionVisuals = new Map();

let containerRect = container.getBoundingClientRect();
window.addEventListener('resize', () => {
  containerRect = container.getBoundingClientRect();
  rebuildRaycastCache();
});

let cachedFaceTargets = [];
let cachedEdgeTargets = [];

export function rebuildRaycastCache() {
  cachedFaceTargets = [];
  cachedEdgeTargets = [];
  modelGroup.traverse((child) => {
    if (child.isMesh && child.userData.type === 'face') {
      child.updateMatrixWorld(true);
      cachedFaceTargets.push(child);
    } else if (child.isLine && child.userData.type === 'edge') {
      child.updateMatrixWorld(true);
      cachedEdgeTargets.push(child);
    }
  });
}
context.on('snapshot:changed', rebuildRaycastCache);
context.on('scene:built', rebuildRaycastCache);
context.on('selectionLevel:changed', () => {
  clearHoverHighlight();
  rebuildRaycastCache();
});

export function clearSelectionVisuals() {
  activeSelectionVisuals.forEach((obj) => {
    selectionGroup.remove(obj);
  });
  activeSelectionVisuals.clear();
  clearHoverHighlight();
}

function clearHoverHighlight() {
  if (hoverHighlightObj) {
    selectionGroup.remove(hoverHighlightObj);
    hoverHighlightObj = null;
  }
  hoveredMesh = null;
}

function updateMouseCoords(clientX, clientY) {
  mouse.x = ((clientX - containerRect.left) / containerRect.width) * 2 - 1;
  mouse.y = -((clientY - containerRect.top) / containerRect.height) * 2 + 1;
}

let moveRafId = null;
let pendingPointer = null;

export function handlePointerMove(clientX, clientY) {
  if (context.mode === 'OBJECT') {
    clearHoverHighlight();
    return;
  }
  pendingPointer = { x: clientX, y: clientY };
  if (!moveRafId) {
    moveRafId = requestAnimationFrame(processPointerMove);
  }
}

function processPointerMove() {
  moveRafId = null;
  if (!pendingPointer) return;
  const { x, y } = pendingPointer;

  if (x < containerRect.left || x > containerRect.right || y < containerRect.top || y > containerRect.bottom) {
    clearHoverHighlight();
    return;
  }

  updateMouseCoords(x, y);
  raycaster.setFromCamera(mouse, activeCamera);

  const targets = context.selectionLevel === 'face' ? cachedFaceTargets : cachedEdgeTargets;
  if (!targets.length) {
    clearHoverHighlight();
    return;
  }

  const intersects = raycaster.intersectObjects(targets, false);
  if (!intersects.length) {
    clearHoverHighlight();
    return;
  }

  const hit = intersects[0].object;
  if (hit === hoveredMesh) return;

  clearHoverHighlight();
  hoveredMesh = hit;

  if (context.selectionLevel === 'face') {
    hoverHighlightObj = new THREE.Mesh(hit.geometry, hoverFaceMat);
    hoverHighlightObj.matrixAutoUpdate = false;
    hoverHighlightObj.matrix.copy(hit.matrixWorld);
    hoverHighlightObj.renderOrder = 9;
  } else {
    hoverHighlightObj = new THREE.Line(hit.geometry, hoverEdgeMat);
    hoverHighlightObj.matrixAutoUpdate = false;
    hoverHighlightObj.matrix.copy(hit.matrixWorld);
    hoverHighlightObj.renderOrder = 10;
  }
  selectionGroup.add(hoverHighlightObj);
}

export function handlePointerClick(clientX, clientY, isShiftKey = false) {
  containerRect = container.getBoundingClientRect();
  if (clientX < containerRect.left || clientX > containerRect.right || clientY < containerRect.top || clientY > containerRect.bottom) {
    return;
  }
  updateMouseCoords(clientX, clientY);
  raycaster.setFromCamera(mouse, activeCamera);

  if (!cachedFaceTargets.length && !cachedEdgeTargets.length) {
    rebuildRaycastCache();
  }

  const targets = context.selectionLevel === 'face' ? cachedFaceTargets : cachedEdgeTargets;
  const intersects = raycaster.intersectObjects(targets, false);
  if (!intersects.length) {
    if (!isShiftKey) context.clearSelections();
    return;
  }

  const hit = intersects[0].object;
  const selector = hit.userData.selector;
  if (!selector) return;

  const current = context.getSelection();
  if (isShiftKey) {
    const next = current.includes(selector)
      ? current.filter(s => s !== selector)
      : [...current, selector];
    context.setSelection(next);
  } else {
    context.setSelection([selector]);
  }
}

context.on('selections:changed', (selections) => {
  clearSelectionVisuals();
  selections.forEach((selExpr) => {
    let targetObj = null;
    modelGroup.traverse((c) => {
      if (c.userData.selector === selExpr) targetObj = c;
    });
    if (!targetObj) return;

    if (targetObj.isMesh) {
      const mesh = new THREE.Mesh(targetObj.geometry, selectedFaceMat);
      mesh.matrixAutoUpdate = false;
      mesh.matrix.copy(targetObj.matrixWorld);
      mesh.renderOrder = 10;
      selectionGroup.add(mesh);
      activeSelectionVisuals.set(selExpr, mesh);
    } else if (targetObj.isLine) {
      const line = new THREE.Line(targetObj.geometry, selectedEdgeMat);
      line.matrixAutoUpdate = false;
      line.matrix.copy(targetObj.matrixWorld);
      line.renderOrder = 11;
      selectionGroup.add(line);
      activeSelectionVisuals.set(selExpr, line);
    }
  });

  const ctxSummary = document.getElementById('ctx-summary');
  const ctxPills = document.getElementById('ctx-pills');
  if (ctxSummary && ctxPills) {
    if (!selections.length) {
      ctxSummary.textContent = '未选中（点击视口中的面或边）';
      ctxPills.innerHTML = '';
    } else {
      ctxSummary.textContent = `已选 ${selections.length} 项 (Shift 可多选)`;
      ctxPills.innerHTML = selections.map(expr => `
        <span class="sel-tag" title="${expr}">
          ${expr}
          <button class="sel-tag-del" data-del-expr="${expr}" title="取消选中" aria-label="取消选中 ${expr}">✕</button>
        </span>
      `).join('');
      ctxPills.querySelectorAll('.sel-tag-del').forEach((btn) => {
        btn.onclick = (e) => {
          e.stopPropagation();
          const targetExpr = btn.dataset.delExpr;
          context.setSelection(context.getSelection().filter(item => item !== targetExpr));
        };
      });
    }
  }
});
