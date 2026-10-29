import * as THREE from 'three';
import { modelGroup } from './viewport.js';
import { ctx } from './context.js';

const patchListEl = document.getElementById('cfd-patch-list');

// 物理边界材质缓存池，避免重复创建材质导致显存泄漏
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

// 标准 CAD 天蓝色默认材质
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
 * 根据边界模式状态与补丁映射更新所有拓扑面的网格材质
 */
export function updateBoundaryVisuals() {
  const isBoundaryActive = ctx.isBoundaryMode;
  const patches = ctx.patches || [];

  // 构建面索引到物理颜色映射表
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

/**
 * 切换物理边界模式与标准 CAD 实体着色模式
 */
export function toggleBoundaryMode() {
  ctx.isBoundaryMode = !ctx.isBoundaryMode;
  updateBoundaryVisuals();
  return ctx.isBoundaryMode;
}

/**
 * 支持单面或多选面批量赋予物理边界语义属性
 * @param {number|number[]} faceIndices 选中的拓扑面索引或索引列表
 * @param {string} semanticType 边界类型 (inlet, outlet, wall, interface, symmetry)
 * @param {string|null} name 自定义边界名称
 */
export async function assignFacePatch(faceIndices, semanticType, name = null) {
  const cleanIndices = Array.isArray(faceIndices)
    ? faceIndices.map(i => parseInt(i, 10)).filter(i => !isNaN(i))
    : [parseInt(faceIndices, 10)];

  if (!cleanIndices.length) return null;

  const res = await fetch('/api/semantic/patch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      face_indices: cleanIndices,
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

/**
 * 移除指定的物理边界补丁并同步视口显示
 */
export async function deletePatch(patchId) {
  const res = await fetch(`/api/semantic/patch/${patchId}`, { method: 'DELETE' });
  const data = await res.json();
  if (res.ok) {
    ctx.setPatches(data.patches);
    updateBoundaryVisuals();
  }
}

/**
 * 清除模型上所有的物理边界标注
 */
export async function clearAllPatches() {
  const res = await fetch('/api/semantic/patches', { method: 'DELETE' });
  const data = await res.json();
  if (res.ok) {
    ctx.setPatches(data.patches || []);
    updateBoundaryVisuals();
  }
}

/**
 * 渲染右侧面板中的物理边界卡片列表与面积统计
 */
function renderPatchList(patches) {
  if (!patchListEl) return;
  if (!patches.length) {
    patchListEl.innerHTML = `
      <div class="empty-hint">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-bottom:6px;opacity:0.6;"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
        <div>暂无物理边界标注</div>
        <div style="font-size:10px;margin-top:4px;color:var(--text-muted)">在 3D 视口中选中面，点击浮动打标条赋予物理边界</div>
      </div>
    `;
    return;
  }

  const totalArea = patches.reduce((sum, p) => sum + (p.area || 0), 0);

  let html = `
    <div class="cfd-patch-summary-bar">
      <span>已定义 <b>${patches.length}</b> 个边界</span>
      <span>总面积: <b>${Math.round(totalArea)}</b> mm²</span>
    </div>
  `;

  html += patches.map((p) => `
    <div class="patch-card" data-patch-id="${p.id}">
      <div class="patch-card-info">
        <div class="patch-title" style="color:${p.color_hex}">
          <span class="patch-dot" style="background:${p.color_hex}"></span>
          <b>${p.name}</b>
          <span class="patch-type-pill" style="border-color:${p.color_hex};color:${p.color_hex}">${p.semantic_type.toUpperCase()}</span>
        </div>
        <div class="patch-sub">
          面 [${p.face_indices.join(', ')}] · 面积: ${p.area} mm²
        </div>
      </div>
      <button class="btn-icon-subtle btn-del-patch" data-patch-id="${p.id}" title="删除此边界标注" aria-label="删除 ${p.name}">✕</button>
    </div>
  `).join('');

  patchListEl.innerHTML = html;
}

// 物理边界补丁列表事件委托，避免频繁增删 DOM 节点时重复绑定事件
if (patchListEl) {
  patchListEl.addEventListener('click', (e) => {
    const delBtn = e.target.closest('.btn-del-patch');
    if (delBtn) {
      e.stopPropagation();
      deletePatch(delBtn.dataset.patchId);
      return;
    }
    const card = e.target.closest('.patch-card');
    if (card) {
      const pid = card.dataset.patchId;
      const targetPatch = (ctx.patches || []).find(p => p.id === pid);
      if (!targetPatch) return;
      const newSels = targetPatch.face_indices.map(fIdx => ({
        type: 'face',
        body: 'part',
        index: fIdx,
        expr: `part.faces()[${fIdx}]`,
        meta: {},
      }));
      ctx.setMode('EDIT');
      ctx.setSelectionLevel('face');
      ctx.setSelections(newSels);
    }
  });
}

ctx.on('patches:updated', () => updateBoundaryVisuals());
ctx.on('scene:updated', () => updateBoundaryVisuals());
