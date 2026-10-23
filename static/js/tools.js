export const RIGHT_TOOLS_SCHEMA = {
  'new-feature-graph': {
    title: '草图驱动零件',
    desc: '矩形草图尺寸驱动拉伸，并可选圆柱凸台、贯穿通孔及外角圆角',
    fields: [
      { key: 'length', label: '草图长度 X (mm)', default: 80 },
      { key: 'width', label: '草图宽度 Y (mm)', default: 50 },
      { key: 'height', label: '拉伸高度 Z (mm)', default: 12 },
      { key: 'boss_d', label: '凸台直径 (mm)', default: 24 },
      { key: 'boss_h', label: '凸台高度 (mm)', default: 15 },
      { key: 'hole_d', label: '贯穿孔直径 (mm)', default: 12 },
      { key: 'fillet_r', label: '四角圆角半径 (mm)', default: 6 },
    ]
  },
  'new-parametric-part': {
    title: '带孔圆角板',
    desc: '在 XY 工作平面拉伸矩形板，施加四个竖边圆角与贯穿中心通孔',
    fields: [
      { key: 'length', label: '基板长度 X (mm)', default: 100 },
      { key: 'width', label: '基板宽度 Y (mm)', default: 80 },
      { key: 'thickness', label: '厚度 Z (mm)', default: 12 },
      { key: 'hole_r', label: '中心孔半径 (mm)', default: 15 },
      { key: 'fillet_r', label: '四角圆角半径 (mm)', default: 10 }
    ]
  },
  'box': {
    title: '长方体',
    desc: '创建标准三维对称长方体',
    fields: [
      { key: 'length', label: '长度 X (mm)', default: 60 },
      { key: 'width', label: '宽度 Y (mm)', default: 40 },
      { key: 'height', label: '高度 Z (mm)', default: 20 }
    ]
  },
  'cylinder': {
    title: '圆柱体',
    desc: '沿 Z 轴创建轴对称实体圆柱',
    fields: [
      { key: 'radius', label: '圆柱半径 R (mm)', default: 15 },
      { key: 'height', label: '圆柱高度 H (mm)', default: 40 }
    ]
  },
  'sphere': {
    title: '球体',
    desc: '以原点为球心创建三维球体',
    fields: [
      { key: 'radius', label: '球体半径 R (mm)', default: 25 }
    ]
  },
  'cone': {
    title: '圆锥 / 圆台',
    desc: '创建截面平滑渐变的圆锥台实体',
    fields: [
      { key: 'radius1', label: '底面半径 R1 (mm)', default: 20 },
      { key: 'radius2', label: '顶面半径 R2 (mm)', default: 10 },
      { key: 'height', label: '圆台高度 H (mm)', default: 40 }
    ]
  },
  'torus': {
    title: '圆环体',
    desc: '截面圆绕 Z 轴回转扫掠出的闭合环体',
    fields: [
      { key: 'radius_major', label: '主环半径 R (mm)', default: 30 },
      { key: 'radius_minor', label: '截面半径 r (mm)', default: 8 }
    ]
  },
  'hole': {
    title: '定位孔',
    desc: '在指定平面坐标切削贯穿通孔',
    allowBaseOnCurrent: true,
    fields: [
      { key: 'radius', label: '通孔半径 R (mm)', default: 8 },
      { key: 'depth', label: '切削深度 (mm)', default: 60 },
      { key: 'x', label: '定位 X (mm)', default: 0 },
      { key: 'y', label: '定位 Y (mm)', default: 0 }
    ]
  },
  'boolean-union': {
    title: '布尔并集',
    desc: '将当前模型与工具体合并为一个新实体',
    allowBaseOnCurrent: true,
    fields: [
      { key: 'tool_kind', label: '工具体类型', type: 'select', options: ['cylinder', 'sphere', 'box'], default: 'cylinder' },
      { key: 'tool_r', label: '工具体尺寸/半径 (mm)', default: 15 },
      { key: 'tool_h', label: '工具体高度 (mm)', default: 45 }
    ]
  },
  'boolean-subtract': {
    title: '布尔差集 (切削)',
    desc: '从主体中减去工具体切削',
    allowBaseOnCurrent: true,
    fields: [
      { key: 'tool_kind', label: '切削工具体类型', type: 'select', options: ['cylinder', 'sphere', 'box'], default: 'cylinder' },
      { key: 'tool_r', label: '切削工具半径 (mm)', default: 12 },
      { key: 'tool_h', label: '切削工具高度 (mm)', default: 50 }
    ]
  },
  'boolean-intersection': {
    title: '布尔交集',
    desc: '保留主体与工具体的公共相交区域',
    allowBaseOnCurrent: true,
    fields: [
      { key: 'tool_kind', label: '工具体类型', type: 'select', options: ['sphere', 'cylinder', 'box'], default: 'sphere' },
      { key: 'tool_r', label: '工具体半径 (mm)', default: 25 },
      { key: 'tool_h', label: '工具体高度 (mm)', default: 50 }
    ]
  },
  'boolean': {
    title: '高级布尔运算设置',
    desc: '自由选择布尔运算类型与工具体参数',
    allowBaseOnCurrent: true,
    fields: [
      { key: 'operation', label: '运算类型', type: 'select', options: ['union', 'difference', 'intersection'], default: 'difference' },
      { key: 'tool_kind', label: '工具体类型', type: 'select', options: ['cylinder', 'sphere', 'box'], default: 'cylinder' },
      { key: 'tool_r', label: '工具体半径 (mm)', default: 14 },
      { key: 'tool_h', label: '工具体高度 (mm)', default: 40 }
    ]
  },
  'line': {
    title: '直线轮廓',
    desc: '创建截面线段轮廓并拉伸成体',
    fields: [{ key: 'dim1', label: '线段长度 (mm)', default: 50 }]
  },
  'rectangle': {
    title: '矩形草图轮廓',
    desc: '创建闭合矩形草图并拉伸成体',
    fields: [
      { key: 'dim1', label: '长度 X (mm)', default: 50 },
      { key: 'dim2', label: '宽度 Y (mm)', default: 30 }
    ]
  },
  'circle': {
    title: '圆形草图轮廓',
    desc: '创建圆形草图轮廓并拉伸成体',
    fields: [{ key: 'dim1', label: '圆半径 R (mm)', default: 20 }]
  },
  'arc': {
    title: '圆弧轮廓',
    desc: '创建圆弧草图轮廓并拉伸成体',
    fields: [{ key: 'dim1', label: '圆弧半径 R (mm)', default: 20 }]
  },
  'polyline': {
    title: '折线多边形轮廓',
    desc: '创建多段多边形轮廓并拉伸成体',
    fields: [
      { key: 'dim1', label: '轮廓跨度尺寸 1 (mm)', default: 45 },
      { key: 'dim2', label: '轮廓跨度尺寸 2 (mm)', default: 25 }
    ]
  },
  'bspline': {
    title: '样条曲线轮廓',
    desc: '创建光滑 NURBS 样条曲线并拉伸成体',
    fields: [
      { key: 'dim1', label: '样条跨度 X (mm)', default: 40 },
      { key: 'dim2', label: '样条起伏 Y (mm)', default: 20 }
    ]
  },
  'extrude': {
    title: '草图轮廓拉伸',
    desc: '将二维草图沿指定厚度拉伸成实体',
    fields: [
      { key: 'profile', label: '截面草图形状', type: 'select', options: ['rectangle', 'circle'], default: 'rectangle' },
      { key: 'dim1', label: '长/半径 (mm)', default: 40 },
      { key: 'dim2', label: '宽 (mm)', default: 30 },
      { key: 'height', label: '拉伸高度 (mm)', default: 25 }
    ]
  },
  'revolve': {
    title: '旋转体',
    desc: 'XZ 平面上的截面绕 Z 轴旋转扫描成体',
    fields: [
      { key: 'radius', label: '截面圆半径 R (mm)', default: 10 },
      { key: 'offset_x', label: '旋转轴偏置距离 (mm)', default: 25 },
      { key: 'angle', label: '旋转角度 (°)', default: 360 }
    ]
  },
  'sweep': {
    title: '空间扫掠成体',
    desc: '截面圆沿三维螺旋路径引导扫掠',
    fields: [
      { key: 'radius', label: '截面圆半径 (mm)', default: 4 },
      { key: 'helix_radius', label: '螺旋回转半径 (mm)', default: 25 },
      { key: 'pitch', label: '导程/螺距 (mm)', default: 20 },
      { key: 'height', label: '扫掠总高 (mm)', default: 60 }
    ]
  },
  'loft': {
    title: '多截面放样',
    desc: '两个截面之间进行平滑 NURBS 曲面放样过渡成体',
    fields: [
      { key: 'bottom_radius', label: '底面截面半径 R1 (mm)', default: 25 },
      { key: 'top_radius', label: '顶面截面半径 R2 (mm)', default: 12 },
      { key: 'height', label: '放样高度 H (mm)', default: 40 }
    ]
  },
  'chamfer': {
    title: '特征倒角',
    desc: '对实体垂直特征边切等距倒角',
    allowBaseOnCurrent: true,
    fields: [{ key: 'distance', label: '倒角距离 (mm)', default: 3 }]
  },
  'fillet': {
    title: '倒圆角',
    desc: '对实体特征边缘应用光滑倒圆角',
    allowBaseOnCurrent: true,
    fields: [{ key: 'radius', label: '圆角半径 R (mm)', default: 5 }]
  },
  'shell': {
    title: '薄壁抽壳',
    desc: '指定壁厚对当前实体掏空抽壳',
    allowBaseOnCurrent: true,
    fields: [{ key: 'thickness', label: '薄壁厚度 (mm)', default: 2 }]
  },
  'offset': {
    title: '几何等距偏移',
    desc: '沿法向整体均匀扩展/收缩',
    allowBaseOnCurrent: true,
    fields: [{ key: 'distance', label: '偏移距离 (mm)', default: 5 }]
  },
  'mirror': {
    title: '对称镜像',
    desc: '沿基准平面对称镜像并组合',
    allowBaseOnCurrent: true,
    fields: [{ key: 'plane', label: '镜像基准面', type: 'select', options: ['YZ', 'XZ', 'XY'], default: 'YZ' }]
  },
  'array': {
    title: '网格阵列',
    desc: '沿 X 和 Y 方向矩形阵列排布',
    allowBaseOnCurrent: true,
    fields: [
      { key: 'count_x', label: 'X 方向数量', default: 2 },
      { key: 'step_x', label: 'X 间距 (mm)', default: 35 },
      { key: 'count_y', label: 'Y 方向数量', default: 2 },
      { key: 'step_y', label: 'Y 间距 (mm)', default: 35 }
    ]
  },
  'circular': {
    title: '圆周环形阵列',
    desc: '绕 Z 轴圆周等角度环形阵列复制',
    allowBaseOnCurrent: true,
    fields: [
      { key: 'count', label: '环阵列数量', default: 6 },
      { key: 'radius', label: '分布圆半径 (mm)', default: 30 }
    ]
  },
  'slice': {
    title: '切分剖切',
    desc: '沿平面切分模型保留半侧',
    allowBaseOnCurrent: true,
    fields: []
  },
  'rotate3d': {
    title: '轴旋转变换',
    desc: '绕指定坐标轴旋转模型角度',
    allowBaseOnCurrent: true,
    fields: [
      { key: 'axis', label: '旋转轴', type: 'select', options: ['Z', 'X', 'Y'], default: 'Z' },
      { key: 'angle', label: '旋转角度 (°)', default: 45 }
    ]
  },
  'copy': {
    title: '复制副本',
    desc: '创建实体副本并平移偏移',
    allowBaseOnCurrent: true,
    fields: [
      { key: 'offset_x', label: '平移偏移 X (mm)', default: 50 },
      { key: 'offset_y', label: '平移偏移 Y (mm)', default: 0 }
    ]
  },
  'move': {
    title: '实体平移变换 (Translate)',
    desc: '沿空间 X、Y、Z 轴方向输入位移增量',
    allowBaseOnCurrent: true,
    fields: [
      { key: 'dx', label: '沿 X 轴位移 (mm)', default: 20 },
      { key: 'dy', label: '沿 Y 轴位移 (mm)', default: 0 },
      { key: 'dz', label: '沿 Z 轴位移 (mm)', default: 0 }
    ]
  },
  'rotate': {
    title: '实体轴旋转变换 (Rotate)',
    desc: '选择旋转基准轴向与空间旋转角度',
    allowBaseOnCurrent: true,
    fields: [
      { key: 'axis', label: '旋转轴', type: 'select', options: ['Z', 'X', 'Y'], default: 'Z' },
      { key: 'angle', label: '旋转角度 (°)', default: 45 }
    ]
  },
  'scale': {
    title: '实体等比缩放 (Scale)',
    desc: '输入三维几何等比缩放因子 (大于0)',
    allowBaseOnCurrent: true,
    fields: [
      { key: 'factor', label: '缩放系数 (如 1.5 放大, 0.8 缩小)', default: 1.25 }
    ]
  },
  'remove_fillets': {
    title: '去特征化 (消除圆角)',
    desc: '一键擦除模型上的微小圆角曲面，将相邻平面自动延伸缝合为锐边，防止网格爆炸',
    allowBaseOnCurrent: true,
    fields: []
  },
  'cavity_extraction': {
    title: '内流体域提取 (Cavity)',
    desc: '对机械阀体/管道外壳执行反向包络差集，一键提取封闭水密流体域',
    allowBaseOnCurrent: true,
    fields: []
  }
};

