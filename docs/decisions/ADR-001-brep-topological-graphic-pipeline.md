# ADR-001: 采用真实 B-Rep 拓扑级图形容器协议替代合并 glTF 网格传输

## Status
Accepted

## Date
2026-10-23

## Context
在 CAD 与 CFD 仿真前处理工作台中，工程师与 AI Agent 的核心操作高度依赖精确的 **B-Rep 拓扑元素拾取**（例如：选中整个法兰盘顶面以拉伸凸台、选中圆柱通孔的圆弧边缘以施加 R3 圆角、选中管道入口截面以标记 `Inlet` 物理边界）。

早期原型采用 `part.export("model.gltf")` 配合前端 `THREE.GLTFLoader` 渲染。这种方式存在致命的架构缺陷：
1. **拓扑身份丢失**：`gltf` 导出器将实体的所有表面合并为单一的三角网格（Indexed Triangle Mesh），前端 Three.js `Raycaster` 命中的 `hit.faceIndex` 仅仅是**单个三角面片 (Triangle)** 的序号，而非 CAD 内核中的真实拓扑面 `part.faces()[j]`；
2. **特征边无法独立拾取**：`THREE.EdgesGeometry(geometry, thresholdAngle)` 基于法向夹角阈值近似生成轮廓线，不仅丢失了圆弧/样条边的精确拓扑索引 `part.edges()[n]`，也无法让用户选中某一条特定边传给后端执行 `part.fillet([part.edges()[n]], r)`；
3. **几何解析属性缺失**：三角网格无法携带底层 NURBS/解析曲面的真实数学参数（如圆柱面的轴线与精确半径、平面的精确法向、圆弧边的圆心）。

## Decision
弃用 `GLTFLoader` 作为主视口的交互式渲染载体，改为在 `backend/brep_graphic.py` 中直接基于 `smlibpy` 原生 `face_meshes` 与 `tessellate_boundaries` 构建 **结构化 B-Rep 拓扑图形容器协议 (B-Rep Graphic Container Protocol)**：
1. **按拓扑面 (`Face`) 独立切分网格**：对 `part.faces()` 中的每个面 $j$，使用 `face_meshes(shape, tol, 12.0)` 获取该面的独立顶点与三角形索引，并附带 `face_index: j`、`expr: "{body}.faces()[{j}]"` 以及解析几何元数据（`geom_type: "plane" | "cylinder" | "sphere" | "cone" | "torus" | "nurbs"`、`area`、`center`、`normal`、`radius`）；
2. **按拓扑边 (`Edge`) 独立提取折线**：调用内核 `k.tessellate_boundaries(shape._brep)` 并过滤闭合曲面的接缝边 (`seam_edges`)，使输出的每条折线严格对应 `part.edges()[n]`，附带 `edge_index: n`、`expr: "{body}.edges()[{n}]"`、`length`、`geom_type`、`radius` 及首尾顶点坐标；
3. **按拓扑顶点 (`Vertex`) 独立映射**：输出 `part.vertices()[v]` 的精确三维坐标与 `vertex_index: v`。

## Alternatives Considered

### 方案 A：继续使用 glTF 2.0 并在 `extras` 中塞入三角形到 B-Rep 面的映射表
- **Pros**：复用浏览器端现成的 `GLTFLoader` 解析器。
- **Cons**：`smlibpy` 原生 C++ 的 `export_gltf` 接口并不输出每个三角形所属的 `face_index` 映射表，若在外部二次通过几何距离反推每个三角形属于哪个 B-Rep 面，不仅耗时且在微小圆角交界处极易错配；同时 glTF 对独立拓扑边 (`Edge`) 与解析几何参数仍无原生表达。
- **Rejected**：无法根治拓扑边精确拾取与解析曲面参数传递问题。

### 方案 B：前端直接加载 WebAssembly 几何内核计算并渲染
- **Pros**：无前后端网络传输开销。
- **Cons**：受限于浏览器单线程内存与 WASM 绑定裁剪，许多高阶算子（如多截面放样 `loft`、特征擦除 `remove_fillets`、孔洞缝合 `remove_faces`、钣金展开 `unfold`）以及 Python 生态的 AI Agent 代码直接执行能力无法在受限 WASM 中完整提供。
- **Rejected**：违背本项目“Python `smlibpy` 全功能内核 + Agent 原生驱动”的核心架构定位。

## Consequences
- **正面影响**：
  - 前端 `static/js/viewport.js` 与 `selection.js` 可直接为每个 CAD 拓扑面和特征边绑定精确的 `faceIndex` / `edgeIndex` 与 Python 拓扑表达式；
  - 鼠标悬停或点击时，**整张 CAD 曲面（无论包含多少个三角形）或整条圆弧特征边完整高亮**，支持 `Shift` 键累加多选；
  - 选面拉伸 (`E`)、选边倒圆角 (`Ctrl+B`)、选开口面抽壳 (`shell`)、选孔洞移除 (`remove_faces`) 以及 CFD 表面边界标注 (`Inlet`/`Outlet`) 100% 作用在真实的 B-Rep 拓扑对象上。
- **代价与约束**：
  - 前后端通过 JSON 传输浮点数顶点与索引数组；为控制载荷体积，顶点坐标统一保留 5 位有效数字，法向量保留 4 位有效数字，并在前端切换模型时严格执行 `geometry.dispose()` 释放显存。
