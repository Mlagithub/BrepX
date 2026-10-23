import * as THREE from 'three';
import { OrbitControls } from 'three/addons/OrbitControls.js';

export const container = document.getElementById('viewport');
const width = container.clientWidth;
const height = container.clientHeight;

export const scene = new THREE.Scene();
scene.background = new THREE.Color(0x1a1d24);

// 相机系统 (支持透视与正交)
const aspect = width / height;
const frustumSize = 160;

export const perspCamera = new THREE.PerspectiveCamera(45, aspect, 0.1, 8000);
perspCamera.position.set(120, 100, 140);

export const orthoCamera = new THREE.OrthographicCamera(
  -frustumSize * aspect / 2,
  frustumSize * aspect / 2,
  frustumSize / 2,
  -frustumSize / 2,
  0.1,
  8000
);
orthoCamera.position.copy(perspCamera.position);

export let activeCamera = perspCamera;

export function setActiveCamera(cam) {
  activeCamera = cam;
  controls.object = cam;
}

// 渲染器
export const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: 'high-performance' });
renderer.setSize(width, height);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.1;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
container.appendChild(renderer.domElement);

// 视图控制器
export const controls = new OrbitControls(activeCamera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.target.set(0, 0, 0);

// 光照系统 (CAD 漫反射三点光)
const ambientLight = new THREE.AmbientLight(0xffffff, 0.85);
scene.add(ambientLight);

const dirLight1 = new THREE.DirectionalLight(0xffffff, 1.2);
dirLight1.position.set(150, 200, 150);
scene.add(dirLight1);

const dirLight2 = new THREE.DirectionalLight(0xb0c4de, 0.6);
dirLight2.position.set(-150, -100, -150);
scene.add(dirLight2);

// 网格辅助面
export const gridHelper = new THREE.GridHelper(300, 60, 0x3e4451, 0x2c313a);
gridHelper.position.y = -0.1;
scene.add(gridHelper);

// 坐标轴辅助
export const axesHelper = new THREE.AxesHelper(50);
axesHelper.material.linewidth = 2;
scene.add(axesHelper);

// 自适应窗口缩放
window.addEventListener('resize', () => {
  const w = container.clientWidth;
  const h = container.clientHeight;
  const asp = w / h;

  perspCamera.aspect = asp;
  perspCamera.updateProjectionMatrix();

  orthoCamera.left = -frustumSize * asp / 2;
  orthoCamera.right = frustumSize * asp / 2;
  orthoCamera.top = frustumSize / 2;
  orthoCamera.bottom = -frustumSize / 2;
  orthoCamera.updateProjectionMatrix();

  renderer.setSize(w, h);
});

// 相机自适应居中对齐模型
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
  activeCamera.far = Math.max(distance * 30, 8000);

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

// 切换标准视角
export function setStandardView(type, currentPartGroup) {
  if (!currentPartGroup) return;
  const box = new THREE.Box3().setFromObject(currentPartGroup);
  const center = box.getCenter(new THREE.Vector3());
  const dist = Math.max(box.getSize(new THREE.Vector3()).length() * 1.5, 80);

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
    fitCameraToObject(currentPartGroup);
    return;
  }
  controls.update();
}

// 动效循环
export function startAnimationLoop() {
  function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, activeCamera);
  }
  animate();
}