const toolDialog = document.getElementById('tool-dialog');
const toolModalTitle = document.getElementById('tool-modal-title');
const toolModalDesc = document.getElementById('tool-modal-desc');
const toolModalFields = document.getElementById('tool-modal-fields');
const toolModalForm = document.getElementById('tool-modal-form');
const toolModalClose = document.getElementById('tool-modal-close');
const toolModalCancel = document.getElementById('tool-modal-cancel');
const toolBaseOption = document.getElementById('tool-modal-base-option');
const toolBaseCheckbox = document.getElementById('tool-base-on-current');
const toolModalError = document.getElementById('tool-modal-error');
const toolModalSubmit = document.getElementById('tool-modal-submit');

let activeToolKey = null;
let onToolExecuteCallback = null;

export function setToolExecuteCallback(cb) {
  onToolExecuteCallback = cb;
}

export function openToolModal(toolKey) {
  const schema = RIGHT_TOOLS_SCHEMA[toolKey];
  if (!schema) return;

  activeToolKey = toolKey;
  toolModalTitle.textContent = schema.title;
  toolModalDesc.textContent = schema.desc;
  toolModalFields.innerHTML = '';
  if (toolModalError) {
    toolModalError.style.display = 'none';
    toolModalError.textContent = '';
  }

  if (toolBaseOption) {
    toolBaseOption.style.display = schema.allowBaseOnCurrent ? 'block' : 'none';
    if (toolBaseCheckbox) toolBaseCheckbox.checked = false;
  }

  (schema.fields || []).forEach(f => {
    const fDiv = document.createElement('div');
    fDiv.className = 'tool-modal-field';

    if (f.type === 'select') {
      let opts = f.options.map(o => `<option value="${o}" ${o === f.default ? 'selected' : ''}>${o}</option>`).join('');
      fDiv.innerHTML = `
        <label for="tf-${f.key}">${f.label}</label>
        <select id="tf-${f.key}">${opts}</select>
      `;
    } else {
      fDiv.innerHTML = `
        <label for="tf-${f.key}">${f.label}</label>
        <input type="number" id="tf-${f.key}" value="${f.default}" step="any">
      `;
    }
    toolModalFields.appendChild(fDiv);
  });

  toolDialog.classList.remove('hidden');
}

