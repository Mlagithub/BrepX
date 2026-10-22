import * as THREE from 'three';
import { OrbitControls } from 'three/addons/OrbitControls.js';
import { GLTFLoader } from 'three/addons/GLTFLoader.js';

// --- 全局状态与配置 ---
const state = {
  template: 'flange',
  params: {},
  cameraType: 'perspective', // 'perspective' | 'orthographic'
  showGrid: true,
  showAxes: true,
  showEdges: true,
  currentPartGroup: null,
  isBuilding: false,
};

// 参数定义配置
const TEMPLATE_CONFIGS = {
  flange: {
    name: '带孔圆角板 / 机械法兰',
    params: [
      { key: 'length', label: '基板长度 X (mm)', min: 40, max: 200, step: 2, default: 100 },
      { key: 'width', label: '基板宽度 Y (mm)', min: 30, max: 160, step: 2, default: 80 },
      { key: 'thickness', label: '厚度 Z (mm)', min: 4, max: 50, step: 1, default: 12 },
      { key: 'fillet_r', label: '四角圆角半径 (mm)', min: 0, max: 30, step: 1, default: 10 },
      { key: 'center_hole_r', label: '中心通孔半径 (mm)', min: 0, max: 40, step: 1, default: 15 },
      { key: 'bolt_holes', label: '安装螺栓孔', type: 'boolean', default: true },
      { key: 'bolt_hole_r', label: '螺栓孔径 (mm)', min: 2, max: 12, step: 0.5, default: 4 },
      { key: 'bolt_offset_x', label: '螺栓 X 偏移 (mm)', min: 10, max: 90, step: 1, default: 35 },
      { key: 'bolt_offset_y', label: '螺栓 Y 偏移 (mm)', min: 10, max: 70, step: 1, default: 25 },
    ]
  },
  bracket: {
    name: 'L型加筋角码 / 结构支架',
    params: [
      { key: 'length', label: '长度 X (mm)', min: 40, max: 150, step: 2, default: 80 },
      { key: 'width', label: '宽度 Y (mm)', min: 30, max: 120, step: 2, default: 50 },
      { key: 'height', label: '高度 Z (mm)', min: 40, max: 150, step: 2, default: 60 },
      { key: 'thickness', label: '壁厚 (mm)', min: 4, max: 25, step: 1, default: 10 },
      { key: 'fillet_r', label: '过渡圆角半径 (mm)', min: 0, max: 15, step: 1, default: 6 },
      { key: 'hole_r', label: '安装孔半径 (mm)', min: 0, max: 15, step: 1, default: 6 },
    ]
  },
  bushing: {
    name: '法兰轴套 / 衬套',
    params: [
      { key: 'od', label: '主体外径 (mm)', min: 20, max: 100, step: 2, default: 40 },
      { key: 'id', label: '内孔直径 (mm)', min: 10, max: 80, step: 2, default: 20 },
      { key: 'length', label: '总长度 (mm)', min: 20, max: 150, step: 2, default: 60 },
      { key: 'flange_od', label: '台阶法兰外径 (mm)', min: 30, max: 140, step: 2, default: 60 },
      { key: 'flange_len', label: '法兰厚度 (mm)', min: 4, max: 30, step: 1, default: 12 },
    ]
  },
  csg_demo: {
    name: '经典 CSG 球芯布尔体',
    params: [
      { key: 'box_size', label: '立方体边长 (mm)', min: 30, max: 120, step: 2, default: 50 },
      { key: 'sphere_r', label: '球体半径 (mm)', min: 20, max: 80, step: 1, default: 32 },
      { key: 'cyl_r', label: '三向贯穿孔半径 (mm)', min: 8, max: 35, step: 1, default: 18 },
    ]
  }
};

// --- Three.js 场景初始化 ---
const container = document.getElementById('viewport');
const width = container.clientWidth;
const height = container.clientHeight;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x1a1d24);

// 相机系统 (支持透视与正交)
const aspect = width / height;
const frustumSize = 160;

const perspCamera = new THREE.PerspectiveCamera(45, aspect, 0.1, 2000);
perspCamera.position.set(120, 100, 140);

