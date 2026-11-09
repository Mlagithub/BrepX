/**
 * Left sidebar CAD modeling toolbar (T-Panel) categorizing all 31 industrial operators.
 */

import { runOperator } from './operator_runner.js';
import { OPERATOR_METADATA } from './operator_meta.js';
import { CAD_ICONS } from './cad_icons.js';

const SHORT_NAMES = {
  box: '长方体',
  cylinder: '圆柱体',
  sphere: '球体',
  cone: '圆台/锥',
  torus: '圆环体',
  wedge: '楔形体',
  extrude: '拉伸',
  hole: '打孔',
  fillet: '圆角',
  chamfer: '倒角',
  shell: '抽壳',
  revolve: '回转',
  sweep: '扫掠',
  loft: '放样',
  draft: '拔模',
  offset: '偏移',
  boolean_cut: '差集',
  boolean_join: '求并',
  boolean_intersect: '相交',
  mirror: '镜像',
  polar_array: '环形阵列',
  grid_array: '矩形阵列',
  translate: '平移',
  rotate: '旋转',
  scale: '缩放',
  section: '截面剖线',
  split: '剖切开模',
  blade_runner: '叶轮',
  volute: '螺旋蜗壳',
  cavity_extraction: '流道提取',
  remove_fillets: '消除圆角',
  remove_faces: '填平孔洞',
  heal: '拓扑缝合',
};

export function renderToolbar(containerEl) {
  if (!containerEl) return;
  containerEl.innerHTML = '';

  const titleEl = document.createElement('div');
  titleEl.className = 'panel-section-title';
  titleEl.innerHTML = `
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:5px; vertical-align:middle;"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
    建模算子工具箱 (T-Panel)
  `;
  containerEl.appendChild(titleEl);

  const categories = [
    { key: 'primitive', label: '3D 基础图元', ops: ['box', 'cylinder', 'sphere', 'cone', 'torus', 'wedge'] },
    { key: 'feature', label: '特征成型与加工', ops: ['extrude', 'hole', 'fillet', 'chamfer', 'shell'] },
    { key: 'surface', label: '高阶曲面造型', ops: ['revolve', 'sweep', 'loft', 'draft', 'offset'] },
    { key: 'pattern', label: '空间变换与布尔阵列', ops: ['boolean_cut', 'boolean_join', 'boolean_intersect', 'mirror', 'polar_array', 'grid_array', 'translate', 'rotate', 'scale', 'section', 'split'] },
    { key: 'turbomachinery', label: '流体机械核心', ops: ['blade_runner', 'volute'] },
    { key: 'cfd', label: 'CFD 几何清洗与修面', ops: ['cavity_extraction', 'remove_fillets', 'remove_faces', 'heal'] },
  ];

  categories.forEach((cat) => {
    const catWrap = document.createElement('div');
    catWrap.className = 'toolbar-category';

    const catLabel = document.createElement('div');
    catLabel.className = 'cat-label';
    catLabel.textContent = cat.label;
    catWrap.appendChild(catLabel);

    const catGrid = document.createElement('div');
    catGrid.className = 'cat-grid';

    cat.ops.forEach((opName) => {
      const meta = OPERATOR_METADATA[opName];
      if (!meta) return;

      const chip = document.createElement('button');
      chip.className = 'tool-chip';
      chip.dataset.op = opName;
      chip.title = `${meta.title}: ${meta.doc}`;

      const iconSvg = CAD_ICONS[opName] || '';
      const shortName = SHORT_NAMES[opName] || meta.title.split(' ')[0];
      const shortcutMatch = meta.title.match(/\[(.*?)\]/);
      const shortcutHtml = shortcutMatch ? `<span class="tool-shortcut">${shortcutMatch[1]}</span>` : '';

      chip.innerHTML = `
        ${iconSvg}
        <span class="tool-name">${shortName}</span>
        ${shortcutHtml}
      `;

      chip.onclick = () => {
        runOperator(opName);
      };
      catGrid.appendChild(chip);
    });

    catWrap.appendChild(catGrid);
    containerEl.appendChild(catWrap);
  });
}
