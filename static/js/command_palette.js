/**
 * Centered Command Palette (Space / F3) for fuzzy searching and executing operators.
 */

import { context } from './context.js';

let paletteEl = null;
let inputEl = null;
let listEl = null;
let isOpen = false;
let selectedIndex = 0;
let filteredItems = [];

const OPERATOR_REGISTRY = [
  { op: 'box', title: '长方体 (Box)', pinyin: 'cft' },
  { op: 'cylinder', title: '圆柱体 (Cylinder)', pinyin: 'yzt' },
  { op: 'sphere', title: '球体 (Sphere)', pinyin: 'qt' },
  { op: 'cone', title: '圆台/圆锥 (Cone)', pinyin: 'yt' },
  { op: 'torus', title: '圆环体 (Torus)', pinyin: 'yht' },
  { op: 'wedge', title: '楔形体 (Wedge)', pinyin: 'xxt' },
  { op: 'extrude', title: '选面拉伸 [E] (Extrude)', pinyin: 'ls' },
  { op: 'revolve', title: '回转成型 (Revolve)', pinyin: 'hz' },
  { op: 'fillet', title: '选边倒圆角 [Ctrl+B] (Fillet)', pinyin: 'yj' },
  { op: 'chamfer', title: '选边倒斜角 (Chamfer)', pinyin: 'dj' },
  { op: 'hole', title: '平面打孔 (Hole)', pinyin: 'dk' },
  { op: 'shell', title: '薄壁抽壳 (Shell)', pinyin: 'ck' },
  { op: 'boolean_cut', title: '布尔差集切削 (Cut)', pinyin: 'be' },
  { op: 'boolean_join', title: '布尔求并融合 (Join)', pinyin: 'be' },
  { op: 'boolean_intersect', title: '布尔相交求重叠 (Intersect)', pinyin: 'be' },
  { op: 'polar_array', title: '环形圆周阵列 (Polar Array)', pinyin: 'zl' },
  { op: 'grid_array', title: '网格矩形阵列 (Grid Array)', pinyin: 'zl' },
  { op: 'volute', title: '离心螺旋蜗壳 (Volute)', pinyin: 'wk' },
  { op: 'blade_runner', title: '参数化叶片叶轮 (Blade Runner)', pinyin: 'yl' },
  { op: 'remove_fillets', title: '一键擦除圆角 (Remove Fillets)', pinyin: 'cy' },
  { op: 'remove_faces', title: '消除孔洞填平 [X] (Remove Faces)', pinyin: 'tp' },
  { op: 'heal', title: '几何拓扑缝合 (Heal)', pinyin: 'fh' },
  { op: 'cavity_extraction', title: '水密内流道提取 (Cavity)', pinyin: 'ld' },
  { op: 'tag_boundary', title: '绑定 CFD 物理边界 (Tag)', pinyin: 'bd' },
];

export function initCommandPalette() {
  ensurePaletteElement();
}

function ensurePaletteElement() {
  if (!paletteEl) {
    paletteEl = document.createElement('div');
    paletteEl.id = 'command-palette-modal';
    paletteEl.className = 'command-palette-backdrop hidden';
    paletteEl.innerHTML = `
      <div class="command-palette-box">
        <div class="palette-input-wrap">
          <span class="palette-search-icon">🔍</span>
          <input type="text" id="palette-search-input" class="palette-search-input" placeholder="输入算子名称或拼音 (如 yl, box)..." />
        </div>
        <div id="palette-result-list" class="palette-result-list"></div>
      </div>
    `;
    document.body.appendChild(paletteEl);

    inputEl = paletteEl.querySelector('#palette-search-input');
    listEl = paletteEl.querySelector('#palette-result-list');

    inputEl.addEventListener('input', () => filterAndRender());
    paletteEl.addEventListener('click', (e) => {
      if (e.target === paletteEl) closeCommandPalette();
    });

    window.addEventListener('keydown', (e) => {
      if (!isOpen) return;
      if (e.key === 'Escape') {
        closeCommandPalette();
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        selectedIndex = (selectedIndex + 1) % Math.max(1, filteredItems.length);
        highlightSelected();
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        selectedIndex = (selectedIndex - 1 + filteredItems.length) % Math.max(1, filteredItems.length);
        highlightSelected();
      } else if (e.key === 'Enter') {
        e.preventDefault();
        executeSelected();
      }
    });
  }
}

export function openCommandPalette() {
  ensurePaletteElement();
  isOpen = true;
  selectedIndex = 0;
  inputEl.value = '';
  paletteEl.classList.remove('hidden');
  inputEl.focus();
  filterAndRender();
}

export function closeCommandPalette() {
  if (paletteEl) {
    paletteEl.classList.add('hidden');
    isOpen = false;
  }
}

function filterAndRender() {
  const query = (inputEl.value || '').trim().toLowerCase();
  filteredItems = OPERATOR_REGISTRY.filter((item) => {
    if (!query) return true;
    return (
      item.op.toLowerCase().includes(query) ||
      item.title.toLowerCase().includes(query) ||
      item.pinyin.toLowerCase().includes(query)
    );
  });

  listEl.innerHTML = '';
  if (!filteredItems.length) {
    listEl.innerHTML = '<div class="palette-empty">未匹配到相关算子</div>';
    return;
  }

  selectedIndex = Math.min(selectedIndex, filteredItems.length - 1);
  filteredItems.forEach((item, idx) => {
    const row = document.createElement('div');
    row.className = `palette-item ${idx === selectedIndex ? 'selected' : ''}`;
    row.innerHTML = `<span class="palette-item-title">${item.title}</span><span class="palette-item-op">${item.op}</span>`;
    row.onclick = () => {
      selectedIndex = idx;
      executeSelected();
    };
    listEl.appendChild(row);
  });
}

function highlightSelected() {
  const rows = listEl.querySelectorAll('.palette-item');
  rows.forEach((r, idx) => {
    r.classList.toggle('selected', idx === selectedIndex);
  });
}

function executeSelected() {
  if (filteredItems[selectedIndex]) {
    const item = filteredItems[selectedIndex];
    closeCommandPalette();
    context.emit('operator:run', { op: item.op });
  }
}

window.addEventListener('keydown', (e) => {
  const tag = (e.target.tagName || '').toLowerCase();
  if (tag === 'input' || tag === 'textarea') return;

  if (e.key === 'F3' || (e.key === ' ' && !e.ctrlKey && !e.shiftKey && !e.altKey)) {
    e.preventDefault();
    openCommandPalette();
  }
});
