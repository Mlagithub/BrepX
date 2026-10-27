/**
 * Three.js Viewport & B-Rep Topology Container Renderer.
 * Builds independent Face Meshes and Edge LineSegments from backend B-Rep data.
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/OrbitControls.js';
import { ctx } from './context.js';
import { initViewCube, updateViewCube } from './view_cube.js';

export const container = document.getElementById('viewport');
const width = container.clientWidth;
const height = container.clientHeight;

export const scene = new THREE.Scene();
scene.background = new THREE.Color(0x1a1d24);

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

// Lighting
const ambientLight = new THREE.AmbientLight(0xffffff, 0.85);
scene.add(ambientLight);

const dirLight1 = new THREE.DirectionalLight(0xffffff, 1.2);
dirLight1.position.set(150, 200, 150);
scene.add(dirLight1);

const dirLight2 = new THREE.DirectionalLight(0xb0c4de, 0.6);
dirLight2.position.set(-150, -100, -150);
scene.add(dirLight2);

// Grid and Axis Helpers
export const gridHelper = new THREE.GridHelper(300, 60, 0x3e4451, 0x2c313a);
gridHelper.position.y = -0.1;
scene.add(gridHelper);

export const axesHelper = new THREE.AxesHelper(50);
axesHelper.material.linewidth = 2;
scene.add(axesHelper);

// Groups for models and previews
export const modelGroup = new THREE.Group();
modelGroup.name = 'brep-models-root';
scene.add(modelGroup);

export const previewGroup = new THREE.Group();
previewGroup.name = 'modal-previews-root';
scene.add(previewGroup);

// Materials for B-Rep entities
const defaultFaceMaterial = new THREE.MeshStandardMaterial({
  color: 0x80baff,
  metalness: 0.15,
  roughness: 0.45,
  side: THREE.DoubleSide,
  polygonOffset: true,
  polygonOffsetFactor: 1,
  polygonOffsetUnits: 1,
});

const defaultEdgeMaterial = new THREE.LineBasicMaterial({
  color: 0x182436,
  linewidth: 2,
});

export function disposeHierarchy(obj) {
  obj.traverse((child) => {
    if (child.geometry) child.geometry.dispose();
    if (child.material) {
      if (Array.isArray(child.material)) child.material.forEach(m => m.dispose());
      else child.material.dispose();
    }
  });
}

/**
 * Rebuild B-Rep objects from backend topological scene data.
 */
export function buildBrepScene(sceneData) {
  while (modelGroup.children.length > 0) {
    const child = modelGroup.children[0];
    modelGroup.remove(child);
    disposeHierarchy(child);
  }

  if (!sceneData || !sceneData.bodies) return;

  sceneData.bodies.forEach((body) => {
    const bodyRoot = new THREE.Group();
    bodyRoot.name = `body_${body.name}`;
    bodyRoot.userData = { bodyName: body.name, bodyExpr: body.expr, kind: body.kind, bbox: body.bbox };

    // 构造具备独立拓扑面索引与几何元数据的可拾取曲面网格
    (body.faces || []).forEach((faceData) => {
      const geom = new THREE.BufferGeometry();
      geom.setAttribute('position', new THREE.Float32BufferAttribute(faceData.vertices, 3));
      if (faceData.normals && faceData.normals.length === faceData.vertices.length) {
        geom.setAttribute('normal', new THREE.Float32BufferAttribute(faceData.normals, 3));
      } else {
        geom.computeVertexNormals();
      }
      geom.setIndex(faceData.indices);

      const mat = defaultFaceMaterial.clone();
      const faceMesh = new THREE.Mesh(geom, mat);
      faceMesh.name = `face_${faceData.face_index}`;
      faceMesh.castShadow = true;
      faceMesh.receiveShadow = true;
      faceMesh.userData = {
        type: 'face',
        bodyName: body.name,
        index: faceData.face_index,
        expr: faceData.expr,
        meta: faceData,
      };
      bodyRoot.add(faceMesh);
    });

    // 构造具备独立拓扑边索引的特征折线渲染对象
    (body.edges || []).forEach((edgeData) => {
      if (!edgeData.points || edgeData.points.length < 6) return;
      const geom = new THREE.BufferGeometry();
      geom.setAttribute('position', new THREE.Float32BufferAttribute(edgeData.points, 3));

      const edgeLine = new THREE.Line(geom, defaultEdgeMaterial.clone());
      edgeLine.name = `edge_${edgeData.edge_index}`;
      edgeLine.renderOrder = 2;
      edgeLine.userData = {
        type: 'edge',
        bodyName: body.name,
        index: edgeData.edge_index,
        expr: edgeData.expr,
        meta: edgeData,
      };
      bodyRoot.add(edgeLine);
    });

    modelGroup.add(bodyRoot);
  });

  // Fit camera & update grid
  const box = new THREE.Box3().setFromObject(modelGroup);
  if (!box.isEmpty()) {
    gridHelper.position.y = box.min.y - 0.2;
    fitCameraToObject(modelGroup);
  }
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

export function setStandardView(type) {
  const box = new THREE.Box3().setFromObject(modelGroup);
  const center = box.isEmpty() ? new THREE.Vector3() : box.getCenter(new THREE.Vector3());
  const dist = box.isEmpty() ? 120 : Math.max(box.getSize(new THREE.Vector3()).length() * 1.5, 80);

  controls.target.copy(center);
  if (type === 'iso') {
    activeCamera.position.set(center.x + dist * 0.7, center.y + dist * 0.6, center.z + dist * 0.7);
  } else if (type === 'front') {
    activeCamera.position.set(center.x, center.y, center.z + dist);
  } else if (type === 'top') {
    activeCamera.position.set(center.x, center.y + dist, center.z);
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
  modelGroup.traverse((child) => {
    if (child.isMesh && child.userData.type === 'face') {
      child.material.transparent = enable;
      child.material.opacity = enable ? 0.35 : 1.0;
      child.material.depthWrite = !enable;
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
