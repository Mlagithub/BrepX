// User-facing commands share the same native action contract as desktop integrations.
const f=(key,label,value,type='number',options)=>({key,label,value,type,...(options?{options}:{})});
const origin=f('origin','位置 XYZ（mm）',[0,0,0],'vector'),points=f('points','XYZ 点（每行一个点）',[[0,0,0],[10,5,0],[20,-5,5],[30,0,0]],'points');
const curve=(id,label,fields)=>({id:'curve-'+id,label,group:'曲线',action:'curve_create',kind:id,fields,min:0,max:0});
const surface=(id,label,fields,min=0,max=min)=>({id:'surface-'+id,label,group:'曲面',action:'surface_create',kind:id,fields,min,max,subSelection:min>0});
const solid=(kind,label,fields)=>({id:'solid-'+kind,label,group:'轮廓成体',action:'profile_solid',kind,fields,min:1,max:20,subSelection:true,note:'处理所选曲线的全部裁剪边，自动识别闭环与孔环；也可使用单个面的全部边界。新增结果并保留轮廓。拉伸或不足一周的旋转可取消封口生成开放壳体；完整一周旋转没有旋转端面。'});
const grid=Array.from({length:16},(_,n)=>{const i=Math.floor(n/4),j=n%4;return [i*10,j*10,4*Math.sin(i)*Math.sin(j)];});
const edge=f('edge','边编号（从 1 开始）',1,'index'),face=f('face','面编号（从 1 开始）',1,'index'),at=f('point','查询点 XYZ（mm）',[0,0,20],'vector');
const auto=f('autoParameters','使用参数范围中点',true,'boolean'),parameter=f('parameter','曲线参数',0),uv=f('uv','曲面参数 U, V',[0,0],'uv');
const query=(kind,label,fields=[],min=1,max=min)=>({id:'query-'+kind,label,group:'几何查询',action:'query',kind,fields,min,max});
const intersection=(kind,label,fields=[],min=2)=>({id:'intersect-'+kind,label,group:'求交与截面',action:'intersect',kind,fields,min,max:min,subSelection:true});
const repair=(kind,label,fields=[])=>({id:'repair-'+kind,label,group:'缝合与修复',action:'repair',kind,fields,min:1,max:64,subSelection:kind==='normals'});
const booleanOptions=[['union','并集'],['difference','差集'],['intersection','交集'],['xor','异或'],['merge','合并保留分界']];
const boolMode=(options=booleanOptions)=>f('operation','运算','union','choice',options);
const advanced=(kind,label,fields=[],min=2,max=min)=>({id:'boolean-'+kind,label,group:'布尔运算',action:'advanced_boolean',kind,fields,min,max});
const project=(kind,label,fields=[],min=2,max=min)=>({id:'project-'+kind,label,group:'投影与裁剪',action:'project_trim',kind,fields,min,max,subSelection:true});
const dir=f('direction','投影方向 XYZ',[0,0,-1],'vector'),planePoint=f('point','平面上一点 XYZ（mm）',[0,0,0],'vector'),normal=f('normal','平面法向 XYZ',[0,0,1],'vector');
const sourceEdge=[f('singleEdge','仅处理选中的一条边',false,'boolean'),edge],ref=f('referencePoint','保留/删除区域参考点 XYZ（mm）',[0,0,0],'vector');
const solidSource=[f('source','轮廓来源','wires','choice',[['wires','所选曲线的全部闭环'],['face','指定面的全部边界']]),{...face,label:'面编号（面来源时使用，从1开始）'}];
export const FEATURE_COMMANDS=[
 curve('line','直线参数',[f('start','起点 XYZ',[0,0,0],'vector'),f('end','终点 XYZ',[30,0,0],'vector')]),
 curve('circle','圆参数',[origin,f('radius','半径（mm）',10)]),curve('arc','圆弧参数',[origin,f('radius','半径（mm）',10),f('startAngle','起始角（°）',0),f('endAngle','终止角（°）',180)]),
 curve('ellipse','椭圆',[origin,f('radius','X 半径（mm）',15),f('radiusY','Y 半径（mm）',8)]),
 curve('rectangle','矩形参数',[origin,f('length','长度（mm）',30),f('width','宽度（mm）',20)]),curve('polygon','正多边形',[origin,f('sides','边数',6),f('radius','外接圆半径（mm）',15)]),
 curve('helix','螺旋线',[origin,f('height','高度（mm）',30),f('radius','起始半径（mm）',10),f('endRadius','终止半径（mm）',10),f('turns','圈数',3),f('rightHanded','右旋',true,'boolean'),f('tolerance','拟合误差（mm）',.01)]),
 curve('polyline','折线参数',[points,f('closed','闭合',false,'boolean')]),curve('bspline','控制点样条',[points]),curve('interpolate','插值样条',[points]),curve('fit','拟合曲线',[points]),
 curve('nurbs','有理 NURBS',[points,f('degree','次数',3),f('knots','不同节点值',[0,1],'list'),f('multiplicities','节点重数',[4,4],'list'),f('weights','控制点权重',[1,2,2,1],'list')]),
 ...[['offset','曲线偏移',[f('distance','偏移距离（mm）',2)]],['remove_knots','移除节点',[]],['lines_arcs','转为线与圆弧',[]]].map(([kind,label,fields])=>({id:'curve-'+kind,label,group:'曲线编辑',action:'curve_edit',kind,fields:[edge,...fields],subSelection:true,min:1,max:1})),
 surface('plane','平面',[origin,f('length','长度（mm）',30),f('width','宽度（mm）',20)]),
 surface('corners','四角曲面',[f('points','四角 XYZ（UminVmin、UmaxVmin、UminVmax、UmaxVmax）',[[0,0,0],[30,0,0],[0,20,0],[30,20,10]],'points')]),
 ...[['control_grid','控制网格曲面'],['through_grid','插值网格曲面'],['point_cloud','点集拟合曲面']].map(([id,label])=>surface(id,label,[f('points','XYZ 点（按 U 行、V 列排列）',grid,'points'),f('rows','行数',4),f('columns','列数',4)])),
 surface('extrude','曲线拉伸面',[edge,f('vector','拉伸向量 XYZ（mm）',[0,0,20],'vector')],1),
 surface('revolve','曲线旋转面',[edge,origin,f('axis','旋转轴方向 XYZ',[0,0,1],'vector'),f('angle','角度（°）',180)],1),
 surface('ruled','直纹曲面',[f('edges','各输入对象的边编号（从1开始）',[1,1],'indices')],2),surface('sweep','曲线扫掠面',[f('edges','截面边、路径边编号（从1开始）',[1,1],'indices')],2),surface('skin','放样曲面',[f('edges','各输入对象的边编号（从1开始）',[1,1],'indices')],2,20),surface('offset','曲面偏置',[face,f('distance','偏置距离（mm）',2)],1),
 solid('extrude','闭环拉伸',[...solidSource,f('vector','拉伸向量 XYZ（mm）',[0,0,20],'vector'),f('cap','封闭两端形成实体',true,'boolean')]),
 solid('revolve','闭环旋转',[...solidSource,origin,f('axis','旋转轴方向 XYZ',[0,0,1],'vector'),f('angle','旋转角度（°）',360),f('cap','封闭旋转端面',true,'boolean')]),
 query('properties','几何属性',[f('tight','紧包围盒',false,'boolean')]),query('bounds','包围盒',[f('tight','紧包围盒',true,'boolean')]),
 query('mass','质量与惯性',[f('density','密度（质量单位/mm³）',1),f('centroidal','以质心为惯性矩原点',true,'boolean'),origin]),
 query('distance','实体距离',[],2),query('relationship','实体位置关系',[],2),
 query('closest','体最近点',[at]),query('closest_all','体最近点候选',[at]),
 query('curve_closest','曲线最近点',[edge,at]),query('curve_closest_all','曲线最近点候选',[edge,at]),query('edge_closest','边最近点',[edge,at]),
 query('face_closest','面最近点',[face,at]),query('surface_closest','曲面最近点',[face,at]),
 query('face','面属性与边界',[face]),query('edge','边属性',[edge]),
 query('curve_evaluate','曲线求值',[edge,auto,parameter]),query('edge_classify','边参数分类',[edge,parameter]),
 query('surface_evaluate','曲面求值',[face,auto,uv]),query('face_classify','面参数分类',[face,uv]),
 query('vertex','顶点坐标',[f('vertex','顶点编号（从 1 开始）',1,'index')]),query('find','按坐标找边面',[at]),
 intersection('section','平面截面',[f('point','截面上一点 XYZ（mm）',[0,0,0],'vector'),f('normal','截面法向 XYZ',[0,0,1],'vector')],1),
 {...intersection('curves','曲线求交',[
  {...edge,hidden:true},{...f('edgeB','第二对象边编号',1,'index'),hidden:true},
  {...f('allEdgesA','使用第一条曲线的全部边',false,'boolean'),hidden:true},
  {...f('allEdgesB','使用第二条曲线的全部边',false,'boolean'),hidden:true}
 ]),note:'使用当前选中的两条曲线或两条边。完整曲线包含全部曲线段；边使用其底层曲线的完整参数范围。没有交点时显示空结果。'},
 intersection('surfaces','曲面求交',[face,f('faceB','第二对象面编号',1,'index')]),intersection('faces','修剪面求交',[face,f('faceB','第二对象面编号',1,'index')]),
 intersection('breps','体求交线'),intersection('curve_surface','曲线与曲面求交',[edge,f('faceB','第二对象面编号',1,'index')]),
 intersection('curve_face','曲线与面求交',[edge,f('faceB','第二对象面编号',1,'index')]),intersection('curve_brep','曲线与体求交',[edge]),
 repair('stitch','自动缝合'),repair('solid','缝合成实体'),repair('shell','缝合成壳',[f('maxGap','最大允许间隙（mm）',.00001),f('wellFormed','输入是规则壳',false,'boolean')]),
 repair('advanced','高级缝合',[f('tolerance','缝合容差（mm）',.00001),f('squeezeSmallEdges','移除短边',false,'boolean'),f('splitEdges','在邻近顶点处分边',true,'boolean'),f('solid','仅缝合成对自由边',false,'boolean'),f('removeSlivers','移除狭长薄片',false,'boolean')]),
 repair('heal','修复模型'),repair('normals','统一法向',[face,f('samples','射线采样数',100)]),repair('nurbs','转换为 NURBS'),
 advanced('merge','合并保留分界'),advanced('imprint','交线印刻'),advanced('slice','曲面切片'),
 advanced('options','布尔参数',[boolMode(),f('cookieCutter','按工具边界切割',false,'boolean'),f('imprinting','仅印刻',false,'boolean'),f('postProcess','整理结果拓扑',true,'boolean'),f('imprintAndClassify','印刻并标记待删除面',false,'boolean'),f('keepOther','保留内部工具副本',false,'boolean')]),
 advanced('2d','二维面域布尔',[boolMode()]),advanced('nonmanifold','非流形布尔',[boolMode()]),advanced('with_curves','布尔与交线编号',[boolMode()]),
 advanced('merge_many','多体布尔',[boolMode(booleanOptions.filter(o=>o[0]!=='xor'))],2,64),
 advanced('lists','两组实体布尔',[boolMode([...booleanOptions.filter(o=>o[0]!=='merge'),['reverse_difference','第二组减第一组']]),f('split','第一组对象数量',1)],2,64),
 advanced('trees','CSG 表达式',[f('tokens','后缀表达式：对象从0编号；-1并/-2交/-3差/-4合并/-5异或',[0,1,-1],'list')],2,64),
 advanced('piecewise','分片合并',[f('newBrepsForFaces','为独立面建立分量',true,'boolean')]),
 project('plane','投影到平面',[planePoint,normal],1),project('silhouette','轮廓线',[normal],1),project('cut','平面切割',[planePoint,normal,f('cap','对原封闭实体的切口封口',true,'boolean')],1),
 project('curve_brep','曲线投影到体',[dir,...sourceEdge]),project('curve_surface','曲线投影到曲面',[face,...sourceEdge]),project('drop_surface','曲线落到曲面',[face,...sourceEdge]),
 project('lift_uv','UV 曲线映射到曲面',[face,...sourceEdge]),project('planar_faces','闭环生成面域',[f('reverseLoops','反转的边界环编号（从1开始）',[],'indices')],1,20),
 project('trim_surface','三维边界裁剪曲面',[face,f('reverseLoops','反转的边界环编号（从1开始）',[],'indices')],2,20),
 project('project_trim','投影并裁剪',[dir,ref,...sourceEdge]),project('parallel_trim','平行投影裁剪',[dir,ref,f('mode','参考点区域处理','keep','choice',[['keep','保留'],['delete','删除'],['split','分割并保留两侧']]),...sourceEdge])
];
export const featureCommand=id=>FEATURE_COMMANDS.find(c=>c.id===id);
export function validateFeatureDefinition(def){
 const cmd=FEATURE_COMMANDS.find(c=>c.action===def.action&&c.kind===def.params?.kind);if(!cmd)throw Error('几何命令类型无效');
 const allowed=new Set(['kind',...cmd.fields.map(f=>f.key)]);
 const finite=v=>typeof v==='number'&&Number.isFinite(v)&&Math.abs(v)<=100000;
 for(const [key,value]of Object.entries(def.params)){if(!allowed.has(key))throw Error('不支持的几何参数');if(key==='kind')continue;const field=cmd.fields.find(f=>f.key===key);if(field.type==='boolean'){if(typeof value!=='boolean')throw Error('参数需要布尔值');}else if(field.type==='index'){if(!Number.isInteger(value)||value<0||value>100000)throw Error('编号无效');}else if(field.type==='choice'){if(typeof value!=='string'||!field.options.some(o=>o[0]===value))throw Error('选项无效');}else if(field.type==='indices'){if(!Array.isArray(value)||value.length>4096||!value.every(v=>Number.isInteger(v)&&v>=0&&v<=100000))throw Error('编号列表无效');}else if(field.type==='number'){if(!finite(value))throw Error('构造参数需要有限数值');}else if(field.type==='vector'||field.type==='uv'){if(!Array.isArray(value)||value.length!==(field.type==='uv'?2:3)||!value.every(finite))throw Error('参数需要 XYZ 向量');}else if(field.type==='points'){if(!Array.isArray(value)||value.length>4096||value.some(p=>!Array.isArray(p)||p.length!==3||!p.every(finite)))throw Error('控制点格式无效');}else if(!Array.isArray(value)||value.length>4096||!value.every(finite))throw Error('数值列表无效');}
}
