import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

let renderer;
let scene;
let camera;
let controls;
let model;
let raycaster;
let pointer;
let selectedMesh = null;
let down = null;

export function initViewport(element, onPick) {
  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(element.clientWidth, element.clientHeight);
  element.appendChild(renderer.domElement);

  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0f1115);

  camera = new THREE.PerspectiveCamera(
    45, element.clientWidth / element.clientHeight, 0.1, 100000,
  );
  camera.up.set(0, 0, 1);
  camera.position.set(160, -160, 120);

  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;

  scene.add(new THREE.HemisphereLight(0xffffff, 0x2a3140, 1.5));
  const key = new THREE.DirectionalLight(0xffffff, 2.2);
  key.position.set(160, 220, 180);
  scene.add(key);
  const fill = new THREE.DirectionalLight(0x8899bb, 0.9);
  fill.position.set(-140, -100, -120);
  scene.add(fill);

  const grid = new THREE.GridHelper(400, 40, 0x2a3140, 0x1b2029);
  grid.rotation.x = Math.PI / 2;
  scene.add(grid);

  model = new THREE.Group();
  scene.add(model);
  raycaster = new THREE.Raycaster();
  pointer = new THREE.Vector2();

  renderer.domElement.addEventListener("pointerdown", (event) => {
    down = { x: event.clientX, y: event.clientY };
  });
  renderer.domElement.addEventListener("pointerup", (event) => {
    if (!down) return;
    const moved = Math.hypot(event.clientX - down.x, event.clientY - down.y);
    down = null;
    if (moved > 4) return;
    pick(event, onPick);
  });

  new ResizeObserver(() => {
    const width = element.clientWidth;
    const height = element.clientHeight;
    if (!width || !height) return;
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
  }).observe(element);

  const animate = () => {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
  };
  animate();
}

function clearModel() {
  for (const child of [...model.children]) {
    model.remove(child);
    child.geometry?.dispose();
    child.material?.dispose?.();
  }
  selectedMesh = null;
}

export function setScene(payload) {
  clearModel();
  if (!payload) return;

  for (const face of payload.faces ?? []) {
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(face.vertices.length * 3);
    face.vertices.forEach((vertex, index) => {
      positions[index * 3] = vertex[0];
      positions[index * 3 + 1] = vertex[1];
      positions[index * 3 + 2] = vertex[2];
    });
    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geometry.setIndex(face.triangles);
    geometry.computeVertexNormals();
    const material = new THREE.MeshStandardMaterial({
      color: new THREE.Color().setHSL(0.58, 0.18, 0.5 + (face.index % 6) * 0.02),
      metalness: 0.12,
      roughness: 0.62,
      emissive: 0x000000,
    });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.userData = { kind: "face", index: face.index, meta: face };
    model.add(mesh);
  }

  const segments = [];
  for (const edge of payload.edges ?? []) {
    for (let index = 0; index < edge.points.length - 1; index += 1) {
      segments.push(...edge.points[index], ...edge.points[index + 1]);
    }
  }
  if (segments.length) {
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.Float32BufferAttribute(segments, 3));
    model.add(new THREE.LineSegments(
      geometry, new THREE.LineBasicMaterial({ color: 0x10141b }),
    ));
  }

  fitCamera();
}

function fitCamera() {
  if (!model.children.length) return;
  const box = new THREE.Box3().setFromObject(model);
  const sphere = box.getBoundingSphere(new THREE.Sphere());
  if (!Number.isFinite(sphere.radius) || sphere.radius <= 0) return;
  const direction = new THREE.Vector3(1, -1, 0.8).normalize();
  controls.target.copy(sphere.center);
  camera.position.copy(sphere.center).addScaledVector(direction, sphere.radius * 2.6);
  camera.near = Math.max(sphere.radius / 2000, 0.01);
  camera.far = sphere.radius * 200;
  camera.updateProjectionMatrix();
  controls.update();
}

function pick(event, onPick) {
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const meshes = model.children.filter((child) => child.isMesh);
  const hits = raycaster.intersectObjects(meshes, false);
  if (!hits.length) {
    select(null);
    onPick?.(null);
    return;
  }
  const mesh = hits[0].object;
  select(mesh);
  onPick?.({ index: mesh.userData.index, ...mesh.userData.meta });
}

function select(mesh) {
  if (selectedMesh && selectedMesh !== mesh) {
    selectedMesh.material.emissive?.setHex(0x000000);
  }
  selectedMesh = mesh;
  if (mesh) {
    mesh.material.emissive?.setHex(0x2a4a7a);
    mesh.material.emissiveIntensity = 1.0;
  }
}
