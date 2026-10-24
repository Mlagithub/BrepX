/**
 * Embodied Agent Panel Controller for SMLib Studio Next.
 * Synchronizes viewport topological selections, LLM config, and chat stream.
 */

import { ctx } from './context.js';

const chatMessages = document.getElementById('chat-messages');
const agentInput = document.getElementById('agent-input');
const btnSendAgent = document.getElementById('btn-send-agent');
const btnClearChat = document.getElementById('btn-clear-chat');
const btnToggleLlm = document.getElementById('btn-toggle-llm-settings');
const llmSettingsPanel = document.getElementById('llm-settings-panel');

const settingBaseUrl = document.getElementById('setting-base-url');
const settingApiKey = document.getElementById('setting-api-key');
const settingModel = document.getElementById('setting-model');

const savedConfig = JSON.parse(localStorage.getItem('smlib_llm_config') || '{}');
if (settingBaseUrl) settingBaseUrl.value = savedConfig.baseUrl || '';
if (settingApiKey) settingApiKey.value = savedConfig.apiKey || '';
if (settingModel) settingModel.value = savedConfig.model || '';

export function getLlmConfig() {
  const cfg = {
    baseUrl: settingBaseUrl ? settingBaseUrl.value.trim() : '',
    apiKey: settingApiKey ? settingApiKey.value.trim() : '',
    model: settingModel ? settingModel.value.trim() : '',
  };
  localStorage.setItem('smlib_llm_config', JSON.stringify(cfg));
  return cfg;
}

[settingBaseUrl, settingApiKey, settingModel].forEach((el) => {
  if (el) {
    el.oninput = getLlmConfig;
    el.onchange = getLlmConfig;
  }
});

if (btnToggleLlm && llmSettingsPanel) {
  btnToggleLlm.onclick = () => {
    llmSettingsPanel.classList.toggle('hidden');
    btnToggleLlm.textContent = llmSettingsPanel.classList.contains('hidden') ? '展开配置 ▾' : '收起配置 ▴';
  };
}

// LLM Connectivity test
const btnTestLlm = document.getElementById('btn-test-llm');
const llmTestResult = document.getElementById('llm-test-result');
if (btnTestLlm) {
  btnTestLlm.onclick = async () => {
    const cfg = getLlmConfig();
    btnTestLlm.disabled = true;
    btnTestLlm.textContent = '测试连接中…';
    llmTestResult.innerHTML = '<span style="color:#abb2bf">正在向大模型端点发送心跳…</span>';
    try {
      const res = await fetch('/api/agent/test_llm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cfg),
      });
      const data = await res.json();
      if (data.ok) {
        llmTestResult.innerHTML = `<span style="color:#98c379">✅ 连通成功！模型: ${data.model} · 延时: ${data.latency_ms} ms</span>`;
      } else {
        llmTestResult.innerHTML = `<span style="color:#e06c75">❌ 握手失败: ${data.error}</span>`;
      }
    } catch (err) {
      llmTestResult.innerHTML = `<span style="color:#e06c75">❌ 网络异常: ${err.message}</span>`;
    } finally {
      btnTestLlm.disabled = false;
      btnTestLlm.textContent = '🧪 测试 API 连通性';
    }
  };
}

let chatHistory = [];

export function appendMessageBubble(role, content, meta = {}) {
  const bubble = document.createElement('div');
  bubble.className = `chat-bubble ${role}`;

  if (role === 'user') {
    bubble.innerHTML = `<div class="bubble-body">${escapeHtml(content)}</div>`;
  } else {
    let html = `
      <div class="bubble-header">
        <span>🤖 SMLib 具身 Agent</span>
        ${meta.elapsed ? `<span style="font-weight:normal;color:#676f7d">${meta.elapsed} ms</span>` : ''}
      </div>
      <div class="bubble-body">${escapeHtml(content).replace(/\n/g, '<br>')}</div>
    `;
    if (meta.code) {
      html += `<pre class="bubble-code"><code>${escapeHtml(meta.code)}</code></pre>`;
    }
    if (meta.error) {
      html += `<div style="color:#e06c75;margin-top:4px;font-size:11px;">⚠️ 执行提示: ${escapeHtml(meta.error)}</div>`;
    }
    bubble.innerHTML = html;
  }

  chatMessages.appendChild(bubble);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function escapeHtml(str) {
  return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

export async function sendAgentTurn(userPrompt = '') {
  const text = (userPrompt || (agentInput ? agentInput.value : '')).trim();
  if (!text) return;

  if (agentInput) agentInput.value = '';
  appendMessageBubble('user', text);

  const reqSels = ctx.getSelectedExpressions();
  const cfg = getLlmConfig();

  try {
    const res = await fetch('/api/agent/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt: text,
        selections: reqSels,
        history: chatHistory,
        config: cfg,
      }),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Agent 请求失败');

    appendMessageBubble('assistant', data.reply, {
      code: data.step_code || data.code,
      error: data.error,
    });

    chatHistory.push({ role: 'user', content: text });
    chatHistory.push({ role: 'assistant', content: data.reply, code: data.step_code });

    if (data.ok && data.state) {
      ctx.setSceneData(data.state.scene);
      ctx.setPatches(data.state.patches);
      ctx.setLastOperation(data.state.last_operation);
    }
  } catch (err) {
    appendMessageBubble('assistant', '网络或执行异常: ' + err.message);
  }
}

export function initAgentPanel() {
  if (btnSendAgent) {
    btnSendAgent.onclick = () => sendAgentTurn();
  }
  if (agentInput) {
    agentInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendAgentTurn();
      }
    });
  }
  if (btnClearChat) {
    btnClearChat.onclick = () => {
      chatHistory = [];
      chatMessages.innerHTML = `
        <div class="chat-bubble assistant">
          <div class="bubble-header">🤖 SMLib 具身 Agent</div>
          <div class="bubble-body">对话历史已清空。请输入你想要设计的几何构型或流道特征！</div>
        </div>
      `;
    };
  }

  // Quick prompt pills
  document.querySelectorAll('.prompt-pill').forEach((pill) => {
    pill.onclick = () => {
      const p = pill.dataset.prompt;
      if (p) sendAgentTurn(p);
    };
  });
}
