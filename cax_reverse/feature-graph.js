const UUID=/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const numeric=(value,min,max)=>typeof value==='number'&&Number.isFinite(value)&&value>=min&&value<=max;
const keys=(value,names)=>value&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).sort().join(',')===names.slice().sort().join(',');
const validSolid=result=>result&&!result.empty&&result.shape?.dimension===3&&result.shape.manifold&&result.shape.topologyValid&&typeof result.brep==='string';

export function validateFeatureGraph(value){
 if(value?.version===2)return validateBranchGraph(value);
 if(value?.version===3||value?.version===4)return validateConcentricGraph(value);
 if(!keys(value,['version','nodes','outputId'])||value.version!==1||!Array.isArray(value.nodes)||value.nodes.length<2||value.nodes.length>4)throw Error('特征依赖格式无效');
 const nodes=value.nodes;
 if(nodes[0]?.kind!=='rectangle_sketch'||nodes[1]?.kind!=='extrude')throw Error('特征依赖需要矩形草图与拉伸');
 const seen=new Set();
 for(let i=0;i<nodes.length;i++){
  const node=nodes[i];
  if(!node||!UUID.test(node.id)||seen.has(node.id))throw Error('特征节点编号无效或重复');
  seen.add(node.id);
  if(i===0){
   if(!keys(node,['id','kind','params'])||!keys(node.params,['x','y','length','width']))throw Error('矩形草图参数无效');
   const p=node.params;
   if(!numeric(p.x,-10000,10000)||!numeric(p.y,-10000,10000)||!numeric(p.length,.1,1000)||!numeric(p.width,.1,1000))throw Error('矩形草图尺寸超出范围');
  }else if(i===1){
   if(!keys(node,['id','kind','inputId','params'])||node.inputId!==nodes[0].id||!keys(node.params,['height'])||!numeric(node.params.height,.1,1000))throw Error('拉伸参数或草图引用无效');
  }else if(node.kind==='through_hole'){
   const p=node.params,s=nodes[0].params;
   if(i!==2||!keys(node,['id','kind','inputId','params'])||node.inputId!==nodes[i-1].id||!keys(p,['diameter','offsetX','offsetY'])||!numeric(p.diameter,.1,1000)||!numeric(p.offsetX,-10000,10000)||!numeric(p.offsetY,-10000,10000))throw Error('贯穿孔参数或基体引用无效');
   if(Math.abs(p.offsetX)+p.diameter/2>=s.length/2-.005||Math.abs(p.offsetY)+p.diameter/2>=s.width/2-.005)throw Error('孔边缘必须位于矩形内部');
  }else if(node.kind==='edge_fillet'){
   const p=node.params,s=nodes[0].params,h=nodes[1].params.height;
   if(i!==nodes.length-1||!keys(node,['id','kind','inputId','target','params'])||node.inputId!==nodes[i-1].id||!keys(node.target,['sketchId','corner'])||node.target.sketchId!==nodes[0].id||!['lower_left','lower_right','upper_right','upper_left'].includes(node.target.corner)||!keys(p,['radius'])||!numeric(p.radius,.01,1000)||p.radius>=Math.min(s.length,s.width,h)/2)throw Error('圆角参数或草图角点引用无效');
  }else throw Error('不支持的特征节点');
 }
 if(nodes.length===4&&(nodes[2].kind!=='through_hole'||nodes[3].kind!=='edge_fillet')||nodes.length===3&&!['through_hole','edge_fillet'].includes(nodes[2].kind)||value.outputId!==nodes.at(-1).id)throw Error('特征依赖顺序无效');
 return {version:1,nodes:nodes.map(node=>structuredClone(node)),outputId:value.outputId};
}