const orthoCamera = new THREE.OrthographicCamera(
  -frustumSize * aspect / 2,
  frustumSize * aspect / 2,
  frustumSize / 2,
  -frustumSize / 2,
  0.1,
  2000
);
orthoCamera.position.copy(perspCamera.position);

let activeCamera = perspCamera;

// 渲染器
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: 'high-performance' });
renderer.setSize(width, height);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.1;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
container.appendChild(renderer.domElement);

// 控制器
const controls = new OrbitControls(activeCamera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.target.set(0, 0, 0);

// 光照系统 (专业 CAD 漫反射三点光)
const ambientLight = new THREE.AmbientLight(0xffffff, 0.85);
scene.add(ambientLight);

const dirLight1 = new THREE.DirectionalLight(0xffffff, 1.2);
dirLight1.position.set(150, 200, 150);
scene.add(dirLight1);

const dirLight2 = new THREE.DirectionalLight(0xb0c4de, 0.6);
dirLight2.position.set(-150, -100, -150);
scene.add(dirLight2);

// 网格辅助面
const gridHelper = new THREE.GridHelper(300, 60, 0x3e4451, 0x2c313a);
gridHelper.position.y = -0.1;
scene.add(gridHelper);

// 坐标轴辅助
const axesHelper = new THREE.AxesHelper(50);
axesHelper.material.linewidth = 2;
scene.add(axesHelper);

// 动效循环
function animate() {
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, activeCamera);
}
animate();

// 自适应窗口缩放
window.addEventListener('resize', () => {
  const w = container.clientWidth;
  const h = container.clientHeight;
  const asp = w / h;

  perspCamera.aspect = asp;
  perspCamera.updateProjectionMatrix();

  orthoCamera.left = -frustumSize * asp / 2;
  orthoCamera.right = frustumSize * asp / 2;
  orthoCamera.top = frustumSize / 2;
  orthoCamera.bottom = -frustumSize / 2;
  orthoCamera.updateProjectionMatrix();

  renderer.setSize(w, h);
});

// --- GLTF 加载与 CAD 渲染管线 ---
const gltfLoader = new GLTFLoader();

function renderModelGLTF(gltfContent) {
  gltfLoader.parse(gltfContent, '', (gltf) => {
    // 移除旧几何体
    if (state.currentPartGroup) {
      scene.remove(state.currentPartGroup);
      state.currentPartGroup.traverse((child) => {
        if (child.geometry) child.geometry.dispose();
        if (child.material) {
          if (Array.isArray(child.material)) child.material.forEach(m => m.dispose());
          else child.material.dispose();
        }
      });
      state.currentPartGroup = null;
    }

    const group = gltf.scene;

    // 处理 smlibpy 导出的 0.001 (mm 转米) 缩放，还原为 1:1 真实的 mm 工程尺寸
    group.traverse((child) => {
      if (child.scale && Math.abs(child.scale.x - 0.001) < 0.0001) {
        child.scale.set(1, 1, 1);
      }
    });

    // 统计三角面并增强材质
    let triangleCount = 0;

    group.traverse((child) => {
      if (child.isMesh) {
        triangleCount += child.geometry.index ? child.geometry.index.count / 3 : child.geometry.attributes.position.count / 3;

        // 统一使用高质感天蓝色 CAD 双面光照材质
        child.material = new THREE.MeshStandardMaterial({
          color: 0x80baff,
          metalness: 0.15,
          roughness: 0.4,
          side: THREE.DoubleSide,
          polygonOffset: true,
          polygonOffsetFactor: 1,
          polygonOffsetUnits: 1
        });
        child.castShadow = true;
        child.receiveShadow = true;

        // 生成特征轮廓边线
        if (state.showEdges) {
          const edges = new THREE.EdgesGeometry(child.geometry, 28);
          const lineMaterial = new THREE.LineBasicMaterial({ color: 0x111c2e, linewidth: 2 });
          const lineSegments = new THREE.LineSegments(edges, lineMaterial);
          lineSegments.name = 'cad-edge-line';
          child.add(lineSegments);
        }
      } else if (child.isLineSegments) {
        // smlibpy 原生导出的边线
        child.material = new THREE.LineBasicMaterial({ color: 0x111c2e, linewidth: 2 });
        child.name = 'cad-edge-line';
      }
    });

    document.getElementById('stat-triangles').textContent = Math.round(triangleCount).toLocaleString();

    scene.add(group);
    state.currentPartGroup = group;

    // 将辅助网格对齐到模型底部
    const box = new THREE.Box3().setFromObject(group);
    if (!box.isEmpty()) {
      gridHelper.position.y = box.min.y - 0.2;
    }

    fitCameraToObject(group);
  }, (err) => {
    console.error('Failed to parse glTF:', err);
    showStatus('GLTF 解析失败: ' + err.message, true);
  });
}

