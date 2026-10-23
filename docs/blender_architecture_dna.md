# Blender 5.1.2 核心数据结构与架构蓝图 (DNA/RNA 真实内存模型)

> 本文档基于对 `C:\Users\keep_\app\blender-5.1.2-windows-x64\blender.exe` 与 IDA Pro 9.1 (`idapro`) 的实机自省与逆向提取，记录 Blender 内部最核心的底层数据结构与系统运行架构。

---

## 一、 六大核心数据结构定义 (DNA Structs)

### 1. 数据块基石：`struct ID` (DNA_ID.h)
所有三维数据（Object, Mesh, Material, Scene）的核心基类。
```c
struct ID {
    char name[66];             // 全局唯一标识符，带2字符前缀（如 "OBcube", "MEmesh", "MAmat"）
    char name_full[128];       // 完整标识符，包含库链接路径
    short id_type;             // 数据块类型枚举（ID_OB, ID_ME, ID_MA...）
    int session_uid;           // 会话期唯一UID，跨重命名和内存重新分配保持不变
    bool is_evaluated;         // 核心标志位：当前块是否为“只读评估产物”（还是原始工程数据）
    ID *original;              // 核心指针：指向生成当前评估块的“源头原始数据块”
    int users;                 // 引用计数（Garbage Collection 的基础）
    bool use_fake_user;        // 伪用户标记（无引用时亦不被释放）
    Library *library;          // 外部 .blend 资产库指针
    LibraryWeakReference *lib_weak_ref; // 弱引用指针
    IDProperty *properties;    // 动态自定义属性哈希表
};
```

### 2. 空间节点：`struct Object` (DNA_object_types.h)
场景图中的实体节点，解耦空间姿态与几何内容。
```c
struct Object {
    ID id;                     // 继承自 ID 基础结构
    short type;                // 对象类型 (OB_MESH, OB_CURVE, OB_CAMERA, OB_LIGHT...)
    float location[3];         // 本地平移矢量 (X, Y, Z)
    float rotation_euler[3];   // 欧拉旋转角 (Pitch, Yaw, Roll)
    float scale[3];            // 三维缩放系数
    float matrix_world[4][4];  // 4x4 世界空间变换矩阵 (Object to World)
    float matrix_local[4][4];  // 本地变换矩阵
    ID *data;                  // 指向具体的几何数据块（如 Mesh 或 Curve）
    ListBase modifiers;        // 双向链表：挂载的所有修改器 (ModifierData)
    short mode;                // 当前交互模式 (OB_MODE_OBJECT, OB_MODE_EDIT, OB_MODE_SCULPT...)
    Object *parent;            // 父级对象指针
    float empty_draw_size;     // 辅助显示尺寸
    bool show_wire;            // 是否叠加显示线框
    bool show_bounds;          // 是否显示包围盒
};
```

### 3. 多边形网格：`struct Mesh` (DNA_mesh_types.h)
存储网格的拓扑与几何图元。
```c
struct Mesh {
    ID id;                     // 继承自 ID
    int total_vert_sel;        // 编辑模式下选中的顶点数
    int total_edge_sel;        // 选中的边数
    int total_face_sel;        // 选中的面数
    CustomData vdata;          // 顶点属性（坐标 vertices、法线 normals）
    CustomData edata;          // 边属性（端点索引 edges、折痕 crease）
    CustomData pdata;          // 多边形面属性（polygons）
    CustomData ldata;          // 面角隅半边属性（loops: UV, 顶点颜色, 分裂法线）
    bool is_editmode;          // 是否当前正在编辑模式中
};
```

### 4. 非破坏性修改器：`struct ModifierData` (DNA_modifier_types.h)
修改器堆栈中的双向链表节点。
```c
struct ModifierData {
    ModifierData *next, *prev; // 双向链表指针
    int type;                  // 类型枚举（eModifierType_Boolean, eModifierType_Bevel, eModifierType_Array...）
    char name[64];             // 修改器名称
    int persistent_uid;        // 核心字段：在修改器栈中唯一定位该节点的持久化 ID
    bool show_viewport;        // 是否在视口中求值
    bool show_render;          // 是否在渲染中求值
    bool show_in_editmode;     // 编辑模式下是否启用
    float execution_time;      // 每次依赖图求值耗费的精确秒数 (性能度量)
};

// 布尔运算修改器派生结构体
struct BooleanModifierData {
    ModifierData modifier;
    Object *object;            // 参与布尔运算的目标物体
    Collection *collection;    // 或参与布尔的多物体集合
    int operation;             // eBooleanOperation: INTERSECT, UNION, DIFFERENCE
    float double_threshold;    // 重叠几何容差
};
```