export function closeToolModal() {
  toolDialog.classList.add('hidden');
  activeToolKey = null;
}

if (toolModalClose) toolModalClose.onclick = closeToolModal;
if (toolModalCancel) toolModalCancel.onclick = closeToolModal;

if (toolModalForm) {
  toolModalForm.onsubmit = async (e) => {
    e.preventDefault();
    if (!activeToolKey || !onToolExecuteCallback) return;

    const schema = RIGHT_TOOLS_SCHEMA[activeToolKey];
    const params = {};
    (schema.fields || []).forEach(f => {
      const el = document.getElementById(`tf-${f.key}`);
      if (el) {
        params[f.key] = f.type === 'select' ? el.value : parseFloat(el.value);
      }
    });

    const baseOnCurrent = schema.allowBaseOnCurrent && toolBaseCheckbox ? toolBaseCheckbox.checked : false;

    if (toolModalSubmit) {
      toolModalSubmit.disabled = true;
      toolModalSubmit.textContent = '计算中…';
    }

    try {
      await onToolExecuteCallback(activeToolKey, params, baseOnCurrent, schema);
      closeToolModal();
    } catch (err) {
      if (toolModalError) {
        toolModalError.style.display = 'block';
        toolModalError.textContent = `⚠️ ${err.message}`;
      }
    } finally {
      if (toolModalSubmit) {
        toolModalSubmit.disabled = false;
        toolModalSubmit.textContent = '确定执行';
      }
    }
  };
}