function validateBranchGraph(value){
 if(!keys(value,['version','nodes','outputId'])||!Array.isArray(value.nodes)||value.nodes.length<5||value.nodes.length>7)throw Error('凸台特征依赖格式无效');
 const nodes=value.nodes,[sketch,extrude,circle,boss,fuse]=nodes;
 if(sketch?.kind!=='rectangle_sketch'||extrude?.kind!=='extrude'||circle?.kind!=='boss_circle_sketch'||boss?.kind!=='boss_extrude'||fuse?.kind!=='fuse')throw Error('凸台特征顺序无效');
 const ids=nodes.map(n=>n?.id);
 if(ids.some(id=>typeof id!=='string'||!UUID.test(id))||new Set(ids).size!==ids.length)throw Error('特征节点编号无效或重复');
 if(!keys(sketch,['id','kind','params'])||!keys(sketch.params,['x','y','length','width']))throw Error('矩形草图参数无效');
 const s=sketch.params;
 if(!numeric(s.x,-10000,10000)||!numeric(s.y,-10000,10000)||!numeric(s.length,.1,1000)||!numeric(s.width,.1,1000))throw Error('矩形草图尺寸超出范围');
 if(!keys(extrude,['id','kind','inputId','params'])||extrude.inputId!==sketch.id||!keys(extrude.params,['height'])||!numeric(extrude.params.height,.1,1000))throw Error('底板拉伸引用无效');
 if(!keys(circle,['id','kind','inputId','params'])||circle.inputId!==sketch.id||!keys(circle.params,['diameter','offsetX','offsetY']))throw Error('凸台圆草图引用无效');
 const c=circle.params;
 if(!numeric(c.diameter,.1,1000)||!numeric(c.offsetX,-10000,10000)||!numeric(c.offsetY,-10000,10000)||Math.abs(c.offsetX)+c.diameter/2>=s.length/2-.005||Math.abs(c.offsetY)+c.diameter/2>=s.width/2-.005)throw Error('凸台圆必须位于底板内部');
 if(!keys(boss,['id','kind','inputId','supportId','params'])||boss.inputId!==circle.id||boss.supportId!==extrude.id||!keys(boss.params,['height'])||!numeric(boss.params.height,.1,1000))throw Error('凸台拉伸引用无效');
 if(!keys(fuse,['id','kind','inputIds','params'])||!Array.isArray(fuse.inputIds)||fuse.inputIds.length!==2||fuse.inputIds[0]!==extrude.id||fuse.inputIds[1]!==boss.id||!keys(fuse.params,[]))throw Error('底板与凸台合并引用无效');
 let last=fuse;
 for(const node of nodes.slice(5)){
  if(node.kind==='through_hole'){
   if(node!==nodes[5]||!keys(node,['id','kind','inputId','params'])||node.inputId!==last.id||!keys(node.params,['diameter','offsetX','offsetY']))throw Error('贯穿孔引用无效');
   const p=node.params;
   if(!numeric(p.diameter,.1,1000)||!numeric(p.offsetX,-10000,10000)||!numeric(p.offsetY,-10000,10000)||Math.abs(p.offsetX)+p.diameter/2>=s.length/2-.005||Math.abs(p.offsetY)+p.diameter/2>=s.width/2-.005)throw Error('孔边缘必须位于底板内部');
  }else if(node.kind==='edge_fillet'){
   if(node!==nodes.at(-1)||!keys(node,['id','kind','inputId','target','params'])||node.inputId!==last.id||!keys(node.target,['sketchId','corner'])||node.target.sketchId!==sketch.id||!['lower_left','lower_right','upper_right','upper_left'].includes(node.target.corner)||!keys(node.params,['radius'])||!numeric(node.params.radius,.01,1000)||node.params.radius>=Math.min(s.length,s.width,extrude.params.height)/2)throw Error('圆角引用无效');
  }else throw Error('不支持的凸台特征节点');
  last=node;
 }
 if(nodes.length===7&&(nodes[5].kind!=='through_hole'||nodes[6].kind!=='edge_fillet')||nodes.length===6&&!['through_hole','edge_fillet'].includes(nodes[5].kind)||value.outputId!==last.id)throw Error('凸台特征输出引用无效');
 return structuredClone(value);
}