function fitCameraToObject(object) {
  const box = new THREE.Box3().setFromObject(object);
  if (box.isEmpty()) return;

  const center = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3());

  const maxDim = Math.max(size.x, size.y, size.z, 20);
  const distance = maxDim * 2.2;

  controls.target.copy(center);

  // 保持当前视角的观察向量，调整距离
  const dir = new THREE.Vector3().subVectors(activeCamera.position, controls.target).normalize();
  if (dir.lengthSq() < 0.001) dir.set(1, 0.8, 1).normalize();

  activeCamera.position.copy(center).addScaledVector(dir, distance);
  activeCamera.near = Math.max(0.5, distance / 200);
  activeCamera.far = Math.max(distance * 30, 8000);

  if (activeCamera.isOrthographicCamera) {
    const asp = container.clientWidth / container.clientHeight;
    activeCamera.left = -maxDim * asp * 1.2;
    activeCamera.right = maxDim * asp * 1.2;
    activeCamera.top = maxDim * 1.2;
    activeCamera.bottom = -maxDim * 1.2;
  }
  activeCamera.updateProjectionMatrix();

  controls.update();
}

// --- 视角控制按钮逻辑 ---
function setStandardView(type) {
  if (!state.currentPartGroup) return;
  const box = new THREE.Box3().setFromObject(state.currentPartGroup);
  const center = box.getCenter(new THREE.Vector3());
  const dist = Math.max(box.getSize(new THREE.Vector3()).length() * 1.5, 80);

  controls.target.copy(center);

  if (type === 'iso') {
    activeCamera.position.set(center.x + dist * 0.7, center.y + dist * 0.6, center.z + dist * 0.7);
  } else if (type === 'front') {
    activeCamera.position.set(center.x, center.y, center.z + dist);
  } else if (type === 'top') {
    activeCamera.position.set(center.x, center.y + dist, center.z);
  } else if (type === 'right') {
    activeCamera.position.set(center.x + dist, center.y, center.z);
  } else if (type === 'fit') {
    fitCameraToObject(state.currentPartGroup);
    return;
  }
  controls.update();
}

document.getElementById('btn-iso').onclick = () => setStandardView('iso');
document.getElementById('btn-front').onclick = () => setStandardView('front');
document.getElementById('btn-top').onclick = () => setStandardView('top');
document.getElementById('btn-right').onclick = () => setStandardView('right');
document.getElementById('btn-fit').onclick = () => setStandardView('fit');

// 正交 / 透视投影切换
document.getElementById('btn-camera-toggle').onclick = (e) => {
  const btn = e.currentTarget;
  if (state.cameraType === 'perspective') {
    state.cameraType = 'orthographic';
    orthoCamera.position.copy(perspCamera.position);
    orthoCamera.quaternion.copy(perspCamera.quaternion);
    controls.object = orthoCamera;
    activeCamera = orthoCamera;
    btn.textContent = '正交';
    btn.classList.add('active');
  } else {
    state.cameraType = 'perspective';
    perspCamera.position.copy(orthoCamera.position);
    perspCamera.quaternion.copy(orthoCamera.quaternion);
    controls.object = perspCamera;
    activeCamera = perspCamera;
    btn.textContent = '透视';
    btn.classList.remove('active');
  }
  controls.update();
};

