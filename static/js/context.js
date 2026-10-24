/**
 * Global reactive CADContext bus for BrepX.
 * Maintains scene data, selections, active mode, and listeners.
 */

class CADContext {
  constructor() {
    this.mode = 'OBJECT'; // 'OBJECT' | 'EDIT'
    this.selectionLevel = 'solid'; // 'solid' | 'face' | 'edge' | 'vertex'
    this.isBoundaryMode = false;
    this.isXrayMode = false;
    this.selections = []; // list of { body, type, index, expr, meta }
    this.sceneData = null; // latest B-Rep scene from backend
    this.lastOperation = null; // latest executed operator for F9 adjust
    this.patches = []; // CFD boundary patches
    this.listeners = new Map();
  }

  on(event, fn) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event).add(fn);
  }

  off(event, fn) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).delete(fn);
    }
  }

  emit(event, payload) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(fn => fn(payload, this));
    }
  }

  setMode(mode) {
    if (this.mode !== mode) {
      this.mode = mode;
      this.emit('mode:changed', mode);
    }
  }

  setSelectionLevel(level) {
    if (this.selectionLevel !== level) {
      this.selectionLevel = level;
      this.clearSelections();
      this.emit('selectionLevel:changed', level);
    }
  }

  setSelections(items) {
    this.selections = items || [];
    this.emit('selections:changed', this.selections);
  }

  toggleSelection(item) {
    const idx = this.selections.findIndex(s => s.expr === item.expr);
    if (idx >= 0) {
      this.selections.splice(idx, 1);
    } else {
      this.selections.push(item);
    }
    this.emit('selections:changed', this.selections);
  }

  clearSelections() {
    if (this.selections.length > 0) {
      this.selections = [];
      this.emit('selections:changed', this.selections);
    }
  }

  getSelectedExpressions() {
    return this.selections.map(s => s.expr);
  }

  setSceneData(data) {
    this.sceneData = data;
    this.emit('scene:updated', data);
  }

  setPatches(patches) {
    this.patches = patches || [];
    this.emit('patches:updated', this.patches);
  }

  setLastOperation(op) {
    this.lastOperation = op;
    this.emit('lastOp:updated', op);
  }
}

export const ctx = new CADContext();
