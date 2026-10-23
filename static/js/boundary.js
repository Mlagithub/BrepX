import * as THREE from 'three';
import { scene } from './viewport.js';

export const boundaryGroup = new THREE.Group();
boundaryGroup.visible = false;
scene.add(boundaryGroup);

let isBoundaryMode = false;
let boundaryPatches = [];

export function getIsBoundaryMode() {
  return isBoundaryMode;
}

export function setBoundaryMode(active, currentPartGroup) {
  isBoundaryMode = active;
  boundaryGroup.visible = active;
  if (active) {
    updateBoundaryVisuals(currentPartGroup);
  }
}

export function setBoundaryPatches(patches, currentPartGroup) {
  boundaryPatches = patches || [];
  if (isBoundaryMode) {
    updateBoundaryVisuals(currentPartGroup);
  }
}

export async function markFaceSemantic(faceIndex, semanticType, normal, currentPartGroup) {
  const res = await fetch('/api/semantic/patch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      face_index: faceIndex,
      semantic_type: semanticType,
      normal: normal || [0, 0, 1],
      area: 0.0
    })
  });
  const data = await res.json();
  if (data.ok) {
    boundaryPatches = data.all_patches;
    setBoundaryMode(true, currentPartGroup);
    return data.patch;
  }
  throw new Error('物理边界打标失败');
}

export function updateBoundaryVisuals(currentPartGroup) {
  while (boundaryGroup.children.length > 0) {
    const obj = boundaryGroup.children[0];
    boundaryGroup.remove(obj);
    if (obj.geometry) obj.geometry.dispose();
  }

  if (!currentPartGroup) return;

  let mainMesh = null;
  currentPartGroup.traverse(child => {
    if (child.isMesh && child.name !== 'cad-edge-line' && !mainMesh) mainMesh = child;
  });
  if (!mainMesh) return;

  const posAttr = mainMesh.geometry.attributes.position;
  const idx = mainMesh.geometry.index;

  boundaryPatches.forEach(p => {
    const colorHex = parseInt(p.color_hex.replace('#', '0x'));
    p.face_indices.forEach(fIdx => {
      const pA = new THREE.Vector3(), pB = new THREE.Vector3(), pC = new THREE.Vector3();
      if (idx) {
        if (fIdx * 3 + 2 >= idx.count) return;
        pA.fromBufferAttribute(posAttr, idx.getX(fIdx * 3));
        pB.fromBufferAttribute(posAttr, idx.getX(fIdx * 3 + 1));
        pC.fromBufferAttribute(posAttr, idx.getX(fIdx * 3 + 2));
      } else {
        if (fIdx * 3 + 2 >= posAttr.count) return;
        pA.fromBufferAttribute(posAttr, fIdx * 3);
        pB.fromBufferAttribute(posAttr, fIdx * 3 + 1);
        pC.fromBufferAttribute(posAttr, fIdx * 3 + 2);
      }

      mainMesh.localToWorld(pA);
      mainMesh.localToWorld(pB);
      mainMesh.localToWorld(pC);

      const geom = new THREE.BufferGeometry();
      geom.setAttribute('position', new THREE.Float32BufferAttribute([
        pA.x, pA.y, pA.z,
        pB.x, pB.y, pB.z,
        pC.x, pC.y, pC.z
      ], 3));
      geom.computeVertexNormals();

      const patchMat = new THREE.MeshBasicMaterial({
        color: colorHex,
        side: THREE.DoubleSide,
        polygonOffset: true,
        polygonOffsetFactor: -2,
        polygonOffsetUnits: -2
      });

      const patchMesh = new THREE.Mesh(geom, patchMat);
      boundaryGroup.add(patchMesh);
    });
  });
}