// 网格 / 坐标轴 / 边线 开关
document.getElementById('btn-grid-toggle').onclick = (e) => {
  state.showGrid = !state.showGrid;
  gridHelper.visible = state.showGrid;
  e.currentTarget.classList.toggle('active', state.showGrid);
};

document.getElementById('btn-axes-toggle').onclick = (e) => {
  state.showAxes = !state.showAxes;
  axesHelper.visible = state.showAxes;
  e.currentTarget.classList.toggle('active', state.showAxes);
};

document.getElementById('btn-edges-toggle').onclick = (e) => {
  state.showEdges = !state.showEdges;
  e.currentTarget.classList.toggle('active', state.showEdges);
  if (state.currentPartGroup) {
    state.currentPartGroup.traverse((child) => {
      if (child.name === 'cad-edge-line') child.visible = state.showEdges;
    });
  }
};

// --- 参数化表单与后端交互 ---
const templateSelect = document.getElementById('template-select');
const paramForm = document.getElementById('parametric-form');
const scriptEditor = document.getElementById('script-editor');
const loadingOverlay = document.getElementById('loading-overlay');
const loadingMsg = document.getElementById('loading-msg');

function showLoading(msg = '正在调用 SMLib 几何内核计算…') {
  loadingMsg.textContent = msg;
  loadingOverlay.classList.remove('hidden');
}

function hideLoading() {
  loadingOverlay.classList.add('hidden');
}

function showStatus(text, isError = false) {
  const el = document.getElementById('status-text');
  el.textContent = text;
  el.style.color = isError ? '#e06c75' : '';
}

// 渲染参数表单
function renderParamForm(templateKey) {
  const config = TEMPLATE_CONFIGS[templateKey];
  if (!config) return;

  state.template = templateKey;
  state.params = {};
  paramForm.innerHTML = '';

  config.params.forEach((p) => {
    state.params[p.key] = p.default;

    const group = document.createElement('div');
    group.className = 'param-group';

    if (p.type === 'boolean') {
      group.innerHTML = `
        <div class="param-header">
          <label class="param-label" for="param-${p.key}">${p.label}</label>
          <input type="checkbox" id="param-${p.key}" ${p.default ? 'checked' : ''}>
        </div>
      `;
      const checkbox = group.querySelector('input');
      checkbox.onchange = () => {
        state.params[p.key] = checkbox.checked;
        triggerParametricBuild();
      };
    } else {
      group.innerHTML = `
        <div class="param-header">
          <label class="param-label" for="param-${p.key}">${p.label}</label>
          <span class="param-val-preview">${p.default}</span>
        </div>
        <div class="param-inputs">
          <input type="range" class="param-slider" id="slider-${p.key}" min="${p.min}" max="${p.max}" step="${p.step}" value="${p.default}">
          <input type="number" class="param-num" id="num-${p.key}" min="${p.min}" max="${p.max}" step="${p.step}" value="${p.default}">
        </div>
      `;

      const slider = group.querySelector('.param-slider');
      const numInput = group.querySelector('.param-num');
      const preview = group.querySelector('.param-val-preview');

      const updateVal = (val) => {
        state.params[p.key] = parseFloat(val);
        slider.value = val;
        numInput.value = val;
        preview.textContent = val;
      };

      slider.oninput = (e) => {
        updateVal(e.target.value);
        debounceBuild();
      };

      numInput.onchange = (e) => {
        updateVal(e.target.value);
        triggerParametricBuild();
      };
    }

    paramForm.appendChild(group);
  });
}

let debounceTimer = null;
let needRebuild = false;

function debounceBuild() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    triggerParametricBuild();
  }, 120);
}

async function triggerParametricBuild() {
  if (state.isBuilding) {
    needRebuild = true;
    return;
  }
  state.isBuilding = true;
  showLoading('SMLib 正在重构参数化特征…');

  try {
    const res = await fetch('/api/build/parametric', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        template: state.template,
        params: state.params
      })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || '建模错误');

    // 渲染几何
    renderModelGLTF(data.gltf);

    // 同步代码与统计
    scriptEditor.value = data.script;
    document.getElementById('stat-volume').textContent = `${data.stats.volume.toLocaleString()} mm³`;
    document.getElementById('stat-time').textContent = `${data.stats.compute_ms} ms`;
    showStatus(`建模完成 · 体积: ${data.stats.volume} mm³ · 耗时: ${data.stats.compute_ms} ms`);
  } catch (err) {
    showStatus(`构建失败: ${err.message}`, true);
  } finally {
    state.isBuilding = false;
    hideLoading();
    if (needRebuild) {
      needRebuild = false;
      triggerParametricBuild();
    }
  }
}

