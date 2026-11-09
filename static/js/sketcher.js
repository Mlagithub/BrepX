/**
 * Interactive 3D Viewport Workplane Sketcher for BrepX.
 * Allows clicking on the XY ground plane or a selected B-Rep face to draw
 * Line, Rectangle, Circle, Arc, Polyline, and Spline with rubber-band previews.
 */

import * as THREE from 'three';
import { activeCamera, container, controls, previewGroup } from './viewport.js';
import { ctx } from './context.js';
import { executeOperator } from './modal_ops.js';

let activeSketchKind = null; // 'line' | 'rectangle' | 'circle' | 'arc' | 'polyline' | 'spline'
let sketchWorkplane = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0);
let capturedPoints = [];
let previewSketchObj = null;

const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();

const sketchPreviewMat = new THREE.LineBasicMaterial({
  color: 0x61afef,
  linewidth: 3,
  depthTest: false,
});

export function isSketchingActive() {
  return activeSketchKind !== null;
}

export function startSketchSession(kind) {
  activeSketchKind = kind;
  capturedPoints = [];
  controls.enabled = false;

  // Determine workplane: if user selected a planar face, snap to it; otherwise XY plane
  const selectedFaces = ctx.selections.filter(s => s.type === 'face');
  if (selectedFaces.length && selectedFaces[0].meta.is_planar) {
    const f = selectedFaces[0];
    const n = new THREE.Vector3(...f.meta.normal).normalize();
    const c = new THREE.Vector3(...f.meta.center);
    sketchWorkplane = new THREE.Plane().setFromNormalAndCoplanarPoint(n, c);
  } else {
    sketchWorkplane = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0);
  }

  const tag = kind.toUpperCase();
  const hud = document.getElementById('modal-status-bar');
  if (hud) {
    hud.textContent = `[草图绘制: ${tag}] 鼠标在视口工作平面点击取点 · Enter 确认 · Esc 退出`;
    hud.classList.remove('hidden');
  }
}

export function endSketchSession() {
  activeSketchKind = null;
  capturedPoints = [];
  controls.enabled = true;
  clearSketchPreview();
  const hud = document.getElementById('modal-status-bar');
  if (hud) hud.classList.add('hidden');
}

function clearSketchPreview() {
  if (previewSketchObj) {
    previewGroup.remove(previewSketchObj);
    if (previewSketchObj.geometry) previewSketchObj.geometry.dispose();
    previewSketchObj = null;
  }
}

function getWorkplaneIntersection(clientX, clientY) {
  const rect = container.getBoundingClientRect();
  mouse.x = ((clientX - rect.left) / rect.width) * 2 - 1;
  mouse.y = -((clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(mouse, activeCamera);

  const hitPoint = new THREE.Vector3();
  const hit = raycaster.ray.intersectPlane(sketchWorkplane, hitPoint);
  return hit ? hitPoint : null;
}

/**
 * Handle mouse move during sketching to draw rubber-band preview
 */
export function handleSketchMouseMove(clientX, clientY) {
  if (!activeSketchKind) return;
  const currentPt = getWorkplaneIntersection(clientX, clientY);
  if (!currentPt) return;

  clearSketchPreview();

  if (activeSketchKind === 'rectangle' && capturedPoints.length === 1) {
    const p0 = capturedPoints[0];
    const pts = [
      p0,
      new THREE.Vector3(currentPt.x, p0.y, p0.z),
      currentPt,
      new THREE.Vector3(p0.x, currentPt.y, p0.z),
      p0,
    ];
    const geom = new THREE.BufferGeometry().setFromPoints(pts);
    previewSketchObj = new THREE.Line(geom, sketchPreviewMat);
    previewSketchObj.renderOrder = 20;
    previewGroup.add(previewSketchObj);
  } else if (activeSketchKind === 'circle' && capturedPoints.length === 1) {
    const r = capturedPoints[0].distanceTo(currentPt);
    const circlePts = [];
    const segs = 48;
    for (let i = 0; i <= segs; i++) {
      const theta = (i / segs) * Math.PI * 2;
      circlePts.push(new THREE.Vector3(
        capturedPoints[0].x + r * Math.cos(theta),
        capturedPoints[0].y + r * Math.sin(theta),
        capturedPoints[0].z
      ));
    }
    const geom = new THREE.BufferGeometry().setFromPoints(circlePts);
    previewSketchObj = new THREE.Line(geom, sketchPreviewMat);
    previewSketchObj.renderOrder = 20;
    previewGroup.add(previewSketchObj);
  } else if ((activeSketchKind === 'line' || activeSketchKind === 'polyline' || activeSketchKind === 'spline') && capturedPoints.length > 0) {
    const pts = [...capturedPoints, currentPt];
    const geom = new THREE.BufferGeometry().setFromPoints(pts);
    previewSketchObj = new THREE.Line(geom, sketchPreviewMat);
    previewSketchObj.renderOrder = 20;
    previewGroup.add(previewSketchObj);
  }
}

/**
 * Handle pointer click during sketching to lock control points
 */
export async function handleSketchClick(clientX, clientY) {
  if (!activeSketchKind) return;
  const currentPt = getWorkplaneIntersection(clientX, clientY);
  if (!currentPt) return;

  // Snap to 1mm grid
  currentPt.x = Math.round(currentPt.x);
  currentPt.y = Math.round(currentPt.y);
  currentPt.z = Math.round(currentPt.z);
  capturedPoints.push(currentPt);

  if (activeSketchKind === 'rectangle' && capturedPoints.length === 2) {
    const p1 = capturedPoints[0];
    const p2 = capturedPoints[1];
    const w = Math.abs(p2.x - p1.x);
    const h = Math.abs(p2.y - p1.y);
    const cx = (p1.x + p2.x) / 2;
    const cy = (p1.y + p2.y) / 2;
    endSketchSession();
    await executeOperator('sketch_draw', { sketch_kind: 'rectangle', width: w || 20, height: h || 20, cx, cy });
  } else if (activeSketchKind === 'circle' && capturedPoints.length === 2) {
    const r = Math.round(capturedPoints[0].distanceTo(capturedPoints[1]));
    const cx = capturedPoints[0].x;
    const cy = capturedPoints[0].y;
    endSketchSession();
    await executeOperator('sketch_draw', { sketch_kind: 'circle', radius: r || 15, cx, cy });
  } else if (activeSketchKind === 'line' && capturedPoints.length === 2) {
    const pts = capturedPoints.map(p => [p.x, p.y, p.z]);
    endSketchSession();
    await executeOperator('sketch_draw', { sketch_kind: 'line', points: pts });
  } else if (activeSketchKind === 'arc' && capturedPoints.length === 3) {
    const pts = capturedPoints.map(p => [p.x, p.y, p.z]);
    endSketchSession();
    await executeOperator('sketch_draw', { sketch_kind: 'arc', points: pts });
  }
}

export async function finishMultiPointSketch() {
  if (!activeSketchKind || capturedPoints.length < 2) {
    endSketchSession();
    return;
  }
  const pts = capturedPoints.map(p => [p.x, p.y, p.z]);
  const kind = activeSketchKind;
  endSketchSession();
  await executeOperator('sketch_draw', { sketch_kind: kind, points: pts, closed: true });
}

// Global sketch hotkeys (Enter finishes polyline/spline, Esc cancels)
window.addEventListener('keydown', (e) => {
  if (!isSketchingActive()) return;
  if (e.key === 'Enter') {
    e.preventDefault();
    finishMultiPointSketch();
  } else if (e.key === 'Escape') {
    e.preventDefault();
    endSketchSession();
  }
});
