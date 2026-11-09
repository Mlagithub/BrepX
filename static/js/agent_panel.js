/**
 * Modern Agent copilot panel with natural language interaction and LLM settings.
 */

import { fetchScene, sendAgentChat, testLlmConnection } from './api.js';
import { context } from './context.js';

let panelEl = null;

export function initAgentPanel(containerEl) {
  panelEl = containerEl;
  if (!panelEl) return;

  const savedCfg = JSON.parse(localStorage.getItem('brepx_llm_cfg') || '{}');
  const defaultBaseUrl = savedCfg.base_url || 'http://127.0.0.1:8000/v1';

  panelEl.innerHTML = `
    <div class="agent-panel-wrap">
      <div class="agent-settings-card">
        <div class="settings-header">
          <span>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:4px; vertical-align:middle;"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
            LLM 服务配置
          </span>
          <button id="btn-toggle-cfg" class="btn-text-sm">展开 ▾</button>
        </div>
        <div id="cfg-body" class="settings-body hidden">
          <input type="text" id="cfg-url" placeholder="API Base URL" value="${defaultBaseUrl}" />
          <input type="password" id="cfg-key" placeholder="API Key" value="${savedCfg.api_key || ''}" />
          <input type="text" id="cfg-model" placeholder="Model" value="${savedCfg.model || 'deepseek-chat'}" />
          <button id="btn-test-cfg" class="btn btn-secondary btn-sm" style="width:100%">测试连通性</button>
          <div id="cfg-status" class="cfg-status-text"></div>
        </div>
      </div>

      <div class="agent-chat-messages" id="agent-chat-msgs">
        <div class="chat-bubble assistant">
          <div class="bubble-header">CAD Agent</div>
          <div class="bubble-content">你好！我是你的 CFD 工业几何副驾。你可以直接用自然语言描述需求，例如“建一个叶轮”或“在选定面上打孔”。</div>
        </div>
      </div>

      <div class="agent-input-box">
        <textarea id="agent-prompt-input" rows="2" placeholder="输入建模指令 (Enter 发送)..."></textarea>
        <button id="btn-agent-send" class="btn btn-primary btn-sm">发送 ↵</button>
      </div>
    </div>
  `;

  _bindEvents();
}

function _bindEvents() {
  const toggleBtn = panelEl.querySelector('#btn-toggle-cfg');
  const cfgBody = panelEl.querySelector('#cfg-body');
  if (toggleBtn && cfgBody) {
    toggleBtn.onclick = () => {
      cfgBody.classList.toggle('hidden');
    };
  }

  const testBtn = panelEl.querySelector('#btn-test-cfg');
  const statusEl = panelEl.querySelector('#cfg-status');
  if (testBtn) {
    testBtn.onclick = async () => {
      const cfg = _readConfig();
      statusEl.textContent = '测试中...';
      try {
        const res = await testLlmConnection(cfg);
        if (res.ok) {
          statusEl.textContent = `连通正常 (${res.latency_ms} ms)`;
          statusEl.style.color = '#98c379';
        } else {
          statusEl.textContent = `${res.error?.message || '连通失败'}`;
          statusEl.style.color = '#e06c75';
        }
      } catch (err) {
        statusEl.textContent = `${err.message}`;
        statusEl.style.color = '#e06c75';
      }
    };
  }

  const sendBtn = panelEl.querySelector('#btn-agent-send');
  const promptInput = panelEl.querySelector('#agent-prompt-input');
  if (sendBtn && promptInput) {
    const doSend = async () => {
      const txt = promptInput.value.trim();
      if (!txt) return;
      promptInput.value = '';

      _appendBubble('user', txt);
      const cfg = _readConfig();
      const selections = context.getSelection();

      try {
        const res = await sendAgentChat(txt, selections, cfg);
        if (res.ok) {
          _appendBubble('assistant', res.explanation || '已生成并提交建模命令');
          const sceneData = await fetchScene();
          context.setSnapshot(res.version, res.body, sceneData);
        } else {
          _appendBubble('assistant', `执行受限: ${res.error?.message || '命令执行失败'}`);
        }
      } catch (err) {
        _appendBubble('assistant', `错误: ${err.message}`);
      }
    };

    sendBtn.onclick = doSend;
    promptInput.onkeydown = (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        doSend();
      }
    };
  }
}

function _readConfig() {
  const cfg = {
    base_url: panelEl.querySelector('#cfg-url').value.trim(),
    api_key: panelEl.querySelector('#cfg-key').value.trim(),
    model: panelEl.querySelector('#cfg-model').value.trim(),
  };
  localStorage.setItem('brepx_llm_cfg', JSON.stringify(cfg));
  return cfg;
}

function _appendBubble(role, content) {
  const msgsEl = panelEl.querySelector('#agent-chat-msgs');
  if (!msgsEl) return;
  const bubble = document.createElement('div');
  bubble.className = `chat-bubble ${role}`;
  bubble.innerHTML = `
    <div class="bubble-header">${role === 'user' ? '工程师' : 'CAD Agent'}</div>
    <div class="bubble-content">${content}</div>
  `;
  msgsEl.appendChild(bubble);
  msgsEl.scrollTop = msgsEl.scrollHeight;
}