// 运行自定义脚本
async function runScript() {
  const code = scriptEditor.value.trim();
  if (!code) return;

  showLoading('SMLib 正在执行自定义 Python 脚本…');
  try {
    const res = await fetch('/api/build/script', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ script: code, name: 'custom_part' })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || '执行失败');

    renderModelGLTF(data.gltf);
    document.getElementById('stat-volume').textContent = `${data.stats.volume.toLocaleString()} mm³`;
    document.getElementById('stat-time').textContent = `${data.stats.compute_ms} ms`;
    showStatus(`脚本构建完成 · 体积: ${data.stats.volume} mm³ · 耗时: ${data.stats.compute_ms} ms`);
  } catch (err) {
    alert('脚本执行出错:\n' + err.message);
    showStatus(`执行失败: ${err.message}`, true);
  } finally {
    hideLoading();
  }
}

// 模板选择器事件
templateSelect.onchange = (e) => {
  renderParamForm(e.target.value);
  triggerParametricBuild();
};

document.getElementById('btn-rebuild-param').onclick = () => triggerParametricBuild();
document.getElementById('btn-run-script').onclick = () => runScript();
document.getElementById('btn-format-script').onclick = () => triggerParametricBuild();

// 快捷插入代码片段
document.querySelectorAll('.snip-btn').forEach((btn) => {
  btn.onclick = () => {
    const code = btn.dataset.code;
    const pos = scriptEditor.selectionStart;
    const prev = scriptEditor.value;
    scriptEditor.value = prev.slice(0, pos) + '\n' + code + prev.slice(pos);
    scriptEditor.focus();
  };
});

// 复制代码
document.getElementById('btn-copy-script').onclick = () => {
  navigator.clipboard.writeText(scriptEditor.value).then(() => {
    showStatus('Python 脚本已复制到剪贴板！');
  });
};

// 快捷键支持 (Ctrl + Enter 运行脚本)
window.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    e.preventDefault();
    runScript();
  }
});

// --- Tab 切换 ---
document.querySelectorAll('.tab-btn').forEach((btn) => {
  btn.onclick = () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));

    btn.classList.add('active');
    const tabId = `tab-${btn.dataset.tab}`;
    const pane = document.getElementById(tabId);
    if (pane) pane.classList.add('active');
  };
});