function validateConcentricGraph(value){
 if(!keys(value,['version','nodes','outputId'])||!Array.isArray(value.nodes)||![7,8].includes(value.nodes.length))throw Error('同心草图约束格式无效');
 const nodes=value.nodes,[sketch,extrude,bossCircle,boss,fuse,holeCircle,hole,fillet]=nodes;
 validateBranchGraph({version:2,nodes:nodes.slice(0,5),outputId:fuse?.id});
 const ids=nodes.map(n=>n?.id);
 if(ids.some(id=>typeof id!=='string'||!UUID.test(id))||new Set(ids).size!==ids.length)throw Error('特征节点编号无效或重复');
 const linkedWall=value.version===4;
 if(!keys(holeCircle,['id','kind','inputId','constraint','params'])||holeCircle.kind!=='hole_circle_sketch'||holeCircle.inputId!==bossCircle.id||!keys(holeCircle.constraint,['kind','referenceId'])||holeCircle.constraint.kind!==(linkedWall?'concentric_wall':'concentric')||holeCircle.constraint.referenceId!==bossCircle.id||!keys(holeCircle.params,linkedWall?['wallThickness']:['diameter']))throw Error('孔圆草图同心约束无效');
 if(linkedWall){
  const wall=holeCircle.params.wallThickness,diameter=bossCircle.params.diameter-2*wall;
  if(!numeric(wall,.01,499.95)||!numeric(diameter,.1,1000)||diameter>=bossCircle.params.diameter-.01)throw Error('壁厚必须使孔径处于有效范围');
 }else if(!numeric(holeCircle.params.diameter,.1,1000)||holeCircle.params.diameter>=bossCircle.params.diameter-.01)throw Error('同心孔径必须小于凸台直径');
 if(!keys(hole,['id','kind','inputIds','params'])||hole.kind!=='through_hole'||!Array.isArray(hole.inputIds)||hole.inputIds.length!==2||hole.inputIds[0]!==fuse.id||hole.inputIds[1]!==holeCircle.id||!keys(hole.params,[]))throw Error('同心孔特征引用无效');
 if(fillet){
  if(!keys(fillet,['id','kind','inputId','target','params'])||fillet.kind!=='edge_fillet'||fillet.inputId!==hole.id||!keys(fillet.target,['sketchId','corner'])||fillet.target.sketchId!==sketch.id||!['lower_left','lower_right','upper_right','upper_left'].includes(fillet.target.corner)||!keys(fillet.params,['radius'])||!numeric(fillet.params.radius,.01,1000)||fillet.params.radius>=Math.min(sketch.params.length,sketch.params.width,extrude.params.height)/2)throw Error('同心孔后圆角引用无效');
 }
 if(value.outputId!==(fillet||hole).id)throw Error('同心草图输出引用无效');
 return structuredClone(value);
}

export function featureGraphParameters(graph){
 const {version,nodes}=validateFeatureGraph(graph),sketch=nodes[0].params,extrude=nodes[1].params;
 const hole=nodes.find(node=>node.kind==='through_hole')?.params,holeCircle=nodes.find(node=>node.kind==='hole_circle_sketch');
 const fillet=nodes.find(node=>node.kind==='edge_fillet');
 const boss=nodes.find(node=>node.kind==='boss_circle_sketch')?.params,bossExtrude=nodes.find(node=>node.kind==='boss_extrude');
 const diameter=version===4?boss.diameter-2*holeCircle.params.wallThickness:holeCircle?.params.diameter??hole?.diameter??6;
 return {x:sketch.x,y:sketch.y,length:sketch.length,width:sketch.width,height:extrude.height,bossEnabled:!!boss,bossDiameter:boss?.diameter??8,bossOffsetX:boss?.offsetX??-10,bossOffsetY:boss?.offsetY??0,bossHeight:bossExtrude?.params.height??4,holeEnabled:!!hole||!!holeCircle,concentricHole:!!holeCircle,wallLinked:version===4,wallThickness:version===4?holeCircle.params.wallThickness:boss?(boss.diameter-diameter)/2:2,diameter,offsetX:holeCircle?boss.offsetX:hole?.offsetX??0,offsetY:holeCircle?boss.offsetY:hole?.offsetY??0,filletEnabled:!!fillet,radius:fillet?.params.radius??1,corner:fillet?.target.corner??'lower_left'};
}

