/**
 * Central interaction lock managing exclusive control across OrbitControls,
 * TransformControls, modal drags, and dynamic numeric input.
 */

class InteractionLockManager {
  constructor() {
    this._locks = new Set();
    this._orbitControls = null;
    this._transformControls = null;
  }

  bindControls(orbit, transform) {
    this._orbitControls = orbit;
    this._transformControls = transform;

    if (this._transformControls && this._orbitControls) {
      this._transformControls.addEventListener('dragging-changed', (event) => {
        if (event.value) {
          this.acquire('gizmo_drag');
        } else {
          this.release('gizmo_drag');
        }
      });
    }
  }

  acquire(lockName) {
    this._locks.add(lockName);
    this._applyState();
  }

  release(lockName) {
    this._locks.delete(lockName);
    this._applyState();
  }

  isLocked() {
    return this._locks.size > 0;
  }

  has(lockName) {
    return this._locks.has(lockName);
  }

  _applyState() {
    if (!this._orbitControls) return;
    const shouldDisableOrbit = this.isLocked();
    this._orbitControls.enabled = !shouldDisableOrbit;
  }
}

export const interactionLock = new InteractionLockManager();