// --- 文件导出绑定 ---
function downloadFile(url) {
  const link = document.createElement('a');
  link.href = url;
  link.download = '';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

document.getElementById('btn-export-step').onclick = () => {
  downloadFile('/api/export/step');
  showStatus('正在生成并下载工业标准 STEP 文件…');
};

document.getElementById('btn-export-stl').onclick = () => {
  downloadFile('/api/export/stl');
  showStatus('正在生成并下载 3D 打印 STL 文件…');
};

document.getElementById('btn-export-gltf').onclick = () => {
  downloadFile('/api/export/gltf');
  showStatus('正在下载 glTF 3D 文件…');
};

document.getElementById('btn-export-py').onclick = () => {
  downloadFile('/api/export/py');
  showStatus('正在下载 Python 独立建模脚本…');
};

// --- AI 对话建模 Agent 前端控制器 ---
const chatMessages = document.getElementById('chat-messages');
const agentInput = document.getElementById('agent-input');
const btnSendAgent = document.getElementById('btn-send-agent');
const btnClearChat = document.getElementById('btn-clear-chat');
const btnToggleLlm = document.getElementById('btn-toggle-llm-settings');
const llmSettingsCard = document.getElementById('llm-settings-panel');

const settingBaseUrl = document.getElementById('setting-base-url');
const settingApiKey = document.getElementById('setting-api-key');
const settingModel = document.getElementById('setting-model');

// 加载持久化的 LLM 设置
const savedLlmConfig = JSON.parse(localStorage.getItem('smlib_llm_config') || '{}');
if (settingBaseUrl) settingBaseUrl.value = savedLlmConfig.baseUrl || '';
if (settingApiKey) settingApiKey.value = savedLlmConfig.apiKey || '';
if (settingModel) settingModel.value = savedLlmConfig.model || '';

function saveLlmConfig() {
  const cfg = {
    baseUrl: settingBaseUrl ? settingBaseUrl.value.trim() : '',
    apiKey: settingApiKey ? settingApiKey.value.trim() : '',
    model: settingModel ? settingModel.value.trim() : '',
  };
  localStorage.setItem('smlib_llm_config', JSON.stringify(cfg));
  return cfg;
}

[settingBaseUrl, settingApiKey, settingModel].forEach(input => {
  if (input) {
    input.onchange = saveLlmConfig;
    input.oninput = saveLlmConfig;
  }
});

// 切换设置面板显示/隐藏
if (btnToggleLlm && llmSettingsCard) {
  btnToggleLlm.onclick = (e) => {
    e.preventDefault();
    llmSettingsCard.classList.toggle('hidden');
  };
}

// 预设切换药丸
document.querySelectorAll('.preset-pill').forEach(pill => {
  pill.onclick = () => {
    if (settingBaseUrl) settingBaseUrl.value = pill.dataset.base || '';
    if (settingModel) settingModel.value = pill.dataset.model || '';
    saveLlmConfig();
  };
});

// 测试大模型连通性
const btnTestLlm = document.getElementById('btn-test-llm');
const llmTestResult = document.getElementById('llm-test-result');
if (btnTestLlm) {
  btnTestLlm.onclick = async () => {
    const cfg = saveLlmConfig();
    if (!cfg.apiKey) {
      llmTestResult.innerHTML = '<span style="color:#e5c07b">⚠️ 请先输入 API Key</span>';
      return;
    }
    btnTestLlm.disabled = true;
    btnTestLlm.textContent = '正在测试连接…';
    llmTestResult.innerHTML = '<span style="color:#abb2bf">正在向大模型接口发送心跳握手…</span>';
    try {
      const res = await fetch('/api/agent/test_llm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cfg)
      });
      const data = await res.json();
      if (data.ok) {
        llmTestResult.innerHTML = `<span style="color:#98c379">✅ 连通成功！模型: ${data.model} · 延时: ${data.latency_ms} ms</span>`;
      } else {
        llmTestResult.innerHTML = `<span style="color:#e06c75">❌ 握手失败: ${escapeHtml(data.error || '未知错误')}</span><br><span style="color:#7f848e;font-size:10px;">目标端点: ${escapeHtml(data.endpoint)}</span>`;
      }
    } catch (err) {
      llmTestResult.innerHTML = `<span style="color:#e06c75">❌ 网络异常: ${escapeHtml(err.message)}</span>`;
    } finally {
      btnTestLlm.disabled = false;
      btnTestLlm.textContent = '🧪 测试 API 连通性';
    }
  };
}

let agentChatHistory = [];