export function featureGraphFromParameters(values,previous=null){
 if(values.wallLinked&&(!values.concentricHole||!values.bossEnabled||!values.holeEnabled))throw Error('固定壁厚需要同心孔和凸台');
 const old=previous?validateFeatureGraph(previous).nodes:[];
 const id=kind=>old.find(node=>node.kind===kind)?.id||crypto.randomUUID();
 const sketch={id:id('rectangle_sketch'),kind:'rectangle_sketch',params:{x:values.x,y:values.y,length:values.length,width:values.width}};
 const extrude={id:id('extrude'),kind:'extrude',inputId:sketch.id,params:{height:values.height}};
 const nodes=[sketch,extrude];
 if(values.bossEnabled){
  const circle={id:id('boss_circle_sketch'),kind:'boss_circle_sketch',inputId:sketch.id,params:{diameter:values.bossDiameter,offsetX:values.bossOffsetX,offsetY:values.bossOffsetY}};
  const boss={id:id('boss_extrude'),kind:'boss_extrude',inputId:circle.id,supportId:extrude.id,params:{height:values.bossHeight}};
  nodes.push(circle,boss,{id:id('fuse'),kind:'fuse',inputIds:[extrude.id,boss.id],params:{}});
 }
 if(values.holeEnabled){
  if(values.concentricHole){
   if(!values.bossEnabled)throw Error('同心约束需要凸台和贯穿孔');
   const bossCircle=nodes.find(node=>node.kind==='boss_circle_sketch');
   const holeCircle={id:id('hole_circle_sketch'),kind:'hole_circle_sketch',inputId:bossCircle.id,constraint:{kind:values.wallLinked?'concentric_wall':'concentric',referenceId:bossCircle.id},params:values.wallLinked?{wallThickness:values.wallThickness}:{diameter:values.diameter}};
   const fuse=nodes.at(-1);
   nodes.push(holeCircle,{id:id('through_hole'),kind:'through_hole',inputIds:[fuse.id,holeCircle.id],params:{}});
  }else nodes.push({id:id('through_hole'),kind:'through_hole',inputId:nodes.at(-1).id,params:{diameter:values.diameter,offsetX:values.offsetX,offsetY:values.offsetY}});
 }
 if(values.filletEnabled)nodes.push({id:id('edge_fillet'),kind:'edge_fillet',inputId:nodes.at(-1).id,target:{sketchId:sketch.id,corner:values.corner},params:{radius:values.radius}});
 return validateFeatureGraph({version:values.wallLinked?4:values.concentricHole&&values.holeEnabled?3:values.bossEnabled?2:1,nodes,outputId:nodes.at(-1).id});
}

function verticalCornerEdge(shape,sketch,height,corner){
 const {x,y,length,width}=sketch;
 const point={lower_left:[x,y],lower_right:[x+length,y],upper_right:[x+length,y+width],upper_left:[x,y+width]}[corner];
 const near=(a,b)=>Math.abs(a-b)<1e-5;
 return shape.mesh.edges.find(edge=>{
  const start=edge.points.slice(0,3),end=edge.points.slice(-3);
  return near(start[0],point[0])&&near(start[1],point[1])&&near(end[0],point[0])&&near(end[1],point[1])&&
   (near(start[2],0)&&near(end[2],height)||near(start[2],height)&&near(end[2],0));
 })?.index;
}

