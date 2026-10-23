import * as THREE from 'three';
import { scene, activeCamera } from './viewport.js';

export const highlightGroup = new THREE.Group();
scene.add(highlightGroup);

const raycaster = new THREE.Raycaster();
const mousePos = new THREE.Vector2();

// 顶点标靶指示小球
export const vertexMarker = new THREE.Mesh(
  new THREE.SphereGeometry(1.2, 16, 16),
  new THREE.MeshBasicMaterial({ color: 0xffd885, depthTest: false })
);
vertexMarker.renderOrder = 999;
vertexMarker.visible = false;
highlightGroup.add(vertexMarker);

// 面高亮网格
let highlightFaceMesh = null;
const faceHighlightMaterial = new THREE.MeshBasicMaterial({
  color: 0xffc766,
  side: THREE.DoubleSide,
  transparent: true,
  opacity: 0.65,
  polygonOffset: true,
  polygonOffsetFactor: -1,
  polygonOffsetUnits: -1
});

// 边高亮线条
let highlightEdgeLine = null;
const edgeHighlightMaterial = new THREE.LineBasicMaterial({
  color: 0xffea00,
  linewidth: 3,
  depthTest: false
});

export function clearHighlights() {
  if (highlightFaceMesh) {
    highlightGroup.remove(highlightFaceMesh);
    if (highlightFaceMesh.geometry) highlightFaceMesh.geometry.dispose();
    highlightFaceMesh = null;
  }
  if (highlightEdgeLine) {
    highlightGroup.remove(highlightEdgeLine);
    if (highlightEdgeLine.geometry) highlightEdgeLine.geometry.dispose();
    highlightEdgeLine = null;
  }
  if (vertexMarker) {
    vertexMarker.visible = false;
  }
}

function round2(v) {
  return Math.round(v * 100) / 100;
}