function appendChatBubble(role, content, meta = {}) {
  const bubble = document.createElement('div');
  bubble.className = `chat-bubble ${role}`;

  if (role === 'user') {
    bubble.innerHTML = `<div class="bubble-body">${escapeHtml(content)}</div>`;
  } else {
    let html = `
      <div class="bubble-header">
        <span>🤖 SMLib 建模 Agent</span>
        ${meta.compute_ms ? `<span class="bubble-meta">${meta.compute_ms} ms</span>` : ''}
      </div>
      <div class="bubble-body">${escapeHtml(content).replace(/\n/g, '<br>')}</div>
    `;

    if (meta.code) {
      html += `
        <pre class="bubble-code"><code>${escapeHtml(meta.code)}</code></pre>
        <div class="bubble-actions">
          <button class="btn-text-sm btn-load-editor">在脚本编辑器中查看</button>
        </div>
      `;
    }

    if (meta.error) {
      html += `<div style="color:#e06c75;margin-top:4px;font-size:11px;">⚠️ 执行提示: ${escapeHtml(meta.error)}</div>`;
    }

    bubble.innerHTML = html;

    const btnLoad = bubble.querySelector('.btn-load-editor');
    if (btnLoad) {
      btnLoad.onclick = () => {
        scriptEditor.value = meta.code;
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
        document.querySelector('[data-tab="script"]').classList.add('active');
        document.getElementById('tab-script').classList.add('active');
      };
    }
  }

  chatMessages.appendChild(bubble);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function escapeHtml(str) {
  return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

async function sendAgentMessage(userPrompt) {
  const text = (userPrompt || (agentInput ? agentInput.value : '')).trim();
  if (!text) return;

  if (agentInput) agentInput.value = '';

  // 渲染用户输入
  appendChatBubble('user', text);
  showLoading('SMLib 智能 Agent 正在分析几何特征并编写代码…');

  const cfg = saveLlmConfig();

  try {
    const res = await fetch('/api/agent/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt: text,
        history: agentChatHistory,
        config: cfg
      })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || '请求 Agent 异常');

    // 渲染 Agent 回复
    appendChatBubble('assistant', data.reply, {
      code: data.code,
      compute_ms: data.stats ? data.stats.compute_ms : null,
      error: data.error
    });

    // 记录历史
    agentChatHistory.push({ role: 'user', content: text });
    agentChatHistory.push({ role: 'assistant', content: data.reply, code: data.code });

    // 成功生成模型后立即渲染 3D 几何
    if (data.ok && data.gltf) {
      renderModelGLTF(data.gltf);
      scriptEditor.value = data.code;
      if (data.stats) {
        document.getElementById('stat-volume').textContent = `${data.stats.volume.toLocaleString()} mm³`;
        document.getElementById('stat-time').textContent = `${data.stats.compute_ms} ms`;
        showStatus(`Agent 建模完成 · 体积: ${data.stats.volume} mm³ · 耗时: ${data.stats.compute_ms} ms`);
      }
    } else if (data.error) {
      showStatus(`Agent 建模失败: ${data.error}`, true);
    }
  } catch (err) {
    appendChatBubble('assistant', '抱歉，建模过程遇到网络或执行异常：' + err.message);
    showStatus(`Agent 失败: ${err.message}`, true);
  } finally {
    hideLoading();
  }
}

if (btnSendAgent) {
  btnSendAgent.onclick = () => sendAgentMessage();
}

if (agentInput) {
  agentInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendAgentMessage();
    }
  });
}

if (btnClearChat) {
  btnClearChat.onclick = () => {
    agentChatHistory = [];
    chatMessages.innerHTML = `
      <div class="chat-bubble assistant">
        <div class="bubble-header">🤖 SMLib 建模 Agent</div>
        <div class="bubble-body">对话历史已重置。请输入你希望生成的零件或几何特征！</div>
      </div>
    `;
  };
}

// 快捷 Prompt 胶囊点击
document.querySelectorAll('.prompt-pill').forEach(pill => {
  pill.onclick = () => {
    const prompt = pill.dataset.prompt;
    if (prompt) sendAgentMessage(prompt);
  };
});

