import { ctx } from './context.js';

const adjustLastPanel = document.getElementById('adjust-last-panel');
const adjustLastTitle = document.getElementById('adjust-last-title');
const adjustLastBody = document.getElementById('adjust-last-body');
const adjustLastClose = document.getElementById('adjust-last-close');

let debounceTimer = null;
let currentOpCache = null;

if (adjustLastClose) {
  adjustLastClose.onclick = () => {
    if (adjustLastPanel) adjustLastPanel.classList.add('hidden');
  };
}

/**
 * 渲染左下角操作微调面板并绑定防抖参数调节器
 * @param {Object} lastOp 最近执行的算子元数据与参数对象
 */
export function renderAdjustLastPanel(lastOp) {
  if (!lastOp || !lastOp.operator_id || !adjustLastPanel || !adjustLastBody) return;

  currentOpCache = JSON.parse(JSON.stringify(lastOp));

  if (adjustLastTitle) {
    adjustLastTitle.textContent = `${lastOp.label || lastOp.operator_id}`;
  }
  adjustLastBody.innerHTML = '';

  const params = lastOp.params || {};
  const keys = Object.keys(params);

  if (keys.length === 0) {
    const emptyRow = document.createElement('div');
    emptyRow.className = 'f9-empty-hint';
    emptyRow.textContent = '此操作无外露微调参数';
    adjustLastBody.appendChild(emptyRow);
  } else {
    keys.forEach((key) => {
      const val = params[key];
      const row = document.createElement('div');
      row.className = 'f9-row';

      if (typeof val === 'number') {
        const minVal = val > 0 ? (val < 1 ? 0.05 : 0.5) : -Math.max(100, Math.abs(val) * 2);
        const maxVal = val > 0 ? Math.max(100, val * 3) : 0;
        const stepVal = Math.abs(val) > 20 ? 1 : 0.5;

        row.innerHTML = `
          <div class="f9-label-line">
            <label class="f9-label" for="f9-input-${key}">${key}</label>
            <span class="f9-val-tag" id="f9-val-tag-${key}">${val}</span>
          </div>
          <div class="f9-input-slider-wrap">
            <input type="range" class="f9-slider" id="f9-slider-${key}" data-param-key="${key}" min="${minVal}" max="${maxVal}" step="${stepVal}" value="${val}">
            <div class="f9-num-wrap">
              <button class="f9-step-btn" data-step-dir="-1" data-param-key="${key}" title="减少" aria-label="减少 ${key}">-</button>
              <input type="number" id="f9-input-${key}" class="f9-input" data-param-key="${key}" value="${val}" step="any" aria-label="${key} 数值">
              <button class="f9-step-btn" data-step-dir="1" data-param-key="${key}" title="增加" aria-label="增加 ${key}">+</button>
            </div>
          </div>
        `;

        const numInput = row.querySelector('.f9-input');
        const sliderInput = row.querySelector('.f9-slider');
        const valTag = row.querySelector(`#f9-val-tag-${key}`);

        // 滑块与数值输入框双向同步绑定
        sliderInput.oninput = () => {
          numInput.value = sliderInput.value;
          if (valTag) valTag.textContent = sliderInput.value;
          debouncedTrigger();
        };

        numInput.oninput = () => {
          sliderInput.value = numInput.value;
          if (valTag) valTag.textContent = numInput.value;
          debouncedTrigger();
        };

        row.querySelectorAll('.f9-step-btn').forEach((sbtn) => {
          sbtn.onclick = () => {
            const dir = parseFloat(sbtn.dataset.stepDir) || 1;
            const current = parseFloat(numInput.value) || 0;
            const step = Math.abs(current) >= 10 ? 1 : 0.5;
            const nextVal = Math.round((current + dir * step) * 100) / 100;
            numInput.value = nextVal;
            sliderInput.value = nextVal;
            if (valTag) valTag.textContent = nextVal;
            debouncedTrigger();
          };
        });
      } else if (typeof val === 'string') {
        row.innerHTML = `
          <div class="f9-label-line">
            <label class="f9-label" for="f9-input-${key}">${key}</label>
          </div>
          <input type="text" id="f9-input-${key}" class="f9-input f9-input-full" data-param-key="${key}" value="${val}" aria-label="${key} 文本">
        `;
        const textInput = row.querySelector('.f9-input');
        textInput.oninput = debouncedTrigger;
      }
      adjustLastBody.appendChild(row);
    });
  }

  adjustLastPanel.classList.remove('hidden');
}

/**
 * 防抖调度，将参数变动合并提交至工作区后端
 */
function debouncedTrigger() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(async () => {
    await triggerAdjustLast();
  }, 90);
}

/**
 * 搜集面板中所有微调输入项并向后端发起重放请求
 */
async function triggerAdjustLast() {
  const newParams = {};
  adjustLastBody.querySelectorAll('input.f9-input[data-param-key]').forEach((inp) => {
    const k = inp.dataset.paramKey;
    newParams[k] = inp.type === 'number' ? parseFloat(inp.value) : inp.value;
  });
  try {
    await adjustLastOperation(newParams);
  } catch (err) {
    console.warn("微调参数执行受限:", err.message);
  }
}

/**
 * 向后端工作区提交参数，重放最后一步建模操作
 * @param {Object} newParams 修改后的算子参数字典
 */
export async function adjustLastOperation(newParams) {
  const res = await fetch('/api/workspace/adjust_last', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ params: newParams }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || '微调失败');

  ctx.setSceneData(data.scene);
  ctx.setPatches(data.patches);
  ctx.setLastOperation(data.last_operation);
}
