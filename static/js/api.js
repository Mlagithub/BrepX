/**
 * REST API client for BrepX command, query, parameter updates, agent and export services.
 */

export async function submitCommand(command) {
  const res = await fetch('/api/command', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(command),
  });
  const data = await res.json();
  if (!res.ok || !data.ok) {
    const errorMsg = data.error ? (data.error.message || JSON.stringify(data.error)) : 'Command execution failed';
    const err = new Error(errorMsg);
    err.diagnostic = data.error;
    throw err;
  }
  return data;
}

export async function updateCommandParams(commandId, params) {
  const res = await fetch(`/api/command/${commandId}/params`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ params }),
  });
  const data = await res.json();
  if (!res.ok || !data.ok) {
    const errorMsg = data.error ? (data.error.message || JSON.stringify(data.error)) : 'Parameter update failed';
    const err = new Error(errorMsg);
    err.diagnostic = data;
    throw err;
  }
  return data;
}

export async function fetchQuery() {
  const res = await fetch('/api/query');
  const data = await res.json();
  if (!res.ok || !data.ok) {
    throw new Error('Failed to fetch geometric query');
  }
  return data;
}

export async function fetchScene() {
  const res = await fetch('/api/scene');
  const data = await res.json();
  if (!res.ok || !data.ok) {
    throw new Error('Failed to fetch viewport scene');
  }
  return data;
}

export async function undo() {
  const res = await fetch('/api/undo', { method: 'POST' });
  const data = await res.json();
  if (!res.ok || !data.ok) {
    throw new Error(data.error ? data.error.message : 'Undo failed');
  }
  return data;
}

export async function redo() {
  const res = await fetch('/api/redo', { method: 'POST' });
  const data = await res.json();
  if (!res.ok || !data.ok) {
    throw new Error(data.error ? data.error.message : 'Redo failed');
  }
  return data;
}

export async function testLlmConnection(config) {
  const res = await fetch('/api/agent/test-llm', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  return await res.json();
}

export async function sendAgentChat(prompt, selections = [], config) {
  const res = await fetch('/api/agent/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, selections, config }),
  });
  return await res.json();
}

export function getExportUrl(type) {
  const map = {
    step: '/api/export/step',
    stl: '/api/export/stl',
    dxf: '/api/export/dxf',
    cfd: '/api/export/cfd-dict',
    python: '/api/export/python',
  };
  return map[type] || '/api/export/step';
}