// --- 右侧几何工具栏控制器 (复刻 cax-viewer) ---
const RIGHT_TOOLS_SCHEMA = {
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
    fields: [
      { key: 'dim1', label: '线段长度 (mm)', default: 50 }
    ]
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
    fields: [
      { key: 'dim1', label: '圆半径 R (mm)', default: 20 }
    ]
  },
  'arc': {
    title: '圆弧轮廓',
    desc: '创建圆弧草图轮廓并拉伸成体',
    fields: [
      { key: 'dim1', label: '圆弧半径 R (mm)', default: 20 }
    ]
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
    fields: [
      { key: 'distance', label: '倒角距离 (mm)', default: 3 }
    ]
  },
  'fillet': {
    title: '倒圆角',
    desc: '对实体特征边缘应用光滑倒圆角',
    allowBaseOnCurrent: true,
    fields: [
      { key: 'radius', label: '圆角半径 R (mm)', default: 5 }
    ]
  },
  'shell': {
    title: '薄壁抽壳',
    desc: '指定壁厚对当前实体掏空抽壳',
    allowBaseOnCurrent: true,
    fields: [
      { key: 'thickness', label: '薄壁厚度 (mm)', default: 2 }
    ]
  },
  'offset': {
    title: '几何等距偏移',
    desc: '沿法向整体均匀扩展/收缩',
    allowBaseOnCurrent: true,
    fields: [
      { key: 'distance', label: '偏移距离 (mm)', default: 5 }
    ]
  },
  'mirror': {
    title: '对称镜像',
    desc: '沿基准平面对称镜像并组合',
    allowBaseOnCurrent: true,
    fields: [
      { key: 'plane', label: '镜像基准面', type: 'select', options: ['YZ', 'XZ', 'XY'], default: 'YZ' }
    ]
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

let activeToolKey = null;

function openToolModal(toolKey) {
  const schema = RIGHT_TOOLS_SCHEMA[toolKey];
  if (!schema) return;

  activeToolKey = toolKey;
  toolModalTitle.textContent = schema.title;
  toolModalDesc.textContent = schema.desc;
  toolModalFields.innerHTML = '';

  // 是否显示“基于当前模型”选项
  if (toolBaseOption) {
    toolBaseOption.style.display = schema.allowBaseOnCurrent ? 'block' : 'none';
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

function closeToolModal() {
  toolDialog.classList.add('hidden');
  activeToolKey = null;
}

if (toolModalClose) toolModalClose.onclick = closeToolModal;
if (toolModalCancel) toolModalCancel.onclick = closeToolModal;

if (toolModalForm) {
  toolModalForm.onsubmit = async (e) => {
    e.preventDefault();
    if (!activeToolKey) return;

    const schema = RIGHT_TOOLS_SCHEMA[activeToolKey];
    const params = {};
    (schema.fields || []).forEach(f => {
      const el = document.getElementById(`tf-${f.key}`);
      if (el) {
        params[f.key] = f.type === 'select' ? el.value : parseFloat(el.value);
      }
    });

    const baseOnCurrent = schema.allowBaseOnCurrent && toolBaseCheckbox ? toolBaseCheckbox.checked : false;

    closeToolModal();
    showLoading(`SMLib 正在执行【${schema.title}】运算…`);

    try {
      const res = await fetch('/api/tools/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tool: activeToolKey,
          params,
          base_on_current: baseOnCurrent
        })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || '工具运算失败');

      // 渲染 3D
      renderModelGLTF(data.gltf);
      scriptEditor.value = data.code;

      if (data.stats) {
        document.getElementById('stat-volume').textContent = `${data.stats.volume.toLocaleString()} mm³`;
        document.getElementById('stat-time').textContent = `${data.stats.compute_ms} ms`;
        showStatus(`${data.explanation} · 耗时: ${data.stats.compute_ms} ms`);
      }

      // 如果在 Agent 标签页，同步插入一条助手气泡
      appendChatBubble('assistant', `🛠️ 执行工具【${schema.title}】：${data.explanation}`, {
        code: data.code,
        compute_ms: data.stats ? data.stats.compute_ms : null
      });

    } catch (err) {
      showStatus(`工具执行失败: ${err.message}`, true);
      alert(`运算失败: ${err.message}`);
    } finally {
      hideLoading();
    }
  };
}

// 绑定右侧工具栏所有按钮点击事件
document.querySelectorAll('.right-tools button[data-tool]').forEach(btn => {
  btn.onclick = () => {
    const tool = btn.dataset.tool;
    if (tool) openToolModal(tool);
  };
});

// 获取系统内核信息
async function fetchInfo() {
  try {
    const res = await fetch('/api/info');
    const info = await res.json();
    document.getElementById('info-kernel').textContent = info.kernel;
    document.getElementById('info-pyver').textContent = `smlibpy ${info.smlibpy_version}`;
  } catch (err) {
    console.warn('Failed to fetch info:', err);
  }
}

// 页面初始化加载
renderParamForm('flange');
triggerParametricBuild();
fetchInfo();
