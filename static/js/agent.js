const chatMessages = document.getElementById('chat-messages');
const agentInput = document.getElementById('agent-input');
const btnSendAgent = document.getElementById('btn-send-agent');
const btnClearChat = document.getElementById('btn-clear-chat');
const btnToggleLlm = document.getElementById('btn-toggle-llm-settings');
const llmSettingsCard = document.getElementById('llm-settings-panel');

const settingBaseUrl = document.getElementById('setting-base-url');
const settingApiKey = document.getElementById('setting-api-key');
const settingModel = document.getElementById('setting-model');

const savedLlmConfig = JSON.parse(localStorage.getItem('smlib_llm_config') || '{}');
if (settingBaseUrl) settingBaseUrl.value = savedLlmConfig.baseUrl || '';
if (settingApiKey) settingApiKey.value = savedLlmConfig.apiKey || '';
if (settingModel) settingModel.value = savedLlmConfig.model || '';

export function saveLlmConfig() {
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

// 预设切换药丸
document.querySelectorAll('.preset-pill').forEach(pill => {
  pill.onclick = () => {
    if (settingBaseUrl) settingBaseUrl.value = pill.dataset.base || '';
    if (settingModel) settingModel.value = pill.dataset.model || '';
    saveLlmConfig();
  };
});

if (btnToggleLlm && llmSettingsCard) {
  btnToggleLlm.onclick = (e) => {
    e.preventDefault();
    llmSettingsCard.classList.toggle('hidden');
  };
}

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
let onAgentSuccessCallback = null;

export function setAgentSuccessCallback(cb) {
  onAgentSuccessCallback = cb;
}

export function appendChatBubble(role, content, meta = {}) {
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
        const editor = document.getElementById('script-editor');
        if (editor) editor.value = meta.code;
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

export async function sendAgentMessage(userPrompt, showLoadingFn, hideLoadingFn, showStatusFn) {
  const text = (userPrompt || (agentInput ? agentInput.value : '')).trim();
  if (!text) return;

  if (agentInput) agentInput.value = '';

  appendChatBubble('user', text);
  if (showLoadingFn) showLoadingFn('SMLib 智能 Agent 正在分析几何特征并编写代码…');

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

    appendChatBubble('assistant', data.reply, {
      code: data.code,
      compute_ms: data.stats ? data.stats.compute_ms : null,
      error: data.error
    });

    agentChatHistory.push({ role: 'user', content: text });
    agentChatHistory.push({ role: 'assistant', content: data.reply, code: data.code });

    if (data.ok && data.gltf && onAgentSuccessCallback) {
      onAgentSuccessCallback(data);
    } else if (data.error && showStatusFn) {
      showStatusFn(`Agent 建模失败: ${data.error}`, true);
    }
  } catch (err) {
    appendChatBubble('assistant', '抱歉，建模过程遇到网络或执行异常：' + err.message);
    if (showStatusFn) showStatusFn(`Agent 失败: ${err.message}`, true);
  } finally {
    if (hideLoadingFn) hideLoadingFn();
  }
}

export function initAgentUI(showLoadingFn, hideLoadingFn, showStatusFn) {
  if (btnSendAgent) {
    btnSendAgent.onclick = () => sendAgentMessage('', showLoadingFn, hideLoadingFn, showStatusFn);
  }

  if (agentInput) {
    agentInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendAgentMessage('', showLoadingFn, hideLoadingFn, showStatusFn);
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

  document.querySelectorAll('.prompt-pill').forEach(pill => {
    pill.onclick = () => {
      const prompt = pill.dataset.prompt;
      if (prompt) sendAgentMessage(prompt, showLoadingFn, hideLoadingFn, showStatusFn);
    };
  });
}
