// Browser interaction definitions follow FasCAD Web; geometry is built by SMLib.
export const DEFAULT_MODEL=Object.freeze({kind:'box',length:60,width:40,height:20,radius:15,hole:false,diameter:12,holeX:0,holeY:0,x:0,y:0,z:0,angle:0,scale:1});
export const MODEL_NAMES={box:'长方体',cylinder:'圆柱',sphere:'球体',cone:'圆锥',torus:'圆环',extrude:'拉伸体',revolve:'旋转体',sweep:'扫掠体',boolean:'布尔体',fillet:'圆角体',chamfer:'倒角体',shell:'抽壳体',offset:'偏移体',brep:'SMLib 实体',profile:'曲线',surface:'曲面',points:'点集'};
export const isPrimitive=model=>['box','cylinder','sphere'].includes(model?.kind);
export function validateModel(value){
 if(!value||typeof value!=='object')throw Error('模型参数格式无效');const model={...DEFAULT_MODEL,...value};
 for(const key of ['length','width','height','radius','diameter'])if(!Number.isFinite(model[key])||model[key]<.1||model[key]>1000)throw Error('尺寸必须为 0.1 至 1000 毫米之间的有限数值');
 for(const key of ['x','y','z','holeX','holeY'])if(!Number.isFinite(model[key])||Math.abs(model[key])>10000)throw Error('坐标必须在 ±10000 mm 内');
 if(!Number.isFinite(model.angle)||Math.abs(model.angle)>360||!Number.isFinite(model.scale)||model.scale<.01||model.scale>100)throw Error('旋转角度或缩放比例无效');
 if(model.hole&&(model.kind!=='box'||Math.abs(model.holeX)+model.diameter/2>=model.length/2-.005||Math.abs(model.holeY)+model.diameter/2>=model.width/2-.005))throw Error('孔必须位于长方体内部，孔边缘与外壁需保留间距');
 if(!Object.hasOwn(MODEL_NAMES,model.kind))throw Error('模型类型无效');
 if(model.kind==='boolean'&&(!['fuse','cut','common','xor'].includes(model.operation)||!Array.isArray(model.operands)||model.operands.length<2||model.operands.length>20))throw Error('布尔构造参数无效');
 if(['fillet','chamfer'].includes(model.kind)&&(!Array.isArray(model.edges)||!model.edges.length||model.edges.some(i=>!Number.isInteger(i)||i<1)||!Number.isFinite(model.size)||model.size<=0))throw Error('选边构造参数无效');
 if(model.kind==='sweep'){
  const section=model.profile,validSize=v=>Number.isFinite(v)&&v>=.1&&v<=1000;
  if(!section||!(section.kind==='circle'?validSize(section.radius):section.kind==='rectangle'&&validSize(section.width)&&validSize(section.height))||!Array.isArray(model.path)||model.path.length<4||model.path.length>32||model.path.some(p=>!Array.isArray(p)||p.length!==3||p.some(v=>!Number.isFinite(v)||Math.abs(v)>100000)))throw Error('扫掠构造参数无效');
 }
 return model;
}
