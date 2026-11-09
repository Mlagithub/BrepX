/**
 * Read-only synchronized Python code viewer mapping current Command Journal state.
 */

import { context } from './context.js';

let editorEl = null;
let isDirty = true;

export function initPythonViewer(textareaEl) {
  editorEl = textareaEl;
  context.on('snapshot:changed', () => {
    isDirty = true;
    if (editorEl && editorEl.offsetParent !== null) {
      syncPythonCode();
    }
  });

  const tabBtn = document.getElementById('tab-btn-python');
  if (tabBtn) {
    tabBtn.addEventListener('click', () => {
      if (isDirty) {
        syncPythonCode();
      }
    });
  }
}

export async function syncPythonCode() {
  if (!editorEl) return;
  try {
    const res = await fetch('/api/export/python');
    if (res.ok) {
      editorEl.value = await res.text();
      isDirty = false;
    }
  } catch (err) {
    editorEl.value = `# 获取 Python 代码受限: ${err.message}`;
  }
}
