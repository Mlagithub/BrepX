/**
 * Three-dimensional orthogonal datum reference planes (XY, XZ, YZ).
 * Provides visual coordinate spatial reference and raycast filter isolation.
 */

import * as THREE from 'three';
import { scene } from './viewport.js';

export const datumGroup = new THREE.Group();
datumGroup.name = 'datum-planes-root';
scene.add(datumGroup);

const planeSize = 80.0;

function createPlaneMesh(colorHex, name) {
  const geom = new THREE.PlaneGeometry(planeSize, planeSize);
  const mat = new THREE.MeshBasicMaterial({
    color: colorHex,
    side: THREE.DoubleSide,
    transparent: true,
    opacity: 0.12,
    depthWrite: false,
  });
  const mesh = new THREE.Mesh(geom, mat);
  mesh.name = name;
  mesh.userData = { isDatumPlane: true, planeName: name };

  const edgesGeom = new THREE.EdgesGeometry(geom);
  const edgesMat = new THREE.LineBasicMaterial({
    color: colorHex,
    transparent: true,
    opacity: 0.45,
  });
  const wire = new THREE.LineSegments(edgesGeom, edgesMat);
  mesh.add(wire);

  return mesh;
}

const xyPlane = createPlaneMesh(0x61afef, 'XY_Front');
datumGroup.add(xyPlane);

const xzPlane = createPlaneMesh(0x98c379, 'XZ_Top');
xzPlane.rotation.x = Math.PI / 2;
datumGroup.add(xzPlane);

const yzPlane = createPlaneMesh(0xe06c75, 'YZ_Right');
yzPlane.rotation.y = Math.PI / 2;
datumGroup.add(yzPlane);

datumGroup.visible = false;

export function toggleDatumPlanes(visible) {
  datumGroup.visible = visible !== undefined ? visible : !datumGroup.visible;
  return datumGroup.visible;
}

export function isDatumPlanesVisible() {
  return datumGroup.visible;
}
