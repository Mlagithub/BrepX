/**
 * Three.js Viewport & B-Rep Topology Container Renderer.
 * Builds independent Face Meshes and Edge LineSegments from backend B-Rep data.
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/OrbitControls.js';
import { context } from './context.js';
import { interactionLock } from './interaction_lock.js';
import { initViewCube, updateViewCube } from './view_cube.js';

export const container = document.getElementById('viewport');
const width = container.clientWidth;
const height = container.clientHeight;

export const scene = new THREE.Scene();
scene.background = new THREE.Color(0xf1f5f9);

const aspect = width / height;
const frustumSize = 160;

export const perspCamera = new THREE.PerspectiveCamera(45, aspect, 0.1, 10000);
perspCamera.position.set(120, 100, 140);

export const orthoCamera = new THREE.OrthographicCamera(
  -frustumSize * aspect / 2, frustumSize * aspect / 2,
  frustumSize / 2, -frustumSize / 2,
  0.1, 10000
);
orthoCamera.position.copy(perspCamera.position);

export let activeCamera = perspCamera;

export const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
renderer.setSize(width, height);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.1;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
container.appendChild(renderer.domElement);

export const controls = new OrbitControls(activeCamera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.target.set(0, 0, 0);

interactionLock.bindControls(controls, null);

const ambientLight = new THREE.AmbientLight(0xffffff, 0.95);
scene.add(ambientLight);

const dirLight1 = new THREE.DirectionalLight(0xffffff, 1.15);
dirLight1.position.set(150, 200, 150);
scene.add(dirLight1);

const dirLight2 = new THREE.DirectionalLight(0xb0c4de, 0.55);
dirLight2.position.set(-150, -100, -150);
scene.add(dirLight2);

export const gridHelper = new THREE.GridHelper(300, 60, 0x94a3b8, 0xdbe2ea);
gridHelper.position.y = -0.1;
scene.add(gridHelper);

export const axesHelper = new THREE.AxesHelper(50);
axesHelper.material.linewidth = 2;
scene.add(axesHelper);

export const modelGroup = new THREE.Group();
modelGroup.name = 'brep-models-root';
scene.add(modelGroup);

export const previewGroup = new THREE.Group();
previewGroup.name = 'modal-previews-root';
scene.add(previewGroup);

const defaultFaceMaterial = new THREE.MeshStandardMaterial({
  color: 0x5b9be6,
  metalness: 0.1,
  roughness: 0.45,
  side: THREE.DoubleSide,
  polygonOffset: true,
  polygonOffsetFactor: 1,
  polygonOffsetUnits: 1,
});

const defaultEdgeMaterial = new THREE.LineBasicMaterial({
  color: 0x1e293b,
  linewidth: 2,
});

export function disposeHierarchy(obj) {
  obj.traverse((child) => {
    if (child.geometry) child.geometry.dispose();
    if (child.material) {
      const mats = Array.isArray(child.material) ? child.material : [child.material];
      mats.forEach((m) => {
        if (m !== defaultFaceMaterial && m !== defaultEdgeMaterial) {
          m.dispose();
        }
      });
    }
  });
}

export function buildBrepScene(sceneData) {
  while (modelGroup.children.length > 0) {
    const child = modelGroup.children[0];
    modelGroup.remove(child);
    disposeHierarchy(child);
  }

  if (!sceneData || !sceneData.bodies) return;

  sceneData.bodies.forEach((body, bIndex) => {
    const bodyRoot = new THREE.Group();
    bodyRoot.name = body.body_id || `body_${bIndex + 1}`;

    (body.faces || []).forEach((faceData) => {
      if (!faceData.vertices || faceData.error) return;
      const geom = new THREE.BufferGeometry();
      geom.setAttribute('position', new THREE.Float32BufferAttribute(faceData.vertices, 3));
      geom.setIndex(faceData.indices);
      geom.computeVertexNormals();

      const faceMesh = new THREE.Mesh(geom, defaultFaceMaterial);
      faceMesh.castShadow = true;
      faceMesh.receiveShadow = true;
      faceMesh.userData = {
        type: 'face',
        selector: faceData.selector,
        meta: faceData,
      };
      bodyRoot.add(faceMesh);
    });

    (body.edges || []).forEach((edgeData) => {
      if (!edgeData.points || edgeData.points.length < 2) return;
      const flatPoints = [];
      edgeData.points.forEach(pt => flatPoints.push(pt[0], pt[1], pt[2]));

      const geom = new THREE.BufferGeometry();
      geom.setAttribute('position', new THREE.Float32BufferAttribute(flatPoints, 3));

      const edgeLine = new THREE.Line(geom, defaultEdgeMaterial);
      edgeLine.renderOrder = 2;
      edgeLine.userData = {
        type: 'edge',
        selector: edgeData.selector,
        meta: edgeData,
      };
      bodyRoot.add(edgeLine);
    });

    modelGroup.add(bodyRoot);
  });

  const box = new THREE.Box3().setFromObject(modelGroup);
  if (!box.isEmpty()) {
    gridHelper.position.y = box.min.y - 0.2;
    fitCameraToObject(modelGroup);
  }

  context.emit('scene:built', sceneData);
}

export function fitCameraToObject(object) {
  const box = new THREE.Box3().setFromObject(object);
  if (box.isEmpty()) return;

  const center = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3());
  const maxDim = Math.max(size.x, size.y, size.z, 20);
  const distance = maxDim * 2.2;

  controls.target.copy(center);
  const dir = new THREE.Vector3().subVectors(activeCamera.position, controls.target).normalize();
  if (dir.lengthSq() < 0.001) dir.set(1, 0.8, 1).normalize();

  activeCamera.position.copy(center).addScaledVector(dir, distance);
  activeCamera.near = Math.max(0.5, distance / 200);
  activeCamera.far = Math.max(distance * 30, 10000);

  if (activeCamera.isOrthographicCamera) {
    const asp = container.clientWidth / container.clientHeight;
    activeCamera.left = -maxDim * asp * 1.2;
    activeCamera.right = maxDim * asp * 1.2;
    activeCamera.top = maxDim * 1.2;
    activeCamera.bottom = -maxDim * 1.2;
  }
  activeCamera.updateProjectionMatrix();
  controls.update();
}

export function alignCameraNormalTo(faceMeta) {
  if (!faceMeta) return;
  const normalArr = faceMeta.normal || [0, 0, 1];
  const centerArr = faceMeta.center || [0, 0, 0];

  const normal = new THREE.Vector3(normalArr[0], normalArr[1], normalArr[2]).normalize();
  const center = new THREE.Vector3(centerArr[0], centerArr[1], centerArr[2]);

  const box = new THREE.Box3().setFromObject(modelGroup);
  const maxDim = box.isEmpty() ? 80 : Math.max(box.getSize(new THREE.Vector3()).length(), 40);
  const dist = maxDim * 1.8;

  controls.target.copy(center);
  activeCamera.position.copy(center).addScaledVector(normal, dist);

  let up = new THREE.Vector3(0, 1, 0);
  if (Math.abs(normal.dot(up)) > 0.9) {
    up.set(0, 0, 1);
  }
  activeCamera.up.copy(up);
  activeCamera.lookAt(center);
  activeCamera.updateProjectionMatrix();
  controls.update();
}

export function setStandardView(type) {
  const box = new THREE.Box3().setFromObject(modelGroup);
  const center = box.isEmpty() ? new THREE.Vector3() : box.getCenter(new THREE.Vector3());
  const dist = box.isEmpty() ? 120 : Math.max(box.getSize(new THREE.Vector3()).length() * 1.5, 80);

  controls.target.copy(center);
  activeCamera.up.set(0, 1, 0);

  if (type === 'iso') {
    activeCamera.position.set(center.x + dist * 0.7, center.y + dist * 0.6, center.z + dist * 0.7);
  } else if (type === 'front') {
    activeCamera.position.set(center.x, center.y, center.z + dist);
  } else if (type === 'top') {
    activeCamera.position.set(center.x, center.y + dist, center.z);
    activeCamera.up.set(0, 0, -1);
  } else if (type === 'right') {
    activeCamera.position.set(center.x + dist, center.y, center.z);
  } else if (type === 'fit') {
    fitCameraToObject(modelGroup);
    return;
  }
  controls.update();
}

export function setCameraType(type) {
  if (type === 'orthographic') {
    orthoCamera.position.copy(perspCamera.position);
    orthoCamera.quaternion.copy(perspCamera.quaternion);
    activeCamera = orthoCamera;
    controls.object = orthoCamera;
  } else {
    perspCamera.position.copy(orthoCamera.position);
    perspCamera.quaternion.copy(orthoCamera.quaternion);
    activeCamera = perspCamera;
    controls.object = perspCamera;
  }
  activeCamera.updateProjectionMatrix();
  controls.update();
}

export function setXrayMode(enable) {
  defaultFaceMaterial.transparent = enable;
  defaultFaceMaterial.opacity = enable ? 0.35 : 1.0;
  defaultFaceMaterial.depthWrite = !enable;
  defaultFaceMaterial.needsUpdate = true;

  modelGroup.traverse((child) => {
    if (child.isMesh && child.userData.type === 'face' && child.material !== defaultFaceMaterial) {
      child.material.transparent = enable;
      child.material.opacity = enable ? 0.35 : 1.0;
      child.material.depthWrite = !enable;
      child.material.needsUpdate = true;
    }
  });
}

export function resizeViewport() {
  const w = container.clientWidth;
  const h = container.clientHeight;
  if (!w || !h) return;
  const asp = w / h;

  perspCamera.aspect = asp;
  perspCamera.updateProjectionMatrix();

  orthoCamera.left = -frustumSize * asp / 2;
  orthoCamera.right = frustumSize * asp / 2;
  orthoCamera.top = frustumSize / 2;
  orthoCamera.bottom = -frustumSize / 2;
  orthoCamera.updateProjectionMatrix();

  renderer.setSize(w, h);
}

window.addEventListener('resize', resizeViewport);

export function startAnimationLoop() {
  initViewCube();
  function animate() {
    requestAnimationFrame(animate);
    controls.update();
    updateViewCube();
    renderer.render(scene, activeCamera);
  }
  animate();
}
