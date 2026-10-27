import xml.etree.ElementTree as ET
import html

def create_element(tag, tree_parent=None, **attribs):
    elem = ET.Element(tag, attribs)
    if tree_parent is not None:
        tree_parent.append(elem)
    return elem

def generate_brepx_architecture_drawio(output_path: str):
    root_file = ET.Element("mxfile", host="drawio", version="26.0.0")
    diagram = create_element("diagram", root_file, id="BrepX-Architecture", name="BrepX 系统整体架构图")
    model = create_element(
        "mxGraphModel", diagram,
        dx="1400", dy="1000", grid="1", gridSize="10",
        guides="1", tooltips="1", connect="1", arrows="1", fold="1",
        page="1", pageScale="1", pageWidth="1320", pageHeight="1220",
        background="#ffffff", math="0", shadow="0"
    )
    root = create_element("root", model)
    create_element("mxCell", root, id="0")
    create_element("mxCell", root, id="1", parent="0")

    cell_id_counter = 2
    def next_id():
        nonlocal cell_id_counter
        cid = str(cell_id_counter)
        cell_id_counter += 1
        return cid

    def add_node(parent_id, value, style, x, y, w, h, node_id=None):
        nid = node_id or next_id()
        cell = create_element(
            "mxCell", root,
            id=nid,
            value=value,
            style=style,
            vertex="1",
            parent=parent_id
        )
        create_element("mxGeometry", cell, x=str(x), y=str(y), width=str(w), height=str(h), **{"as": "geometry"})
        return nid

    def add_edge(source_id, target_id, label="", style=None, edge_id=None, exit_xy=None, entry_xy=None):
        eid = edge_id or next_id()
        default_style = "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#455a64;strokeWidth=1.5;fontFamily=Arial;fontSize=10;fontColor=#37474f;"
        edge_style = style or default_style
        if exit_xy:
            edge_style += f";exitX={exit_xy[0]};exitY={exit_xy[1]};exitDx=0;exitDy=0"
        if entry_xy:
            edge_style += f";entryX={entry_xy[0]};entryY={entry_xy[1]};entryDx=0;entryDy=0"
        cell = create_element(
            "mxCell", root,
            id=eid,
            value=label,
            style=edge_style,
            edge="1",
            source=source_id,
            target=target_id,
            parent="1"
        )
        create_element("mxGeometry", cell, relative="1", **{"as": "geometry"})
        return eid

    # ==================== 1. 顶层：前端视口与交互层 ====================
    c_fe = add_node(
        "1", "前端客户端与视口交互层 (Client Viewport &amp; Interaction Tier)",
        "swimlane;startSize=28;fontFamily=Arial;fontSize=13;fontStyle=1;fillColor=#e3f2fd;strokeColor=#1565c0;collapsible=0;container=1;whiteSpace=wrap;html=1;",
        40, 40, 1240, 240
    )

    # 1.1 UI Shell
    add_node(
        c_fe, "<b>UI Shell 外壳与状态栏</b><br/><font color='#546e7a'>• 顶部工具栏 (模式/视图/快照)<br/>• 左侧 T-Panel (图元/草图/特征)<br/>• 底部模态状态 HUD<br/>• 右侧 Agent 抽屉与代码编辑器</font>",
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#1565c0;fontFamily=Arial;fontSize=11;align=left;spacingLeft=8;",
        20, 40, 250, 90, "node_ui_shell"
    )

    # 1.2 CADContext 状态总线
    add_node(
        c_fe, "<b>CADContext 响应式状态总线</b><br/><font color='#546e7a'>• Mode: OBJECT / EDIT<br/>• Selection Level: 面 / 边 / 点<br/>• Active Selection 拓扑表达式<br/>• Event Bus (scene:updated, sel:change)</font>",
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#e1f5fe;strokeColor=#0288d1;fontFamily=Arial;fontSize=11;align=left;spacingLeft=8;",
        300, 40, 270, 90, "node_cad_context"
    )

    # 1.3 Three.js 视口渲染引擎
    add_node(
        c_fe, "<b>Three.js 真实 B-Rep 视口渲染引擎</b><br/><font color='#546e7a'>• 独立 Face Meshes (face_index 拓扑映射)<br/>• 独立 Edge Polylines (接缝线过滤)<br/>• 独立 Vertex 点集渲染<br/>• 显存生命周期回收 (.dispose())</font>",
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#1565c0;fontFamily=Arial;fontSize=11;align=left;spacingLeft=8;",
        600, 40, 310, 90, "node_viewport_engine"
    )

    # 1.4 交互子模块群
    add_node(
        c_fe, "<b>Selection 拓扑拾取</b><br/><font color='#546e7a'>Raycasting 射线拾取<br/>Face/Edge/Vertex 预高亮<br/>Shift 累加多选</font>",
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#f3e5f5;strokeColor=#7b1fa2;fontFamily=Arial;fontSize=10;align=center;",
        20, 150, 200, 75, "node_selection"
    )

    add_node(
        c_fe, "<b>ModalOps 模态操作符</b><br/><font color='#546e7a'>E 面拉伸 / Ctrl+B 边倒角<br/>G/R/S 空间变换手柄<br/>Adjust Last (F9) 参数微调</font>",
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#f3e5f5;strokeColor=#7b1fa2;fontFamily=Arial;fontSize=10;align=center;",
        240, 150, 230, 75, "node_modal_ops"
    )

    add_node(
        c_fe, "<b>Sketcher 交互式草图</b><br/><font color='#546e7a'>工作平面/面基准对齐<br/>直线/矩形/圆/弧线绘制<br/>草图实时几何投影</font>",
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#f3e5f5;strokeColor=#7b1fa2;fontFamily=Arial;fontSize=10;align=center;",
        490, 150, 220, 75, "node_sketcher"
    )

    add_node(
        c_fe, "<b>Boundary 物理边界着色</b><br/><font color='#546e7a'>Inlet/Outlet/Wall 识别<br/>物理补丁实时着色<br/>CFD 边界浮动标签分配</font>",
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#fff9c4;strokeColor=#f57c00;fontFamily=Arial;fontSize=10;align=center;",
        730, 150, 230, 75, "node_boundary_ui"
    )

    add_node(
        c_fe, "<b>Agent 交互抽屉面板</b><br/><font color='#546e7a'>自然语言对话流<br/>选区胶囊实时同步<br/>流体设计意图转译</font>",
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#fff3e0;strokeColor=#e65100;fontFamily=Arial;fontSize=10;align=center;",
        980, 40, 240, 185, "node_agent_panel"
    )

    # ==================== 2. 通信网关层 ====================
    c_gw = add_node(
        "1", "通信与路由网关层 (FastAPI REST API Gateway)",
        "swimlane;startSize=28;fontFamily=Arial;fontSize=13;fontStyle=1;fillColor=#eceff1;strokeColor=#455a64;collapsible=0;container=1;whiteSpace=wrap;html=1;",
        40, 310, 1240, 100
    )

    add_node(
        c_gw, "<b>工作区与算子路由</b><br/><font color='#37474f'>/api/workspace/state<br/>/api/workspace/execute_operator<br/>/api/workspace/adjust_last<br/>/api/workspace/undo | redo</font>",
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#455a64;fontFamily=Arial;fontSize=10;align=center;",
        20, 35, 270, 55, "node_gw_workspace"
    )

    add_node(
        c_gw, "<b>具身 Agent 交互路由</b><br/><font color='#37474f'>/api/agent/chat<br/>• 选区与历史上下文注入<br/>• 自动化纠错重试机制</font>",
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#455a64;fontFamily=Arial;fontSize=10;align=center;",
        320, 35, 270, 55, "node_gw_agent"
    )

    add_node(
        c_gw, "<b>CFD 物理语义路由</b><br/><font color='#37474f'>/api/semantic/patches<br/>/api/semantic/assign<br/>/api/semantic/remove</font>",
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#455a64;fontFamily=Arial;fontSize=10;align=center;",
        620, 35, 270, 55, "node_gw_semantic"
    )

    add_node(
        c_gw, "<b>工程标准导出路由</b><br/><font color='#37474f'>/api/export/step (AP242)<br/>/api/export/cfd_meta<br/>/api/export/stl | gltf | py</font>",
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#455a64;fontFamily=Arial;fontSize=10;align=center;",
        920, 35, 290, 55, "node_gw_export"
    )

    # ==================== 3. 核心后端与建模工作区层 ====================
    c_be = add_node(
        "1", "后端核心建模与工作区引擎 (Backend Core Modeling &amp; Workspace Engine)",
        "swimlane;startSize=28;fontFamily=Arial;fontSize=13;fontStyle=1;fillColor=#f1f8e9;strokeColor=#2e7d32;collapsible=0;container=1;whiteSpace=wrap;html=1;",
        40, 440, 1240, 330
    )

    # 3.1 WorkspaceSession
    add_node(
        c_be, "<b>WorkspaceSession 统一工作区中枢</b><br/><font color='#33691e'>• <b>持久化 Python 命名空间</b>: 持有当前主几何实体 (part)<br/>• <b>AST 安全沙盒审计</b>: 限制模块白名单，拦截危险内置函数与系统调用<br/>• <b>无损撤销重做栈</b>: HistoryStep 快照链、Undo/Redo 状态同步<br/>• <b>Adjust Last 操作重放</b>: 原地参数更新并重新执行最后算子<br/>• <b>代码即原始定义 (Code-as-Original)</b>: 增量生成纯净可复现的 Python 脚本</font>",
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#2e7d32;fontFamily=Arial;fontSize=11;align=left;spacingLeft=8;",
        20, 40, 570, 130, "node_workspace_session"
    )

    # 3.2 算子库
    add_node(
        c_be, "<b>operators.py 选区敏感几何算子库</b><br/><font color='#33691e'>• <b>解析图元与样板</b>: Box, Cylinder, Sphere, Flange...<br/>• <b>草图成型算子</b>: Extrude (拉伸/开槽), Revolve, Sweep, Loft<br/>• <b>拓扑特征算子</b>: Fillet (倒圆角), Chamfer (倒角), Hole, Shell, Draft<br/>• <b>布尔与变换</b>: Union, Difference, Intersection, Split, Mirror, Array<br/>• <b>CFD 直接建模与去特征</b>: remove_fillets (去圆角), remove_faces (填平愈合), cavity_extraction (水密流道提取), heal (拓扑修复)</font>",
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#2e7d32;fontFamily=Arial;fontSize=11;align=left;spacingLeft=8;",
        20, 185, 570, 130, "node_operators"
    )

    # 3.3 具身 Agent 引擎
    add_node(
        c_be, "<b>agent_engine.py 具身 CAD/CFD Agent</b><br/><font color='#e65100'>• <b>实时视口选区感知</b>: 解析注入当前选中面/边表达式 (如 part.faces()[j])<br/>• <b>smlibpy.mcp.discovery RAG</b>: 动态检索 SMLib 原生 API 签名与设计用法<br/>• <b>LocalEmbodiedResolver</b>: 针对打孔、拉伸、倒角、流道抽取的离线零延迟解析<br/>• <b>LLM 云端智能协同</b>: 支持 DeepSeek / OpenAI / Ollama 协议<br/>• <b>闭环自愈重试</b>: 捕获内核异常 Traceback，驱动模型自动修正重试</font>",
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#e65100;fontFamily=Arial;fontSize=11;align=left;spacingLeft=8;",
        610, 40, 600, 130, "node_agent_engine"
    )

    # 3.4 物理语义管理器
    add_node(
        c_be, "<b>semantic_patches.py CFD 物理边界语义管理</b><br/><font color='#e65100'>• <b>物理边界分类</b>: Inlet (入口), Outlet (出口), Wall (壁面), Symmetry (对称), Interface (交界), Internal (内流道)<br/>• <b>几何指纹跟踪</b>: 记录面积、中心坐标、法向向量、曲面几何类型 (geom_type)<br/>• <b>拓扑重绑定算法</b>: 几何体参数变化导致 face_index 变化时，按几何指纹最接近原则自动重新关联<br/>• <b>标准属性生成</b>: 面向 STEP AP242 属性写入与 OpenFOAM 边界字典序列化</font>",
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#e65100;fontFamily=Arial;fontSize=11;align=left;spacingLeft=8;",
        610, 185, 600, 130, "node_semantic_patches"
    )

    # ==================== 4. 拓扑图形序列化管线 ====================
    c_pipe = add_node(
        "1", "真实 B-Rep 拓扑图形序列化管线 (brep_graphic.py)",
        "swimlane;startSize=28;fontFamily=Arial;fontSize=13;fontStyle=1;fillColor=#e0f2f1;strokeColor=#00796b;collapsible=0;container=1;whiteSpace=wrap;html=1;",
        40, 795, 1240, 130
    )

    add_node(
        c_pipe, "<b>独立面网格 (Face Meshes)</b><br/><font color='#004d40'>• 严格保留 face_index 对应 part.faces()[j]<br/>• 解析几何元数据 (类型/法向/中心/面积/曲率半径)<br/>• 高保真三角网格顶点与法向离散</font>",
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#00796b;fontFamily=Arial;fontSize=10;align=left;spacingLeft=6;",
        20, 35, 360, 80, "node_pipe_face"
    )

    add_node(
        c_pipe, "<b>独立边折线 (Edge Polylines)</b><br/><font color='#004d40'>• 严格保留 edge_index 对应 part.edges()[n]<br/>• 直线、圆弧、高阶 NURBS 样条曲线采样<br/>• 自动识别并过滤圆柱/环体假特征接缝线 (Seam Edges)</font>",
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#00796b;fontFamily=Arial;fontSize=10;align=left;spacingLeft=6;",
        410, 35, 410, 80, "node_pipe_edge"
    )

    add_node(
        c_pipe, "<b>独立拓扑顶点 (Vertex Points)</b><br/><font color='#004d40'>• 严格保留 vertex_index 对应 part.vertices()[k]<br/>• 精确三维坐标几何点集采样<br/>• 供前端测量与捕捉辅助</font>",
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#00796b;fontFamily=Arial;fontSize=10;align=left;spacingLeft=6;",
        850, 35, 360, 80, "node_pipe_vertex"
    )

    # ==================== 5. 底层工业几何内核与工程标准交付 ====================
    c_core = add_node(
        "1", "底层工业几何内核与工业物理标准交付 (Geometry Kernel &amp; Engineering Deliverables)",
        "swimlane;startSize=28;fontFamily=Arial;fontSize=13;fontStyle=1;fillColor=#fffde7;strokeColor=#fbc02d;collapsible=0;container=1;whiteSpace=wrap;html=1;",
        40, 950, 1240, 140
    )

    add_node(
        c_core, "<b>SMLib NURBS C++ Kernel (smlibpy 0.4.0)</b><br/><font color='#f57f17'>• <b>B-Rep 真实拓扑结构</b>: Part, Shell, Face, Wire, Edge, Vertex, Sketch<br/>• <b>高精度几何算法</b>: NURBS 曲面构建、连续性倒圆角、修剪曲面布尔运算<br/>• <b>工业内核三角化引擎</b>: C++ 级边界网格划分与离散曲率控制</font>",
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#fbc02d;fontFamily=Arial;fontSize=11;align=left;spacingLeft=8;",
        20, 35, 570, 90, "node_smlib_kernel"
    )

    add_node(
        c_core, "<b>工业标准与 CFD 仿真全栈交付</b><br/><font color='#f57f17'>• <b>STEP AP242 标准文件</b>: 携带面级装配与物理边界属性 (Inlet/Outlet/Wall)<br/>• <b>OpenFOAM 仿真边界字典</b>: 导出零网格歧义的边界条件配置<br/>• <b>工程三维资产</b>: 高精度 STL 流体域表面网格、glTF 实时预览模型</font>",
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#fbc02d;fontFamily=Arial;fontSize=11;align=left;spacingLeft=8;",
        610, 35, 600, 90, "node_engineering_delivery"
    )

    # ==================== 6. 核心数据流连线 (Edges) ====================
    # 交互 -> 网关
    add_edge("node_modal_ops", "node_gw_workspace", "确认操作 (operator, params, selections)", exit_xy=(0.5, 1.0), entry_xy=(0.2, 0.0))
    add_edge("node_agent_panel", "node_gw_agent", "意图提示词 + 视口选区", exit_xy=(0.5, 1.0), entry_xy=(0.5, 0.0))
    add_edge("node_boundary_ui", "node_gw_semantic", "边界补丁分配 (face_indices, type)", exit_xy=(0.5, 1.0), entry_xy=(0.5, 0.0))

    # 网关 -> 后端工作区与引擎
    add_edge("node_gw_workspace", "node_operators", "分发算子参数构建代码", exit_xy=(0.3, 1.0), entry_xy=(0.2, 0.0))
    add_edge("node_operators", "node_workspace_session", "返回 Python 执行代码与标签", exit_xy=(0.5, 0.0), entry_xy=(0.5, 1.0))
    add_edge("node_gw_agent", "node_agent_engine", "自然语言转译与调用", exit_xy=(0.5, 1.0), entry_xy=(0.5, 0.0))
    add_edge("node_agent_engine", "node_workspace_session", "提交增量建模代码与执行", exit_xy=(0.0, 0.5), entry_xy=(1.0, 0.5))
    add_edge("node_gw_semantic", "node_semantic_patches", "更新/重绑定边界补丁", exit_xy=(0.5, 1.0), entry_xy=(0.5, 0.0))

    # 工作区与内核
    add_edge("node_workspace_session", "node_smlib_kernel", "Python AST 沙盒执行驱动 SMLib 内核", exit_xy=(0.3, 1.0), entry_xy=(0.3, 0.0))
    add_edge("node_smlib_kernel", "node_pipe_face", "传递生成好的 Part / Shell 拓扑实体", exit_xy=(0.1, 0.0), entry_xy=(0.1, 1.0))

    # 图形管线 -> 视口
    add_edge("node_pipe_edge", "node_viewport_engine", "结构化 B-Rep 场景数据包 (Face/Edge/Vertex 独立缓冲)", exit_xy=(0.5, 0.0), entry_xy=(0.5, 1.0))
    add_edge("node_viewport_engine", "node_cad_context", "拾取命中事件与拓扑序号同步", exit_xy=(0.0, 0.5), entry_xy=(1.0, 0.5))
    add_edge("node_cad_context", "node_selection", "分发拓扑选区更新", exit_xy=(0.1, 1.0), entry_xy=(0.5, 0.0))
    add_edge("node_cad_context", "node_agent_panel", "选区表达式注入 Agent 上下文", exit_xy=(1.0, 0.2), entry_xy=(0.0, 0.2))

    # 导出与交付
    add_edge("node_semantic_patches", "node_engineering_delivery", "注入几何指纹与边界语义元数据", exit_xy=(0.5, 1.0), entry_xy=(0.5, 0.0))
    add_edge("node_gw_export", "node_engineering_delivery", "触发工业标准 STEP AP242 / CFD 文件生成", exit_xy=(0.5, 1.0), entry_xy=(0.8, 0.0))

    tree = ET.ElementTree(root_file)
    ET.indent(tree, space="  ", level=0)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)

if __name__ == "__main__":
    generate_brepx_architecture_drawio("architecture.drawio")
    print("architecture.drawio generated successfully.")
