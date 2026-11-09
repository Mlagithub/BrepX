/**
 * Follow-cursor HUD numeric input overlay during modal operations.
 * Captures direct keyboard digits, minus signs, dots, and backspaces.
 */

import { interactionLock } from './interaction_lock.js';

let hudElement = null;
let currentBuffer = '';
let isListening = false;
let onValueChangeCallback = null;

function ensureHudElement() {
  if (!hudElement) {
    hudElement = document.createElement('div');
    hudElement.id = 'hud-numeric-overlay';
    hudElement.className = 'hud-numeric-input hidden';
    document.body.appendChild(hudElement);
  }
}

export function activateHudInput(initialValue = 0, onValueChange = null) {
  ensureHudElement();
  currentBuffer = '';
  isListening = true;
  onValueChangeCallback = onValueChange;
  interactionLock.acquire('numeric_input');

  hudElement.textContent = `${initialValue}`;
  hudElement.classList.remove('hidden');
}

export function deactivateHudInput() {
  if (!hudElement) return;
  hudElement.classList.add('hidden');
  isListening = false;
  currentBuffer = '';
  onValueChangeCallback = null;
  interactionLock.release('numeric_input');
}

export function updateHudValue(val) {
  if (!hudElement || !isListening) return;
  if (!currentBuffer) {
    hudElement.textContent = typeof val === 'number' ? val.toFixed(1) : val;
  }
}

export function updateHudPosition(clientX, clientY) {
  if (!hudElement || !isListening) return;
  hudElement.style.transform = `translate3d(${clientX + 16}px, ${clientY + 16}px, 0)`;
}

export function getTypedNumericValue(fallbackValue = 0) {
  if (!currentBuffer) return fallbackValue;
  const parsed = parseFloat(currentBuffer);
  return isNaN(parsed) ? fallbackValue : parsed;
}

export function hasUserTyped() {
  return currentBuffer.length > 0;
}

window.addEventListener('keydown', (e) => {
  if (!isListening) return;

  const validKeys = '0123456789.-';
  if (validKeys.includes(e.key)) {
    e.preventDefault();
    if (e.key === '.' && currentBuffer.includes('.')) return;
    if (e.key === '-' && currentBuffer.length > 0) return;

    currentBuffer += e.key;
    hudElement.textContent = currentBuffer;
    if (onValueChangeCallback) {
      const val = parseFloat(currentBuffer);
      if (!isNaN(val)) onValueChangeCallback(val);
    }
  } else if (e.key === 'Backspace') {
    e.preventDefault();
    currentBuffer = currentBuffer.slice(0, -1);
    hudElement.textContent = currentBuffer || '0';
    if (onValueChangeCallback) {
      const val = parseFloat(currentBuffer) || 0;
      onValueChangeCallback(val);
    }
  }
});