export async function buildFeatureGraph(graph,geometry){
 const {nodes}=validateFeatureGraph(graph),sketch=nodes[0].params,height=nodes[1].params.height;
 const bossHeight=nodes.find(n=>n.kind==='boss_extrude')?.params.height??0;
 const profile=[[sketch.x,sketch.y],[sketch.x+sketch.length,sketch.y],[sketch.x+sketch.length,sketch.y+sketch.width],[sketch.x,sketch.y+sketch.width]];
 const outputs=new Map([[nodes[0].id,{profile}]]);
 for(const node of nodes.slice(1)){
  const input=outputs.get(node.inputId);
  if(node.kind==='boss_circle_sketch'){
   if(!input)throw Error('凸台草图输入不存在');
   outputs.set(node.id,{circle:node.params});
   continue;
  }
  if(node.kind==='fuse'){
   const operands=node.inputIds.map(id=>outputs.get(id));
   if(operands.some(o=>!o))throw Error('合并输入不存在');
   const joined=await geometry('boolean',{operation:'union'},operands);
   if(!validSolid(joined))throw Error('底板与凸台未合并为有效实体，原模型已保留');
   outputs.set(node.id,joined);
   continue;
  }
  if(node.kind==='hole_circle_sketch'){
   if(!input?.circle||node.constraint.referenceId!==node.inputId)throw Error('同心孔的参考圆不存在');
   const diameter=node.constraint.kind==='concentric_wall'?input.circle.diameter-2*node.params.wallThickness:node.params.diameter;
   outputs.set(node.id,{circle:{diameter,offsetX:input.circle.offsetX,offsetY:input.circle.offsetY}});
   continue;
  }
  if(node.kind==='through_hole'&&Array.isArray(node.inputIds)){
   const base=outputs.get(node.inputIds[0]),profile=outputs.get(node.inputIds[1])?.circle;
   if(!validSolid(base)||!profile)throw Error('同心孔的草图或实体不存在');
   const tool=await geometry('create',{kind:'cylinder',origin:[sketch.x+sketch.length/2+profile.offsetX,sketch.y+sketch.width/2+profile.offsetY,-1],radius:profile.diameter/2,height:height+bossHeight+2});
   const cut=await geometry('boolean',{operation:'difference'},[base,tool]);
   if(!validSolid(cut))throw Error('同心孔未生成有效封闭实体，原模型已保留');
   outputs.set(node.id,cut);
   continue;
  }
  if(!input)throw Error('特征输入不存在');
  let result;
  if(node.kind==='extrude')result=await geometry('create',{kind:'extrude',origin:[0,0,0],profile:input.profile,height:node.params.height});
  else if(node.kind==='boss_extrude'){
   const p=input.circle;
   const support=outputs.get(node.supportId);
   if(!validSolid(support))throw Error('凸台底板引用无效');
   const top=support.shape.bounds?.[1]?.[2];
   if(!Number.isFinite(top))throw Error('凸台底板高度无效');
   result=await geometry('create',{kind:'cylinder',origin:[sketch.x+sketch.length/2+p.offsetX,sketch.y+sketch.width/2+p.offsetY,top-.01],radius:p.diameter/2,height:node.params.height+.01});
  }
  else if(node.kind==='through_hole'){
   const p=node.params;
   const tool=await geometry('create',{kind:'cylinder',origin:[sketch.x+sketch.length/2+p.offsetX,sketch.y+sketch.width/2+p.offsetY,-1],radius:p.diameter/2,height:height+bossHeight+2});
   result=await geometry('boolean',{operation:'difference'},[input,tool]);
  }else if(node.kind==='edge_fillet'){
   const edge=verticalCornerEdge(input.shape,sketch,height,node.target.corner);
   if(!Number.isInteger(edge))throw Error('无法定位草图角点对应的竖边，原模型已保留');
   result=await geometry('fillet',{radius:node.params.radius,edges:[edge]},[input]);
  }
  if(!validSolid(result))throw Error('特征未生成有效封闭实体，原模型已保留');
  outputs.set(node.id,result);
 }
 return outputs.get(graph.outputId);
}