// 执行射线拾取
export function performSelectionPick(clientX, clientY, container, currentPartGroup, selectionMode, callbacks = {}) {
  if (!currentPartGroup) return null;

  const rect = container.getBoundingClientRect();
  mousePos.x = ((clientX - rect.left) / rect.width) * 2 - 1;
  mousePos.y = -((clientY - rect.top) / rect.height) * 2 + 1;

  raycaster.setFromCamera(mousePos, activeCamera);
  const meshes = [];
  currentPartGroup.traverse(child => {
    if (child.isMesh && child.name !== 'cad-edge-line') meshes.push(child);
  });

  const intersects = raycaster.intersectObjects(meshes, true);
  clearHighlights();

  if (!intersects.length) {
    if (callbacks.onClear) callbacks.onClear();
    return null;
  }

  const hit = intersects[0];

  if (selectionMode === 'solid') {
    if (callbacks.onSolidPick) callbacks.onSolidPick(hit);
    return { type: 'solid', hit };

  } else if (selectionMode === 'face') {
    if (hit.face) {
      const geom = new THREE.BufferGeometry();
      const posAttr = hit.object.geometry.attributes.position;
      const idx = hit.object.geometry.index;

      const pA = new THREE.Vector3(), pB = new THREE.Vector3(), pC = new THREE.Vector3();
      if (idx) {
        const iA = idx.getX(hit.faceIndex * 3);
        const iB = idx.getX(hit.faceIndex * 3 + 1);
        const iC = idx.getX(hit.faceIndex * 3 + 2);
        pA.fromBufferAttribute(posAttr, iA);
        pB.fromBufferAttribute(posAttr, iB);
        pC.fromBufferAttribute(posAttr, iC);
      } else {
        pA.fromBufferAttribute(posAttr, hit.faceIndex * 3);
        pB.fromBufferAttribute(posAttr, hit.faceIndex * 3 + 1);
        pC.fromBufferAttribute(posAttr, hit.faceIndex * 3 + 2);
      }

      hit.object.localToWorld(pA);
      hit.object.localToWorld(pB);
      hit.object.localToWorld(pC);

      geom.setAttribute('position', new THREE.Float32BufferAttribute([
        pA.x, pA.y, pA.z,
        pB.x, pB.y, pB.z,
        pC.x, pC.y, pC.z
      ], 3));
      geom.computeVertexNormals();

      highlightFaceMesh = new THREE.Mesh(geom, faceHighlightMaterial);
      highlightGroup.add(highlightFaceMesh);

      const normal = hit.face.normal.clone().applyQuaternion(hit.object.getWorldQuaternion(new THREE.Quaternion()));
      let orient = '空间倾斜面';
      if (Math.abs(normal.z) > 0.95) orient = normal.z > 0 ? '顶面 (+Z)' : '底面 (-Z)';
      else if (Math.abs(normal.y) > 0.95) orient = normal.y > 0 ? '侧面 (+Y)' : '侧面 (-Y)';
      else if (Math.abs(normal.x) > 0.95) orient = normal.x > 0 ? '右侧面 (+X)' : '左侧面 (-X)';

      const res = {
        type: 'face',
        index: hit.faceIndex,
        normal: [round2(normal.x), round2(normal.y), round2(normal.z)],
        orient,
        point: hit.point
      };
      if (callbacks.onFacePick) callbacks.onFacePick(res);
      return res;
    }

  } else if (selectionMode === 'edge') {
    const geom = hit.object.geometry;
    let closestLine = null;
    let minD = Infinity;

    const pos = geom.attributes.position;
    const v1 = new THREE.Vector3(), v2 = new THREE.Vector3();
    const hitPt = hit.object.worldToLocal(hit.point.clone());

    for (let i = 0; i < pos.count; i += 3) {
      for (let j = 0; j < 3; j++) {
        v1.fromBufferAttribute(pos, i + j);
        v2.fromBufferAttribute(pos, i + ((j + 1) % 3));
        const line = new THREE.Line3(v1, v2);
        const closestPt = new THREE.Vector3();
        line.closestPointToPoint(hitPt, true, closestPt);
        const d = closestPt.distanceTo(hitPt);
        if (d < minD) {
          minD = d;
          closestLine = [v1.clone(), v2.clone()];
        }
      }
    }

    if (closestLine) {
      const p1 = hit.object.localToWorld(closestLine[0]);
      const p2 = hit.object.localToWorld(closestLine[1]);
      const lineGeom = new THREE.BufferGeometry().setFromPoints([p1, p2]);
      highlightEdgeLine = new THREE.LineSegments(lineGeom, edgeHighlightMaterial);
      highlightGroup.add(highlightEdgeLine);

      const length = p1.distanceTo(p2);
      const res = { type: 'edge', length, p1, p2 };
      if (callbacks.onEdgePick) callbacks.onEdgePick(res);
      return res;
    }

  } else if (selectionMode === 'vertex') {
    const geom = hit.object.geometry;
    const pos = geom.attributes.position;
    const idx = geom.index;
    let closestV = null;
    let minD = Infinity;

    const testIndices = idx ? [
      idx.getX(hit.faceIndex * 3),
      idx.getX(hit.faceIndex * 3 + 1),
      idx.getX(hit.faceIndex * 3 + 2)
    ] : [hit.faceIndex * 3, hit.faceIndex * 3 + 1, hit.faceIndex * 3 + 2];

    for (const i of testIndices) {
      const v = new THREE.Vector3().fromBufferAttribute(pos, i);
      hit.object.localToWorld(v);
      const d = v.distanceTo(hit.point);
      if (d < minD) {
        minD = d;
        closestV = v;
      }
    }

    if (closestV) {
      vertexMarker.position.copy(closestV);
      vertexMarker.visible = true;

      const res = { type: 'vertex', vertex: closestV };
      if (callbacks.onVertexPick) callbacks.onVertexPick(res);
      return res;
    }
  }

  return null;
}
