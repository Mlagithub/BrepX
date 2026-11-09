/**
 * Global reactive CADContext bus for BrepX.
 * Maintains read-only geometric snapshots, versioning, mode, timeline, and selections.
 */

export class CADContext {
  constructor() {
    this.mode = 'OBJECT';
    this.selectionLevel = 'face';
    this.displayMode = 'shaded_edges';
    this.version = 1;
    this.body = null;
    this.scene = null;
    this.selections = [];
    this.journal = [];
    this.activeStepId = null;
    this.rollbackIndex = null;
    this.lastCommand = null;
    this.isSectionActive = false;
    this.hoveredTopology = null;
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

  setDisplayMode(mode) {
    if (this.displayMode !== mode) {
      this.displayMode = mode;
      this.emit('displayMode:changed', mode);
    }
  }

  setSnapshot(version, body, scene) {
    this.version = version;
    this.body = body;
    this.scene = scene;
    this.emit('snapshot:changed', { version, body, scene });
  }

  setJournal(journal) {
    this.journal = Array.isArray(journal) ? journal : [];
    this.emit('journal:changed', this.journal);
  }

  setActiveStep(stepId) {
    this.activeStepId = stepId;
    this.emit('activeStep:changed', stepId);
  }

  setRollbackIndex(idx) {
    this.rollbackIndex = idx;
    this.emit('rollback:changed', idx);
  }

  setSelection(selectors) {
    this.selections = Array.isArray(selectors) ? selectors : [selectors];
    this.emit('selections:changed', this.selections);
  }

  getSelection() {
    return [...this.selections];
  }

  clearSelections() {
    this.selections = [];
    this.emit('selections:changed', this.selections);
  }

  setHoveredTopology(topo) {
    this.hoveredTopology = topo;
    this.emit('hover:changed', topo);
  }

  setLastCommand(cmd) {
    this.lastCommand = cmd;
    this.emit('lastCommand:changed', cmd);
  }
}

export const context = new CADContext();
