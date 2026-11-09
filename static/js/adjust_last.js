import { fetchScene, updateCommandParams } from './api.js';
import { context } from './context.js';

const adjustLastPanel = document.getElementById('adjust-last-panel');
const adjustLastTitle = document.getElementById('adjust-last-title');
const adjustLastBody = document.getElementById('adjust-last-body');
const adjustLastClose = document.getElementById('adjust-last-close');

let debounceTimer = null;
let currentCommandCache = null;

if (adjustLastClose) {
  adjustLastClose.onclick = () => {
    if (adjustLastPanel) adjustLastPanel.classList.add('hidden');
  };
}

export function renderAdjustLastPanel(cmd) {
  if (!cmd || !adjustLastPanel || !adjustLastBody) return;

  currentCommandCache = JSON.parse(JSON.stringify(cmd));

  if (adjustLastTitle) {
    adjustLastTitle.textContent = `${cmd.op.toUpperCase()}`;
  }
  adjustLastBody.innerHTML = '';

  const params = cmd.params || {};
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

function debouncedTrigger() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(async () => {
    await triggerAdjustLast();
  }, 90);
}

async function triggerAdjustLast() {
  if (!currentCommandCache) return;
  const newParams = {};
  adjustLastBody.querySelectorAll('input.f9-input[data-param-key]').forEach((inp) => {
    const k = inp.dataset.paramKey;
    const val = inp.type === 'number' ? parseFloat(inp.value) : inp.value;
    if (!isNaN(val)) {
      newParams[k] = val;
    }
  });

  try {
    const res = await updateCommandParams(currentCommandCache.command_id, newParams);
    const sceneData = await fetchScene();
    currentCommandCache.params = { ...currentCommandCache.params, ...newParams };
    if (res.journal) context.setJournal(res.journal);
    context.setSnapshot(res.version, res.body, sceneData);
    context.setLastCommand(currentCommandCache);
  } catch (err) {
    console.warn("微调参数执行受限:", err.message);
  }
}
