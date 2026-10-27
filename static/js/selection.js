import * as THREE from 'three';
import { activeCamera, container, modelGroup, scene } from './viewport.js';
import { ctx } from './context.js';

const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();

export const selectionGroup = new THREE.Group();
selectionGroup.name = 'selection-highlight-root';
scene.add(selectionGroup);

// 高亮着色材质池
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

// 视口边界尺寸与可拾取拓扑对象缓存池，消除高频 DOM 回流与递归遍历
let containerRect = container.getBoundingClientRect();
window.addEventListener('resize', () => {
  containerRect = container.getBoundingClientRect();
  rebuildRaycastCache();
});

let cachedFaceTargets = [];
let cachedEdgeTargets = [];

function rebuildRaycastCache() {
  cachedFaceTargets = [];
  cachedEdgeTargets = [];
  modelGroup.traverse((child) => {
    if (child.isMesh && child.userData.type === 'face') {
      cachedFaceTargets.push(child);
    } else if (child.isLine && child.userData.type === 'edge') {
      cachedEdgeTargets.push(child);
    }
  });
}
ctx.on('scene:updated', rebuildRaycastCache);

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
  mouse.x = ((clientX - containerRect.left) / containerRect.width) * 2 - 1;
  mouse.y = -((clientY - containerRect.top) / containerRect.height) * 2 + 1;
}

// 射线相交计算帧调度器，避免高频鼠标移动阻塞主线程
let moveRafId = null;
let pendingPointer = null;

export function handlePointerMove(clientX, clientY) {
  if (ctx.mode === 'OBJECT') {
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

  updateMouseCoords(x, y);
  raycaster.setFromCamera(mouse, activeCamera);

  const targets = ctx.selectionLevel === 'face' ? cachedFaceTargets : cachedEdgeTargets;
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

  const cloneGeom = hit.geometry.clone();
  cloneGeom.applyMatrix4(hit.matrixWorld);

  if (ctx.selectionLevel === 'face') {
    hoverHighlightObj = new THREE.Mesh(cloneGeom, hoverFaceMat);
    hoverHighlightObj.renderOrder = 9;
  } else {
    hoverHighlightObj = new THREE.Line(cloneGeom, hoverEdgeMat);
    hoverHighlightObj.renderOrder = 10;
  }
  selectionGroup.add(hoverHighlightObj);
}

/**
 * 处理视口单选与 Shift 累加多选交互
 */
export function handlePointerClick(clientX, clientY, isShiftKey = false) {
  containerRect = container.getBoundingClientRect();
  updateMouseCoords(clientX, clientY);
  raycaster.setFromCamera(mouse, activeCamera);

  if (ctx.selectionLevel === 'solid') {
    const hits = raycaster.intersectObjects(cachedFaceTargets, false);
    if (!hits.length) {
      ctx.clearSelections();
      return;
    }
    let rootBody = hits[0].object;
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

  const targets = ctx.selectionLevel === 'face' ? cachedFaceTargets : cachedEdgeTargets;
  const intersects = raycaster.intersectObjects(targets, false);
  if (!intersects.length) {
    if (!isShiftKey) ctx.clearSelections();
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

// 响应全局选区变更重建拓扑高亮并同步打标栏
ctx.on('selections:changed', (selections) => {
  clearSelectionVisuals();
  selections.forEach((sel) => {
    let targetObj = null;
    modelGroup.traverse((c) => {
      if (c.userData.expr === sel.expr) targetObj = c;
    });
    if (!targetObj) return;

    const g = targetObj.geometry.clone();
    g.applyMatrix4(targetObj.matrixWorld);

    if (sel.type === 'face' && targetObj.isMesh) {
      const mesh = new THREE.Mesh(g, selectedFaceMat);
      mesh.renderOrder = 10;
      selectionGroup.add(mesh);
      activeSelectionVisuals.set(sel.expr, mesh);
    } else if (sel.type === 'edge' && targetObj.isLine) {
      const line = new THREE.Line(g, selectedEdgeMat);
      line.renderOrder = 11;
      selectionGroup.add(line);
      activeSelectionVisuals.set(sel.expr, line);
    }
  });

  // 选定面浮动快捷打标条
  const pill = document.getElementById('face-action-pill');
  if (pill) {
    const faceSels = selections.filter(s => s.type === 'face');
    if (faceSels.length > 0) {
      const titleEl = document.getElementById('pill-face-title');
      if (faceSels.length === 1) {
        const s = faceSels[0];
        const geom = (s.meta && s.meta.geom_type) ? ` (${s.meta.geom_type})` : '';
        titleEl.textContent = `Face #${s.index}${geom}`;
      } else {
        const indices = faceSels.map(f => f.index).join(', ');
        titleEl.textContent = `已选 ${faceSels.length} 个面 [${indices}]`;
      }
      pill.classList.remove('hidden');
    } else {
      pill.classList.add('hidden');
    }
  }

  // 右侧选区胶囊状态栏同步
  const ctxSummary = document.getElementById('ctx-summary');
  const ctxPills = document.getElementById('ctx-pills');
  if (ctxSummary && ctxPills) {
    if (!selections.length) {
      ctxSummary.textContent = '未选中（点击视口中的面或边）';
      ctxPills.innerHTML = '';
    } else {
      ctxSummary.textContent = `已选 ${selections.length} 项 (Shift 可多选)`;
      ctxPills.innerHTML = selections.map(s => `
        <span class="sel-tag" title="${s.expr}" data-sel-expr="${s.expr}">
          ${s.type.toUpperCase()} #${s.index}
          <button class="sel-tag-del" data-del-expr="${s.expr}" title="取消此项选中" aria-label="取消选中 ${s.expr}">✕</button>
        </span>
      `).join('');
      ctxPills.querySelectorAll('.sel-tag-del').forEach((btn) => {
        btn.onclick = (e) => {
          e.stopPropagation();
          const expr = btn.dataset.delExpr;
          ctx.setSelections(ctx.selections.filter(item => item.expr !== expr));
        };
      });
    }
  }
});
