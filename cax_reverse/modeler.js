import {retainOriginalStep} from './source-archive.js';
import { installModelingI18n } from './modeling-i18n.js';
import { setModelingText, modelingOption, setModelingHTML } from './modeling-i18n.js';
import * as THREE from 'three';
import {CadCameraControls,convertProjection,visibleHeight} from './camera-controls.js';
import {KernelClient} from './kernel-client.js';
import {DEFAULT_MODEL,MODEL_NAMES,isPrimitive,validateModel} from './modeling-state.js';
import {installModelingUI} from './modeling-ui.js';
import {installMouseModeling} from './modeling-mouse.js';
import {installModelingInteraction} from './modeling-interaction.js';
import {parseModelingCommand} from './modeling-command-line.js';
import {installModelingAxes} from './modeling-axes.js';
import {selectProjected} from './modeling-selection.js';
import {installFeatureUI} from './feature-ui.js';
import {validateFeatureDefinition,FEATURE_COMMANDS} from './feature-commands.js';
import {buildParametricPart,validateParametricPart} from './parametric-part.js';
import {buildFeatureGraph,featureGraphFromParameters,featureGraphParameters,validateFeatureGraph} from './feature-graph.js';
const $=id=>document.getElementById(id);
const html=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let project={name:'未命名模型',objects:[]},entries=[project],historyIndex=0,historyVersion=0;
let selections=[],activeId=null,selectionMode='solid',boxSelection=false,busy=true,initialized=false,stepAvailable=false,lastOperation=null,activeOperation=null;
let ui,mouse,axes,database,featureUI,renderFrame=0,renderCount=0,resizeCount=0,viewHeight=160,canvasWidth=0,canvasHeight=0,sequence=1;
const profiles={XY:[[0,0],[20,0],[20,12],[0,12]],XZ:[[10,0],[20,0],[20,20],[10,20]]};
let formSignature='',constructionCommand=null,profilePoints=[[0,0],[20,0],[20,12],[0,12]],wireframe=false;
const objects=new Map(),highlightGroup=new THREE.Group();
const renderer=new THREE.WebGLRenderer({antialias:true,alpha:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));$('viewport').append(renderer.domElement);
const scene=new THREE.Scene();scene.background=null;
let camera=new THREE.OrthographicCamera(-80,80,80,-80,.001,20000);camera.up.set(0,0,1);camera.position.set(120,-120,120);
const controls=new CadCameraControls(camera,renderer.domElement,e=>{camera.updateMatrixWorld();const r=renderer.domElement.getBoundingClientRect(),ray=new THREE.Raycaster();ray.setFromCamera(new THREE.Vector2((e.clientX-r.left)/r.width*2-1,1-(e.clientY-r.top)/r.height*2),camera);return ray.intersectObjects([...objects.values()].filter(o=>o.mesh.visible).map(o=>o.mesh),false)[0]?.point;});controls.target.set(20,20,0);controls.mouseButtons.MIDDLE=THREE.MOUSE.PAN;controls.mouseButtons.RIGHT=THREE.MOUSE.DOLLY;controls.update();
const interaction=installModelingInteraction();
scene.add(new THREE.HemisphereLight(0xdceaff,0x48546c,2.4));const light=new THREE.DirectionalLight(0xffffff,3);light.position.set(100,-100,200);scene.add(light,highlightGroup);
function requestRender(){if(renderFrame)return;renderFrame=requestAnimationFrame(()=>{renderFrame=0;axes?.update(camera);renderer.render(scene,camera);renderCount++;});}
controls.addEventListener('change',requestRender);
new ResizeObserver(()=>{const width=$('viewport').clientWidth,height=$('viewport').clientHeight;if(!width||!height||width===canvasWidth&&height===canvasHeight)return;canvasWidth=width;canvasHeight=height;renderer.setSize(width,height,false);if(camera.isOrthographicCamera){camera.left=-viewHeight*width/height/2;camera.right=-camera.left;camera.top=viewHeight/2;camera.bottom=-camera.top;}else camera.aspect=width/height;camera.updateProjectionMatrix();resizeCount++;requestRender();}).observe($('viewport'));
axes=installModelingAxes(scene,$('viewport'),$('show-axes'),requestRender);
function message(text,error=false){setModelingText($('status'),text);$('status').dataset.error=String(error);ui?.appendMessage(text,error);}
function dispose(object){object.traverse?.(o=>{o.geometry?.dispose();if(o.material)for(const m of Array.isArray(o.material)?o.material:[o.material])m.dispose();});object.parent?.remove(object);object.clear?.();}
function clearHighlight(){for(const child of [...highlightGroup.children])dispose(child);}
function fallbackModel(object){return {...DEFAULT_MODEL,kind:'brep',x:object.shape.bounds[0][0],y:object.shape.bounds[0][1],z:object.shape.bounds[0][2]};}
function objectModel(object){return object?.model||object&&fallbackModel(object);}
function active(){return project.objects.find(o=>o.id===activeId);}
function solidIds(){return [...new Set(selections.filter(s=>s.type==='solid').map(s=>s.objectId))];}
function selectedBooleanObjects(){if(selections.length<2||selections.length>20||selections.some(s=>s.type!=='solid'))return null;const selected=selections.map(s=>project.objects.find(o=>o.id===s.objectId));return selected.every(o=>o?.shape.dimension===3&&o.shape.manifold)?selected:null;}
function canEdit(){return selections.length===1&&selections[0].type==='solid';}
function selectionKey(s){return [s.objectId,s.type,s.id??''].join(':');}
function selectItems(items,append=false){if(busy)return;const next=append?[...selections]:[];for(const item of items){const i=next.findIndex(s=>selectionKey(s)===selectionKey(item));if(i>=0&&append)next.splice(i,1);else if(i<0)next.push(item);}selections=next;activeId=next.at(-1)?.objectId??activeId;refresh();}
function selectModel(id,append=false){if(objects.has(id))selectItems([{objectId:id,type:'solid'}],append);}
function makeTopology(object){
 const edges=object.shape.mesh.edges.map(e=>{const samples=[];for(let i=0;i<e.points.length;i+=3)samples.push(e.points.slice(i,i+3));let length=0;for(let i=1;i<samples.length;i++)length+=new THREE.Vector3(...samples[i]).distanceTo(new THREE.Vector3(...samples[i-1]));const start=samples[0]||[0,0,0],end=samples.at(-1)||start;return {id:e.index+1,kind:'curve',first:0,last:1,samples:samples.length>1?samples:[start,end],start,end,midpoint:samples[Math.floor((samples.length-1)/2)]||start,length:e.length??length,faceIds:[],isSeam:false};});
 const vertices=[],seen=new Set();const isolated=object.shape.mesh.points||[];for(let i=0;i<isolated.length;i+=3)vertices.push({id:vertices.length+1,point:isolated.slice(i,i+3)});for(const edge of edges)for(const point of [edge.start,edge.end]){const key=point.map(v=>v.toPrecision(12)).join(',');if(!seen.has(key)){seen.add(key);vertices.push({id:vertices.length+1,point});}}
 return {edges,vertices};
}
function allTopology(){const vertices=[],edges=[];for(const [id,item]of objects){if(!item.mesh.visible)continue;vertices.push(...item.topology.vertices.map(v=>({...v,id:id+':'+v.id})));edges.push(...item.topology.edges.map(e=>({...e,id:id+':'+e.id})));}return {vertices,edges};}
function makeGeometry(mesh){
 const indexed=new THREE.BufferGeometry();indexed.setAttribute('position',new THREE.Float32BufferAttribute(mesh.positions,3));indexed.setIndex(mesh.indices);const geometry=indexed.toNonIndexed();indexed.dispose();
 const sums=new Map(),a=new THREE.Vector3(),b=new THREE.Vector3(),c=new THREE.Vector3(),n=new THREE.Vector3();
 for(let i=0;i<mesh.indices.length;i+=3){a.fromArray(mesh.positions,mesh.indices[i]*3);b.fromArray(mesh.positions,mesh.indices[i+1]*3);c.fromArray(mesh.positions,mesh.indices[i+2]*3);n.crossVectors(b.sub(a),c.sub(a));for(let j=0;j<3;j++){const key=mesh.faceMap[i/3]+':'+mesh.indices[i+j];if(!sums.has(key))sums.set(key,new THREE.Vector3());sums.get(key).add(n);}}
 const normals=new Float32Array(mesh.indices.length*3);for(let i=0;i<mesh.indices.length;i++)sums.get(mesh.faceMap[Math.floor(i/3)]+':'+mesh.indices[i]).clone().normalize().toArray(normals,i*3);geometry.setAttribute('normal',new THREE.BufferAttribute(normals,3));return geometry;
}
function edgeGeometry(topologyEdges){const points=[];for(const e of topologyEdges)for(let i=1;i<e.samples.length;i++)points.push(...e.samples[i-1],...e.samples[i]);const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(points,3));return g;}
function renderObjects(){
 clearHighlight();for(const item of objects.values()){dispose(item.mesh);dispose(item.edges);if(item.points)dispose(item.points);}objects.clear();
 for(const object of project.objects){
  const geometry=makeGeometry(object.shape.mesh),opacity=object.opacity??1;
  const mesh=new THREE.Mesh(geometry,new THREE.MeshStandardMaterial({color:object.color||'#80baff',roughness:.5,metalness:.15,side:THREE.DoubleSide,transparent:opacity<1,opacity,wireframe}));mesh.userData.objectId=object.id;mesh.visible=object.visible!==false;
  const topology=makeTopology(object),edges=new THREE.LineSegments(edgeGeometry(topology.edges),new THREE.LineBasicMaterial({color:0x223c59}));edges.userData.objectId=object.id;edges.visible=mesh.visible&&$('show-edges').checked;
  const pointGeometry=new THREE.BufferGeometry();pointGeometry.setAttribute('position',new THREE.Float32BufferAttribute(object.shape.mesh.points||[],3));const points=new THREE.Points(pointGeometry,new THREE.PointsMaterial({color:object.color||'#80baff',size:8,sizeAttenuation:false,transparent:opacity<1,opacity}));points.userData.objectId=object.id;points.visible=mesh.visible;
  const faces=Array.from({length:object.shape.faces},(_,i)=>({id:i+1,surfaceType:'SMLib 曲面',area:'—',center:'—',surface:{}}));
  const center=object.shape.bounds[0].map((v,i)=>(v+object.shape.bounds[1][i])/2),metrics={dimension:object.shape.dimension??3,volume:object.shape.volume==null?null:Math.abs(object.shape.volume),area:object.shape.area??'—',length:topology.edges.reduce((s,e)=>s+e.length,0),center:'—',valid:object.shape.topologyValid??object.shape.manifold};
  objects.set(object.id,{object,mesh,edges,points,topology,faces,metrics,center});scene.add(mesh,edges,points);
 }
 refresh();mouse?.refreshGrid();requestRender();
}
function refreshHighlight(){
 clearHighlight();for(const s of selections){const item=objects.get(s.objectId);if(!item?.mesh.visible)continue;let object;
  if(s.type==='solid'){
   if(item.points.geometry.getAttribute('position').count){const selectedPoints=new THREE.Points(item.points.geometry.clone(),new THREE.PointsMaterial({color:0xff9d00,size:11,sizeAttenuation:false,depthTest:true,depthWrite:false}));selectedPoints.userData.selectedObjectId=s.objectId;highlightGroup.add(selectedPoints);}
   const surface=new THREE.Mesh(item.mesh.geometry.clone(),new THREE.MeshBasicMaterial({color:0xffff00,transparent:true,opacity:.55*item.mesh.material.opacity,side:THREE.DoubleSide,depthWrite:false,polygonOffset:true,polygonOffsetFactor:-1,polygonOffsetUnits:-1}));surface.userData.selectedSurfaceId=s.objectId;highlightGroup.add(surface);
   object=new THREE.LineSegments(item.edges.geometry.clone(),new THREE.LineBasicMaterial({color:0xff9d00,depthTest:true,depthWrite:false}));object.userData.selectedObjectId=s.objectId;
  }else if(s.type==='edge'){const edge=item.topology.edges.find(e=>e.id===s.id);if(edge)object=new THREE.LineSegments(edgeGeometry([edge]),new THREE.LineBasicMaterial({color:0xff9d00,depthTest:true,depthWrite:false}));}
  else{const {mesh}=item.object.shape,p=[];mesh.faceMap.forEach((id,i)=>{if(id===s.id-1)for(let j=0;j<3;j++){const k=mesh.indices[i*3+j]*3;p.push(...mesh.positions.slice(k,k+3));}});const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(p,3));g.computeVertexNormals();object=new THREE.Mesh(g,new THREE.MeshStandardMaterial({color:0xffc766,roughness:.5,metalness:.15,side:THREE.DoubleSide,polygonOffset:true,polygonOffsetFactor:-1,polygonOffsetUnits:-1}));}
  if(object)highlightGroup.add(object);
 }
 // Draw highlights after opaque geometry, while retaining its depth occlusion.
 for(const child of highlightGroup.children)child.renderOrder=1;
 requestRender();
}
function getState(){const object=active(),item=objects.get(activeId),selected=selections.find(s=>s.objectId===activeId);return {project,model:objectModel(object),history:{index:historyIndex,entries,version:historyVersion},activeId,objects:[...objects.values()].map(o=>({object:o.object,metrics:o.metrics})),selections,boxSelection,busy,initialized,selected:!!selected,selectedFaceId:selected?.type==='face'?selected.id:null,selectedEdgeId:selected?.type==='edge'?selected.id:null,selectionMode,metrics:item?.metrics,faces:item?.faces||[],topology:item?.topology||{vertices:[],edges:[]}};}
function refresh(){
 const s=getState();ui?.refresh();refreshHighlight();
 setModelingText($('volume'),s.metrics?.volume?.toFixed(6)??'—');setModelingText($('area'),s.metrics?.area??'—');setModelingText($('compute'),lastOperation?.computeMs?.toFixed(2)??'—');setModelingText($('model-info'),project.objects.length?`${project.objects.length} 个对象 · ${project.name}`:'');
 for(const [id,type,values]of [['face-select','face',s.faces],['edge-select','edge',s.topology.edges]]){const select=$(id);select.replaceChildren(modelingOption('请选择'+(type==='face'?'面':'边'),''),...values.map(v=>modelingOption((type==='face'?'面 ':'边 ')+v.id,String(v.id))));select.disabled=busy||!initialized||!values.length;select.value=s.selections.find(v=>v.objectId===activeId&&v.type===type)?.id??'';}
 setModelingText($('face-detail'),s.selectedFaceId?`面 ${s.selectedFaceId}`:s.selectedEdgeId?`边 ${s.selectedEdgeId}`:'');
 const creating=['box','cylinder','sphere'].includes(mouse?.tool()),editable=canEdit()&&isPrimitive(active()?.model);$('model-form').hidden=!creating&&!editable;$('new-object').hidden=$('model-form').hidden;$('parameters-empty').hidden=creating||editable;refreshConstructionProperties();
 const signature=JSON.stringify([activeId,active()?.model,creating?mouse?.tool():null]);if(signature!==formSignature&&!busy){fillForm(editable?active().model:{...DEFAULT_MODEL,kind:creating?mouse.tool():'box'});formSignature=signature;}
 for(const fs of $('model-form').querySelectorAll('fieldset'))fs.disabled=busy||!initialized;
 for(const id of ['open','new-project','demo-project','new-object','new-parametric-part','new-feature-graph'])$(id).disabled=busy||!initialized;
 $('import-step').disabled=busy||!initialized||!stepAvailable;$('export-step').disabled=busy||!initialized||!stepAvailable||solidIds().length!==1||selections.length!==1||active()?.shape.dimension!==3||!active()?.shape.manifold;
 $('save').disabled=busy||!initialized||!project.objects.length;$('undo').disabled=busy||!initialized||historyIndex===0;$('redo').disabled=busy||!initialized||historyIndex===entries.length-1;
 for(const b of document.querySelectorAll('[data-view],[data-camera-projection],[data-construction],[data-feature]')){const c=b.dataset.construction;let invalid=false;if(['extrude','revolve'].includes(c))invalid=selections.length>0&&!selectedProfile()&&!selections.every(s=>s.type==='solid'&&project.objects.find(o=>o.id===s.objectId)?.shape.dimension===3);if(['offset','rotate3d'].includes(c))invalid=!solidIds().length;if(c==='shell')invalid=!selections.length||new Set(selections.map(s=>s.objectId)).size!==1;if(c==='copy')invalid=!solidIds().length;if(c==='distance')invalid=solidIds().length!==2;if(c==='slice')invalid=[...new Set(selections.map(s=>s.objectId))].length!==1;if(['fillet','chamfer'].includes(b.dataset.feature))invalid=!selections.length;if(b.dataset.feature==='boolean')invalid=solidIds().length<2;b.disabled=busy||!initialized||invalid;}
 for(const b of document.querySelectorAll('[data-boolean-operation]'))b.disabled=busy||!initialized||!selectedBooleanObjects();
 for(const b of document.querySelectorAll('[data-unavailable]'))b.disabled=true;
 featureUI?.refresh();
 controls.enabled=initialized&&!busy&&!document.querySelector('dialog[open]');controls.mouseButtons.LEFT=mouse?.tool()==='navigate'&&!boxSelection?THREE.MOUSE.ROTATE:null;
 document.querySelectorAll('[data-tool]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.tool===mouse?.tool())));
 syncViewButtons();requestRender();
}
function fillForm(model){for(const key of ['length','width','height','radius','diameter','holeX','holeY','x','y','z','angle','scale','kind'])$('model-form').elements.namedItem(key).value=model[key];$('model-form').elements.namedItem('hole').checked=model.hole;syncFields();}
function syncFields(){const f=$('model-form'),kind=f.elements.namedItem('kind').value;for(const l of f.querySelectorAll('[data-shapes]')){l.hidden=!l.dataset.shapes.split(' ').includes(kind);for(const input of l.querySelectorAll('input'))input.disabled=l.hidden;}$('hole-fields').hidden=kind!=='box'||!f.elements.namedItem('hole').checked;for(const input of $('hole-fields').querySelectorAll('input'))input.disabled=$('hole-fields').hidden;}
function readModel(){const f=$('model-form'),model={...DEFAULT_MODEL};for(const key of ['length','width','height','radius','diameter','holeX','holeY','x','y','z','angle','scale'])model[key]=Number(f.elements.namedItem(key).value);model.kind=f.elements.namedItem('kind').value;model.hole=model.kind==='box'&&f.elements.namedItem('hole').checked;return validateModel(model);}
$('model-form').addEventListener('change',syncFields);
function fitView(view='fit'){
 const box=new THREE.Box3();for(const item of objects.values())if(item.mesh.visible){if(item.object.shape.dimension===0){for(const v of item.topology.vertices)box.expandByPoint(new THREE.Vector3(...v.point));}else box.union(new THREE.Box3(new THREE.Vector3(...item.object.shape.bounds[0]),new THREE.Vector3(...item.object.shape.bounds[1])));};const sphere=box.isEmpty()?{center:new THREE.Vector3(20,20,Number($('workplane-z').value)||0),radius:60}:box.getBoundingSphere(new THREE.Sphere());
 const center=sphere.center,radius=sphere.radius>1e-5?sphere.radius:1,directions={iso:[1,-1,1],top:[0,0,1],front:[0,-1,0],right:[1,0,0],bottom:[0,0,-1],back:[0,1,0],left:[-1,0,0]};const direction=directions[view]?new THREE.Vector3(...directions[view]).normalize():camera.position.clone().sub(controls.target).normalize();
 if(directions[view])camera.up.set(...(['top','bottom'].includes(view)?[0,1,0]:[0,0,1]));controls.target.copy(center);const aspect=canvasWidth/canvasHeight||1;
 viewHeight=Math.max(radius,.00001)*2.6*Math.max(1,1/aspect);camera.zoom=1;
 const distance=camera.isPerspectiveCamera?Math.max(viewHeight/(2*Math.tan(THREE.MathUtils.degToRad(camera.fov/2))),.001):Math.max(radius*4,.001);
 if(camera.isOrthographicCamera){camera.left=-viewHeight*aspect/2;camera.right=-camera.left;camera.top=viewHeight/2;camera.bottom=-camera.top;}else camera.aspect=aspect;
 camera.position.copy(center).addScaledVector(direction,distance);camera.near=Math.max(.00001,radius/10000);camera.far=distance+radius*20;camera.updateProjectionMatrix();controls.update();mouse?.refreshGrid();syncViewButtons();requestRender();
}
function syncViewButtons(){
 const direction=camera.position.clone().sub(controls.target).normalize(),up=camera.up;
 const views={iso:[1,-1,1],top:[0,0,1],front:[0,-1,0],right:[1,0,0],bottom:[0,0,-1],back:[0,1,0],left:[-1,0,0]};
 for(const b of document.querySelectorAll('[data-view]')){const v=views[b.dataset.view],expectedUp=['top','bottom'].includes(b.dataset.view)?new THREE.Vector3(0,1,0):new THREE.Vector3(0,0,1);b.setAttribute('aria-pressed',String(!!v&&direction.distanceTo(new THREE.Vector3(...v).normalize())<1e-6&&up.distanceTo(expectedUp)<1e-6));}
 for(const b of document.querySelectorAll('[data-camera-projection]'))b.setAttribute('aria-pressed',String(b.dataset.cameraProjection===(camera.isOrthographicCamera?'orthographic':'perspective')));
 renderer.domElement.dataset.cameraProjectionMode=camera.isOrthographicCamera?'orthographic':'perspective';
}
function setProjection(mode){
 if(busy||!initialized)return;const next=convertProjection(camera,controls.target,mode,canvasWidth/canvasHeight||1);if(next===camera)return;
 camera=next;controls.object=camera;viewHeight=visibleHeight(camera,controls.target);mouse?.setCamera(camera);controls.update();mouse?.refreshGrid();syncViewButtons();requestRender();
}
controls.addEventListener('change',syncViewButtons);
for(const b of document.querySelectorAll('[data-camera-projection]'))b.onclick=()=>setProjection(b.dataset.cameraProjection);

let selectionDrag;
renderer.domElement.addEventListener('pointerdown',e=>{if(e.button!==0||busy||mouse?.tool()!=='navigate')return;selectionDrag={x:e.clientX,y:e.clientY,id:e.pointerId,append:e.ctrlKey||e.metaKey};if(boxSelection)renderer.domElement.setPointerCapture(e.pointerId);});
renderer.domElement.addEventListener('pointermove',e=>{if(!selectionDrag||!boxSelection)return;const r=renderer.domElement.getBoundingClientRect(),d=selectionDrag,element=$('selection-rectangle');element.hidden=false;element.dataset.mode=e.clientX>=d.x?'window':'crossing';element.style.left=Math.min(d.x,e.clientX)-r.left+'px';element.style.top=Math.min(d.y,e.clientY)-r.top+'px';element.style.width=Math.abs(d.x-e.clientX)+'px';element.style.height=Math.abs(d.y-e.clientY)+'px';});
const raycaster=new THREE.Raycaster();
interaction.setPickWorldPoint(event=>{const r=renderer.domElement.getBoundingClientRect();camera.updateMatrixWorld();raycaster.setFromCamera(new THREE.Vector2((event.clientX-r.left)/r.width*2-1,1-(event.clientY-r.top)/r.height*2),camera);const hit=raycaster.intersectObjects([...objects.values()].filter(o=>o.mesh.visible).map(o=>o.mesh),false)[0];if(hit)return hit.point.toArray();const z=Number($('workplane-z').value);return Number.isFinite(z)?raycaster.ray.intersectPlane(new THREE.Plane(new THREE.Vector3(0,0,1),-z),new THREE.Vector3())?.toArray()||null:null;});
function screenPoint(point){const p=new THREE.Vector3(...point).project(camera);return [(p.x+1)*canvasWidth/2,(1-p.y)*canvasHeight/2];}
function edgeHit(x,y){let best=null;for(const [objectId,item]of objects){if(!item.mesh.visible)continue;for(const edge of item.topology.edges){for(let i=1;i<edge.samples.length;i++){const a=screenPoint(edge.samples[i-1]),b=screenPoint(edge.samples[i]),dx=b[0]-a[0],dy=b[1]-a[1],t=Math.max(0,Math.min(1,((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy||1))),distance=Math.hypot(x-a[0]-t*dx,y-a[1]-t*dy);if(distance<=8&&(!best||distance<best.distance))best={objectId,type:'edge',id:edge.id,distance};}}}return best;}
function boxPick(d,e){const r=renderer.domElement.getBoundingClientRect(),rect={left:Math.min(d.x,e.clientX)-r.left,right:Math.max(d.x,e.clientX)-r.left,top:Math.min(d.y,e.clientY)-r.top,bottom:Math.max(d.y,e.clientY)-r.top},windowMode=e.clientX>=d.x,result=[];
 for(const [objectId,item]of objects){if(!item.mesh.visible)continue;const mesh=item.object.shape.mesh;if(selectionMode==='edge'){for(const edge of item.topology.edges)if(selectProjected(edge.samples.map(screenPoint),rect,windowMode,true))result.push({objectId,type:'edge',id:edge.id});}
 else if(selectionMode==='solid'){if(item.object.shape.dimension===0){const hits=item.topology.vertices.map(v=>{const p=screenPoint(v.point);return p[0]>=rect.left&&p[0]<=rect.right&&p[1]>=rect.top&&p[1]<=rect.bottom;});if(hits.length&&(windowMode?hits.every(Boolean):hits.some(Boolean)))result.push({objectId,type:'solid'});continue;}if(item.object.shape.dimension===1){const hits=item.topology.edges.map(edge=>selectProjected(edge.samples.map(screenPoint),rect,windowMode,true));if(windowMode?hits.every(Boolean):hits.some(Boolean))result.push({objectId,type:'solid'});continue;}const points=mesh.indices.map(i=>screenPoint(mesh.positions.slice(i*3,i*3+3)));if(selectProjected(points,rect,windowMode))result.push({objectId,type:'solid'});}
 else{for(const face of item.faces){const points=[];mesh.faceMap.forEach((id,i)=>{if(id===face.id-1)for(let j=0;j<3;j++){const k=mesh.indices[i*3+j]*3;points.push(screenPoint(mesh.positions.slice(k,k+3)));}});if(selectProjected(points,rect,windowMode))result.push({objectId,type:'face',id:face.id});}}}
 selectItems(result,d.append);
}
renderer.domElement.addEventListener('pointerup',e=>{if(e.button!==0||!selectionDrag)return;const d=selectionDrag;selectionDrag=null;$('selection-rectangle').hidden=true;if(renderer.domElement.hasPointerCapture(e.pointerId))renderer.domElement.releasePointerCapture(e.pointerId);if(busy||mouse?.tool()!=='navigate')return;const moved=Math.hypot(e.clientX-d.x,e.clientY-d.y)>4;if(boxSelection&&moved){boxPick(d,e);return;}if(moved)return;const r=renderer.domElement.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top;let selected;
 if(selectionMode==='edge')selected=edgeHit(x,y);else{camera.updateMatrixWorld();raycaster.setFromCamera(new THREE.Vector2(x/r.width*2-1,1-y/r.height*2),camera);let hit=raycaster.intersectObjects([...objects.values()].filter(o=>o.mesh.visible).map(o=>o.mesh),false)[0];if(!hit&&selectionMode==='solid'){raycaster.params.Line.threshold=(camera.isOrthographicCamera?(camera.top-camera.bottom)/camera.zoom:2*camera.position.distanceTo(controls.target)*Math.tan(camera.fov*Math.PI/360))/r.height*6;hit=raycaster.intersectObjects([...objects.values()].filter(o=>o.object.shape.dimension===1&&o.edges.visible).map(o=>o.edges),false)[0];}if(selectionMode==='solid'){raycaster.params.Points.threshold=(camera.isOrthographicCamera?(camera.top-camera.bottom)/camera.zoom:2*camera.position.distanceTo(controls.target)*Math.tan(camera.fov*Math.PI/360))/r.height*7;const pointHit=raycaster.intersectObjects([...objects.values()].filter(o=>o.points.visible).map(o=>o.points),false)[0];if(pointHit&&(!hit||pointHit.distance<=hit.distance))hit=pointHit;}if(hit){const item=objects.get(hit.object.userData.objectId);selected={objectId:item.object.id,type:selectionMode,...(selectionMode==='face'?{id:item.object.shape.mesh.faceMap[hit.faceIndex]+1}:{})};}}
 selectItems(selected?[selected]:[],d.append);
});
renderer.domElement.addEventListener('pointercancel',()=>{selectionDrag=null;$('selection-rectangle').hidden=true;});
for(const b of document.querySelectorAll('[data-selection-mode]'))b.onclick=()=>{selectionMode=b.dataset.selectionMode;selections=[];refresh();};
for(const b of document.querySelectorAll('[data-select-tool]'))b.onclick=()=>{mouse.cancel(true);boxSelection=true;refresh();};
for(const b of document.querySelectorAll('[data-clear-selection]'))b.onclick=()=>selectItems([]);
for(const b of document.querySelectorAll('[data-view]'))b.onclick=()=>fitView(b.dataset.view);
for(const [id,type]of [['face-select','face'],['edge-select','edge']])$(id).onchange=()=>{if($(id).value){selectionMode=type;selectItems([{objectId:activeId,type,id:Number($(id).value)}]);}};
$('show-edges').onchange=()=>{for(const item of objects.values())item.edges.visible=item.mesh.visible&&$('show-edges').checked;requestRender();};
async function openStorage(){return new Promise((resolve,reject)=>{const r=indexedDB.open('cax-smlib-modeler',1);r.onupgradeneeded=()=>r.result.createObjectStore('projects');r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});}
function persist(){if(!database)return;try{const t=database.transaction('projects','readwrite');t.objectStore('projects').put(project,'current');t.oncomplete=()=>setModelingText($('save-status'),'已自动保存');t.onerror=()=>message('自动保存失败，请保存 Web 工程到本机',true);}catch{message('自动保存失败，请保存 Web 工程到本机',true);}}
function commit(next,selectedIds=[]){project=next;entries=entries.slice(0,historyIndex+1);entries.push(next);if(entries.length>21)entries.shift();historyIndex=entries.length-1;historyVersion++;selections=selectedIds.filter(id=>next.objects.some(o=>o.id===id)).map(objectId=>({objectId,type:'solid'}));activeId=selections.at(-1)?.objectId??next.objects.at(-1)?.id??null;renderObjects();persist();}
function restore(index){if(busy||index<0||index>=entries.length||index===historyIndex)return;mouse.cancel(true);historyIndex=index;project=entries[index];selections=[];activeId=project.objects.at(-1)?.id??null;renderObjects();persist();message('历史记录已恢复');}
const kernel=new KernelClient(()=>{});
// The loading panel is shared by startup and explicit, cancelable geometry operations.
kernel.progress=text=>{setModelingText($('modeling-startup').querySelector('[data-startup-title]'),text);};
function checkCancellation(){if(activeOperation?.cancelled)throw Error('操作已取消，原模型已保留。');}
function cancelOperation(){if(activeOperation)activeOperation.cancelled=true;kernel.cancel?.();}
async function geometry(action,params={},operands=[]){checkCancellation();const start=performance.now();const result=await kernel.run({action,params},operands.map(o=>o.brep));checkCancellation();lastOperation={action,elapsedMs:performance.now()-start,computeMs:result.computeMs,heapBytes:result.heapBytes};return result;}
function makeObject(name,result,model=null,definition=null){return {id:crypto.randomUUID(),name,visible:true,color:'#80baff',opacity:1,shape:result.shape,brep:result.brep,...(model?{model}:{}),...(definition?{definition}:{}),postTransforms:[]};}
function featureModel(kind,params,operands=[],base=null){
 const model={...DEFAULT_MODEL,...base,kind};
 if(kind==='boolean'){model.operation={union:'fuse',difference:'cut',intersection:'common',xor:'xor'}[params.operation];model.operands=operands.length?operands.map(objectModel):(base?.operands||[]);}
 if(['fillet','chamfer'].includes(kind)){model.size=params.radius;model.edges=(params.edges||[]).map(i=>i+1);}
 if(kind==='sweep'){model.profile=params.profileKind==='rectangle'?{kind:'rectangle',width:params.width,height:params.height}:{kind:'circle',radius:params.radius};model.path=params.path;}
 return model;
}
async function operation(label,run,errorNode=null){if(busy||!initialized)return false;const previous={project,entries,historyIndex,selections,activeId};const token={cancelled:false};activeOperation=token;busy=true;mouse?.cancel(true);refresh();message('正在'+label+'…');if(errorNode)setModelingText(errorNode,'');
 try{await run(token);checkCancellation();message(label+'完成'+(lastOperation?' · '+(lastOperation.elapsedMs/1000).toFixed(2)+' s':''));return true;}
 catch(error){if(project!==previous.project){project=previous.project;entries=previous.entries;historyIndex=previous.historyIndex;selections=previous.selections;activeId=previous.activeId;historyVersion++;renderObjects();persist();}if(errorNode)setModelingText(errorNode,error.message);message(label+'失败：'+error.message,true);return false;}
 finally{if(activeOperation===token)activeOperation=null;busy=false;refresh();}
}
async function primitiveResult(model){
 const m=validateModel(model);if(!isPrimitive(m))throw Error('当前对象没有基础体构造参数');const transformed=m.angle!==0||m.scale!==1,origin=transformed?[0,0,0]:[m.x,m.y,m.z];let result=await geometry('create',{kind:m.kind,origin,length:m.length,width:m.width,height:m.height,radius:m.radius});
 if(m.hole){const tool=await geometry('create',{kind:'cylinder',origin:[origin[0]+m.length/2+m.holeX,origin[1]+m.width/2+m.holeY,origin[2]-1],radius:m.diameter/2,height:m.height+2});result=await geometry('boolean',{operation:'difference'},[result,tool]);if(result.empty)throw Error('开孔结果为空');}
 if(transformed)result=await geometry('transform',{translation:[m.x,m.y,m.z],rotation:[0,0,m.angle],scale:[m.scale,m.scale,m.scale]},[result]);return result;
}
async function createModel(model){if(model.kind==='profile')return createMouseCurve(model);return operation('新增模型',async()=>{const m=validateModel(model),result=await primitiveResult(m),object=makeObject((MODEL_NAMES[m.kind]||'实体')+sequence++,result,m);commit({...project,objects:[...project.objects,object]},[object.id]);});}
function arcParams(points){
 const [[ax,ay,az],[bx,by,bz],[cx,cy,cz]]=points;if(Math.max(Math.abs(az-bz),Math.abs(az-cz))>1e-6)throw Error('三点圆弧需要位于同一 XY 工作平面');const d=2*(ax*(by-cy)+bx*(cy-ay)+cx*(ay-by));if(Math.abs(d)<1e-8)throw Error('圆弧的三个点不能共线');
 const a=ax*ax+ay*ay,b=bx*bx+by*by,c=cx*cx+cy*cy,x=(a*(by-cy)+b*(cy-ay)+c*(ay-by))/d,y=(a*(cx-bx)+b*(ax-cx)+c*(bx-ax))/d,angle=(px,py)=>(Math.atan2(py-y,px-x)*180/Math.PI+360)%360;
 let start=angle(ax,ay),end=angle(cx,cy),middle=angle(bx,by);const span=(end-start+360)%360;if((middle-start+360)%360>span)[start,end]=[end,start];if(end<=start)end+=360;if(end>360){start-=360;end-=360;}return {kind:'arc',origin:[x,y,az],radius:Math.hypot(ax-x,ay-y),startAngle:start,endAngle:end};
}
async function createMouseCurve(value){return operation('创建曲线',async()=>{
 const m=validateModel(value);let params={kind:m.curve,points:m.points};if(m.curve==='line')params={kind:'line',start:m.points[0],end:m.points[1]};
 else if(m.curve==='circle')params={kind:'circle',origin:[m.x,m.y,m.z],radius:m.radius};else if(m.curve==='rectangle')params={kind:'rectangle',origin:[m.x+m.length/2,m.y+m.width/2,m.z],length:m.length,width:m.width};
 else if(m.curve==='arc')params=arcParams(m.points);else if(m.curve==='polyline')params.closed=!!m.closed;else if(m.curve==='bspline')params={kind:'interpolate',points:m.closed?[...m.points,m.points[0]]:m.points};
 const r=await geometry('curve_create',params),object=makeObject(({line:'直线',rectangle:'矩形',circle:'圆',arc:'圆弧',polyline:'折线',bspline:'样条'}[m.curve]||'曲线')+sequence++,r,m,{action:'curve_create',params,inputs:[]});commit({...project,objects:[...project.objects,object]},[object.id]);
 });}

function transformedModel(model,kind,p){if(!model)return null;const m={...model};if(kind==='move'){['x','y','z'].forEach((k,i)=>m[k]+=p.translation[i]);return m;}const [x,y,z]=p.pivot||[0,0,0];if(kind==='rotate'){const a=p.rotation[2]*Math.PI/180,dx=m.x-x,dy=m.y-y;m.x=x+Math.cos(a)*dx-Math.sin(a)*dy;m.y=y+Math.sin(a)*dx+Math.cos(a)*dy;m.angle=((m.angle+p.rotation[2]+540)%360)-180;return m;}const scale=p.scale[0];m.x=x+(m.x-x)*scale;m.y=y+(m.y-y)*scale;m.z=z+(m.z-z)*scale;m.scale*=scale;return m;}
async function transformObjects(kind,p){const ids=solidIds();if(!ids.length||ids.length!==selections.length)throw Error('请选择要变换的实体');const updates=new Map();for(const id of ids){const object=project.objects.find(o=>o.id===id),r=await geometry('transform',p,[object]);updates.set(id,{...object,brep:r.brep,shape:r.shape,model:transformedModel(object.model,kind,p),postTransforms:[...(object.postTransforms||[]),p]});}commit({...project,objects:project.objects.map(o=>updates.get(o.id)||o)},ids);}
async function buildModel(model,{operation:kind}={}){
 if(kind==='move'){const base=objectModel(active()),delta=[model.x-base.x,model.y-base.y,model.z-base.z];return operation('移动模型',()=>transformObjects('move',{translation:delta}));}
 return operation('更新几何',async()=>{if(!canEdit()||!isPrimitive(active()?.model))throw Error('请选择具有基础体参数的实体');const object=active(),m=validateModel(model),result=await primitiveResult(m);commit({...project,objects:project.objects.map(o=>o.id===object.id?{...o,model:m,brep:result.brep,shape:result.shape,postTransforms:[]}:o)},[object.id]);});
}
mouse=installMouseModeling({renderer,scene,camera,controls,viewport:$('viewport'),getModel:()=>selections.length?objectModel(active()):null,getTopology:allTopology,getMesh:()=>objects.get(activeId)?.mesh,getMeshes:()=>solidIds().map(id=>objects.get(id)?.mesh).filter(m=>m?.visible),isBusy:()=>busy||!initialized,buildModel,createModel,requestRender,message,directMode:interaction.direct});
document.addEventListener('modeling-interaction-change',()=>{mouse.cancel(true);refresh();});
ui=installModelingUI({getState,restore,selectModel,fitView,setTool:tool=>{if(busy||!initialized||!['navigate','box','cylinder','sphere','move','resize','height','hole','line','rectangle','circle','arc','polyline','bspline'].includes(tool))return;boxSelection=false;mouse.setTool(tool);refresh();},onSettingsVisibilityChange:refresh});
document.addEventListener('modeling-toolchange',()=>{if(ui)refresh();});
$('model-form').onsubmit=e=>{e.preventDefault();try{const m=readModel();if(canEdit()&&isPrimitive(active()?.model))buildModel(m);else createModel(m);}catch(error){message(error.message,true);}};
$('new-object').onclick=()=>{try{createModel(readModel());}catch(error){message(error.message,true);}};
let editingParametricPart=null;
const defaultPartValues=()=>({length:40,width:25,height:12,holeDiameter:6,holeX:0,holeY:0,filletRadius:1});
const defaultGraphValues=()=>({x:0,y:0,length:40,width:25,height:12,bossEnabled:false,bossDiameter:8,bossOffsetX:-10,bossOffsetY:0,bossHeight:4,holeEnabled:true,concentricHole:false,wallLinked:false,wallThickness:2,diameter:6,offsetX:0,offsetY:0,filletEnabled:true,radius:1,corner:'lower_left'});
function openParametricPart(object=null){if(busy||!initialized)return;editingParametricPart=object?.recipe?object.id:null;const params=object?.recipe?.params||{length:40,width:25,height:12,holeDiameter:6,holeX:0,holeY:0,filletRadius:1};for(const [key,value]of Object.entries(params))$('parametric-part-form').elements.namedItem(key).value=value;setModelingText($('parametric-part-title'),editingParametricPart?'编辑带孔圆角板':'创建带孔圆角板');setModelingText($('parametric-part-error'),'');$('parametric-part-dialog').showModal();refresh();}
$('new-parametric-part').onclick=()=>openParametricPart();
$('edit-parametric-part').onclick=()=>openParametricPart(active());
$('parametric-part-cancel').onclick=()=>$('parametric-part-dialog').close();
$('parametric-part-dialog').addEventListener('close',()=>{editingParametricPart=null;refresh();});
$('parametric-part-form').onsubmit=async e=>{e.preventDefault();const form=new FormData(e.target),params=Object.fromEntries(['length','width','height','holeDiameter','holeX','holeY','filletRadius'].map(key=>[key,Number(form.get(key))]));let recipe;try{recipe=validateParametricPart({kind:'rectangular-plate',version:1,params});}catch(error){setModelingText($('parametric-part-error'),error.message);return;}
 const id=editingParametricPart;const success=await operation(id?'更新带孔圆角板':'创建带孔圆角板',async()=>{const original=id?project.objects.find(o=>o.id===id):null;if(id&&!original?.recipe)throw Error('原零件不存在');let result=await buildParametricPart(recipe,geometry);for(const transform of original?.postTransforms||[])result=await geometry('transform',transform,[result]);if(original)commit({...project,objects:project.objects.map(o=>o.id===id?{...o,shape:result.shape,brep:result.brep,recipe}:o)},[id]);else{const object={...makeObject('带孔圆角板'+sequence++,result),recipe};commit({...project,objects:[...project.objects,object]},[object.id]);}},$('parametric-part-error'));if(success)$('parametric-part-dialog').close();};
let editingFeatureGraph=null;
function refreshFeatureGraphFields(){
 const form=$('feature-graph-form');
 for(const [check,id]of [['bossEnabled','feature-graph-boss-fields'],['holeEnabled','feature-graph-hole-fields'],['filletEnabled','feature-graph-fillet-fields']]){const fields=$(id),enabled=form.elements.namedItem(check).checked;fields.hidden=!enabled;for(const input of fields.querySelectorAll('input,select'))input.disabled=!enabled;}
 const boss=form.elements.namedItem('bossEnabled').checked,hole=form.elements.namedItem('holeEnabled').checked,concentric=form.elements.namedItem('concentricHole');
 $('feature-graph-concentric-row').hidden=!(boss&&hole);concentric.disabled=!(boss&&hole);
 if(concentric.disabled)concentric.checked=false;
 const follow=concentric.checked;
 $('feature-graph-hole-offset-fields').hidden=follow;
 for(const input of $('feature-graph-hole-offset-fields').querySelectorAll('input'))input.disabled=follow||!hole;
 $('feature-graph-concentric-info').hidden=!follow;
 const linked=form.elements.namedItem('wallLinked');
 $('feature-graph-wall-row').hidden=!follow;linked.disabled=!follow;
 if(!follow)linked.checked=false;
 $('feature-graph-diameter-row').hidden=linked.checked;
 form.elements.namedItem('diameter').disabled=!hole||linked.checked;
 $('feature-graph-wall-fields').hidden=!linked.checked;
 form.elements.namedItem('wallThickness').disabled=!linked.checked;
}
function openFeatureGraph(object=null){if(busy||!initialized)return;let values;try{values=object?.featureGraph?featureGraphParameters(object.featureGraph):{x:0,y:0,length:40,width:25,height:12,bossEnabled:false,bossDiameter:8,bossOffsetX:-10,bossOffsetY:0,bossHeight:4,holeEnabled:true,concentricHole:false,wallLinked:false,wallThickness:2,diameter:6,offsetX:0,offsetY:0,filletEnabled:true,radius:1,corner:'lower_left'};}catch(error){message(error.message,true);return;}editingFeatureGraph=object?.featureGraph?object.id:null;const form=$('feature-graph-form');for(const [key,value]of Object.entries(values)){const field=form.elements.namedItem(key);if(field.type==='checkbox')field.checked=value;else field.value=value;}setModelingText($('feature-graph-title'),editingFeatureGraph?'编辑草图驱动零件':'创建草图驱动零件');setModelingText($('feature-graph-error'),'');refreshFeatureGraphFields();$('feature-graph-dialog').showModal();refresh();}
$('new-feature-graph').onclick=()=>openFeatureGraph();
$('edit-feature-graph').onclick=()=>openFeatureGraph(active());
for(const name of ['bossEnabled','holeEnabled','concentricHole','wallLinked','filletEnabled'])$('feature-graph-form').elements.namedItem(name).onchange=refreshFeatureGraphFields;
$('feature-graph-cancel').onclick=()=>$('feature-graph-dialog').close();
$('feature-graph-dialog').addEventListener('close',()=>{editingFeatureGraph=null;refresh();});
$('feature-graph-form').onsubmit=async e=>{e.preventDefault();const form=e.target,number=name=>Number(form.elements.namedItem(name).value);const values={x:number('x'),y:number('y'),length:number('length'),width:number('width'),height:number('height'),bossEnabled:form.elements.namedItem('bossEnabled').checked,bossDiameter:number('bossDiameter'),bossOffsetX:number('bossOffsetX'),bossOffsetY:number('bossOffsetY'),bossHeight:number('bossHeight'),holeEnabled:form.elements.namedItem('holeEnabled').checked,concentricHole:form.elements.namedItem('concentricHole').checked,wallLinked:form.elements.namedItem('wallLinked').checked,wallThickness:number('wallThickness'),diameter:number('diameter'),offsetX:number('offsetX'),offsetY:number('offsetY'),filletEnabled:form.elements.namedItem('filletEnabled').checked,radius:number('radius'),corner:form.elements.namedItem('corner').value};const id=editingFeatureGraph;let graph;try{graph=featureGraphFromParameters(values,id?project.objects.find(o=>o.id===id)?.featureGraph:null);}catch(error){setModelingText($('feature-graph-error'),error.message);return;}
 const success=await operation(id?'更新草图驱动零件':'创建草图驱动零件',async()=>{const original=id?project.objects.find(o=>o.id===id):null;if(id&&!original?.featureGraph)throw Error('原特征依赖不存在');let result=await buildFeatureGraph(graph,geometry);for(const transform of original?.postTransforms||[])result=await geometry('transform',transform,[result]);if(original)commit({...project,objects:project.objects.map(o=>o.id===id?{...o,shape:result.shape,brep:result.brep,featureGraph:graph}:o)},[id]);else{const object={...makeObject('草图驱动零件'+sequence++,result),featureGraph:graph};commit({...project,objects:[...project.objects,object]},[object.id]);}},$('feature-graph-error'));if(success)$('feature-graph-dialog').close();};
$('undo').onclick=()=>restore(historyIndex-1);$('redo').onclick=()=>restore(historyIndex+1);
$('delete-model').onclick=()=>{const ids=solidIds();if(busy||!ids.length||ids.length!==selections.length)return;mouse.cancel(true);commit({...project,objects:project.objects.filter(o=>!ids.includes(o.id))});message('已删除选中实体');};
$('apply-object-properties').onclick=()=>{if(!canEdit()||busy)return;const name=$('object-name').value.trim(),color=$('object-color').value,transparency=Number($('object-opacity').value);if(!name||!Number.isFinite(transparency)||transparency<0||transparency>.9){message('名称或透明度无效',true);return;}const id=activeId;commit({...project,objects:project.objects.map(o=>o.id===id?{...o,name,color,opacity:1-transparency,visible:$('object-visible').checked}:o)},[id]);message('对象属性已更新');};
for(const id of ['object-color','object-visible'])$(id).onchange=()=>$('apply-object-properties').click();
for(const b of document.querySelectorAll('[data-transform]'))b.onclick=()=>openTransform(b.dataset.transform);
let transformKind;
function openTransform(kind){if(busy||!solidIds().length)return;mouse.cancel(true);transformKind=kind;setModelingText($('transform-title'),{move:'位移',rotate:'旋转',scale:'缩放'}[kind]);setModelingText($('transform-targets'),`已选择 ${solidIds().length} 个实体`);$('move-inputs').hidden=kind!=='move';$('base-inputs').hidden=kind==='move';$('rotation-input').hidden=kind!=='rotate';$('scale-input').hidden=kind!=='scale';$('transform-form').reset();setModelingText($('transform-error'),'');$('transform-dialog').showModal();refresh();}
$('transform-cancel').onclick=()=>$('transform-dialog').close();$('transform-dialog').addEventListener('close',refresh);
$('transform-form').onsubmit=async e=>{e.preventDefault();const f=new FormData(e.target),v=k=>Number(f.get(k)),p={};if(transformKind==='move')p.translation=['x','y','z'].map(k=>v('delta-'+k));else{p.pivot=['x','y','z'].map(k=>v('base-'+k));if(transformKind==='rotate')p.rotation=[0,0,v('rotation-angle')];else p.scale=Array(3).fill(v('scale-factor'));}if(await operation('几何变换',()=>transformObjects(transformKind,p),$('transform-error')))$('transform-dialog').close();};
function selectedObject(){const ids=[...new Set(selections.map(s=>s.objectId))];if(ids.length!==1)throw Error('请选择同一个实体');return project.objects.find(o=>o.id===ids[0]);}
for(const b of document.querySelectorAll('[data-feature]'))b.onclick=()=>openAdvanced(b.dataset.feature);
for(const button of document.querySelectorAll('[data-boolean-operation]'))button.onclick=()=>{
 const operationName=button.dataset.booleanOperation,label=operationName==='union'?'布尔并':button.id==='boolean-subtract'?'布尔减':'布尔差';
 operation(label,async()=>{
  const operands=selectedBooleanObjects();if(!operands)throw Error('请按顺序选择 2～20 个封闭实体');
  const params={operation:operationName},r=await geometry('boolean',params,operands);if(r.empty)throw Error('运算结果为空，原场景已保留');
  const object=makeObject(label+sequence++,r,featureModel('boolean',params,operands),{action:'boolean',params,inputs:operands.map(o=>o.brep)}),remove=new Set(operands.map(o=>o.id));
  commit({...project,objects:project.objects.filter(o=>!remove.has(o.id)).concat(object)},[object.id]);
 });
};
let advancedKind;
function openAdvanced(kind){if(busy)return;mouse.cancel(true);advancedKind=kind;setModelingText($('advanced-title'),{boolean:'布尔运算',sweep:'扫掠',fillet:'圆角',chamfer:'倒角'}[kind]);setModelingText($('advanced-targets'),`当前选择 ${selections.length} 项`);for(const [id,enabled]of [['boolean-fields',kind==='boolean'],['sweep-fields',kind==='sweep'],['bevel-fields',['fillet','chamfer'].includes(kind)]]){$(id).hidden=!enabled;$(id).disabled=!enabled;}setModelingText($('advanced-error'),'');setModelingText($('bevel-size-label'),kind==='fillet'?'圆角半径':'倒角距离');$('bevel-edges').value=selections.filter(s=>s.type==='edge').map(s=>s.id).join(', ');$('advanced-dialog').showModal();refresh();}
$('advanced-cancel').onclick=()=>$('advanced-dialog').close();$('advanced-dialog').addEventListener('close',refresh);
$('sweep-path').value='0, 0, 0\n0, 0, 15\n10, 0, 30\n25, 0, 40';setModelingText($('sweep-fields').querySelector('.scope'),'每行一个 XYZ 点，逗号或空格分隔，支持 4～32 点。圆形或矩形截面沿插值曲线扫掠，两端封闭；截面过大或路径自交可能失败。');
function refreshSweepSection(){const rectangle=$('sweep-profile').value==='rectangle';$('sweep-radius-row').hidden=rectangle;$('sweep-radius').disabled=rectangle;$('sweep-rectangle-rows').hidden=!rectangle;for(const id of ['sweep-width','sweep-height'])$(id).disabled=!rectangle;}
$('sweep-profile').onchange=refreshSweepSection;refreshSweepSection();
$('advanced-form').onsubmit=async e=>{e.preventDefault();const kind=advancedKind;
 const success=await operation($('advanced-title').textContent,async()=>{let action,params,operands,keep=false;
  if(kind==='boolean'){const ids=solidIds();if(ids.length<2||ids.length!==selections.length)throw Error('请按顺序选择至少两个实体');action='boolean';params={operation:{fuse:'union',cut:'difference',common:'intersection',xor:'xor'}[$('boolean-operation').value]};operands=ids.map(id=>project.objects.find(o=>o.id===id));keep=$('keep-operands').checked;}
  else if(kind==='sweep'){action='create';params={kind:'sweep',profileKind:$('sweep-profile').value,radius:Number($('sweep-radius').value),width:Number($('sweep-width').value),height:Number($('sweep-height').value),path:parsePoints($('sweep-path').value,3)};validateModel(featureModel(kind,params));operands=[];}
  else{action=kind;const object=selectedObject(),chosen=$('bevel-edges').value.trim();params={radius:Number($('bevel-size').value),edges:chosen?chosen.split(/[,，\s]+/).map(v=>Number(v)-1):selections.filter(s=>s.type==='edge').map(s=>s.id-1)};if(!params.edges.length)throw Error('请选择或填写需要修改的边编号');if(params.edges.some(i=>!Number.isInteger(i)||i<0||i>=object.shape.edgeCount))throw Error('边编号无效');operands=[object];}
  const r=await geometry(action,params,operands);if(r.empty)throw Error('运算结果为空，原场景已保留');const definition={action,params,inputs:operands.map(o=>o.brep)},object=makeObject((MODEL_NAMES[kind]||'布尔体')+sequence++,r,featureModel(kind,params,operands),definition),remove=new Set(operands.map(o=>o.id));commit({...project,objects:project.objects.filter(o=>keep||!remove.has(o.id)).concat(object)},[object.id]);
 },$('advanced-error'));if(success)$('advanced-dialog').close();
};
$('boolean-operation').add(modelingOption('异或','xor'));
const numberField=(key,label,value,min=null)=>`<label>${label}<input name="${key}" type="number" value="${value}" step="any" ${min!==null?'min="'+min+'"':''} required></label>`;
const vectorFields=(key,label,value=[0,0,0])=>`<fieldset><legend>${label}</legend>${value.map((v,i)=>numberField(key+'-'+i,['X','Y','Z'][i],v)).join('')}</fieldset>`;
for(const b of document.querySelectorAll('[data-construction]'))b.onclick=()=>{if(!b.dataset.unavailable)openConstruction(b.dataset.construction);};
function selectedProfile(){return selections.length>0&&(selections.length===1&&selections[0].type==='face'||selections.every(s=>s.type==='solid'&&(project.objects.find(o=>o.id===s.objectId)?.shape.dimension===1||selections.length===1&&project.objects.find(o=>o.id===s.objectId)?.shape.dimension===2&&project.objects.find(o=>o.id===s.objectId)?.shape.faces===1)));}
function openConstruction(kind){if(busy)return;if(['extrude','revolve'].includes(kind)&&selections.length&&!selectedProfile()&&!selections.every(s=>s.type==='solid'&&project.objects.find(o=>o.id===s.objectId)?.shape.dimension===3)){message('请选择完整闭合曲线或一个面',true);return;}if(['extrude','revolve'].includes(kind)&&selectedProfile()){mouse.cancel(true);featureUI.open('solid-'+kind);return;}mouse.cancel(true);if(kind==='copy'){operation('复制',async()=>{const additions=[];for(const id of solidIds()){const base=project.objects.find(o=>o.id===id),r=await geometry('copy',{},[base]);additions.push({...base,id:crypto.randomUUID(),name:base.name+' 副本',brep:r.brep,shape:r.shape});}commit({...project,objects:[...project.objects,...additions]},additions.map(o=>o.id));});return;}
 if(kind==='profile'){constructionCommand='profile';profilePoints=profiles.XY;openProfile();return;}constructionCommand=kind;setModelingText($('construction-title'),{cone:'圆锥',torus:'圆环',extrude:'拉伸',revolve:'旋转体',rotate3d:'轴旋转',shell:'抽壳',offset:'偏移'}[kind]||kind);setModelingText($('construction-targets'),['shell','offset','rotate3d'].includes(kind)?`当前选择 ${selections.length} 项`:'设置参数后创建独立对象');$('construction-keep-row').hidden=true;let fields='';
 if(['cone','torus','extrude','revolve'].includes(kind))fields=vectorFields('origin','位置（mm）');
 if(kind==='cone')fields+=numberField('radius','底面半径',15,.1)+numberField('topRadius','顶面半径',0,0)+numberField('height','高度',30,.1);
 if(kind==='torus')fields+=numberField('radius','主半径',20,.1)+numberField('tubeRadius','管半径',5,.1);
 if(['extrude','revolve'].includes(kind)){profilePoints=profiles[kind==='revolve'?'XZ':'XY'];fields+='<button id="edit-profile" type="button">编辑封闭轮廓</button>';fields+=kind==='extrude'?numberField('height','高度',20,.1):numberField('angle','绕 Z 轴角度（°）',360,.1);}
 if(kind==='shell')fields+=numberField('thickness','壁厚（mm）',2,.1)+'<p class="scope">选中的面将被移除；未选择面时生成封闭薄壁体。</p>';
 if(kind==='offset')fields+=numberField('distance','偏置距离（mm）',1);
 if(kind==='rotate3d')fields+=vectorFields('rotation','绕世界轴旋转（°）')+vectorFields('pivot','变换基点（mm）');
 setModelingHTML($('construction-inputs'),fields);setModelingText($('construction-error'),'');setModelingText($('construction-result'),'');$('construction-dialog').showModal();if($('edit-profile'))$('edit-profile').onclick=openProfile;refresh();
}
$('construction-cancel').onclick=()=>$('construction-dialog').close();$('construction-dialog').addEventListener('close',refresh);
function readFields(form){const d=new FormData(form),p={};for(const [key,value]of d)if(!/-[012]$/.test(key))p[key]=Number(value);for(const key of ['origin','rotation','pivot'])if(d.has(key+'-0'))p[key]=[0,1,2].map(i=>Number(d.get(key+'-'+i)));return p;}
$('construction-form').onsubmit=async e=>{e.preventDefault();const kind=constructionCommand;const success=await operation($('construction-title').textContent,async()=>{const p=readFields(e.target);let action='create',operands=[];if(['shell','offset','rotate3d'].includes(kind)){operands=[selectedObject()];action=kind==='rotate3d'?'transform':kind;}else p.kind=kind;if(['extrude','revolve'].includes(kind))p.profile=profilePoints;if(kind==='shell'){p.distance=-p.thickness;p.faces=selections.filter(s=>s.type==='face').map(s=>s.id-1);}const r=await geometry(action,p,operands);const object=makeObject((MODEL_NAMES[kind]||'轴旋转体')+sequence++,r,{...DEFAULT_MODEL,kind:MODEL_NAMES[kind]?kind:'brep'},{action,params:p,inputs:operands.map(o=>o.brep)}),remove=new Set(operands.map(o=>o.id));commit({...project,objects:project.objects.filter(o=>!remove.has(o.id)).concat(object)},[object.id]);},$('construction-error'));if(success)$('construction-dialog').close();};
const definitionField=(def,key)=>def.action==='create'&&def.params.kind==='sweep'&&key==='profileKind'?{label:'截面',options:[['circle','圆形'],['rectangle','矩形']]}:FEATURE_COMMANDS.find(c=>c.action===def.action&&c.kind===def.params.kind)?.fields.find(f=>f.key===key);
let parameterSignature='';
function refreshConstructionProperties(){const object=active(),part=canEdit()&&!!object?.recipe,graph=canEdit()&&!!object?.featureGraph,enabled=canEdit()&&object?.definition&&!isPrimitive(object.model);$('construction-properties').hidden=!enabled;$('edit-construction').hidden=true;$('feature-properties').hidden=true;$('array-properties').hidden=true;$('edit-feature').hidden=true;$('adopt-array').hidden=true;$('edit-parametric-part').hidden=!part;$('edit-parametric-part').disabled=busy||!initialized;$('edit-feature-graph').hidden=!graph;$('edit-feature-graph').disabled=busy||!initialized;if(part||graph)$('parameters-empty').hidden=true;if(!enabled)return;
 $('parameters-empty').hidden=true;const signature=JSON.stringify([object.id,object.definition,object.postTransforms]);if(signature===parameterSignature)return;parameterSignature=signature;setModelingText($('parameter-type'),MODEL_NAMES[object.model?.kind]||'实体');
 setModelingHTML($('parameter-inputs'),Object.entries(object.definition.params).filter(([key])=>key!=='kind'&&!definitionField(object.definition,key)?.hidden).map(([key,value])=>typeof value==='boolean'?`<label class="check"><input type="checkbox" data-parameter="${key}" ${value?'checked':''}>${html(definitionField(object.definition,key)?.label||{closed:'闭合',rightHanded:'右旋'}[key]||key)}</label>`:Array.isArray(value)?`<label>${html(definitionField(object.definition,key)?.label||{origin:'位置 XYZ',profile:'轮廓坐标',path:'路径 XYZ',edges:'边索引（从 1 开始）',faces:'面索引（从 1 开始）',rotation:'旋转 XYZ（°）',pivot:'变换基点'}[key]||key)}<textarea data-parameter="${key}">${html(JSON.stringify(['edges','faces'].includes(key)||definitionField(object.definition,key)?.type==='indices'?value.map(i=>i+1):value))}</textarea></label>`:typeof value==='string'?`<label>${html(definitionField(object.definition,key)?.label||key)}<select name="${key}">${(definitionField(object.definition,key)?.options||[['union','并集'],['difference','差集'],['intersection','交集'],['xor','异或']]).map(([v,label])=>`<option value="${v}" ${value===v?'selected':''}>${html(label)}</option>`).join('')}</select></label>`:numberField(key,definitionField(object.definition,key)?.label||{length:'长度',width:'宽度',height:'高度',radius:'半径',topRadius:'顶面半径',tubeRadius:'管半径',angle:'旋转角度（°）',distance:'偏置距离',thickness:'壁厚'}[key]||key,value+(definitionField(object.definition,key)?.type==='index'?1:0))).join(''));
}
$('construction-properties').onsubmit=async e=>{e.preventDefault();const base=active();if(!base?.definition)return;await operation('更新几何',async()=>{const def=structuredClone(base.definition),p=def.params;for(const input of e.target.querySelectorAll('input[name]'))p[input.name]=Number(input.value)-(definitionField(def,input.name)?.type==='index'?1:0);for(const input of e.target.querySelectorAll('input[type="checkbox"][data-parameter]'))p[input.dataset.parameter]=input.checked;for(const select of e.target.querySelectorAll('select[name]'))p[select.name]=select.value;for(const textarea of e.target.querySelectorAll('textarea[data-parameter]')){const key=textarea.dataset.parameter;p[key]=JSON.parse(textarea.value);if(['edges','faces'].includes(key)||definitionField(def,key)?.type==='indices')p[key]=p[key].map(i=>i-1);}if(def.action==='shell'&&'thickness'in p)p.distance=-p.thickness;validateDefinition(def);
 let result=await geometry(def.action,p,def.inputs.map(brep=>({brep})));if(result.empty)throw Error('结果为空，原对象已保留');for(const transform of base.postTransforms||[])result=await geometry('transform',transform,[result]);commit({...project,objects:project.objects.map(o=>o.id===base.id?{...o,shape:result.shape,brep:result.brep,model:featureModel(def.action==='profile_solid'?(result.shape.dimension===3?'brep':'surface'):base.model.kind,p,[],base.model),definition:def}:o)},[base.id]);},$('parameter-error'));};
function parsePoints(text,dimension=2){const points=text.trim().split(/\n|;/).filter(s=>s.trim()).map(s=>s.trim().split(/[,，\s]+/).map(Number));if(points.some(p=>p.length!==dimension||p.some(v=>!Number.isFinite(v)||Math.abs(v)>10000)))throw Error(`每个顶点需要 ${dimension} 个有效坐标`);return points;}
function openProfile(){const plane=constructionCommand==='revolve'?'XZ':'XY';setModelingText($('profile-plane'),plane+' 平面');$('profile-points').value=profilePoints.map(p=>p.join(', ')).join('\n');setModelingText($('profile-error'),'');drawProfile();$('sketch-dialog').showModal();refresh();}
let sketchTransform;
function drawProfile(){let points;try{points=parsePoints($('profile-points').value);}catch{return;}const scale=260/(Math.max(30,...points.flat().map(Math.abs))*1.35+10);sketchTransform={scale,ox:55,oy:270};let content='<defs><pattern id="smallGrid" width="20" height="20" patternUnits="userSpaceOnUse"><path d="M20 0H0V20" fill="none" stroke="#dfe6f0" stroke-width=".6"/></pattern></defs><rect width="400" height="320" fill="url(#smallGrid)"/><path d="M0 270H400M55 0V320" stroke="#aab9cc" stroke-width="1"/>';
 if(points.length){content+=`<polygon points="${points.map(([x,y])=>`${55+x*scale},${270-y*scale}`).join(' ')}" fill="#3f83e72b" stroke="#3f83e7" stroke-width="2"/>`;points.forEach(([x,y],i)=>content+=`<circle cx="${55+x*scale}" cy="${270-y*scale}" r="3.5" fill="#2563eb"/><text x="${62+x*scale}" y="${263-y*scale}" fill="#60799c" font-size="10">${i+1}</text>`);}setModelingHTML($('profile-preview'),content);}
$('profile-points').oninput=drawProfile;$('profile-preview').onclick=e=>{const r=e.currentTarget.getBoundingClientRect(),{scale,ox,oy}=sketchTransform;let points=[];try{points=parsePoints($('profile-points').value);}catch{}points.push([Math.round(((e.clientX-r.left)*400/r.width-ox)/scale),Math.round((oy-(e.clientY-r.top)*320/r.height)/scale)]);$('profile-points').value=points.map(p=>p.join(', ')).join('\n');drawProfile();};
$('profile-rect').onclick=()=>{$('profile-points').value=constructionCommand==='revolve'?'10, 0\n20, 0\n20, 20\n10, 20':'0, 0\n20, 0\n20, 12\n0, 12';drawProfile();};$('profile-l').onclick=()=>{$('profile-points').value='0, 0\n30, 0\n30, 10\n10, 10\n10, 30\n0, 30';drawProfile();};$('profile-clear').onclick=()=>{$('profile-points').value='';drawProfile();};
$('profile-apply').onclick=()=>{try{const points=parsePoints($('profile-points').value);if(points.length<3||points.length>64)throw Error('轮廓需要 3～64 个顶点');profilePoints=points;if(constructionCommand==='revolve')profiles.XZ=points;else profiles.XY=points;$('sketch-dialog').close();}catch(error){setModelingText($('profile-error'),error.message);}};$('sketch-dialog').addEventListener('close',refresh);
async function confirmAction(title,message){setModelingText($('confirm-title'),title);setModelingText($('confirm-message'),message);$('confirm-dialog').showModal();refresh();return new Promise(resolve=>$('confirm-dialog').onclose=()=>{refresh();resolve($('confirm-dialog').returnValue==='ok');});}
$('new-project').onclick=async()=>{$('viewport-context').hidden=true;if(project.objects.length&&!await confirmAction('新建项目','新建会替换浏览器中保存的当前项目。请先保存 Web 工程；继续后仍可撤销。'))return;mouse.cancel(true);commit({name:'未命名模型',objects:[]});fitView('iso');message('已新建空场景');};
$('demo-project').onclick=()=>{$('viewport-context').hidden=true;return operation('创建示例',async()=>{const m={...DEFAULT_MODEL,length:50,width:36,height:20,hole:true,diameter:18},r=await primitiveResult(m),object=makeObject('带孔基座',r,m);commit({name:'带孔基座示例',objects:[object]},[object.id]);fitView('iso');});};
$('save').onclick=()=>{const document={format:'cax-smlib-project',version:1,units:'mm',name:project.name,objects:project.objects.map(({shape,...object})=>object)};const url=URL.createObjectURL(new Blob([JSON.stringify(document)],{type:'application/json'})),link=window.document.createElement('a');link.href=url;link.download=project.name.replace(/[\\/:*?"<>|]/g,'_')+'.smlib.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);message('Web 工程已保存到本机');};
$('import-step').onclick=()=>$('step-file').click();
$('step-file').onchange=async e=>{const file=e.target.files[0];e.target.value='';if(!file)return;if(file.size>100*1024*1024){message('STEP 文件最大为100 MB',true);return;}if(!/\.(step|stp)$/i.test(file.name)){message('请选择 STEP 或 STP 文件',true);return;}await operation('导入 STEP',async()=>{setModelingText($('source-retention'),'正在上传原始文件…');const receipt=await retainOriginalStep(file);setModelingText($('source-retention'),receipt.retained?`原始文件已留存，编号：${receipt.archiveId}`:'原始文件未留存；浏览器仍继续导入。请保管本机原文件。');checkCancellation();const text=await file.text();checkCancellation();const start=performance.now(),r=await kernel.run({action:'step_import',text});checkCancellation();lastOperation={action:'step_import',elapsedMs:performance.now()-start,computeMs:r.computeMs,heapBytes:r.heapBytes};const object=makeObject(file.name.replace(/\.(step|stp)$/i,''),r,{...DEFAULT_MODEL,kind:'brep'});commit({...project,objects:[...project.objects,object]},[object.id]);fitView('iso');});};
$('export-step').onclick=async()=>{const object=project.objects.find(o=>o.id===solidIds()[0]);if(!object||!stepAvailable||selections.length!==1||selections[0].type!=='solid'||object.shape.dimension!==3||!object.shape.manifold)return;await operation('导出 STEP',async()=>{const params=object.recipe?.kind==='rectangular-plate'||object.featureGraph?{representation:'nurbs'}:{};const r=await geometry('step_export',params,[object]);if(typeof r.text!=='string'||!r.text.startsWith('ISO-10303-21;'))throw Error('STEP 文件生成失败');const url=URL.createObjectURL(new Blob([r.text],{type:'application/step'})),link=document.createElement('a');link.href=url;link.download=object.name.replace(/[\\/:*?"<>|]/g,'_')+'.step';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});};
$('open').onclick=()=>$('model-file').click();
function validateDefinition(definition){
 if(!definition||!['create','boolean','fillet','chamfer','shell','offset','transform','curve_create','curve_edit','surface_create','intersect','repair','project_trim','advanced_boolean','profile_solid'].includes(definition.action)||!definition.params||!Array.isArray(definition.inputs)||definition.inputs.length>64||definition.inputs.some(v=>typeof v!=='string'))throw Error('构造参数格式无效');
 if(['curve_create','curve_edit','surface_create','intersect','repair','project_trim','advanced_boolean','profile_solid'].includes(definition.action)){validateFeatureDefinition(definition);if(definition.action==='profile_solid'&&(definition.inputs.length<1||definition.inputs.length>20||definition.params.source==='face'&&definition.inputs.length!==1))throw Error('轮廓成体需要1～20个曲线对象，面模式需要一个对象');return definition;}
 const allowed=new Set(['kind','operation','origin','length','width','height','radius','topRadius','tubeRadius','angle','profile','profileKind','path','rotation','translation','scale','pivot','edges','faces','distance','thickness','chord']);
 const numeric=(v,depth=0)=>typeof v==='number'?Number.isFinite(v)&&Math.abs(v)<=100000:Array.isArray(v)&&depth<2&&v.length<=256&&v.every(x=>numeric(x,depth+1));
 for(const [key,value]of Object.entries(definition.params)){if(!allowed.has(key))throw Error('不支持的构造参数');if(key==='kind'){if(!['box','cylinder','sphere','cone','torus','extrude','revolve','sweep'].includes(value))throw Error('构造类型无效');}else if(key==='profileKind'){if(definition.action!=='create'||definition.params.kind!=='sweep'||!['circle','rectangle'].includes(value))throw Error('扫掠构造参数无效');}else if(key==='operation'){if(!['union','difference','intersection','xor'].includes(value))throw Error('布尔运算类型无效');}else if(!numeric(value))throw Error('构造参数需要有限数值');}
 if(definition.action==='create'&&definition.params.kind==='sweep')validateModel(featureModel('sweep',definition.params));
 return definition;
}
function validateTransforms(transforms){if(!Array.isArray(transforms)||transforms.length>100)throw Error('变换记录无效');for(const transform of transforms){if(!transform||typeof transform!=='object')throw Error('变换记录无效');for(const [key,value]of Object.entries(transform))if(!['translation','rotation','scale','pivot'].includes(key)||!Array.isArray(value)||value.length!==3||value.some(v=>!Number.isFinite(v)||Math.abs(v)>100000))throw Error('变换参数无效');}return transforms;}
async function openProjectDocument(saved){
 if(saved.format!=='cax-smlib-project'||saved.version!==1||!Array.isArray(saved.objects)||saved.objects.length>100||saved.objects.some(o=>typeof o.brep!=='string'||typeof o.name!=='string'))throw Error('不支持的 Web 工程格式');
 for(const object of saved.objects){if(object.featureGraph&&(object.recipe||object.definition||object.model))throw Error('特征依赖不能与旧构造记录混用');if(object.definition)validateDefinition(object.definition);if(object.recipe)validateParametricPart(object.recipe);if(object.featureGraph)validateFeatureGraph(object.featureGraph);validateTransforms(object.postTransforms||[]);if(object.model)validateModel(object.model);}
 if(project.objects.length&&!await confirmAction('打开 Web 工程','打开工程会替换当前场景；继续后可撤销恢复。'))return false;
 return operation('打开 Web 工程',async()=>{
  const imported=[],ids=new Set();
  for(const source of saved.objects){
   const graph=source.featureGraph?validateFeatureGraph(source.featureGraph):null,transforms=validateTransforms(source.postTransforms||[]);
   let result=graph?await buildFeatureGraph(graph,geometry):await geometry('describe',{},[source]);
   if(graph)for(const transform of transforms)result=await geometry('transform',transform,[result]);
   const storedId=source.id;
   if(typeof storedId==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(storedId)&&ids.has(storedId))throw Error('工程对象编号重复');
   const object={...makeObject(source.name.slice(0,80),result),color:/^#[0-9a-f]{6}$/i.test(source.color)?source.color:'#80baff',visible:source.visible!==false,opacity:Number.isFinite(source.opacity)?Math.max(.1,Math.min(1,source.opacity)):1,...(source.model?{model:validateModel(source.model)}:{}),...(source.definition?{definition:validateDefinition(source.definition)}:{}),...(source.recipe?{recipe:validateParametricPart(source.recipe)}:{}),...(graph?{featureGraph:graph}:{}),postTransforms:transforms};
   if(typeof storedId==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(storedId))object.id=storedId;
   ids.add(object.id);imported.push(object);
  }
  commit({name:String(saved.name||'导入项目').slice(0,80),objects:imported},imported.slice(-1).map(o=>o.id));fitView('iso');
 });
}
$('model-file').onchange=async e=>{const file=e.target.files[0];e.target.value='';if(!file)return;try{if(file.size>25*1024*1024)throw Error('项目文件最大为 25 MB');await openProjectDocument(JSON.parse(await file.text()));}catch(error){message('打开失败：'+error.message,true);}};
$('document-state').ondblclick=()=>{setModelingText($('name-dialog-title'),'项目名称');$('name-input').value=project.name;$('name-dialog').showModal();refresh();};$('name-dialog').onclose=()=>{if($('name-dialog').returnValue==='ok'&&$('name-input').value.trim())commit({...project,name:$('name-input').value.trim()},solidIds());refresh();};
$('cancel-mouse').addEventListener('click',()=>{if(busy&&initialized)cancelOperation();else if(mouse.tool()==='navigate')selectItems([]);});
window.addEventListener('keydown',e=>{if(e.target.closest('input,textarea,select,[contenteditable]'))return;if(document.querySelector('dialog[open]'))return;const ctrl=e.ctrlKey||e.metaKey,key=e.key.toLowerCase();if(ctrl&&['z','y','s','o'].includes(key)){e.preventDefault();if(busy)return;if(key==='z')restore(historyIndex+(e.shiftKey?1:-1));if(key==='y')restore(historyIndex+1);if(key==='s')$('save').click();if(key==='o')$('open').click();}else if(e.key==='Delete'&&!busy)$('delete-model').click();else if(e.key==='Escape'){e.preventDefault();if(busy)cancelOperation();else{const wasNavigating=mouse.tool()==='navigate';mouse.cancel(true);boxSelection=false;if(wasNavigating)selectItems([]);refresh();}}});
function selectedCurves(){return selections.length===2&&selections.every(s=>{const object=project.objects.find(o=>o.id===s.objectId);return object&&(s.type==='solid'&&object.shape.dimension===1||s.type==='edge'&&Number.isInteger(s.id)&&s.id>=1&&s.id<=object.shape.edgeCount);});}
function curveIntersectionParams(){if(!selectedCurves())throw Error('请选择两条完整曲线或两条边');return Object.fromEntries(selections.flatMap((s,i)=>[[i?'edgeB':'edge',s.type==='edge'?s.id-1:0],[i?'allEdgesB':'allEdgesA',s.type==='solid']]));}
function featureOperands(cmd){if(cmd.id==='intersect-curves')return selections.map(s=>project.objects.find(o=>o.id===s.objectId));const ids=cmd.action==='query'||cmd.subSelection?[...new Set(selections.map(s=>s.objectId))]:solidIds();return ids.map(id=>project.objects.find(o=>o.id===id));}
featureUI=installFeatureUI({
 canExecute:cmd=>initialized&&!busy&&(cmd.id!=='intersect-curves'||selectedCurves())&&(cmd.action!=='profile_solid'||selections.every(s=>s.type==='solid')||(selections.length===1&&selections[0].type==='face'))&&(!cmd.min||((cmd.action==='query'||cmd.subSelection||solidIds().length===selections.length)&&featureOperands(cmd).length>=cmd.min&&featureOperands(cmd).length<=cmd.max)),
 selectionDefaults:cmd=>{const ids=featureOperands(cmd).map(o=>o.id),selected=(i,type)=>selections.find(s=>s.objectId===ids[i]&&s.type===type)?.id;const source=cmd.action==='project_trim'&&ids.length>1?1:0;return {...(cmd.action==='profile_solid'&&ids.length===1&&(selected(0,'face')||featureOperands(cmd)[0]?.shape.dimension===2&&featureOperands(cmd)[0]?.shape.faces===1)?{source:'face'}:{}),edge:selected(source,'edge')??1,face:selected(0,'face')??1,edgeB:selected(1,'edge')??1,faceB:selected(1,'face')??1,...(cmd.kind==='trees'?{tokens:ids.flatMap((_,i)=>i===0?[0]:[i,-1])}:{}),...(cmd.fields.some(f=>f.key==='edges')?{edges:ids.map((_,i)=>selected(i,'edge')??1)}:{}),...(cmd.fields.some(f=>f.key==='singleEdge')?{singleEdge:!!selected(source,'edge')}:{})};},
 execute:async(cmd,params,error)=>{let report;const ok=await operation(cmd.label,async()=>{if(cmd.id==='intersect-curves')params={kind:cmd.kind,...curveIntersectionParams()};const operands=cmd.min?featureOperands(cmd):[],r=await geometry(cmd.action,params,operands);if(cmd.action==='query'){report=r.query;return;}report=r.report;if(r.empty){report={...report,empty:true};return;}const model={...DEFAULT_MODEL,kind:({0:'points',1:'profile',2:'surface',3:'brep'})[r.shape.dimension]||'brep'},definition={action:cmd.action,params,inputs:operands.map(o=>o.brep)},object=makeObject(cmd.label+sequence++,r,model,definition);commit({...project,objects:[...project.objects,object]},[object.id]);},error);return ok?{report}:false;}
});
for(const id of ['distance','slice']){const button=document.querySelector(`[data-construction="${id}"]`);delete button.dataset.unavailable;button.onclick=()=>featureUI.open(id==='distance'?'query-distance':'project-cut');}

$('feature-command-dialog').addEventListener('close',refresh);$('geometry-report-dialog').addEventListener('close',refresh);

// The command line supplies every target and parameter in text. Mouse selection
// is optional; it is never an implicit input to a command line modeling action.
function commandObject(reference){
 const value=String(reference??'');let matches=[];
 if(Number.isInteger(reference))matches=project.objects[reference-1]?[project.objects[reference-1]]:[];
 else matches=project.objects.filter(o=>o.id===value||o.name===value);
 if(matches.length!==1)throw Error(`对象引用 ${value} 不唯一或不存在；使用项目树中的序号或 UUID`);
 return matches[0];
}
function commandTargets(value,required=false){
 if(value===undefined){if(required)throw Error('命令行需要 targets=对象序号[,对象序号]');return [];}
 const refs=Array.isArray(value)?value:[value];
 if(!refs.length)throw Error('targets 不能为空');
 return refs.map(ref=>{const [objectRef,type='solid',number]=String(ref).split(':'),object=commandObject(/^\d+$/.test(objectRef)?Number(objectRef):objectRef);
  if(!['solid','edge','face'].includes(type))throw Error('选择类型应为 solid、edge 或 face');
  if(type==='solid'&&number!==undefined)throw Error('实体选择不使用子编号');
  const id=Number(number),limit=type==='edge'?object.shape.edgeCount:object.shape.faces;
  if(type!=='solid'&&(!Number.isInteger(id)||id<1||id>limit))throw Error(`${type} 编号超出对象范围`);
  return {objectId:object.id,type,...(type==='solid'?{}:{id})};
 });
}
function commandSelect(value,required=false){
 const items=commandTargets(value,required);selections=items;activeId=items.at(-1)?.objectId??null;
 if(items.length)selectionMode=items[0].type;
 refresh();return items;
}
function commandFields(base,provided,allowed=Object.keys(base)){
 const next=structuredClone(base);for(const [key,value]of Object.entries(provided)){if(!allowed.includes(key))throw Error(`不支持的参数 ${key}`);next[key]=value;}return next;
}
function commandParams(named,excluded=[]){return Object.fromEntries(Object.entries(named).filter(([key])=>!excluded.includes(key)));}
function commandSucceeded(ok){if(!ok)throw Error($('status').textContent||'建模命令失败');}
async function commandGraph(named,reference=null){
 const original=reference?commandObject(reference):null;if(original&&!original.featureGraph)throw Error('对象没有草图特征记录');
 const values=commandFields(original?featureGraphParameters(original.featureGraph):defaultGraphValues(),named);
 const graph=featureGraphFromParameters(values,original?.featureGraph);
 commandSucceeded(await operation(original?'更新草图驱动零件':'创建草图驱动零件',async()=>{let result=await buildFeatureGraph(graph,geometry);
  for(const transform of original?.postTransforms||[])result=await geometry('transform',transform,[result]);
  if(original)commit({...project,objects:project.objects.map(o=>o.id===original.id?{...o,shape:result.shape,brep:result.brep,featureGraph:graph}:o)},[original.id]);
  else{const object={...makeObject('草图驱动零件'+sequence++,result),featureGraph:graph};commit({...project,objects:[...project.objects,object]},[object.id]);}
 }));
}
async function commandPart(named,reference=null){
 const original=reference?commandObject(reference):null;if(original&&!original.recipe)throw Error('对象没有带孔圆角板记录');
 const params=commandFields(original?original.recipe.params:defaultPartValues(),named);
 const recipe=validateParametricPart({kind:'rectangular-plate',version:1,params});
 commandSucceeded(await operation(original?'更新带孔圆角板':'创建带孔圆角板',async()=>{let result=await buildParametricPart(recipe,geometry);
  for(const transform of original?.postTransforms||[])result=await geometry('transform',transform,[result]);
  if(original)commit({...project,objects:project.objects.map(o=>o.id===original.id?{...o,shape:result.shape,brep:result.brep,recipe}:o)},[original.id]);
  else{const object={...makeObject('带孔圆角板'+sequence++,result),recipe};commit({...project,objects:[...project.objects,object]},[object.id]);}
 }));
}
async function commandEdit(reference,named){
 const object=commandObject(reference);commandSelect(object.id,true);
 if(object.featureGraph)return commandGraph(named,object.id);
 if(object.recipe)return commandPart(named,object.id);
 if(isPrimitive(object.model)){const model=commandFields(object.model,named,Object.keys(DEFAULT_MODEL));commandSucceeded(await buildModel(model));return;}
 if(!object.definition)throw Error('该对象没有可编辑构造记录');
 const def=structuredClone(object.definition),params=def.params;
 for(const [key,value]of Object.entries(named)){if(!Object.hasOwn(params,key)||key==='kind')throw Error(`不能修改参数 ${key}`);const field=definitionField(def,key);params[key]=field?.type==='index'?Number(value)-1:field?.type==='indices'?value.map(v=>Number(v)-1):value;}
 if(def.action==='shell'&&'thickness'in params)params.distance=-params.thickness;
 validateDefinition(def);
 commandSucceeded(await operation('更新几何',async()=>{let result=await geometry(def.action,params,def.inputs.map(brep=>({brep})));
  if(result.empty)throw Error('结果为空，原对象已保留');
  for(const transform of object.postTransforms||[])result=await geometry('transform',transform,[result]);
  commit({...project,objects:project.objects.map(o=>o.id===object.id?{...o,shape:result.shape,brep:result.brep,model:featureModel(def.action==='profile_solid'?(result.shape.dimension===3?'brep':'surface'):object.model.kind,params,[],object.model),definition:def}:o)},[object.id]);
 }));
}
async function commandFeature(id,named){
 const cmd=FEATURE_COMMANDS.find(c=>c.id===id);if(!cmd)throw Error(`未知几何命令 ${id}`);
 commandSelect(named.targets,cmd.min>0);
 const provided=commandParams(named,['targets']);const fields=new Map(cmd.fields.map(f=>[f.key,f]));
 for(const key of Object.keys(provided))if(!fields.has(key))throw Error(`不支持的参数 ${key}`);
 const params={kind:cmd.kind};
 for(const field of cmd.fields){const raw=Object.hasOwn(provided,field.key)?provided[field.key]:field.value;
  params[field.key]=field.type==='index'?Number(raw)-1:field.type==='indices'?raw.map(v=>Number(v)-1):raw;
 }
 const result=await featureUI.run(id,params);commandSucceeded(result);
 return result?.report?JSON.stringify(result.report):`${cmd.label}完成`;
}
async function commandConstruction(kind,named){
 if(['loft','distance','slice'].includes(kind))return commandFeature({loft:'surface-skin',distance:'query-distance',slice:'project-cut'}[kind],named);
 if(kind==='copy'){commandSelect(named.targets,true);commandSucceeded(await operation('复制',async()=>{const additions=[];for(const id of solidIds()){const base=project.objects.find(o=>o.id===id),r=await geometry('copy',{},[base]);additions.push({...base,id:crypto.randomUUID(),name:base.name+' 副本',brep:r.brep,shape:r.shape});}commit({...project,objects:[...project.objects,...additions]},additions.map(o=>o.id));}));return;}
 if(!['cone','torus','extrude','revolve','shell','offset','rotate3d'].includes(kind))throw Error('未知构造命令');
 const targets=['shell','offset','rotate3d'].includes(kind),selected=commandSelect(named.targets,targets);
 if(targets&&new Set(selected.map(s=>s.objectId)).size!==1)throw Error('该命令需要一个对象');
 const defaults={cone:{origin:[0,0,0],radius:15,topRadius:0,height:30},torus:{origin:[0,0,0],radius:20,tubeRadius:5},extrude:{origin:[0,0,0],profile:profiles.XY,height:20},revolve:{origin:[0,0,0],profile:profiles.XZ,angle:360},shell:{thickness:2},offset:{distance:1},rotate3d:{rotation:[0,0,0],pivot:[0,0,0]}}[kind];
 const p=commandFields(defaults,commandParams(named,['targets']));
 commandSucceeded(await operation('构造'+kind,async()=>{let action='create',operands=[];
  if(targets){operands=[selectedObject()];action=kind==='rotate3d'?'transform':kind;}else p.kind=kind;
  if(kind==='shell'){p.distance=-p.thickness;p.faces=selected.filter(s=>s.type==='face').map(s=>s.id-1);}
  const r=await geometry(action,p,operands);if(r.empty)throw Error('运算结果为空，原场景已保留');
  const object=makeObject((MODEL_NAMES[kind]||'轴旋转体')+sequence++,r,{...DEFAULT_MODEL,kind:MODEL_NAMES[kind]?kind:'brep'},{action,params:p,inputs:operands.map(o=>o.brep)}),remove=new Set(operands.map(o=>o.id));
  commit({...project,objects:project.objects.filter(o=>!remove.has(o.id)).concat(object)},[object.id]);
 }));
}
async function commandAdvanced(kind,named){
 if(kind==='boolean')return commandBoolean(String(named.operation??'union'),named);
 if(kind==='sweep'){
  const params=commandFields({kind:'sweep',profileKind:'circle',radius:3,width:6,height:4,path:[[0,0,0],[0,0,15],[10,0,30],[25,0,40]]},named,['profileKind','radius','width','height','path']);
  validateModel(featureModel('sweep',params));
  commandSucceeded(await operation('扫掠',async()=>{const r=await geometry('create',params);if(r.empty)throw Error('扫掠结果为空');const object=makeObject('扫掠体'+sequence++,r,featureModel('sweep',params),{action:'create',params,inputs:[]});commit({...project,objects:[...project.objects,object]},[object.id]);}));return;
 }
 if(!['fillet','chamfer'].includes(kind))throw Error('高级命令应为 boolean、sweep、fillet 或 chamfer');
 const selected=commandSelect(named.targets,true),object=selectedObject();
 const edges=named.edges===undefined?selected.filter(s=>s.type==='edge').map(s=>s.id):Array.isArray(named.edges)?named.edges:[named.edges];
 if(!edges.length||edges.some(i=>!Number.isInteger(i)||i<1||i>object.shape.edgeCount))throw Error('请选择或指定有效边编号');
 const radius=Number(named.radius??named.size??2);if(!Number.isFinite(radius)||radius<=0)throw Error('圆角或倒角尺寸无效');
 const params={radius,edges:edges.map(i=>i-1)};
 commandSucceeded(await operation(kind==='fillet'?'圆角':'倒角',async()=>{const r=await geometry(kind,params,[object]);if(r.empty)throw Error('结果为空，原场景已保留');const result=makeObject((MODEL_NAMES[kind]||'实体')+sequence++,r,featureModel(kind,params,[object]),{action:kind,params,inputs:[object.brep]});commit({...project,objects:project.objects.filter(o=>o.id!==object.id).concat(result)},[result.id]);}));
}
async function commandBoolean(op,named){
 if(!['union','difference','intersection','xor'].includes(op))throw Error('布尔运算类型无效');commandSelect(named.targets,true);
 commandSucceeded(await operation('布尔运算',async()=>{const operands=selectedBooleanObjects();if(!operands)throw Error('请选择 2～20 个封闭实体');const params={operation:op},r=await geometry('boolean',params,operands);if(r.empty)throw Error('运算结果为空，原场景已保留');const object=makeObject('布尔体'+sequence++,r,featureModel('boolean',params,operands),{action:'boolean',params,inputs:operands.map(o=>o.brep)}),remove=new Set(operands.map(o=>o.id));commit({...project,objects:project.objects.filter(o=>named.keep||!remove.has(o.id)).concat(object)},[object.id]);}));
}
async function executeModelingCommand(text){
 if(!interaction.direct())throw Error('请先切换到鼠标与命令行模式');
 if(busy||!initialized)throw Error('建模计算尚未就绪');
 const {verb,positionals,named}=parseModelingCommand(text);
 if(verb==='help')return '命令：box/cylinder/sphere、graph、part、edit 对象序号、feature 命令ID、construction 类型、advanced 类型、boolean 运算、transform 类型、select、property、delete、undo/redo、view、workplane。对象引用可用序号或 UUID；多对象用 targets=1,2，边/面用 1:edge:2。';
 if(verb==='objects')return project.objects.map((o,i)=>`${i+1}: ${o.name} (${o.id})`).join('；')||'当前没有对象';
 if(verb==='select'){commandSelect(named.targets??positionals,true);return '已按命令行对象引用选择';}
 if(verb==='clear'){selections=[];activeId=null;refresh();return '选择已清除';}
 if(verb==='undo'){restore(historyIndex-1);return '已撤销';}
 if(verb==='redo'){restore(historyIndex+1);return '已重做';}
 if(verb==='view'){fitView(String(positionals[0]||named.direction||'fit'));return '视图已更新';}
 if(verb==='workplane'){const z=Number(named.z??positionals[0]);if(!Number.isFinite(z)||Math.abs(z)>10000)throw Error('工作平面 Z 超出范围');$('workplane-z').value=String(z);$('workplane-z').dispatchEvent(new Event('change'));return '工作平面已更新';}
 if(verb==='grid'){const spacing=Number(named.spacing??positionals[0]);if(!Number.isFinite(spacing)||spacing<.1||spacing>1000)throw Error('网格间距应为 0.1～1000 mm');$('grid-spacing').value=String(spacing);$('grid-spacing').dispatchEvent(new Event('change'));return '网格间距已更新';}
 if(verb==='property'){const object=commandObject(named.target??positionals[0]),updates=commandParams(named,['target']);for(const key of Object.keys(updates))if(!['name','color','opacity','visible'].includes(key))throw Error(`不支持的对象属性 ${key}`);
  const next={...object,...updates};if(typeof next.name!=='string'||!next.name.trim()||next.name.length>80||!/^#[0-9a-f]{6}$/i.test(next.color)||typeof next.opacity!=='number'||next.opacity<.1||next.opacity>1||typeof next.visible!=='boolean')throw Error('对象属性无效');
  commit({...project,objects:project.objects.map(o=>o.id===object.id?next:o)},[object.id]);return '对象属性已更新';}
 if(verb==='delete'){commandSelect(named.targets??positionals,true);const ids=solidIds();if(ids.length!==selections.length)throw Error('删除命令只接受实体引用');commit({...project,objects:project.objects.filter(o=>!ids.includes(o.id))});return '对象已删除';}
 if(['box','cylinder','sphere'].includes(verb)){const model=commandFields({...DEFAULT_MODEL,kind:verb},named,Object.keys(DEFAULT_MODEL).filter(k=>k!=='kind'));commandSucceeded(await createModel(model));return `${verb} 已创建`;}
 if(verb==='graph'){await commandGraph(commandParams(named,['id']),named.id??null);return '草图特征已更新';}
 if(verb==='part'){await commandPart(commandParams(named,['id']),named.id??null);return '带孔圆角板已更新';}
 if(verb==='edit'){await commandEdit(positionals[0]??named.id,commandParams(named,['id']));return '对象已更新';}
 if(verb==='feature'||verb==='curve')return commandFeature(verb==='curve'?'curve-'+positionals[0]:String(positionals[0]),named);
 if(verb==='construction'){await commandConstruction(String(positionals[0]),named);return '构造完成';}
 if(verb==='advanced'){await commandAdvanced(String(positionals[0]),named);return '高级建模完成';}
 if(verb==='transform'){const kind=String(positionals[0]);if(!['move','rotate','scale'].includes(kind))throw Error('变换类型应为 move、rotate 或 scale');commandSelect(named.targets,true);
  const p=kind==='move'?{translation:named.delta}:kind==='rotate'?{pivot:named.pivot??[0,0,0],rotation:[0,0,named.angle]}:{pivot:named.pivot??[0,0,0],scale:[named.factor,named.factor,named.factor]};
  if(Object.values(p).some(v=>!Array.isArray(v)||v.some(n=>typeof n!=='number'||!Number.isFinite(n))))throw Error('变换参数需要有限数值');
  commandSucceeded(await operation('几何变换',()=>transformObjects(kind,p)));return '变换完成';}
 if(verb==='boolean'){await commandBoolean(String(positionals[0]),named);return '布尔运算完成';}
 throw Error(`未知命令 ${verb}；输入 help 查看用法`);
}
interaction.setCommandHandler(executeModelingCommand);

window.smlibModeler={snapshot:()=>structuredClone({ready:initialized,initialized,busy,name:project.name,objects:project.objects,project,selections,selected:[...new Set(selections.map(s=>s.objectId))],subSelected:selections.filter(s=>s.type!=='solid').map(s=>s.id-1),selectionMode,activeId,boxSelection,lastOperation,undo:historyIndex,redo:entries.length-1-historyIndex,history:{index:historyIndex,count:entries.length},interaction:mouse.snapshot(),axes:axes.snapshot(),renderCount,resizeCount,camera:{type:camera.type,projection:camera.isOrthographicCamera?'orthographic':'perspective',fov:camera.fov,visibleHeight:visibleHeight(camera,controls.target),pivot:controls.gesture?.pivot?.toArray(),position:camera.position.toArray(),up:camera.up.toArray(),target:controls.target.toArray(),zoom:camera.zoom,left:camera.left,right:camera.right,top:camera.top,bottom:camera.bottom,mouseButtons:controls.mouseButtons},rendering:{selectionSurfaces:highlightGroup.children.filter(o=>o.userData.selectedSurfaceId).map(o=>({id:o.userData.selectedSurfaceId,color:'#'+o.material.color.getHexString(),opacity:o.material.opacity})),objects:[...objects.values()].map(o=>({id:o.object.id,color:'#'+o.mesh.material.color.getHexString(),opacity:o.mesh.material.opacity,visible:o.mesh.visible}))}}),project:point=>mouse.project(point),select:selectModel};
async function start(){const start=performance.now();
 try{try{database=await openStorage();const saved=await new Promise((resolve,reject)=>{const r=database.transaction('projects').objectStore('projects').get('current');r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});if(saved?.objects?.every(o=>o.shape?.mesh&&typeof o.brep==='string')){project=saved;entries=[project];historyIndex=0;renderObjects();}}catch{message('本机自动保存不可用，请保存 Web 工程文件',true);}
 const health=await kernel.init();stepAvailable=health.features?.step===true;initialized=true;busy=false;$('modeling-startup').hidden=true;$('modeling-startup').setAttribute('aria-busy','false');document.body.dataset.loadMs=String(performance.now()-start);refresh();message('本地计算已就绪，请创建模型');
 }catch(error){busy=false;setModelingText($('modeling-startup').querySelector('[data-startup-title]'),'本地计算模块加载失败');setModelingText($('modeling-startup').querySelector('[data-startup-detail]'),error.message);$('modeling-startup').querySelector('[data-startup-retry]').hidden=false;message(error.message,true);refresh();}}
$('modeling-startup').querySelector('[data-startup-retry]').onclick=()=>location.reload();
installModelingI18n({storageKey:'smlib-modeling-locale'});
document.addEventListener('DOMContentLoaded',()=>queueMicrotask(()=>{const link=document.querySelector('.local-note a[href="./diagnostics.html"]');if(link)setModelingText(link,'匿名诊断说明');}),{once:true});
start();
