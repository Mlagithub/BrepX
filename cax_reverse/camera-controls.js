import * as THREE from 'three';

// FasCAD Web viewer rotation: orbit around the picked surface, preserving a free camera up vector.
export function rotateCadCameraAroundPivot(camera,target,pivot,dx,dy,width,height,motionFactor=10){
 if(width<=0||height<=0||(!dx&&!dy))return;
 const eye=camera.position.clone().sub(pivot),aim=target.clone().sub(pivot),q=new THREE.Quaternion();
 q.setFromAxisAngle(camera.up.clone().normalize(),THREE.MathUtils.degToRad(dx*(-20/width)*motionFactor));eye.applyQuaternion(q);aim.applyQuaternion(q);
 const right=aim.clone().sub(eye).normalize().cross(camera.up).normalize();
 q.setFromAxisAngle(right,THREE.MathUtils.degToRad(dy*(-20/height)*motionFactor));eye.applyQuaternion(q);aim.applyQuaternion(q);camera.up.applyQuaternion(q).normalize();
 camera.position.copy(pivot).add(eye);target.copy(pivot).add(aim);
 const view=target.clone().sub(camera.position).normalize(),correctedRight=view.clone().cross(camera.up).normalize();
 camera.up.copy(correctedRight.cross(view).normalize());camera.lookAt(target);
}
export function visibleHeight(camera,target){return camera.isOrthographicCamera?(camera.top-camera.bottom)/camera.zoom:2*camera.position.distanceTo(target)*Math.tan(THREE.MathUtils.degToRad(camera.fov/2));}
export function convertProjection(camera,target,mode,aspect){
 if((mode==='orthographic'&&camera.isOrthographicCamera)||(mode==='perspective'&&camera.isPerspectiveCamera))return camera;
 if(!['orthographic','perspective'].includes(mode))throw Error('Unknown projection');
 const height=visibleHeight(camera,target),direction=camera.position.clone().sub(target).normalize();let next;
 if(mode==='orthographic'){next=new THREE.OrthographicCamera(-height*aspect/2,height*aspect/2,height/2,-height/2,camera.near,camera.far);next.position.copy(camera.position);}
 else{const distance=height/(2*Math.tan(THREE.MathUtils.degToRad(20)));next=new THREE.PerspectiveCamera(40,aspect,camera.near,Math.max(camera.far,distance*100));next.position.copy(target).addScaledVector(direction,distance);}
 next.up.copy(camera.up);next.layers.mask=camera.layers.mask;next.lookAt(target);next.updateMatrixWorld(true);next.updateProjectionMatrix();return next;
}
export class CadCameraControls extends THREE.EventDispatcher{
 constructor(camera,canvas,resolvePivot){
  super();this.object=camera;this.target=new THREE.Vector3();this.enabled=true;this.mouseButtons={LEFT:THREE.MOUSE.ROTATE,MIDDLE:THREE.MOUSE.PAN,RIGHT:THREE.MOUSE.DOLLY};this.motionFactor=10;this.gesture=null;canvas.style.touchAction='none';
  const change=()=>this.dispatchEvent({type:'change'});
  canvas.addEventListener('pointerdown',e=>{
   if(!this.enabled||this.gesture)return;
   const action=this.mouseButtons[['LEFT','MIDDLE','RIGHT'][e.button]];if(action===null||action===undefined)return;
   this.gesture={id:e.pointerId,x:e.clientX,y:e.clientY,startX:e.clientX,startY:e.clientY,action,pivot:(action===THREE.MOUSE.ROTATE?resolvePivot(e):null)?.clone()||this.target.clone(),moved:false};canvas.setPointerCapture(e.pointerId);e.preventDefault();
  });
  canvas.addEventListener('pointermove',e=>{
   const g=this.gesture;if(!g||g.id!==e.pointerId||!this.enabled)return;
   if(!g.moved&&Math.hypot(e.clientX-g.startX,e.clientY-g.startY)<=4)return;
   g.moved=true;const dx=e.clientX-g.x,dy=e.clientY-g.y,r=canvas.getBoundingClientRect();g.x=e.clientX;g.y=e.clientY;
   if(g.action===THREE.MOUSE.ROTATE)rotateCadCameraAroundPivot(this.object,this.target,g.pivot,dx,dy,r.width,r.height,this.motionFactor);
   else if(g.action===THREE.MOUSE.PAN){const scale=visibleHeight(this.object,this.target)/Math.max(1,r.height),view=this.target.clone().sub(this.object.position).normalize(),right=view.cross(this.object.up).normalize(),translation=right.multiplyScalar(-dx*scale).add(this.object.up.clone().normalize().multiplyScalar(dy*scale));this.object.position.add(translation);this.target.add(translation);}
   else this.dolly(Math.exp(dy*.01));
   this.update();change();e.preventDefault();
  });
  const finish=e=>{if(this.gesture?.id!==e.pointerId)return;this.gesture=null;if(canvas.hasPointerCapture(e.pointerId))canvas.releasePointerCapture(e.pointerId);};
  canvas.addEventListener('pointerup',finish);canvas.addEventListener('pointercancel',finish);canvas.addEventListener('lostpointercapture',finish);
  canvas.addEventListener('wheel',e=>{if(!this.enabled)return;e.preventDefault();const scale=e.deltaMode===1?16:e.deltaMode===2?100:1;this.dolly(Math.exp(e.deltaY*scale*.001));this.update();change();},{passive:false});
 }
 dolly(factor){if(this.object.isOrthographicCamera){this.object.zoom=THREE.MathUtils.clamp(this.object.zoom/factor,1e-4,1e4);this.object.updateProjectionMatrix();}else{const eye=this.object.position.clone().sub(this.target);this.object.position.copy(this.target).add(eye.setLength(THREE.MathUtils.clamp(eye.length()*factor,1e-4,1e8)));}}
 update(){this.object.lookAt(this.target);this.object.updateMatrixWorld(true);}
}