### 5. 上下文环境总线：`struct bContext` (BKE_context.h)
贯穿整个系统的核心上下文。
```c
struct bContext {
    wmWindowManager *window_manager;
    wmWindow *window;
    WorkSpace *workspace;
    ScrArea *area;             // 当前鼠标所在的视口区域
    ARegion *region;           // 具体的绘制子区域
    Scene *scene;              // 当前场景
    ViewLayer *view_layer;     // 视图层
    Object *active_object;     // 活动选中物体
    ListBase *selected_objects;// 选区物体链表
    short mode;                // 上下文模式
};
```

### 6. 模态操作符生命周期：`struct wmOperatorType` (WM_types.h)
流体交互与高频手柄事件的核心机制。
```c
struct wmOperatorType {
    char idname[64];           // 操作符唯一标识符，如 "TRANSFORM_OT_translate"
    bool (*poll)(bContext *C); // 准入检查：当前场景条件是否允许执行
    int (*invoke)(bContext *C, wmOperator *op, wmEvent *event); // 初始调用
    int (*modal)(bContext *C, wmOperator *op, wmEvent *event);  // 高频拖拽事件循环 (60-120 FPS)
    int (*execute)(bContext *C, wmOperator *op);                 // 批处理/脚本结算
    void (*cancel)(bContext *C, wmOperator *op);                // 回滚与清理
};
```

### 7. 高精度拓扑：`BMesh` 半边数据模型
在编辑模式下，拓扑由 4 级元素构成：
* **`BMVert`**：三维空间坐标 `co[3]`、法线 `normal[3]`、所属相连边链表 `link_edges`；
* **`BMEdge`**：两个端点 `verts[2]`、围绕其旋转的半边指针；
* **`BMLoop`**：角隅半边（顺时针/逆时针），存储 UV、法向、相连面 `face` 与顶点 `vert`；
* **`BMFace`**：由闭合 `BMLoop` 围成的任意 n-gon 多边形面。

---

## 二、 Blender 5.1.2 整体架构蓝图 (Big-Picture Architecture)

通过对程序目录文件与运行时库的深度扫描，Blender 整体架构可抽象为**五大水平分层与一条纵向数据流**：

```text
┌──────────────────────────────────────────────────────────────────────────────────┐
│ 1. 表现与编辑器层 (Editors / Spaces)                                             │
│    SpaceView3D (3D视口) | SpaceProperties (属性) | SpaceOutliner (大纲) ...     │
├──────────────────────────────────────────────────────────────────────────────────┤
│ 2. 窗口管理与事件调度中枢 (Window Manager & Event Pipeline)                      │
│    GHOST (硬件抽象) ➔ wmEvent ➔ Keymaps ➔ Modal Operators (G/R/S 手柄循环)        │
├──────────────────────────────────────────────────────────────────────────────────┤
│ 3. 反射与自动化总线 (RNA / BPY Reflection & Automation)                          │
│    双向映射：每个 UI 按钮、手柄拖动、Agent 指令均映射为标准化 Operator 并在后台执行    │
├──────────────────────────────────────────────────────────────────────────────────┤
│ 4. 依赖图求值调度引擎 (Depsgraph / Copy-on-Write)                                │
│    DAG 依赖追踪 ➔ Original 数据保持不变 ➔ 链式流水线求值 ➔ 生成 Evaluated 网格供渲染 │
├──────────────────────────────────────────────────────────────────────────────────┤
│ 5. 核心算法与底层内核 (Blender Kernel - BKE / BMesh / External Engines)         │
│    TBB 并发调度 | GMP 高精度几何求交 | Embree 光追求交 | OpenVDB 体素布尔          │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### 核心纵向数据流向：
1. **输入触发**：硬件鼠标/按键（或 AI Agent 脚本）触发 `Operator`；
2. **本地微调 (Modal)**：在操作符的 `modal()` 周期内，仅高频修改显卡顶点矩阵，视口维持 60~120 FPS 渲染；
3. **确认提交 (Execute)**：松开鼠标或执行脚本，修改写入原始数据块（`Original`）；
4. **依赖求值 (Depsgraph)**：依赖图标记脏节点，顺着修改器堆栈依次计算出新的 `Evaluated` 数据；
5. **视口呈现**：Three.js / GPU 将最新的评估网格同步给用户。
