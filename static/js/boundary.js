/**
 * CFD Physical Boundary Surface Coloring & Patch Manager for BrepX.
 * Switches face colors only in Boundary Mode and renders patch cards.
 */

import * as THREE from 'three';
import { modelGroup } from './viewport.js';
import { ctx } from './context.js';

const patchListEl = document.getElementById('cfd-patch-list');

const boundaryMaterialCache = new Map();
function getBoundaryMaterial(colorHex) {
  if (!boundaryMaterialCache.has(colorHex)) {
    const mat = new THREE.MeshStandardMaterial({
      color: parseInt(colorHex.replace('#', '0x'), 16),
      metalness: 0.1,
      roughness: 0.35,
      side: THREE.DoubleSide,
      polygonOffset: true,
      polygonOffsetFactor: 1,
      polygonOffsetUnits: 1,
    });
    boundaryMaterialCache.set(colorHex, mat);
  }
  return boundaryMaterialCache.get(colorHex);
}

const defaultCADMaterial = new THREE.MeshStandardMaterial({
  color: 0x80baff,
  metalness: 0.15,
  roughness: 0.45,
  side: THREE.DoubleSide,
  polygonOffset: true,
  polygonOffsetFactor: 1,
  polygonOffsetUnits: 1,
});

/**
 * Update face mesh materials according to boundary mode status.
 */
export function updateBoundaryVisuals() {
  const isBoundaryActive = ctx.isBoundaryMode;
  const patches = ctx.patches || [];

  // Build a fast lookup: face_index -> color_hex
  const faceColorMap = new Map();
  patches.forEach((p) => {
    (p.face_indices || []).forEach((fIdx) => {
      faceColorMap.set(fIdx, p.color_hex);
    });
  });

  modelGroup.traverse((child) => {
    if (child.isMesh && child.userData.type === 'face') {
      const fIdx = child.userData.index;
      if (isBoundaryActive && faceColorMap.has(fIdx)) {
        child.material = getBoundaryMaterial(faceColorMap.get(fIdx));
      } else {
        child.material = defaultCADMaterial.clone();
      }
    }
  });

  renderPatchList(patches);
}

export function toggleBoundaryMode() {
  ctx.isBoundaryMode = !ctx.isBoundaryMode;
  updateBoundaryVisuals();
  return ctx.isBoundaryMode;
}

export async function assignFacePatch(faceIndex, semanticType, name = null) {
  const res = await fetch('/api/semantic/patch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      face_indices: [faceIndex],
      semantic_type: semanticType,
      name,
    }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || '标注失败');

  ctx.setPatches(data.patches);
  if (!ctx.isBoundaryMode) {
    toggleBoundaryMode();
  } else {
    updateBoundaryVisuals();
  }
  return data.patch;
}

export async function deletePatch(patchId) {
  const res = await fetch(`/api/semantic/patch/${patchId}`, { method: 'DELETE' });
  const data = await res.json();
  if (res.ok) {
    ctx.setPatches(data.patches);
    updateBoundaryVisuals();
  }
}

function renderPatchList(patches) {
  if (!patchListEl) return;
  if (!patches.length) {
    patchListEl.innerHTML = '<div class="empty-hint">暂无已标注边界。在 3D 视口中点击拓扑面并标记为对应边界类型。</div>';
    return;
  }

  patchListEl.innerHTML = patches.map((p) => `
    <div class="patch-card">
      <div class="patch-card-info">
        <div class="patch-title" style="color:${p.color_hex}">● ${p.name} (${p.semantic_type.toUpperCase()})</div>
        <div class="patch-sub">面索引: [${p.face_indices.join(', ')}] · 面积: ${p.area} mm² · 法向: [${p.normal.join(', ')}]</div>
      </div>
      <button class="btn-icon-subtle btn-del-patch" data-patch-id="${p.id}" title="删除此边界标注">✕</button>
    </div>
  `).join('');

  patchListEl.querySelectorAll('.btn-del-patch').forEach((btn) => {
    btn.onclick = () => deletePatch(btn.dataset.patchId);
  });
}

ctx.on('patches:updated', () => updateBoundaryVisuals());
ctx.on('scene:updated', () => updateBoundaryVisuals());
