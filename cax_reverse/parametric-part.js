const keys=['length','width','height','holeDiameter','holeX','holeY','filletRadius'];

export function validateParametricPart(value){
 if(!value||value.kind!=='rectangular-plate'||value.version!==1||!value.params||typeof value.params!=='object'||Object.keys(value.params).some(key=>!keys.includes(key)))throw Error('参数化零件格式无效');
 const p=value.params;
 if(keys.some(key=>!Number.isFinite(p[key])))throw Error('零件尺寸需要有限数值');
 if([p.length,p.width,p.height].some(n=>n<.1||n>1000)||p.holeDiameter<.1||p.holeDiameter>1000||p.filletRadius<.01||p.filletRadius>1000)throw Error('零件尺寸超出允许范围');
 if(Math.abs(p.holeX)>10000||Math.abs(p.holeY)>10000||Math.abs(p.holeX)+p.holeDiameter/2>=p.length/2-.005||Math.abs(p.holeY)+p.holeDiameter/2>=p.width/2-.005)throw Error('孔边缘必须位于矩形内部');
 if(p.filletRadius>=Math.min(p.length,p.width,p.height)/2)throw Error('圆角半径须小于零件最小尺寸的一半');
 return {version:1,kind:'rectangular-plate',params:Object.fromEntries(keys.map(key=>[key,p[key]]))};
}

function outerVerticalEdge(shape,height){
 const close=(a,b)=>Math.abs(a-b)<1e-5;
 return shape.mesh.edges.find(edge=>{
  const points=edge.points,start=points.slice(0,3),end=points.slice(-3);
  return close(start[0],0)&&close(start[1],0)&&close(end[0],0)&&close(end[1],0)&&
   (close(start[2],0)&&close(end[2],height)||close(start[2],height)&&close(end[2],0));
 })?.index;
}

export async function buildParametricPart(recipe,geometry){
 const {length,width,height,holeDiameter,holeX,holeY,filletRadius}=validateParametricPart(recipe).params;
 const profile=[[0,0],[length,0],[length,width],[0,width]];
 const extrusion=await geometry('create',{kind:'extrude',origin:[0,0,0],profile,height});
 const cutter=await geometry('create',{kind:'cylinder',origin:[length/2+holeX,width/2+holeY,-1],radius:holeDiameter/2,height:height+2});
 const drilled=await geometry('boolean',{operation:'difference'},[extrusion,cutter]);
 if(drilled.empty)throw Error('开孔结果为空');
 const edge=outerVerticalEdge(drilled.shape,height);
 if(!Number.isInteger(edge))throw Error('无法定位矩形外角边，原模型已保留');
 const result=await geometry('fillet',{radius:filletRadius,edges:[edge]},[drilled]);
 if(result.empty||result.shape?.dimension!==3||!result.shape.manifold||!result.shape.topologyValid)throw Error('零件未生成有效封闭实体，原模型已保留');
 return result;
}
