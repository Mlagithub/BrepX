const STYLE_ID = 'bx-workbench-style'
const THEME_ID = 'bx-workbench-theme'

const css = `
  body.bxw-workbench [data-sidebar-collapsed="true"] { grid-template-columns: 0 minmax(0, 1fr) 0 !important; }
  body.bxw-workbench [data-sidebar-collapsed="true"] > :first-child { display: none !important; }
  .bxw-shell {
    position: absolute;
    inset: 0;
    display: grid;
    grid-template-rows: 56px minmax(0, 1fr);
    overflow: hidden;
    color: var(--dsw-alias-label-primary, #e8edf5);
    background: var(--dsw-alias-bg-base, #101318);
    font: 13px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif;
    --bxw-panel: var(--dsw-alias-bg-layer-1, #15191f);
    --bxw-layer: var(--dsw-alias-bg-layer-2, #1a1f27);
    --bxw-line: var(--dsw-alias-border-l2, #2a313c);
    --bxw-soft: var(--dsw-alias-label-secondary, #9aa7b8);
    --bxw-muted: var(--dsw-alias-label-tertiary, #6d7b8e);
    --bxw-accent: var(--dsw-alias-state-business-primary, #4f8cff);
    --bxw-ok: var(--dsw-alias-state-success-primary, #3fb950);
    --bxw-warn: var(--dsw-alias-state-warn-primary, #d29922);
    --bxw-bad: var(--dsw-alias-state-error-primary, #f85149);
    --bxw-primary: var(--dsw-alias-label-primary, #e8edf5);
    --bxw-bg: var(--dsw-alias-bg-base, #101318);
  }
  .bxw-shell *, .bxw-shell *::before, .bxw-shell *::after { box-sizing: border-box; }
  .bxw-shell button, .bxw-shell select, .bxw-shell textarea { font: inherit; color: inherit; }
  .bxw-shell button {
    display: inline-flex; align-items: center; justify-content: center; gap: 6px;
    height: 30px; padding: 0 10px; border: 1px solid var(--bxw-line);
    border-radius: 6px; background: transparent; cursor: pointer; white-space: nowrap;
  }
  .bxw-shell button:hover { background: var(--bxw-layer); border-color: color-mix(in srgb, var(--bxw-accent) 55%, var(--bxw-line)); }
  .bxw-shell button:focus-visible, .bxw-shell select:focus-visible {
    outline: 2px solid color-mix(in srgb, var(--bxw-accent) 70%, transparent); outline-offset: 1px;
  }
  .bxw-shell button:disabled { opacity: .5; cursor: default; }
  .bxw-icon { width: 16px; height: 16px; flex: none; }
  .bxw-header {
    display: flex; align-items: center; gap: 12px; min-width: 0; padding: 0 14px;
    border-bottom: 1px solid var(--bxw-line); background: var(--bxw-panel);
  }
  .bxw-brand { display: flex; align-items: center; gap: 8px; flex: none; font-weight: 650; letter-spacing: .2px; }
  .bxw-mark { width: 24px; height: 24px; display: grid; place-items: center; border-radius: 6px;
    background: color-mix(in srgb, var(--bxw-accent) 16%, transparent); color: var(--bxw-accent); }
  .bxw-context { display: flex; align-items: center; gap: 8px; min-width: 0; flex: 1; }
  .bxw-context-label { color: var(--bxw-muted); font-size: 11px; flex: none; }
  .bxw-context select {
    max-width: min(360px, 40vw); height: 30px; padding: 0 30px 0 10px; border: 1px solid var(--bxw-line);
    border-radius: 6px; background-color: var(--bxw-layer) !important; color: var(--bxw-primary) !important;
    appearance: none; -webkit-appearance: none;
    background-image: linear-gradient(45deg, transparent 50%, var(--bxw-soft) 50%), linear-gradient(135deg, var(--bxw-soft) 50%, transparent 50%);
    background-position: calc(100% - 14px) 13px, calc(100% - 9px) 13px;
    background-size: 5px 5px, 5px 5px;
    background-repeat: no-repeat;
  }
  .bxw-context select option { background: #1a1f27; color: #e8edf5; }
  .bxw-version { font: 11px/1 var(--dsw-font-mono, ui-monospace, monospace); color: var(--bxw-muted); flex: none; }
  .bxw-badge { display: inline-flex; align-items: center; gap: 5px; height: 22px; padding: 0 8px;
    border-radius: 999px; border: 1px solid var(--bxw-line); color: var(--bxw-soft); font-size: 11px; flex: none; }
  .bxw-badge[data-tone="ok"] { color: var(--bxw-ok); border-color: color-mix(in srgb, var(--bxw-ok) 42%, transparent); }
  .bxw-badge[data-tone="bad"] { color: var(--bxw-bad); border-color: color-mix(in srgb, var(--bxw-bad) 42%, transparent); }
  .bxw-badge-button { cursor: pointer; }
  .bxw-badge-button:hover { border-color: color-mix(in srgb, var(--bxw-accent) 55%, var(--bxw-line)); }
  .bxw-badge-button[aria-pressed="true"] { background: color-mix(in srgb, var(--bxw-accent) 9%, transparent); }
  .bxw-progress { display: none; position: absolute; left: 0; right: 0; bottom: -1px; height: 2px; overflow: hidden; }
  .bxw-shell[data-running="true"] .bxw-progress { display: block; }
  .bxw-progress::after { content: ""; display: block; width: 42%; height: 100%; background: var(--bxw-accent);
    animation: bxw-progress 1.2s ease-in-out infinite; }
  @keyframes bxw-progress { from { transform: translateX(-110%); } to { transform: translateX(250%); } }
  @media (prefers-reduced-motion: reduce) { .bxw-progress::after { animation: none; width: 100%; opacity: .55; } }
  .bxw-actions { position: relative; display: flex; align-items: center; gap: 6px; flex: none; }
  .bxw-view-trigger, .bxw-structure-trigger, .bxw-review-trigger { gap: 6px; padding: 0 9px; }
  .bxw-import-trigger { padding: 0 9px; }
  .bxw-import-trigger[data-busy="true"] { opacity: .55; }
  .bxw-review-trigger svg:last-child { width: 12px; height: 12px; opacity: .7; }
  .bxw-structure-trigger[aria-pressed="true"] { border-color: color-mix(in srgb, var(--bxw-accent) 45%, var(--bxw-line));
    background: color-mix(in srgb, var(--bxw-accent) 10%, transparent); color: var(--bxw-primary); }
  .bxw-view-trigger svg:last-child { width: 12px; height: 12px; opacity: .7; }
  .bxw-view-menu { position: absolute; top: calc(100% + 8px); right: 0; z-index: 20; width: 196px; padding: 5px;
    border: 1px solid var(--bxw-line); border-radius: 8px; background: var(--bxw-panel);
    box-shadow: 0 12px 30px rgba(0,0,0,.18); }
  .bxw-view-menu[hidden] { display: none; }
  .bxw-menu-scrim { position: fixed; inset: 0; z-index: 19; }
  .bxw-menu-scrim[hidden] { display: none; }
  .bxw-view-menu button { width: 100%; height: 32px; justify-content: flex-start; gap: 8px; padding: 0 8px;
    border-color: transparent; background: transparent; color: var(--bxw-primary); font-size: 12px; }
  .bxw-view-menu button:hover { background: var(--bxw-layer); }
  .bxw-view-menu button::before { content: ""; width: 14px; color: var(--bxw-accent); font-weight: 700; }
  .bxw-view-menu button[aria-checked="true"]::before { content: "✓"; }
  .bxw-menu-sep { height: 1px; margin: 4px 6px; background: var(--bxw-line); }
  .bxw-review-menu { position: absolute; top: calc(100% + 8px); right: 0; z-index: 20; width: 304px;
    max-height: calc(100vh - 92px); overflow: auto; padding: 6px 10px;
    border: 1px solid var(--bxw-line); border-radius: 8px; background: var(--bxw-panel);
    box-shadow: 0 16px 38px rgb(0 0 0 / 22%); }
  .bxw-review-menu[hidden] { display: none; }
  .bxw-review-section { display: flex; flex-direction: column; gap: 7px; padding: 9px 2px;
    border-top: 1px solid var(--bxw-line); }
  .bxw-review-section:first-child { border-top: 0; }
  .bxw-review-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
  .bxw-review-head h3 { margin: 0; color: var(--bxw-muted); font-size: 10px; font-weight: 650;
    letter-spacing: .8px; text-transform: uppercase; }
  .bxw-review-meta { color: var(--bxw-muted); font: 10px/1.3 var(--dsw-font-mono, ui-monospace, monospace); }
  .bxw-review-row { display: flex; align-items: center; gap: 7px; }
  .bxw-review-row[hidden] { display: none; }
  .bxw-review-select { flex: 1; min-width: 0; height: 26px; padding: 0 8px; border: 1px solid var(--bxw-line);
    border-radius: 5px; background: var(--bxw-layer); color: var(--bxw-primary); font-size: 11px; }
  .bxw-review-select:disabled { opacity: .55; }
  .bxw-review-range { flex: 1; min-width: 0; accent-color: var(--bxw-accent); }
  .bxw-review-seg { display: flex; gap: 4px; }
  .bxw-review-seg button { height: 24px; padding: 0 9px; font-size: 11px; }
  .bxw-review-seg button[aria-pressed="true"] { color: var(--bxw-accent);
    border-color: color-mix(in srgb, var(--bxw-accent) 45%, var(--bxw-line));
    background: color-mix(in srgb, var(--bxw-accent) 10%, transparent); }
  .bxw-review-export { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
  .bxw-review-export button { height: 28px; font-size: 11px; }
  .bxw-review-note { color: var(--bxw-muted); font-size: 10px; line-height: 1.45; }
  .bxw-main { position: relative; min-height: 0; overflow: hidden; background: var(--bxw-panel); }
  .bxw-stage { position: absolute; inset: 0; }
  .bxw-models { position: absolute; z-index: 10; left: 14px; top: 14px; bottom: calc(var(--bxw-dock-h, 112px) + 26px);
    width: min(var(--bxw-left-width, 236px), 34vw); min-width: 0; display: flex; flex-direction: column;
    border: 1px solid var(--bxw-line); border-radius: 9px; background: var(--bxw-panel);
    box-shadow: 0 12px 32px rgb(0 0 0 / 18%); overflow: hidden; }
  .bxw-shell[data-models="off"] .bxw-models { display: none; }
  .bxw-resizer { position: absolute; top: 14px; bottom: calc(var(--bxw-dock-h, 112px) + 26px); z-index: 12; width: 7px; margin-left: -3px;
    cursor: col-resize; background: transparent; touch-action: none; }
  .bxw-resizer:hover, .bxw-resizer[data-drag="true"] { background: color-mix(in srgb, var(--bxw-accent) 35%, transparent); }
  .bxw-resizer-left { left: calc(14px + min(var(--bxw-left-width, 236px), 34vw)); }
  .bxw-resizer-right { top: 14px; bottom: auto; height: var(--bxw-inspector-h, 0px);
    right: calc(14px + min(var(--bxw-right-width, 292px), 36vw)); }
  .bxw-resizer:focus-visible { outline: 2px solid var(--bxw-accent); outline-offset: -2px; }
  .bxw-models-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; height: 42px; padding: 0 12px; border-bottom: 1px solid var(--bxw-line); }
  .bxw-models-head strong { font-size: 12px; font-weight: 600; }
  .bxw-structure-meta { margin-left: auto; color: var(--bxw-muted); font: 10px/1 var(--dsw-font-mono, ui-monospace, monospace); }
  .bxw-structure-list { flex: 1; min-height: 0; overflow: auto; padding: 6px; display: flex; flex-direction: column; gap: 2px; }
  .bxw-structure-progress { margin: 6px 8px 0; padding: 6px 7px; border: 1px solid color-mix(in srgb, var(--bxw-accent) 35%, var(--bxw-line));
    border-radius: 6px; color: var(--bxw-soft); font-size: 10px; display: flex; flex-direction: column; gap: 3px; }
  .bxw-structure-progress[hidden] { display: none; }
  .bxw-structure-row { display: flex; align-items: flex-start; gap: 7px; padding: 7px 7px; border-radius: 6px; cursor: default; }
  .bxw-structure-row:hover { background: var(--bxw-layer); }
  .bxw-structure-row[data-node] { cursor: pointer; }
  .bxw-structure-row[data-selected="true"] { background: color-mix(in srgb, var(--bxw-accent) 10%, transparent);
    box-shadow: inset 2px 0 0 var(--bxw-accent); }
  .bxw-structure-row .bxw-dot { margin-top: 4px; }
  .bxw-structure-main { min-width: 0; flex: 1; }
  .bxw-structure-main b { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--bxw-primary);
    font-size: 11px; font-weight: 550; }
  .bxw-structure-main span { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--bxw-muted);
    font: 9px/1.5 var(--dsw-font-mono, ui-monospace, monospace); }
  .bxw-structure-empty { padding: 10px 8px; color: var(--bxw-muted); font-size: 11px; }
  .bxw-model-list { flex: 1; min-height: 0; overflow-x: hidden; overflow-y: auto; padding: 4px 6px 12px; }
  .bxw-pane[hidden] { display: none; }
  .bxw-selection { display: flex; align-items: center; gap: 7px; max-width: none; margin: 0 0 7px; min-height: 24px; color: var(--bxw-soft); font-size: 11px; }
  .bxw-selection[hidden] { display: none; }
  .bxw-selection-chip { display: inline-flex; align-items: center; gap: 6px; max-width: 100%; padding: 3px 7px; border: 1px solid color-mix(in srgb, var(--bxw-accent) 40%, var(--bxw-line)); border-radius: 999px; color: var(--bxw-primary); background: color-mix(in srgb, var(--bxw-accent) 9%, transparent); }
  .bxw-selection-chip button { width: 16px; height: 16px; padding: 0; border: 0; background: transparent; color: var(--bxw-muted); }
  .bxw-agent-slot { flex: 1; min-height: 0; overflow: auto; }
  .bxw-agent-slot [data-conversation-region="composer"], .bxw-agent-slot [data-composer-seat],
  .bxw-agent-slot [data-conversation-scroll] > [data-conversation-region="composer"] { display: none !important; }
  .bxw-agent-slot [data-composer-seat]:has([data-question-key]) { display: flex !important; }
  .bxw-agent-slot [data-composer-seat] [data-composer-card],
  .bxw-agent-slot [data-composer-seat] [data-composer-input] { display: none !important; }
  .bxw-thread-item { padding: 8px 9px; border: 1px solid var(--bxw-line); border-radius: 6px; background: var(--bxw-layer); }
  .bxw-plan-card { padding: 8px 9px; border: 1px solid var(--bxw-line); border-radius: 6px; background: var(--bxw-layer); }
  .bxw-plan-card-head { display: flex; align-items: center; gap: 7px; }
  .bxw-plan-card-head b { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; font-weight: 550; }
  .bxw-plan-card-meta { margin-top: 3px; color: var(--bxw-muted); font: 10px/1.4 var(--dsw-font-mono, ui-monospace, monospace); }
  .bxw-stage { min-width: 0; min-height: 0; background: color-mix(in srgb, var(--bxw-panel) 70%, var(--bxw-bg, #101318)); }
  .bxw-frame { width: 100%; height: 100%; border: 0; display: block; }
  .bxw-handle-hint { position: absolute; top: 12px; left: 50%; transform: translateX(-50%);
    padding: 6px 10px; border: 1px solid color-mix(in srgb, var(--bxw-accent) 45%, var(--bxw-line));
    border-radius: 6px; background: color-mix(in srgb, var(--bxw-panel) 92%, transparent);
    color: var(--bxw-primary); font-size: 11px; pointer-events: none; z-index: 5; white-space: nowrap; }
  .bxw-handle-hint[hidden] { display: none; }
  .bxw-tools { display: flex; align-items: center; gap: 2px; flex: none; padding-left: 10px;
    border-left: 1px solid var(--bxw-line); }
  .bxw-tools .bxw-sep { width: 1px; height: 16px; background: var(--bxw-line); margin: 0 4px; }
  .bxw-tools button { height: 26px; padding: 0 7px; border-color: transparent; color: var(--bxw-soft); }
  .bxw-tools button:hover { color: var(--bxw-primary, #e8edf5); background: var(--bxw-layer); }
  .bxw-tools button[aria-pressed="true"] { color: var(--bxw-accent); background: color-mix(in srgb, var(--bxw-accent) 12%, transparent); }
  .bxw-scopes { display: flex; gap: 2px; padding: 2px; border-radius: 6px; background: var(--bxw-layer); }
  .bxw-scopes button { height: 22px; min-width: 24px; padding: 0 6px; border: 0; background: transparent;
    color: var(--bxw-muted); font-size: 10px; }
  .bxw-scopes button[aria-pressed="true"] { color: var(--bxw-accent);
    background: color-mix(in srgb, var(--bxw-accent) 15%, transparent); }
  .bxw-caption { display: flex; align-items: center; gap: 0; white-space: nowrap;
    color: var(--bxw-muted); font: 10px/1.3 var(--dsw-font-mono, ui-monospace, monospace); }
  .bxw-caption span + span::before { content: "·"; margin: 0 6px; color: var(--bxw-line); }
  .bxw-dock-bar .bxw-caption { margin-left: auto; }
  .bxw-empty { position: absolute; inset: 0; display: none; place-items: center; padding: 24px; }
  .bxw-empty[data-on="true"] { display: grid; }
  .bxw-empty-card { max-width: 340px; text-align: center; }
  .bxw-empty-card h2 { margin: 0 0 6px; font-size: 18px; font-weight: 600; }
  .bxw-empty-card p { margin: 0 0 16px; color: var(--bxw-soft); }
  .bxw-spinner { width: 24px; height: 24px; margin: 0 auto 14px; border: 2px solid var(--bxw-line);
    border-top-color: var(--bxw-accent); border-radius: 50%; animation: bxw-spin .7s linear infinite; }
  @keyframes bxw-spin { to { transform: rotate(360deg); } }
  @media (prefers-reduced-motion: reduce) { .bxw-spinner { animation: none; } }
  .bxw-inspector { position: absolute; z-index: 10; right: 14px; top: 14px; bottom: auto; max-height: calc(100% - 38px - var(--bxw-dock-h, 112px));
    width: min(var(--bxw-right-width, 292px), 36vw); min-width: 0; border: 1px solid var(--bxw-line);
    border-radius: 9px; background: var(--bxw-panel); overflow: auto; box-shadow: 0 12px 32px rgb(0 0 0 / 18%); }
  .bxw-inspector[hidden] { display: none; }
  .bxw-inspector-head { position: sticky; top: 0; z-index: 1; display: flex; align-items: center; justify-content: space-between;
    gap: 8px; height: 42px; padding: 0 12px; border-bottom: 1px solid var(--bxw-line); background: var(--bxw-panel); }
  .bxw-inspector-head strong { font-size: 12px; font-weight: 600; letter-spacing: .2px; }
  .bxw-inspector-body { padding: 10px 12px 20px; display: flex; flex-direction: column; gap: 16px; }
  .bxw-section { display: flex; flex-direction: column; gap: 7px; }
  .bxw-section[hidden] { display: none; }
  .bxw-focus { display: flex; flex-direction: column; gap: 10px; }
  .bxw-focus-row { display: flex; flex-direction: column; gap: 5px; }
  .bxw-focus-row[data-busy="true"] { opacity: .6; }
  .bxw-focus-head { display: flex; align-items: center; gap: 7px; }
  .bxw-focus-head span { flex: 1; min-width: 0; color: var(--bxw-soft); font-size: 11px;
    line-height: 1.35; white-space: normal; }
  .bxw-focus-number { width: 76px; height: 24px; padding: 0 6px; border: 1px solid var(--bxw-line);
    border-radius: 5px; background: var(--bxw-layer); color: var(--bxw-primary);
    font: 11px/1 var(--dsw-font-mono, ui-monospace, monospace); }
  .bxw-focus-unit { flex: none; color: var(--bxw-muted); font: 10px/1 var(--dsw-font-mono, ui-monospace, monospace); }
  .bxw-focus-range { width: 100%; accent-color: var(--bxw-accent); }  .bxw-focus-actions { display: flex; justify-content: flex-end; margin-top: -2px; }
  .bxw-focus-compare { height: 20px; padding: 0 4px; border: 0; background: transparent;
    color: var(--bxw-accent); font-size: 10px; }
  .bxw-focus-compare:hover { background: color-mix(in srgb, var(--bxw-accent) 9%, transparent); }
  .bxw-node-head { display: flex; align-items: center; gap: 7px; }
  .bxw-node-head b { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .bxw-node-status { margin-left: auto; flex: none; color: var(--bxw-muted);
    font: 9px/1 var(--dsw-font-mono, ui-monospace, monospace); text-transform: uppercase; }
  .bxw-node-status[data-state="failed"] { color: var(--bxw-bad); }
  .bxw-node-status[data-state="done"] { color: var(--bxw-ok); }
  .bxw-node-meta { color: var(--bxw-muted); font: 10px/1.4 var(--dsw-font-mono, ui-monospace, monospace); }
  .bxw-node-actions { display: flex; flex-wrap: wrap; gap: 5px; }
  .bxw-node-actions button { height: 24px; padding: 0 8px; font-size: 10px; }
  .bxw-node-deps { display: flex; flex-wrap: wrap; gap: 4px; }
  .bxw-node-dep { padding: 1px 5px; border: 1px solid var(--bxw-line); border-radius: 4px;
    color: var(--bxw-soft); font: 9px/1.4 var(--dsw-font-mono, ui-monospace, monospace); }
  .bxw-node-block { max-height: 112px; overflow: auto; padding: 6px 7px; border: 1px solid var(--bxw-line);
    border-radius: 5px; background: var(--bxw-layer); color: var(--bxw-soft);
    font: 10px/1.45 var(--dsw-font-mono, ui-monospace, monospace); white-space: pre-wrap; word-break: break-word; }
  .bxw-check-observed { color: var(--bxw-soft); font: 9px/1.4 var(--dsw-font-mono, ui-monospace, monospace);
    word-break: break-word; }
  .bxw-row[data-ok="false"] { cursor: pointer; }
  .bxw-job { display: flex; align-items: center; gap: 7px; padding: 7px 8px; border: 1px solid
    color-mix(in srgb, var(--bxw-accent) 32%, var(--bxw-line)); border-radius: 6px; background: var(--bxw-layer); }
  .bxw-job[hidden] { display: none; }
  .bxw-job span { min-width: 0; flex: 1; color: var(--bxw-soft); font-size: 10px; }
  .bxw-job button { flex: none; height: 23px; padding: 0 7px; font-size: 10px; }
  .bxw-history-row { display: flex; align-items: center; gap: 6px; padding: 4px 0; border-top: 1px solid var(--bxw-line); }
  .bxw-history-row:first-child { border-top: 0; }
  .bxw-history-row b { min-width: 0; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    color: var(--bxw-soft); font-size: 10px; font-weight: 500; }
  .bxw-history-row small { flex: none; color: var(--bxw-muted); font: 9px/1 var(--dsw-font-mono, ui-monospace, monospace); }
  .bxw-history-row button { flex: none; height: 22px; padding: 0 6px; font-size: 9px; }
  .bxw-doc-actions { display: flex; gap: 6px; }
  .bxw-doc-actions button { height: 25px; font-size: 10px; }
  .bxw-dimensions { display: flex; flex-direction: column; gap: 6px; }
  .bxw-dimension { display: flex; align-items: center; gap: 6px; }
  .bxw-dimension label { min-width: 0; flex: 1; color: var(--bxw-soft); font-size: 11px;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .bxw-dimension input { width: 76px; height: 25px; padding: 0 6px; border: 1px solid var(--bxw-line);
    border-radius: 5px; background: var(--bxw-layer); color: var(--bxw-primary);
    font-size: 11px; text-align: right; }
  .bxw-dimension-unit { min-width: 26px; color: var(--bxw-muted); font-size: 9px; }
  .bxw-dimension button { height: 24px; padding: 0 7px; font-size: 10px; }
  .bxw-dimension[data-busy="true"] { opacity: .55; }
  .bxw-dimension input[data-invalid="true"] { border-color: var(--bxw-bad); }
  .bxw-check[hidden] { display: none; }
  .bxw-section-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
  .bxw-section-head h3 { margin: 0; }
  .bxw-section h3 { margin: 0; color: var(--bxw-muted); font-size: 10px; font-weight: 650;
    letter-spacing: .9px; text-transform: uppercase; }
  .bxw-metrics { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
  .bxw-metric { padding: 8px 9px; border: 1px solid var(--bxw-line); border-radius: 6px; background: var(--bxw-layer); }
  .bxw-metric span { display: block; color: var(--bxw-muted); font-size: 10px; }
  .bxw-metric b { display: block; margin-top: 2px; font: 12px/1.35 var(--dsw-font-mono, ui-monospace, monospace); font-weight: 500; }
  .bxw-list { display: flex; flex-direction: column; gap: 2px; margin: 0; padding: 0; list-style: none; }
  .bxw-row { display: flex; align-items: center; gap: 8px; min-width: 0; padding: 6px 7px; border-radius: 5px; }
  .bxw-row:hover { background: var(--bxw-layer); }
  .bxw-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--bxw-muted); flex: none; }
  .bxw-dot[data-state="done"] { background: var(--bxw-ok); }
  .bxw-dot[data-state="failed"] { background: var(--bxw-bad); }
  .bxw-dot[data-state="running"] { background: var(--bxw-warn); }
  .bxw-row-main { min-width: 0; flex: 1; }
  .bxw-row-main b { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; font-weight: 500; }
  .bxw-row-main span { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    color: var(--bxw-muted); font: 10px/1.35 var(--dsw-font-mono, ui-monospace, monospace); }
  .bxw-check { font-size: 11px; color: var(--bxw-soft); }
  .bxw-check[data-ok="false"] { color: var(--bxw-bad); }
  .bxw-dock { position: absolute; left: 50%; bottom: 12px; transform: translateX(-50%); z-index: 15;
    width: min(900px, calc(100% - 28px)); display: flex; flex-direction: column;
    min-height: 0; border: 1px solid var(--bxw-line); border-radius: 10px; background: var(--bxw-panel);
    box-shadow: 0 12px 34px rgb(0 0 0 / 14%); }
  .bxw-history-peek { position: absolute; right: 18px; bottom: calc(100% + 7px); z-index: 18; width: min(420px, 70vw);
    max-height: 120px; overflow: hidden; padding: 8px 10px; border: 1px solid var(--bxw-line); border-radius: 7px;
    background: var(--bxw-panel); color: var(--bxw-soft); box-shadow: 0 10px 26px rgb(0 0 0 / 18%); font-size: 11px; line-height: 1.5; }
  .bxw-history-peek[hidden] { display: none; }
  .bxw-dock-active { display: flex; align-items: center; gap: 9px; min-height: 38px; padding: 7px 18px; border-bottom: 1px solid var(--bxw-line);
    border-radius: 10px 10px 0 0;
    background: color-mix(in srgb, var(--bxw-accent) 6%, var(--bxw-panel)); }
  .bxw-dock-active[hidden] { display: none; }
  .bxw-dock-active b { color: var(--bxw-primary); font-size: 12px; font-weight: 550; flex: none; }
  .bxw-dock-active span { min-width: 0; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--bxw-soft); font-size: 11px; }
  .bxw-dock-active button { flex: none; height: 26px; padding: 0 9px; font-size: 11px; }
  .bxw-dock-history { position: absolute; left: 50%; bottom: calc(100% + 8px); transform: translateX(-50%); z-index: 18;
    width: min(700px, calc(100vw - 48px)); height: min(360px, 44vh); min-height: 180px; overflow: hidden; display: flex; flex-direction: column;
    border: 1px solid var(--bxw-line); border-radius: 10px; background: var(--bxw-panel); box-shadow: 0 18px 46px rgb(0 0 0 / 24%); }
  .bxw-dock-history[hidden] { display: none; }
  .bxw-dock-history .bxw-agent-slot { width: 100%; max-width: 660px; margin: 0 auto; padding: 8px 16px 12px; }
  .bxw-dock-history:has([data-question-key]) { width: min(900px, calc(100vw - 48px)); height: min(560px, 62vh); }
  .bxw-dock-history:has([data-question-key]) .bxw-agent-slot { max-width: 860px; }
  .bxw-variants { position: absolute; left: 50%; bottom: calc(var(--bxw-dock-h, 112px) + 14px);
    transform: translateX(-50%); z-index: 14; width: min(920px, calc(100% - 28px));
    display: flex; flex-direction: column; overflow: hidden;
    border: 1px solid var(--bxw-line); border-radius: 10px; background: var(--bxw-panel);
    box-shadow: 0 16px 40px rgb(0 0 0 / 20%); }
  .bxw-variants[hidden] { display: none; }
  .bxw-shell[data-history="on"] .bxw-variants { display: none; }
  .bxw-shell[data-inspector="on"] .bxw-variants {
    left: calc((100% - min(var(--bxw-right-width, 292px), 36vw)) / 2);
    width: min(720px, calc(100% - min(var(--bxw-right-width, 292px), 36vw) - 56px)); }
  .bxw-variants-head { display: flex; align-items: center; gap: 8px; padding: 8px 12px;
    border-bottom: 1px solid var(--bxw-line); }
  .bxw-variants-head strong { font-size: 11px; font-weight: 600; }
  .bxw-variants-head span { min-width: 0; overflow: hidden; text-overflow: ellipsis;
    white-space: nowrap; color: var(--bxw-muted); font-size: 10px; }
  .bxw-variants-actions { display: flex; gap: 6px; margin-left: auto; }
  .bxw-variants-actions button { height: 24px; padding: 0 8px; font-size: 10px; }
  .bxw-variants-actions button[hidden] { display: none; }
  .bxw-variants-grid { display: flex; gap: 8px; padding: 10px 12px; overflow-x: auto; }
  .bxw-variant { flex: 1 1 0; min-width: 176px; display: flex; flex-direction: column;
    border: 1px solid var(--bxw-line); border-radius: 8px; background: var(--bxw-layer);
    overflow: hidden; cursor: pointer; }
  .bxw-variant:hover { border-color: color-mix(in srgb, var(--bxw-accent) 38%, var(--bxw-line)); }
  .bxw-variant[data-active="true"] { border-color: var(--bxw-accent);
    box-shadow: 0 0 0 1px color-mix(in srgb, var(--bxw-accent) 45%, transparent); }
  .bxw-variant[data-failed="true"] { opacity: .62; cursor: default; }
  .bxw-variant-thumb { width: 100%; height: 98px; object-fit: contain;
    background: color-mix(in srgb, var(--bxw-canvas, #f2f5f9) 80%, var(--bxw-panel));
    border-bottom: 1px solid var(--bxw-line); }
  .bxw-variant-thumb.empty { display: flex; align-items: center; justify-content: center;
    color: var(--bxw-muted); font-size: 9px; }
  .bxw-variant-body { display: flex; flex-direction: column; gap: 3px; padding: 7px 8px 4px; }
  .bxw-variant-label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    color: var(--bxw-primary); font-size: 11px; font-weight: 600; }
  .bxw-variant-meta { color: var(--bxw-muted); font: 9px/1.35 var(--dsw-font-mono, ui-monospace, monospace); }
  .bxw-variant-status { color: var(--bxw-muted); font-size: 9px; line-height: 1.35; }
  .bxw-variant-status[data-ok="false"] { color: var(--bxw-danger, #c94f4f); }
  .bxw-variant-buttons { display: flex; gap: 5px; padding: 4px 8px 8px; margin-top: auto; }
  .bxw-variant-buttons button { flex: 1; height: 24px; font-size: 10px; }
  .bxw-variants-loading { padding: 20px 14px; color: var(--bxw-muted); font-size: 11px; }
  .bxw-candidates { position: absolute; left: 50%; bottom: calc(var(--bxw-dock-h, 112px) + 14px);
    transform: translateX(-50%); z-index: 14; width: min(920px, calc(100% - 28px));
    display: flex; flex-direction: column; overflow: hidden;
    border: 1px solid var(--bxw-line); border-radius: 10px; background: var(--bxw-panel);
    box-shadow: 0 16px 40px rgb(0 0 0 / 20%); }
  .bxw-candidates[hidden] { display: none; }
  .bxw-shell[data-history="on"] .bxw-candidates { display: none; }
  .bxw-shell[data-inspector="on"] .bxw-candidates {
    left: calc((100% - min(var(--bxw-right-width, 292px), 36vw)) / 2);
    width: min(720px, calc(100% - min(var(--bxw-right-width, 292px), 36vw) - 56px)); }
  .bxw-candidates-head { display: flex; align-items: center; gap: 8px; padding: 8px 12px;
    border-bottom: 1px solid var(--bxw-line); }
  .bxw-candidates-head strong { font-size: 11px; font-weight: 600; }
  .bxw-candidates-head span { min-width: 0; overflow: hidden; text-overflow: ellipsis;
    white-space: nowrap; color: var(--bxw-muted); font-size: 10px; }
  .bxw-candidates-head button { margin-left: auto; height: 24px; padding: 0 8px; font-size: 10px; }
  .bxw-candidates-note { padding: 8px 12px; color: var(--bxw-soft); font-size: 11px; line-height: 1.5; }
  .bxw-candidates-grid { display: flex; gap: 8px; padding: 10px 12px; overflow-x: auto; }
  .bxw-candidates .bxw-candidate { flex: 1 1 0; min-width: 196px; height: auto; display: flex; flex-direction: column;
    align-items: stretch; justify-content: flex-start; gap: 5px; white-space: normal;
    padding: 10px; border: 1px solid var(--bxw-line); border-radius: 8px;
    background: var(--bxw-layer); text-align: left; cursor: pointer; }
  .bxw-candidate:hover, .bxw-candidate:focus-visible { border-color: var(--bxw-accent);
    box-shadow: 0 0 0 1px color-mix(in srgb, var(--bxw-accent) 35%, transparent); }
  .bxw-candidate[data-locate="failed"] { border-color: color-mix(in srgb, var(--bxw-danger, #c94f4f) 35%, var(--bxw-line)); }
  .bxw-candidate-id { color: var(--bxw-primary); font: 11px/1.3 var(--dsw-font-mono, ui-monospace, monospace); font-weight: 650; }
  .bxw-candidate-what { color: var(--bxw-soft); font-size: 11px; line-height: 1.4; }
  .bxw-candidate-type { color: var(--bxw-muted); font-size: 9px; }
  .bxw-candidate-reasons { color: var(--bxw-muted); font-size: 10px; line-height: 1.45; }
  .bxw-candidate-status { color: var(--bxw-muted); font-size: 9px; line-height: 1.35; }
  .bxw-candidate-status[data-failed="true"] { color: var(--bxw-danger, #c94f4f); }
  .bxw-dock-bar { height: 30px; flex: none; display: flex; align-items: center; gap: 8px; padding: 0 18px; background: var(--bxw-panel);
    border-radius: 10px 10px 0 0; }
  .bxw-dock:has(.bxw-dock-active:not([hidden])) .bxw-dock-bar { border-radius: 0; }
  .bxw-dock-agent { height: 24px; padding: 0 7px; border-color: transparent; color: var(--bxw-soft); font-size: 11px; }
  .bxw-dock-agent svg { width: 14px; height: 14px; }
  .bxw-dock-agent[aria-pressed="true"] { color: var(--bxw-accent); background: color-mix(in srgb, var(--bxw-accent) 9%, transparent); }
  .bxw-dock-status { min-width: 0; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--bxw-muted); font-size: 10px; }
  .bxw-dock-history-toggle { height: 24px; padding: 0 7px; border-color: transparent; color: var(--bxw-muted); font-size: 10px; }
  .bxw-dock-history-toggle:hover { color: var(--bxw-primary); background: var(--bxw-layer); }
  .bxw-composer { border-top: 0; background: var(--bxw-panel); padding: 0 10px 10px; border-radius: 0 0 10px 10px; }
  .bxw-composer[data-target="agent"] { border-top-color: color-mix(in srgb, var(--bxw-accent) 45%, var(--bxw-line)); }
  .bxw-composer-target { flex: none; height: 30px; display: inline-flex; align-items: center; padding: 0 8px;
    border: 1px solid var(--bxw-line); border-radius: 999px; color: var(--bxw-muted); font-size: 10px; user-select: none; }
  .bxw-composer[data-target="agent"] .bxw-composer-target { color: var(--bxw-accent); border-color: color-mix(in srgb, var(--bxw-accent) 45%, var(--bxw-line)); }
  .bxw-composer-box { max-width: none; margin: 0; display: flex; align-items: flex-end; gap: 8px;
    padding: 7px; border: 1px solid var(--bxw-line); border-radius: 8px; background: var(--bxw-layer); }
  .bxw-composer-box:focus-within { border-color: color-mix(in srgb, var(--bxw-accent) 70%, var(--bxw-line)); }
  .bxw-composer textarea { flex: 1; min-height: 34px; max-height: 120px; resize: none; border: 0; outline: 0;
    background: transparent; padding: 7px 8px; line-height: 1.5; }
  .bxw-composer textarea::placeholder { color: var(--bxw-muted); }
  .bxw-send { height: 34px; padding: 0 14px; border-color: color-mix(in srgb, var(--bxw-accent) 60%, transparent);
    background: color-mix(in srgb, var(--bxw-accent) 16%, transparent); color: var(--bxw-primary, #e8edf5); }
  .bxw-send:hover { background: color-mix(in srgb, var(--bxw-accent) 26%, transparent); }
  .bxw-hint { max-width: none; margin: 6px 0 0; color: var(--bxw-muted); font-size: 10px; }
  .bxw-toast { position: fixed; right: 20px; bottom: calc(var(--bxw-dock-h, 112px) + 24px); z-index: 30; max-width: 360px; padding: 9px 12px;
    border: 1px solid var(--bxw-line); border-radius: 7px; background: var(--bxw-panel); color: var(--bxw-soft);
    box-shadow: 0 10px 28px rgb(0 0 0 / 28%); opacity: 0; transform: translateY(6px); pointer-events: none;
    transition: opacity .16s ease, transform .16s ease; font-size: 12px; }
  .bxw-toast[data-on="true"] { opacity: 1; transform: none; }
  .bxw-toast[data-tone="error"] { border-color: color-mix(in srgb, var(--bxw-bad) 45%, var(--bxw-line)); color: var(--bxw-bad); }
  @media (max-width: 1280px) {
    .bxw-models { width: min(var(--bxw-left-width, 210px), 38vw); }
    .bxw-inspector { width: min(var(--bxw-right-width, 292px), 42vw); }
    .bxw-resizer-left { left: calc(14px + min(var(--bxw-left-width, 210px), 38vw)); }
    .bxw-resizer-right { right: calc(14px + min(var(--bxw-right-width, 292px), 42vw)); }
  }
  @media (max-width: 1180px) {
    .bxw-context-label, .bxw-version { display: none; }
    .bxw-context select { max-width: min(300px, 34vw); }
  }
  @media (max-width: 960px) {
    .bxw-metric { display: none; }
    .bxw-tools button { padding: 0 5px; }
    .bxw-review-trigger span { display: none; }
    .bxw-scopes button { min-width: 20px; padding: 0 4px; }
  }
  @media (max-width: 720px) {
    .bxw-models, .bxw-inspector, .bxw-resizer, .bxw-structure-trigger { display: none; }
    .bxw-brand span { display: none; }
    .bxw-context select { max-width: 32vw; }
  }
  @media (prefers-reduced-motion: reduce) {
    .bxw-toast { transition: none; }
  }
`

const svg = (path, size = 16) => `<svg class="bxw-icon" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${path}</svg>`
const ICONS = {
  cube: svg('<path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Z"/><path d="m4 7.5 8 4.5 8-4.5M12 12v9"/>'),
  chat: svg('<path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4v8Z"/>'),
  chevron: svg('<path d="m7 10 5 5 5-5"/>'),
  panel: svg('<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M15 4v16"/>'),
  sliders: svg('<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>'),
  fit: svg('<path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/>'),
  wire: svg('<path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Z"/><path d="M4 7.5 12 12l8-4.5M12 12v9"/>'),
  refresh: svg('<path d="M20 11a8 8 0 1 0-2.3 5.7"/><path d="M20 4v7h-7"/>'),
  review: svg('<path d="M4 4h16v16H4z"/><path d="m8 12 3 3 5-6"/>'),
  ghost: svg('<path d="M12 3a7 7 0 0 1 7 7v11l-3-2-2 2-2-2-2 2-2-2-3 2V10a7 7 0 0 1 7-7Z"/><circle cx="9" cy="10" r="1"/><circle cx="15" cy="10" r="1"/>'),
  section: svg('<path d="M4 7h16v10H4z"/><path d="M4 12h16"/>'),
  measure: svg('<path d="m3 17 14-14 4 4L7 21z"/><path d="m7 13 4 4M11 9l4 4"/>'),
  download: svg('<path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M4 21h16"/>'),
  send: svg('<path d="m22 2-7 20-4-9-9-4 20-7Z"/><path d="M22 2 11 13"/>'),
  close: svg('<path d="m6 6 12 12M18 6 6 18"/>'),
  plus: svg('<path d="M12 5v14M5 12h14"/>'),
}

const el = (tag, attrs = {}, text) => {
  const node = document.createElement(tag)
  for (const [key, value] of Object.entries(attrs)) {
    if (value == null) continue
    if (key === 'className') node.className = value
    else if (key === 'style') node.style.cssText = value
    else if (key === 'html') node.innerHTML = value
    else if (key.startsWith('aria-') || key === 'role' || key === 'title') node.setAttribute(key, value)
    else node[key] = value
  }
  if (text != null) node.textContent = text
  return node
}

const fmt = (value, digits = 0) => {
  if (value == null || Number.isNaN(Number(value))) return '—'
  return Number(value).toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits })
}

const api = async (url, options) => {
  const response = await fetch(url, options)
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`
    let hint = ''
    try {
      const payload = await response.json()
      if (payload?.error?.message) message = payload.error.message
      if (payload?.error?.hint) hint = payload.error.hint
    } catch (error) { /* status is enough */ }
    const failure = new Error(message)
    failure.hint = hint
    throw failure
  }
  return response.json()
}

const style = () => {
  if (document.getElementById(STYLE_ID)) return
  const tag = el('style', { id: STYLE_ID })
  tag.textContent = css
  document.head.append(tag)
}

const readTheme = () => {
  const style = getComputedStyle(document.body)
  const parse = (value, fallback) => {
    const match = String(value || '').match(/rgba?\(([^)]+)\)/)
    if (!match) return fallback
    const [r, g, b, a = 1] = match[1].split(',').map((n) => Number(n.trim()))
    return [r, g, b].some(Number.isNaN) || a === 0 ? fallback : { r, g, b }
  }
  const background = parse(style.backgroundColor, { r: 16, g: 19, b: 24 })
  const foreground = parse(style.color, { r: 232, g: 237, b: 245 })
  const light = (0.299 * background.r + 0.587 * background.g + 0.114 * background.b) / 255 > 0.5
  return { background: `rgb(${background.r}, ${background.g}, ${background.b})`, foreground: `rgb(${foreground.r}, ${foreground.g}, ${foreground.b})`, light }
}

export function mountWorkbench(host, options) {
  style()
  document.body.classList.add('bxw-workbench')
  host.textContent = ''
  const base = options.base
  const state = {
    documents: [],
    docId: options.documentId || null,
    sessionId: options.sessionId || options.getSessionId?.() || null,
    current: null,
    plan: null,
    checks: null,
    version: 0,
    request: 0,
    shown: -1,
    ready: false,
    wire: false,
    pickScope: 'face',
    inspector: true,
    busy: false,
    selection: null,
    leftWidth: 260,
    rightWidth: 320,
    timings: {},
    designStarted: null,
    renderMs: null,
    modeling: false,
    simplified: false,
    ghost: false,
    ghostVersion: null,
    section: { on: false, axis: 'Z', t: 0.5 },
    measure: false,
    measureResult: null,
    variantSet: null,
    variantPreview: null,
    variantBusy: false,
    variantApplying: null,
    candidates: null,
    candidateBusy: false,
    reference: null,
    selectedNode: null,
    job: null,
    jobTimer: null,
    dimensions: null,
    dimensionFeature: null,
    dimensionBusy: false,
    handle: null,
    handleBusy: false,
    drag: null,
    historyOpen: false,
    dockQuestion: false,
    dockQuestionText: '',
  }

  const shell = el('div', { className: 'bxw-shell' })
  const header = el('header', { className: 'bxw-header' })
  const brand = el('div', { className: 'bxw-brand' })
  brand.append(el('span', { className: 'bxw-mark', html: ICONS.cube }), el('span', {}, 'BrepX'))
  const context = el('div', { className: 'bxw-context' })
  const contextLabel = el('span', { className: 'bxw-context-label' }, '模型')
  const docSelect = el('select', { 'aria-label': '当前模型' })
  const version = el('span', { className: 'bxw-version' }, '')
  const checkBadge = el('button', { type: 'button', className: 'bxw-badge bxw-badge-button', 'aria-label': '打开检查器', title: '打开检查器' }, '检查 —')
  const metricBadge = el('span', { className: 'bxw-badge bxw-metric' }, '—')
  context.append(contextLabel, docSelect, version, checkBadge, metricBadge)
  const actions = el('div', { className: 'bxw-actions' })
  const importInput = el('input', {
    type: 'file',
    accept: '.step,.stp,.stl,.iges,.igs,.brep',
    hidden: true,
    'aria-hidden': 'true',
  })
  const importButton = el('button', {
    className: 'bxw-import-trigger',
    title: '导入参考几何（当前模型已有特征时会新建模型）',
    'aria-label': '导入参考几何',
  }, '导入')
  importButton.addEventListener('click', () => {
    if (!state.docId) {
      toast('先选择一个模型，再导入参考几何', 'info', 3)
      return
    }
    importInput.click()
  })
  importInput.addEventListener('change', () => {
    const file = importInput.files?.[0]
    importInput.value = ''
    if (file) importReference(file)
  })
  const structureButton = el('button', {
    className: 'bxw-structure-trigger',
    title: '显示或隐藏结构',
    'aria-label': '显示或隐藏结构',
    'aria-pressed': 'false',
    html: ICONS.panel + '<span>结构</span>',
  })
  const viewButton = el('button', {
    className: 'bxw-view-trigger',
    title: '视图与刷新',
    'aria-label': '视图与刷新',
    'aria-haspopup': 'menu',
    'aria-expanded': 'false',
    html: ICONS.sliders + '<span>视图</span>' + ICONS.chevron,
  })
  const viewMenu = el('div', {
    className: 'bxw-view-menu',
    role: 'menu',
    'aria-label': '视图与刷新',
    hidden: true,
  })
  const menuModels = el('button', { type: 'button', role: 'menuitemcheckbox', 'aria-checked': 'true' }, '结构面板')
  const menuNav = el('button', { type: 'button', role: 'menuitem' }, '宿主侧栏')
  const menuInspector = el('button', { type: 'button', role: 'menuitemcheckbox', 'aria-checked': 'true' }, '检查器')
  const menuRefresh = el('button', { type: 'button', role: 'menuitem' }, '刷新模型状态')
  viewMenu.append(menuModels, menuNav, menuInspector, el('div', { className: 'bxw-menu-sep' }), menuRefresh)
  const reviewButton = el('button', {
    className: 'bxw-review-trigger',
    title: '审查工具',
    'aria-label': '审查工具',
    'aria-haspopup': 'dialog',
    'aria-expanded': 'false',
    html: ICONS.review + '<span>审查</span>' + ICONS.chevron,
  })
  const reviewMenu = el('div', {
    className: 'bxw-review-menu',
    role: 'dialog',
    'aria-label': '审查工具',
    hidden: true,
  })
  const reviewScrim = el('div', { className: 'bxw-menu-scrim', hidden: true })
  const reviewSection = (title) => {
    const section = el('section', { className: 'bxw-review-section' })
    const head = el('div', { className: 'bxw-review-head' })
    head.append(el('h3', {}, title))
    section.append(head)
    return { section, head }
  }
  const ghostSection = reviewSection('残影对比')
  const ghostMeta = el('span', { className: 'bxw-review-meta' }, '')
  const ghostToggle = el('button', { type: 'button', 'aria-pressed': 'false' }, '开启残影')
  ghostSection.head.append(ghostMeta, ghostToggle)
  ghostSection.section.append(el('div', { className: 'bxw-review-note' }, '半透明叠加上一里程碑，相机保持不变。'))
  const ghostRow = el('div', { className: 'bxw-review-row' })
  const ghostSelect = el('select', { className: 'bxw-review-select', 'aria-label': '残影基准版本' })
  ghostRow.append(ghostSelect)
  ghostSection.section.append(ghostRow)
  const sectionSection = reviewSection('动态剖切')
  const sectionToggle = el('button', { type: 'button', 'aria-pressed': 'false' }, '开启剖切')
  sectionSection.head.append(sectionToggle)
  const sectionControls = el('div', { className: 'bxw-review-row' })
  const sectionAxisGroup = el('div', { className: 'bxw-review-seg', role: 'group', 'aria-label': '剖切轴' })
  const sectionAxisButtons = {}
  for (const axis of ['X', 'Y', 'Z']) {
    const button = el('button', { type: 'button', 'aria-pressed': axis === state.section.axis ? 'true' : 'false' }, axis)
    button.addEventListener('click', () => {
      state.section.axis = axis
      for (const [name, node] of Object.entries(sectionAxisButtons)) {
        node.setAttribute('aria-pressed', name === axis ? 'true' : 'false')
      }
      post('section', { ...state.section })
    })
    sectionAxisButtons[axis] = button
    sectionAxisGroup.append(button)
  }
  const sectionRange = el('input', {
    type: 'range', min: '0', max: '1', step: '0.01', value: String(state.section.t),
    className: 'bxw-review-range', 'aria-label': '剖切位置',
  })
  sectionRange.disabled = true
  sectionRange.addEventListener('input', () => {
    state.section.t = Number(sectionRange.value)
    post('section', { ...state.section })
  })
  sectionControls.append(sectionAxisGroup, sectionRange)
  sectionSection.section.append(sectionControls)
  const measureSection = reviewSection('几何测量')
  const measureToggle = el('button', { type: 'button', 'aria-pressed': 'false' }, '开始测量')
  measureSection.head.append(measureToggle)
  measureSection.section.append(el('div', { className: 'bxw-review-note' }, '在画布上点两处，显示距离、三轴分量与法向夹角。'))
  const exportSection = reviewSection('导出当前版本')
  const exportGrid = el('div', { className: 'bxw-review-export' })
  for (const [format, label] of [['step', 'STEP'], ['stl', 'STL'], ['glb', 'GLB'], ['cfd', 'CFD JSON']]) {
    const button = el('button', { type: 'button', title: `导出 ${label}` }, label)
    button.addEventListener('click', () => { downloadExport(format).catch(() => {}) })
    exportGrid.append(button)
  }
  exportSection.section.append(exportGrid)
  reviewMenu.append(ghostSection.section, sectionSection.section, measureSection.section, exportSection.section)
  actions.append(importButton, importInput, structureButton, viewButton, reviewButton, viewMenu, reviewMenu)
  const progressLine = el('div', { className: 'bxw-progress', 'aria-hidden': 'true' })
  header.append(brand, context, actions, progressLine)

  const main = el('main', { className: 'bxw-main' })
  const stage = el('section', { className: 'bxw-stage' })
  const frame = el('iframe', { className: 'bxw-frame', title: '3D 模型', src: `${base}/api/kernel-view` })
  const tools = el('div', { className: 'bxw-tools' })
  const toolButtons = {}
  for (const [name, label] of [['iso', '等轴'], ['front', '前'], ['top', '顶'], ['right', '右']]) {
    const button = el('button', { type: 'button', title: `${label}视图` }, label)
    button.addEventListener('click', () => post('view', { name }))
    toolButtons[name] = button
    tools.append(button)
  }
  tools.append(el('span', { className: 'bxw-sep' }))
  const fitButton = el('button', { type: 'button', title: '适配视图', html: ICONS.fit })
  fitButton.addEventListener('click', () => post('fit', {}))
  const wireButton = el('button', { type: 'button', title: '线框模式', html: ICONS.wire })
  wireButton.setAttribute('aria-pressed', 'false')
  wireButton.addEventListener('click', () => {
    state.wire = !state.wire
    wireButton.setAttribute('aria-pressed', state.wire ? 'true' : 'false')
    post('wire', { on: state.wire })
  })
  tools.append(fitButton, wireButton)
  tools.append(el('span', { className: 'bxw-sep' }))
  const scopeGroup = el('div', { className: 'bxw-scopes', role: 'group', 'aria-label': '选择范围' })
  const scopeButtons = {}
  for (const [scope, label, title] of [
    ['body', '体', '选择整个实体'],
    ['face', '面', '选择面'],
    ['edge', '边', '选择边'],
    ['point', '点', '选择顶点'],
  ]) {
    const button = el('button', { type: 'button', title, 'aria-pressed': scope === state.pickScope ? 'true' : 'false' }, label)
    button.addEventListener('click', () => setPickScope(scope))
    scopeButtons[scope] = button
    scopeGroup.append(button)
  }
  tools.append(scopeGroup)
  header.insertBefore(tools, actions)
  const caption = el('div', { className: 'bxw-caption' })
  const captionFaces = el('span', {}, '—')
  const captionTight = el('span', {}, '—')
  const captionTiming = el('span', {}, '')
  caption.append(captionFaces, captionTight, captionTiming)
  const empty = el('div', { className: 'bxw-empty' })
  const emptyCard = el('div', { className: 'bxw-empty-card' })
  const emptySpinner = el('div', { className: 'bxw-spinner', hidden: true })
  const emptyTitle = el('h2', {}, '选择一个模型')
  const emptyBody = el('p', {}, '新建文档或从模型库打开已有文档，画布会在这里显示。')
  emptyCard.append(emptySpinner, emptyTitle, emptyBody)
  const emptyButton = el('button', { type: 'button', html: ICONS.plus + '<span>新建模型</span>' })
  emptyCard.append(emptyButton)
  empty.append(emptyCard)
  empty.dataset.on = 'false'
  const handleChip = el('div', { className: 'bxw-handle-hint', hidden: true, 'aria-live': 'polite' })
  stage.append(frame, empty, handleChip)

  const models = el('aside', { className: 'bxw-models', 'aria-label': '当前模型结构' })
  const modelsHead = el('div', { className: 'bxw-models-head' })
  const modelsTitle = el('strong', {}, '结构')
  const structureMeta = el('span', { className: 'bxw-structure-meta' }, 'rev —')
  const modelsNew = el('button', { type: 'button', title: '新建模型', 'aria-label': '新建模型', html: ICONS.plus })
  const modelsClose = el('button', { type: 'button', title: '关闭结构面板', 'aria-label': '关闭结构面板', html: ICONS.close })
  modelsHead.append(modelsTitle, structureMeta, modelsClose, modelsNew)
  const structureProgress = el('div', { className: 'bxw-structure-progress', hidden: true })
  const structureList = el('div', { className: 'bxw-structure-list' })
  models.append(modelsHead, structureProgress, structureList)

  const inspector = el('aside', { className: 'bxw-inspector', 'aria-label': '模型检查器' })
  const inspectorHead = el('div', { className: 'bxw-inspector-head' })
  const inspectorTitle = el('strong', {}, '模型检查器')
  const inspectorClose = el('button', { type: 'button', title: '收起检查器', 'aria-label': '收起检查器', html: ICONS.close })
  inspectorClose.addEventListener('click', () => setInspector(false))
  inspectorHead.append(inspectorTitle, inspectorClose)

  const inspectorBody = el('div', { className: 'bxw-inspector-body' })
  const metricsSection = el('section', { className: 'bxw-section' })
  metricsSection.append(el('h3', {}, '几何'))
  const metricsGrid = el('div', { className: 'bxw-metrics' })
  const metricNodes = {}
  for (const [key, label] of [['faces', '面'], ['volume', '体积 mm³'], ['area', '面积 mm²'], ['watertight', '水密']]) {
    const card = el('div', { className: 'bxw-metric' })
    card.append(el('span', {}, label), el('b', {}, '—'))
    metricNodes[key] = card.querySelector('b')
    metricsGrid.append(card)
  }
  metricsSection.append(metricsGrid)

  const selectionSection = el('section', { className: 'bxw-section' })
  selectionSection.append(el('h3', {}, '选择'))
  const selectionSummary = el('div', { className: 'bxw-check' }, '在画布上点选面或边')
  selectionSection.append(selectionSummary)

  const focusSection = el('section', { className: 'bxw-section', hidden: true })
  focusSection.append(el('h3', {}, '焦点参数'))
  const focusList = el('div', { className: 'bxw-focus' })
  focusSection.append(focusList)

  const dimensionSection = el('section', { className: 'bxw-section', hidden: true })
  const dimensionHead = el('div', { className: 'bxw-section-head' })
  const dimensionTitle = el('h3', {}, '尺寸')
  const dimensionRefresh = el('button', { type: 'button', title: '重新读取尺寸', 'aria-label': '重新读取尺寸' }, '刷新')
  dimensionHead.append(dimensionTitle, dimensionRefresh)
  dimensionSection.append(dimensionHead)
  const dimensionHint = el('div', { className: 'bxw-node-meta' }, '')
  const dimensionList = el('div', { className: 'bxw-dimensions' })
  const dimensionError = el('div', { className: 'bxw-check', hidden: true, role: 'alert' })
  dimensionSection.append(dimensionHint, dimensionList, dimensionError)

  const measureInspector = el('section', { className: 'bxw-section', hidden: true })
  const measureHead = el('div', { className: 'bxw-section-head' })
  measureHead.append(el('h3', {}, '测量'))
  const measureClear = el('button', { type: 'button', title: '清除测量', 'aria-label': '清除测量', html: ICONS.close })
  measureHead.append(measureClear)
  const measureText = el('div', { className: 'bxw-check' }, '在画布上点两处')
  measureInspector.append(measureHead, measureText)
  inspectorBody.append(measureInspector)

  const checkSection = el('section', { className: 'bxw-section' })
  checkSection.append(el('h3', {}, '检查'))
  const checkSummary = el('div', { className: 'bxw-check' }, '—')
  const checkList = el('ul', { className: 'bxw-list' })
  checkSection.append(checkSummary, checkList)

  const planSection = el('section', { className: 'bxw-section', hidden: true })
  planSection.append(el('h3', {}, '计划节点'))
  const planHead = el('div', { className: 'bxw-node-head' })
  const planTitle = el('b', {}, '选择一个节点')
  const planStatus = el('span', { className: 'bxw-node-status' }, '')
  planHead.append(planTitle, planStatus)
  const planPicker = el('select', { className: 'bxw-review-select', 'aria-label': '选择计划节点' })
  planPicker.addEventListener('change', () => {
    if (planPicker.value) selectPlanNode(planPicker.value)
  })
  const planActions = el('div', { className: 'bxw-node-actions' })
  const planDetails = el('div', { className: 'bxw-focus' })
  const planJob = el('div', { className: 'bxw-job', hidden: true })
  const planJobText = el('span', {}, '')
  const planJobCancel = el('button', { type: 'button' }, '取消')
  planJob.append(planJobText, planJobCancel)
  planSection.append(planHead, planPicker, planActions, planJob, planDetails)

  const historySection = el('section', { className: 'bxw-section', hidden: true })
  historySection.append(el('h3', {}, '版本历史'))
  const historyList = el('div', {})
  historySection.append(historyList)

  const referenceSection = el('section', { className: 'bxw-section', hidden: true })
  referenceSection.append(el('h3', {}, '参考几何'))
  referenceSection.append(el('div', { className: 'bxw-node-meta' },
    '作为基准体加入当前模型；后续特征与计划节点可引用其 id。'))
  const referenceList = el('div', {})
  referenceSection.append(referenceList)

  const docSection = el('section', { className: 'bxw-section' })
  docSection.append(el('h3', {}, '文档'))
  const docActions = el('div', { className: 'bxw-doc-actions' })
  const docNew = el('button', { type: 'button' }, '新建')
  const docDelete = el('button', { type: 'button' }, '删除当前模型')
  docActions.append(docNew, docDelete)
  docSection.append(docActions)

  inspectorBody.append(metricsSection, selectionSection, focusSection, dimensionSection, planSection,
    checkSection, referenceSection, historySection, docSection)
  inspector.append(inspectorHead, inspectorBody)

  const dock = el('section', { className: 'bxw-dock', 'aria-label': '命令与 Agent' })
  const activeCard = el('div', { className: 'bxw-dock-active', hidden: true })
  const activeTitle = el('b', {}, '')
  const activeBody = el('span', {}, '')
  const activeAction = el('button', { type: 'button' }, '查看')
  activeCard.append(activeTitle, activeBody, activeAction)
  const historyPanel = el('div', { className: 'bxw-dock-history', hidden: true })
  const agentSlot = el('div', { className: 'bxw-agent-slot' })
  historyPanel.append(agentSlot)
  options.onAgentHost?.(agentSlot)
  const dockBar = el('div', { className: 'bxw-dock-bar' })
  const dockAgent = el('button', { type: 'button', className: 'bxw-dock-agent', 'aria-label': '展开 Agent 历史', html: ICONS.chat + '<span>Agent</span>' })
  const dockStatus = el('span', { className: 'bxw-dock-status' }, '等待指令')
  const historyToggle = el('button', { type: 'button', className: 'bxw-dock-history-toggle' }, '历史')
  dockBar.append(dockAgent, dockStatus, caption, historyToggle)
  const historyPeek = el('div', { className: 'bxw-history-peek', hidden: true })
  dock.append(activeCard, dockBar, historyPanel, historyPeek)

  const composer = el('form', { className: 'bxw-composer' })
  const selectionBar = el('div', { className: 'bxw-selection', hidden: true })
  const composerBox = el('div', { className: 'bxw-composer-box' })
  const composerTarget = el('span', { className: 'bxw-composer-target', 'aria-hidden': 'true' }, '命令')
  const input = el('textarea', {
    rows: 1,
    placeholder: '输入命令，或描述设计变更… 例如 /fit、/checks、把中心孔改为 Ø40',
    'aria-label': '命令或设计意图',
  })
  const send = el('button', { type: 'submit', className: 'bxw-send', 'aria-label': '执行或发送给 Agent', html: ICONS.send + '<span>执行</span>' })
  composerBox.append(composerTarget, input, send)
  composer.dataset.target = 'inspect'
  const hint = el('div', { className: 'bxw-hint' }, '/fit /top /front /checks /find /agent /new   ·   Enter 执行 · Shift+Enter 换行')
  composer.append(selectionBar, composerBox, hint)

  dock.append(composer)
  const variantPanel = el('div', {
    className: 'bxw-variants', role: 'region', 'aria-label': '方案对比', hidden: true,
  })
  const variantHead = el('div', { className: 'bxw-variants-head' })
  const variantTitle = el('strong', {}, '方案对比')
  const variantMeta = el('span', {}, '')
  const variantActions = el('div', { className: 'bxw-variants-actions' })
  const variantBack = el('button', { type: 'button', title: '退出方案预览' }, '返回当前')
  const variantClose = el('button', {
    type: 'button', title: '关闭方案对比', 'aria-label': '关闭方案对比', html: ICONS.close,
  })
  variantActions.append(variantBack, variantClose)
  variantHead.append(variantTitle, variantMeta, variantActions)
  const variantGrid = el('div', { className: 'bxw-variants-grid' })
  variantPanel.append(variantHead, variantGrid)
  variantBack.addEventListener('click', () => exitVariantPreview())
  variantClose.addEventListener('click', () => closeVariants())
  const candidatePanel = el('div', {
    className: 'bxw-candidates', role: 'dialog', 'aria-label': '消歧候选', hidden: true,
  })
  const candidateHead = el('div', { className: 'bxw-candidates-head' })
  const candidateTitle = el('strong', {}, '消歧候选')
  const candidateMeta = el('span', {}, '')
  const candidateClose = el('button', {
    type: 'button', title: '关闭消歧候选', 'aria-label': '关闭消歧候选', html: ICONS.close,
  })
  candidateClose.addEventListener('click', () => closeCandidates())
  candidateHead.append(candidateTitle, candidateMeta, candidateClose)
  const candidateNote = el('div', { className: 'bxw-candidates-note', hidden: true })
  const candidateGrid = el('div', { className: 'bxw-candidates-grid' })
  candidatePanel.append(candidateHead, candidateNote, candidateGrid)
  const toastNode = el('div', { className: 'bxw-toast', role: 'status' })
  const menuScrim = el('div', { className: 'bxw-menu-scrim', hidden: true })
  shell.append(header, main, dock, variantPanel, candidatePanel, menuScrim, reviewScrim, toastNode)
  main.append(models, stage, inspector)
  const leftResizer = el('div', { className: 'bxw-resizer bxw-resizer-left', role: 'separator', tabindex: '0', 'aria-label': '调整结构栏宽度', 'aria-orientation': 'vertical' })
  const rightResizer = el('div', { className: 'bxw-resizer bxw-resizer-right', role: 'separator', tabindex: '0', 'aria-label': '调整检查器宽度', 'aria-orientation': 'vertical' })
  main.append(leftResizer, rightResizer)
  host.append(shell)

  const dockResize = new ResizeObserver(() => {
    shell.style.setProperty('--bxw-dock-h', `${Math.ceil(dock.getBoundingClientRect().height)}px`)
  })
  dockResize.observe(dock)
  const inspectorResize = new ResizeObserver(() => {
    shell.style.setProperty('--bxw-inspector-h', `${Math.ceil(inspector.getBoundingClientRect().height)}px`)
  })
  inspectorResize.observe(inspector)

  let toastTimer = null
  const toast = (text, tone = 'info', seconds = 4) => {
    toastNode.textContent = text
    toastNode.dataset.tone = tone
    toastNode.dataset.on = 'true'
    toastNode.setAttribute('role', tone === 'error' ? 'alert' : 'status')
    clearTimeout(toastTimer)
    toastTimer = setTimeout(() => { toastNode.dataset.on = 'false' }, seconds * 1000)
  }

  const setLoading = (on) => {
    empty.dataset.on = 'true'
    emptySpinner.hidden = !on
    emptyTitle.textContent = on ? '正在加载模型' : '选择一个模型'
    emptyBody.textContent = on
      ? '正在读取几何、计划和检查结果。'
      : '新建文档或从模型库打开已有文档，画布会在这里显示。'
    emptyButton.hidden = on
    if (on) {
      checkBadge.textContent = '加载中…'
      checkBadge.dataset.tone = ''
      metricBadge.textContent = '—'
      captionFaces.textContent = '—'
      captionTight.textContent = '—'
      captionTiming.textContent = ''
      caption.title = ''
    }
  }

  const setInspector = (on) => {
    state.inspector = Boolean(on)
    inspector.hidden = !state.inspector
    rightResizer.hidden = !state.inspector
    shell.dataset.inspector = state.inspector ? 'on' : 'off'
    checkBadge.setAttribute('aria-pressed', state.inspector ? 'true' : 'false')
    menuInspector.setAttribute('aria-checked', state.inspector ? 'true' : 'false')
  }

  const saveLayout = () => {
    try {
      localStorage.setItem('cadview.layout', JSON.stringify({
        left: state.leftWidth,
        right: state.rightWidth,
      }))
    } catch (error) { /* private mode */ }
  }
  const setLeftWidth = (width) => {
    state.leftWidth = Math.max(220, Math.min(380, Math.round(width)))
    shell.style.setProperty('--bxw-left-width', `${state.leftWidth}px`)
    saveLayout()
  }
  const setRightWidth = (width) => {
    state.rightWidth = Math.max(240, Math.min(480, Math.round(width)))
    shell.style.setProperty('--bxw-right-width', `${state.rightWidth}px`)
    saveLayout()
  }

  const startResize = (event, side) => {
    if (event.button !== 0) return
    event.preventDefault()
    const startX = event.clientX
    const startWidth = side === 'left' ? state.leftWidth : state.rightWidth
    const handle = side === 'left' ? leftResizer : rightResizer
    handle.dataset.drag = 'true'
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
    try { handle.setPointerCapture(event.pointerId) } catch (error) { /* non-pointer input */ }
    const onMove = (moveEvent) => {
      const delta = side === 'left' ? moveEvent.clientX - startX : startX - moveEvent.clientX
      if (side === 'left') setLeftWidth(startWidth + delta)
      else setRightWidth(startWidth + delta)
    }
    let ended = false
    const onEnd = () => {
      if (ended) return
      ended = true
      handle.dataset.drag = 'false'
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
      try { handle.releasePointerCapture(event.pointerId) } catch (error) { /* already released */ }
      window.removeEventListener('pointermove', onMove)
      window.removeEventListener('pointerup', onEnd)
      window.removeEventListener('pointercancel', onEnd)
    }
    window.addEventListener('pointermove', onMove)
    window.addEventListener('pointerup', onEnd)
    window.addEventListener('pointercancel', onEnd)
  }

  const setComposerTarget = (agent) => {
    composer.dataset.target = agent ? 'agent' : 'inspect'
    composerTarget.textContent = agent ? 'Agent' : '命令'
    input.placeholder = agent
      ? '回复 Agent，或输入 /命令…'
      : '输入命令，或描述设计变更… 例如 /fit、/checks、把中心孔改为 Ø40'
  }

  const renderDock = () => {
    const question = state.dockQuestion
    const modeling = state.modeling
    dockStatus.textContent = question
      ? 'Agent 需要你确认'
      : modeling
        ? 'Agent 正在建模…'
        : state.historyOpen
          ? '历史已展开'
          : '等待指令'
    dockAgent.setAttribute('aria-pressed', state.historyOpen ? 'true' : 'false')
    historyToggle.textContent = state.historyOpen ? '收起历史' : '历史'
    if (state.historyOpen) {
      activeCard.hidden = true
      dockStatus.hidden = false
      return
    }
    let active = false
    if (question) {
      activeTitle.textContent = 'Agent 待确认'
      activeBody.textContent = state.dockQuestionText || '需要你回答一个问题才能继续。'
      activeAction.textContent = '查看并回答'
      active = true
    } else if (modeling) {
      const nodes = state.plan?.plan?.nodes || []
      const done = nodes.filter((node) => node.status === 'done').length
      const finished = nodes.length > 0 && done === nodes.length
      activeTitle.textContent = finished ? '计划已完成' : 'Agent 正在建模'
      activeBody.textContent = nodes.length
        ? `${done}/${nodes.length} 个计划节点完成${finished ? '，等待 Agent 收尾' : ''}`
        : '正在生成计划…'
      activeAction.textContent = '查看进度'
      active = true
    } else if (state.checks && !state.checks.ok) {
      activeTitle.textContent = '检查未通过'
      activeBody.textContent = `${state.checks.passed}/${state.checks.total} 通过`
      activeAction.textContent = '查看检查'
      active = true
    }
    activeCard.hidden = !active
    dockStatus.hidden = active
  }

  const revealQuestion = () => {
    agentSlot.querySelector('[data-question-key]')?.scrollIntoView({ block: 'nearest' })
  }

  const openHistory = (open) => {
    state.historyOpen = Boolean(open)
    shell.dataset.history = state.historyOpen ? 'on' : 'off'
    if (state.historyOpen) historyPeek.hidden = true
    historyPanel.hidden = !state.historyOpen
    setComposerTarget(state.historyOpen)
    renderDock()
    if (state.historyOpen) {
      requestAnimationFrame(() => requestAnimationFrame(revealQuestion))
    }
  }

  const setDockQuestion = (active, text) => {
    const next = Boolean(active)
    const changed = next !== state.dockQuestion
    state.dockQuestion = next
    state.dockQuestionText = next ? (text || '') : ''
    renderDock()
    if (next && state.historyOpen) {
      requestAnimationFrame(() => requestAnimationFrame(revealQuestion))
    }
    return changed
  }

  const SURFACE_LABELS = {
    planar: '平面', plane: '平面',
    cylindrical: '圆柱面', cylinder: '圆柱面',
    conical: '圆锥面', cone: '圆锥面',
    spherical: '球面', sphere: '球面',
    toroidal: '环面', torus: '环面',
    bspline: '曲面', nurbs: '曲面',
  }
  const ORIENTATION_LABELS = {
    'top (+Z)': '顶面 (+Z)',
    'bottom (-Z)': '底面 (-Z)',
    'left (-X)': '左侧 (-X)',
    'right (+X)': '右侧 (+X)',
    'front (-Y)': '前面 (-Y)',
    'back (+Y)': '后面 (+Y)',
    angled: '斜面',
    face: '面',
  }
  const DIMENSION_LABELS = {
    radius: '半径', r_out: '外半径', r_in: '内半径', diameter: '直径',
    hole_radius: '孔半径', height: '高度', depth: '深度', length: '长度',
    width: '宽度', thickness: '壁厚', size: '尺寸', offset: '偏移',
    distance: '距离', spacing: '孔距', pitch: '节距', count: '数量',
    start_angle: '起始角', angle: '角度', turns: '圈数', wrap: '包角',
    amount: '数量', factor: '系数', fillet_r: '圆角半径',
    x: 'X 位置', y: 'Y 位置', z: 'Z 位置',
  }
  const DIMENSION_UNITS = { deg: '°', degree: '°', degrees: '°', mm: 'mm', rad: 'rad' }
  const LINEAR_DIMENSIONS = new Set([
    'radius', 'r_out', 'r_in', 'diameter', 'hole_radius', 'height', 'depth',
    'length', 'width', 'thickness', 'size', 'offset', 'distance', 'spacing',
    'pitch', 'fillet_r', 'x', 'y', 'z',
  ])
  const ANGLE_DIMENSIONS = new Set(['angle', 'start_angle', 'wrap'])
  let pickSeq = 0
  let dimensionSeq = 0
  let handleSeq = 0

  const selectionText = (pick) => {
    if (!pick) return ''
    if (pick.pending) return '正在解析拾取…'
    const parts = []
    if (pick.scope === 'body') {
      if (pick.feature_id) parts.push(pick.feature_id)
      parts.push('实体')
      if (pick.body_metrics?.faces != null) parts.push(`${pick.body_metrics.faces} 面`)
      if (pick.body_bbox) parts.push(`范围 ${pick.body_bbox.map((value) => fmt(value, 1)).join('×')} mm`)
      if (pick.body_metrics?.volume != null) parts.push(`${fmt(pick.body_metrics.volume, 1)} mm³`)
      return parts.join(' · ')
    }
    if (pick.scope === 'edge') {
      parts.push('边')
      if (Number.isInteger(pick.edge_index)) parts.push(`#${pick.edge_index}`)
      if (pick.edge_length != null) parts.push(`${fmt(pick.edge_length, 2)} mm`)
      if (pick.feature_id) parts.push(pick.feature_id)
      return parts.join(' · ')
    }
    if (pick.scope === 'point') {
      parts.push('顶点')
      if (pick.point) parts.push(`(${pick.point.map((value) => Number(value).toFixed(1)).join(', ')})`)
      if (pick.feature_id) parts.push(pick.feature_id)
      return parts.join(' · ')
    }
    if (pick.feature_id) parts.push(pick.feature_id)
    if (pick.surface_type) parts.push(SURFACE_LABELS[pick.surface_type] || pick.surface_type)
    if (pick.orientation) parts.push(ORIENTATION_LABELS[pick.orientation] || pick.orientation)
    if (Number.isInteger(pick.face_index)) parts.push(`面 ${pick.face_index}`)
    if (pick.area != null) parts.push(`${fmt(pick.area, 1)} mm²`)
    return parts.join(' · ') || '几何面'
  }

  const selectionPoint = (pick) => {
    if (!pick?.point) return ''
    return pick.point.map((value) => Number(value).toFixed(2)).join(', ')
  }

  const formatSelection = (pick) => {
    if (!pick) return ''
    const point = selectionPoint(pick)
    return `选中 ${selectionText(pick)}${point ? ` @(${point})` : ''}`
  }

  const sceneCache = new Map()

  const sceneForDocument = async () => {
    if (!state.docId || !state.current) return null
    const key = `${state.docId}:${state.version}`
    if (sceneCache.has(key)) return sceneCache.get(key)
    const scene = await api(`${base}/api/docs/${state.docId}/scene`)
    sceneCache.set(key, scene)
    return scene
  }

  const nearestOnSegment = (point, a, b) => {
    const ab = [b[0] - a[0], b[1] - a[1], b[2] - a[2]]
    const ap = [point[0] - a[0], point[1] - a[1], point[2] - a[2]]
    const length2 = ab[0] * ab[0] + ab[1] * ab[1] + ab[2] * ab[2]
    const t = length2 > 0 ? Math.min(1, Math.max(0, (ap[0] * ab[0] + ap[1] * ab[1] + ap[2] * ab[2]) / length2)) : 0
    const closest = [a[0] + ab[0] * t, a[1] + ab[1] * t, a[2] + ab[2] * t]
    const dx = point[0] - closest[0]
    const dy = point[1] - closest[1]
    const dz = point[2] - closest[2]
    return { closest, distance: Math.hypot(dx, dy, dz) }
  }

  const nearestEdge = (scene, point) => {
    let best = null
    for (const edge of scene.edges || []) {
      const points = edge.points || []
      for (let index = 1; index < points.length; index += 1) {
        const near = nearestOnSegment(point, points[index - 1], points[index])
        if (!best || near.distance < best.distance) best = { edge, closest: near.closest, distance: near.distance }
      }
    }
    return best
  }

  const nearestVertex = (scene, point) => {
    let best = null
    const visit = (value) => {
      if (!Array.isArray(value) || value.length < 3) return
      const distance = Math.hypot(point[0] - value[0], point[1] - value[1], point[2] - value[2])
      if (!best || distance < best.distance) best = { value: [value[0], value[1], value[2]], distance }
    }
    for (const edge of scene.edges || []) for (const value of edge.points || []) visit(value)
    for (const face of scene.faces || []) for (const value of face.vertices || []) visit(value)
    return best
  }

  const sceneSize = (scene) => {
    let min = [Infinity, Infinity, Infinity]
    let max = [-Infinity, -Infinity, -Infinity]
    for (const edge of scene.edges || []) {
      for (const value of edge.points || []) {
        for (let axis = 0; axis < 3; axis += 1) {
          min[axis] = Math.min(min[axis], value[axis])
          max[axis] = Math.max(max[axis], value[axis])
        }
      }
    }
    if (!min.every(Number.isFinite)) return null
    return [max[0] - min[0], max[1] - min[1], max[2] - min[2]]
  }

  const scopeTolerance = (scene) => {
    const size = sceneSize(scene)
    const diag = size ? Math.hypot(...size) : 0
    return diag > 0 ? Math.max(0.8, diag * 0.012) : 1.5
  }

  const resolveSelection = async (raw) => {
    const documentId = raw.documentId || state.docId
    const version = Number.isFinite(Number(raw.version))
      ? Number(raw.version)
      : state.current?.document?.version
    if (!documentId || version == null) return { ...raw, pending: false, face_index: undefined }
    let semantic = null
    try {
      semantic = await api(`${base}/api/docs/${documentId}/pick`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          version,
          point: raw.point,
          normal: raw.normal,
          area: raw.area,
          face_index: raw.face_index,
        }),
      })
    } catch (error) {
      semantic = null
    }
    const dimensions = semantic?.dimensions || {}
    const resolved = {
      ...raw,
      pending: false,
      feature_id: semantic?.feature_id || '',
      face_index: semantic?.face_index,
      surface_type: semantic?.surface_type || '',
      orientation: dimensions.orientation || '',
      area: dimensions.area ?? raw.area,
      center: dimensions.center || raw.point,
      normal: dimensions.normal || raw.normal,
      label: semantic?.label || '',
      suggested_ref: semantic?.suggested_ref || null,
    }
    if (!raw.scope || raw.scope === 'face') return resolved
    let scene
    try {
      scene = await sceneForDocument()
    } catch (error) {
      return { ...resolved, scopeError: '无法读取该模型的实体/边/点信息' }
    }
    if (!scene) return { ...resolved, scopeError: '当前没有可分析的几何' }
    if (raw.scope === 'body') {
      const centers = (scene.faces || []).map((face) => face.center).filter(Array.isArray)
      return {
        ...resolved,
        scope: 'body',
        feature_id: scene.feature || resolved.feature_id,
        body_metrics: scene.metrics || {},
        body_bbox: sceneSize(scene),
        highlight_centers: centers.length ? centers : (resolved.center ? [resolved.center] : []),
      }
    }
    const tolerance = scopeTolerance(scene)
    if (raw.scope === 'edge') {
      const nearest = nearestEdge(scene, raw.point)
      if (!nearest || nearest.distance > tolerance) {
        return { ...resolved, scope: 'edge', scopeError: '附近没有可命中的边；请放大或切回面选择' }
      }
      return {
        ...resolved,
        scope: 'edge',
        edge_index: nearest.edge.index,
        edge_length: nearest.edge.length,
        point: nearest.closest,
        center: resolved.center || nearest.closest,
        highlight_centers: resolved.center ? [resolved.center] : [nearest.closest],
      }
    }
    if (raw.scope === 'point') {
      const nearest = nearestVertex(scene, raw.point)
      if (!nearest || nearest.distance > tolerance) {
        return { ...resolved, scope: 'point', scopeError: '附近没有可命中的顶点；请放大或切回面选择' }
      }
      return {
        ...resolved,
        scope: 'point',
        point: nearest.value,
        center: resolved.center || nearest.value,
        highlight_centers: resolved.center ? [resolved.center] : [nearest.value],
      }
    }
    return resolved
  }

  const refreshAfterCommit = async () => {
    if (!state.docId) return
    const [view, planView, checks] = await Promise.all([
      api(`${base}/api/docs/${state.docId}/state`),
      api(`${base}/api/docs/${state.docId}/plan`),
      api(`${base}/api/docs/${state.docId}/checks`),
    ])
    if (!view?.document || view.document.id !== state.docId) return
    state.current = view
    state.version = view.document.version
    state.plan = planView
    state.checks = checks ? { ...checks, items: checkItems(checks) } : null
    if (state.selection) state.selection = { ...state.selection, version: state.version }
    renderState()
  }

  const loadDimensions = async (featureId) => {
    const seq = ++dimensionSeq
    state.dimensionFeature = featureId || null
    state.dimensions = null
    renderDimensions()
    if (!featureId || !state.docId) return
    try {
      const dimensions = await api(
        `${base}/api/docs/${state.docId}/dimensions?feature_id=${encodeURIComponent(featureId)}`)
      if (seq !== dimensionSeq) return
      state.dimensions = dimensions
      renderDimensions()
    } catch (error) {
      if (seq !== dimensionSeq) return
      state.dimensions = null
      renderDimensions()
      toast(`读取尺寸失败：${error.message}`, 'error', 4)
    }
  }

  const applyDimension = async (param, input, row) => {
    if (!state.docId || !state.dimensionFeature || state.dimensionBusy) return
    const raw = input.value.trim()
    const value = Number(raw)
    let problem = ''
    if (raw === '' || !Number.isFinite(value)) problem = '请输入数值'
    else if (param.integer && !Number.isInteger(value)) problem = '需要整数'
    else if (param.minimum != null && value < param.minimum) problem = `不能小于 ${param.minimum}`
    else if (param.maximum != null && value > param.maximum) problem = `不能大于 ${param.maximum}`
    if (problem) {
      input.dataset.invalid = 'true'
      dimensionError.hidden = false
      dimensionError.textContent = `${param.label || param.name}：${problem}`
      toast(dimensionError.textContent, 'error', 4)
      return
    }
    if (value === param.value) {
      input.dataset.invalid = 'false'
      return
    }
    input.dataset.invalid = 'false'
    dimensionError.hidden = true
    state.dimensionBusy = true
    row.dataset.busy = 'true'
    try {
      await api(`${base}/api/docs/${state.docId}/tweak`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          base_version: state.version,
          changes: [{ feature_id: state.dimensionFeature, params: { [param.name]: value } }],
          title: `尺寸 ${state.dimensionFeature}.${param.name} = ${value}${param.unit || ''}`,
        }),
      })
      toast(`已更新 ${param.name} = ${value}`, 'info', 2)
      await refreshAfterCommit()
      await loadDimensions(state.dimensionFeature)
      post('handle', null)
      state.handle = null
      setHandleHint(null)
    } catch (error) {
      input.value = String(param.value)
      input.dataset.invalid = 'true'
      dimensionError.hidden = false
      dimensionError.textContent = `更新失败：${error.message}${error.hint ? ` · ${error.hint}` : ''}`
      toast(dimensionError.textContent, 'error', 6)
    } finally {
      state.dimensionBusy = false
      row.dataset.busy = 'false'
    }
  }

  const renderDimensions = () => {
    const featureId = state.dimensionFeature
    dimensionSection.hidden = !featureId
    dimensionError.hidden = true
    dimensionError.textContent = ''
    dimensionList.textContent = ''
    if (!featureId) return
    dimensionTitle.textContent = `尺寸 · ${featureId}`
    const dimensions = state.dimensions
    if (!dimensions) {
      dimensionHint.textContent = '正在读取尺寸…'
      return
    }
    dimensionHint.textContent = dimensions.feature_type || ''
    if (!dimensions.params?.length) {
      dimensionHint.textContent = '这个特征没有可直接编辑的数值参数'
      return
    }
    for (const param of dimensions.params) {
      const row = el('div', { className: 'bxw-dimension' })
      const range = []
      if (param.minimum != null) range.push(`≥ ${param.minimum}`)
      if (param.maximum != null) range.push(`≤ ${param.maximum}`)
      const baseLabel = DIMENSION_LABELS[param.name] || param.label || param.name
      const label = el('label', {
        title: param.label || param.name,
      }, baseLabel + (range.length ? ` (${range.join(' ')})` : ''))
      let unitText = DIMENSION_UNITS[param.unit] || param.unit || ''
      if (!unitText && ANGLE_DIMENSIONS.has(param.name)) unitText = '°'
      else if (!unitText && LINEAR_DIMENSIONS.has(param.name)) unitText = 'mm'
      const input = el('input', {
        type: 'number',
        value: String(param.value),
        step: param.integer ? '1' : 'any',
        'aria-label': `${baseLabel}${unitText ? ` (${unitText})` : ''}`,
      })
      if (param.minimum != null) input.min = String(param.minimum)
      if (param.maximum != null) input.max = String(param.maximum)
      const unit = el('span', { className: 'bxw-dimension-unit' }, unitText)
      const apply = el('button', { type: 'button', title: '应用这个尺寸' }, '应用')
      apply.addEventListener('click', () => applyDimension(param, input, row))
      input.addEventListener('keydown', (event) => {
        if (event.key !== 'Enter') return
        event.preventDefault()
        applyDimension(param, input, row)
      })
      input.addEventListener('input', () => {
        input.dataset.invalid = 'false'
        dimensionError.hidden = true
        dimensionError.textContent = ''
      })
      if (range.length) row.title = `范围 ${range.join(' 且 ')}`
      row.append(label, input, unit, apply)
      dimensionList.append(row)
    }
  }

  const dimensionLabel = (param, fallback) => DIMENSION_LABELS[param] || fallback || param

  const setHandleHint = (handle, value) => {
    if (!handle) {
      handleChip.hidden = true
      handleChip.textContent = ''
      return
    }
    const unit = DIMENSION_UNITS[handle.unit] || handle.unit
      || (ANGLE_DIMENSIONS.has(handle.param) ? '°'
        : LINEAR_DIMENSIONS.has(handle.param) ? 'mm' : '')
    const axis = handle.axis || [0, 0, 1]
    const absolute = axis.map((item) => Math.abs(item))
    let direction = '法向'
    if (!['radius', 'diameter', 'hole_radius'].includes(handle.param)) {
      if (absolute[0] > 0.8) direction = 'X 轴'
      else if (absolute[1] > 0.8) direction = 'Y 轴'
      else if (absolute[2] > 0.8) direction = 'Z 轴'
    }
    const current = value ?? handle.value
    handleChip.textContent = `拖动 ${dimensionLabel(handle.param, handle.label)} · ${current}${unit} · 沿 ${direction}`
    handleChip.hidden = false
  }

  const loadHandle = async (selection) => {
    const seq = ++handleSeq
    state.handle = null
    post('handle', null)
    setHandleHint(null)
    if (!state.docId || !selection?.feature_id) return
    try {
      const result = await api(`${base}/api/docs/${state.docId}/handles`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          feature_id: selection.feature_id,
          point: selection.point || selection.center || [0, 0, 0],
          normal: selection.normal || [0, 0, 1],
          scope: selection.scope || 'face',
        }),
      })
      if (seq !== handleSeq) return
      if (!result.handle) {
        post('handle', null)
        setHandleHint(null)
        return
      }
      state.handle = result.handle
      setHandleHint(result.handle)
      post('handle', { ...result.handle, point: selection.point || selection.center })
    } catch (error) {
      if (seq !== handleSeq) return
      state.handle = null
      post('handle', null)
      setHandleHint(null)
    }
  }

  const commitHandleValue = async (payload) => {
    if (!state.handle || !state.docId || state.dimensionBusy) return
    const handle = state.handle
    const value = Number(payload?.value)
    if (!Number.isFinite(value)) return
    const label = dimensionLabel(handle.param, handle.label)
    let problem = ''
    if (handle.integer && !Number.isInteger(value)) problem = '需要整数'
    else if (handle.minimum != null && value < handle.minimum) problem = `不能小于 ${handle.minimum}`
    else if (handle.maximum != null && value > handle.maximum) problem = `不能大于 ${handle.maximum}`
    if (problem) {
      toast(`${label}：${problem}`, 'error', 4)
      return
    }
    state.dimensionBusy = true
    try {
      await api(`${base}/api/docs/${state.docId}/tweak`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          base_version: state.version,
          changes: [{ feature_id: handle.feature_id, params: { [handle.param]: value } }],
          title: `拖动 ${label} = ${value}${handle.unit || ''}`,
        }),
      })
      toast(`已拖动 ${label} 到 ${value}${handle.unit || ''}`, 'info', 3)
      await refreshAfterCommit()
      clearSelection()
    } catch (error) {
      toast(`拖动失败：${error.message}${error.hint ? ` · ${error.hint}` : ''}`, 'error', 6)
    } finally {
      state.dimensionBusy = false
      state.drag = null
    }
  }

  const setPickScope = (scope) => {
    if (!['body', 'face', 'edge', 'point'].includes(scope)) return
    state.pickScope = scope
    for (const [name, button] of Object.entries(scopeButtons)) {
      button.setAttribute('aria-pressed', name === scope ? 'true' : 'false')
    }
    post('scope', { scope })
    if (state.selection) clearSelection()
  }

  const clearSelection = () => {
    pickSeq += 1
    dimensionSeq += 1
    handleSeq += 1
    state.selection = null
    state.reference = null
    state.handle = null
    state.dimensions = null
    state.dimensionFeature = null
    state.drag = null
    renderDimensions()
    setHandleHint(null)
    post('handle', null)
    renderSelection()
    post('highlight', { centers: [] })
  }

  const applyPick = (raw) => {
    if (!raw) {
      clearSelection()
      return
    }
    if (raw.documentId && raw.documentId !== state.docId) return
    state.reference = null
    const seq = ++pickSeq
    state.selection = { ...raw, pending: true, face_index: undefined }
    renderSelection()
    setInspector(true)
    resolveSelection(raw).then((resolved) => {
      if (seq !== pickSeq) return
      if (resolved.scopeError) {
        clearSelection()
        toast(resolved.scopeError, 'info', 5)
        return
      }
      state.selection = resolved
      renderSelection()
      const centers = resolved.highlight_centers
        || (resolved.center ? [resolved.center] : [])
      post('highlight', centers.length ? { centers, seconds: 0, tone: 'selection' } : { centers: [] })
      loadDimensions(resolved.feature_id)
      loadHandle(resolved)
    })
  }

  const renderSelection = () => {
    selectionBar.textContent = ''
    if (!state.selection && !state.reference) {
      selectionBar.hidden = true
      selectionSummary.textContent = '在画布上点选面或边'
      return
    }
    selectionBar.hidden = false
    if (state.reference) {
      const reference = state.reference
      const chip = el('span', { className: 'bxw-selection-chip' })
      chip.append(el('span', {}, `${reference.what} · ${reference.id}`))
      chip.title = [reference.id, reference.type, ...(reference.reasons || [])].join('\n')
      const clear = el('button', { type: 'button', title: '清除特征引用', 'aria-label': '清除特征引用', html: ICONS.close })
      clear.addEventListener('click', clearSelection)
      chip.append(clear)
      selectionBar.append(el('span', {}, '特征'), chip)
      selectionSummary.textContent = `特征 ${reference.id} · ${reference.what}`
      return
    }
    const label = selectionText(state.selection)
    const chip = el('span', { className: 'bxw-selection-chip' })
    chip.append(el('span', {}, label))
    chip.title = formatSelection(state.selection)
    const clear = el('button', { type: 'button', title: '清除选择', 'aria-label': '清除选择', html: ICONS.close })
    clear.addEventListener('click', clearSelection)
    chip.append(clear)
    selectionBar.append(el('span', {}, '上下文'), chip)
    selectionSummary.textContent = formatSelection(state.selection)
  }

  const loadThread = async () => {
    if (!options.getThread) return
    const sessionId = state.sessionId || options.getSessionId?.()
    if (!sessionId) return
    try {
      const result = await options.getThread(sessionId)
      const documentId = Array.isArray(result) ? null : result?.documentId
      if (documentId && !readBinding(sessionId)?.manual && documentId !== state.docId
          && state.documents.some((doc) => doc.id === documentId)) {
        loadDocument(documentId, true, false).catch(() => {})
      }
      if (state.modeling && result?.running === false && state.progressStartedAt) {
        const elapsed = performance.now() - state.progressStartedAt
        const status = state.plan?.plan?.status
        if (elapsed > 6000 && (status === 'done' || state.plan?.plan?.revision === state.progressStartRevision)) {
          stopModelingProgress()
        }
      }
    } catch (error) {
      /* history is optional; the model binding remains usable */
    }
  }

  const stopModelingProgress = () => {
    if (state.progressTimer) clearInterval(state.progressTimer)
    state.progressTimer = null
    state.modeling = false
    shell.dataset.running = 'false'
    if (state.checks) {
      checkBadge.textContent = `检查 ${state.checks.passed}/${state.checks.total}`
      checkBadge.dataset.tone = state.checks.ok ? 'ok' : 'bad'
    }
  }

  const pollModelingProgress = async () => {
    if (!state.modeling || !state.docId) return
    if (performance.now() - state.progressStartedAt > 10 * 60 * 1000) {
      stopModelingProgress()
      return
    }
    try {
      const plan = await api(`${base}/api/docs/${state.docId}/plan`)
      state.plan = plan
      renderPlan()
      const revision = plan?.plan?.revision
      const status = plan?.plan?.status
      if (revision != null && revision !== state.progressRevision) {
        state.progressRevision = revision
        state.progressStable = 0
      } else if (state.progressRevision != null) {
        state.progressStable += 1
      }
      if (state.progressStartRevision != null && revision != null
          && revision > state.progressStartRevision && status === 'done' && state.progressStable >= 3) {
        stopModelingProgress()
        renderTiming()
      }
    } catch (error) {
      /* keep polling; transient failures should not hide progress */
    }
  }

  const startModelingProgress = () => {
    state.modeling = true
    checkBadge.textContent = '建模中…'
    checkBadge.dataset.tone = 'busy'
    state.progressStartedAt = performance.now()
    state.progressStartRevision = state.plan?.plan?.revision ?? null
    state.progressRevision = state.progressStartRevision
    state.progressStable = 0
    shell.dataset.running = 'true'
    if (!state.progressTimer) state.progressTimer = setInterval(pollModelingProgress, 1200)
  }

  const createModel = async () => {
    if (!state.documents) state.documents = []
    try {
      const name = `Model ${new Date().toLocaleDateString('zh-CN')}`
      const doc = await api(`${base}/api/docs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      })
      state.documents.unshift(doc)
      renderDocuments()
      await loadDocument(doc.id, true, true)
      toast('已创建空白模型')
    } catch (error) {
      toast(`新建模型失败：${error.message}`, 'error', 6)
    }
  }

  const importReference = async (file) => {
    if (!state.docId || !file) return
    const suffix = (file.name.split('.').pop() || '').toLowerCase()
    const formats = {
      step: 'step', stp: 'step', iges: 'iges', igs: 'iges', brep: 'brep', stl: 'stl',
    }
    const format = formats[suffix]
    if (!format) {
      toast(`不支持 ${file.name}；请选择 STEP / IGES / BREP / STL`, 'error', 6)
      return
    }
    if (file.size > 40_000_000) {
      toast('参考文件超过 40 MB', 'error', 5)
      return
    }
    if (importButton.disabled) return
    importButton.disabled = true
    importButton.dataset.busy = 'true'
    let targetId = state.docId
    let created = false
    let imported = false
    try {
      if ((state.current?.features || []).length) {
        const name = `参考 ${file.name.replace(/\.[^.]+$/, '').slice(0, 60)}`
        const document = await api(`${base}/api/docs`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name }),
        })
        state.documents.unshift(document)
        renderDocuments()
        targetId = document.id
        created = true
      }
      const buffer = await file.arrayBuffer()
      const bytes = new Uint8Array(buffer)
      let binary = ''
      const chunk = 0x8000
      for (let offset = 0; offset < bytes.length; offset += chunk) {
        binary += String.fromCharCode(...bytes.subarray(offset, offset + chunk))
      }
      const result = await api(`${base}/api/docs/${targetId}/import/file`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: file.name, data: btoa(binary), format }),
      })
      imported = true
      toast(created
        ? `已新建模型并导入 ${file.name} · ${result.feature_id}`
        : `已导入 ${file.name} · ${result.feature_id}`, 'info', 4)
      setModels(true)
      setInspector(true)
      await loadDocument(targetId, true, true)
    } catch (error) {
      if (created && !imported) {
        try {
          await api(`${base}/api/docs/${targetId}`, { method: 'DELETE' })
          state.documents = state.documents.filter((item) => item.id !== targetId)
          renderDocuments()
        } catch (cleanup) {
          /* keep the readable import error even if the empty model cannot be removed */
        }
      }
      toast(`导入失败：${error.message}${error.hint ? ` · ${error.hint}` : ''}`, 'error', 7)
    } finally {
      importButton.disabled = false
      delete importButton.dataset.busy
    }
  }

  const deleteCurrentDocument = async () => {
    if (!state.docId) return
    const deleted = state.docId
    try {
      await api(`${base}/api/docs/${deleted}`, { method: 'DELETE' })
      state.documents = state.documents.filter((item) => item.id !== deleted)
      renderDocuments()
      const next = state.documents[0]?.id
      if (next) await loadDocument(next, true, true)
      else await loadDocument('', true)
      toast('模型已删除', 'info', 2)
    } catch (error) {
      toast(`删除模型失败：${error.message}`, 'error', 6)
    }
  }

  const runCommand = (text) => {
    if (!text.startsWith('/')) return false
    const [rawName, ...args] = text.slice(1).trim().split(/\s+/)
    const name = rawName.toLowerCase()
    const arg = args.join(' ')
    switch (name) {
      case 'fit': post('fit', {}); return true
      case 'iso': post('view', { name: 'iso' }); return true
      case 'top': post('view', { name: 'top' }); return true
      case 'front': post('view', { name: 'front' }); return true
      case 'right': post('view', { name: 'right' }); return true
      case 'wire':
        state.wire = !state.wire
        wireButton.setAttribute('aria-pressed', state.wire ? 'true' : 'false')
        post('wire', { on: state.wire })
        return true
      case 'checks': setInspector(true); return true
      case 'agent': openHistory(!state.historyOpen); return true
      case 'models': setModels(shell.dataset.models === 'off'); return true
      case 'new': createModel(); return true
      case 'refresh': loadDocument(state.docId, true).catch((error) => toast(error.message, 'error')); return true
      case 'export':
        if (!state.docId) return true
        window.open(`${base}/api/docs/${state.docId}/export/${arg || 'step'}`, '_blank', 'noopener')
        return true
      case 'find':
        if (!arg) {
          toast('用法：/find 左边的沉头孔', 'info', 4)
          return true
        }
        resolveCandidates(arg)
        return true
      case 'help':
        toast('命令：/fit /iso /top /front /right /wire /find /checks /agent /models /new /refresh /export')
        return true
      default:
        toast(`未知命令：/${name}`, 'error', 4)
        return true
    }
  }

  const setModels = (on) => {
    shell.dataset.models = on ? 'on' : 'off'
    leftResizer.hidden = !on
    structureButton.setAttribute('aria-pressed', on ? 'true' : 'false')
    menuModels.setAttribute('aria-checked', on ? 'true' : 'false')
  }
  const closeViewMenu = () => {
    viewMenu.hidden = true
    menuScrim.hidden = true
    viewButton.setAttribute('aria-expanded', 'false')
  }
  const openViewMenu = () => {
    closeReviewMenu()
    viewMenu.hidden = false
    menuScrim.hidden = false
    viewButton.setAttribute('aria-expanded', 'true')
    menuInspector.setAttribute('aria-checked', state.inspector ? 'true' : 'false')
    menuModels.setAttribute('aria-checked', shell.dataset.models === 'off' ? 'false' : 'true')
  }

  viewButton.addEventListener('click', (event) => {
    event.stopPropagation()
    if (viewMenu.hidden) openViewMenu()
    else closeViewMenu()
  })
  viewMenu.addEventListener('click', (event) => event.stopPropagation())
  menuModels.addEventListener('click', () => { setModels(shell.dataset.models === 'off'); closeViewMenu() })
  menuNav.addEventListener('click', () => { options.onToggleNavigation?.(); closeViewMenu() })
  menuInspector.addEventListener('click', () => { setInspector(!state.inspector); closeViewMenu() })
  menuRefresh.addEventListener('click', () => {
    closeViewMenu()
    loadDocument(state.docId, true).catch((error) => toast(error.message, 'error'))
  })
  document.addEventListener('click', closeViewMenu)
  menuScrim.addEventListener('click', closeViewMenu)

  reviewButton.addEventListener('click', (event) => {
    event.stopPropagation()
    if (reviewMenu.hidden) openReviewMenu()
    else closeReviewMenu()
  })
  reviewMenu.addEventListener('click', (event) => event.stopPropagation())
  reviewScrim.addEventListener('click', () => closeReviewMenu())
  document.addEventListener('click', () => closeReviewMenu())
  ghostToggle.addEventListener('click', () => setGhost(!state.ghost))
  ghostSelect.addEventListener('change', () => {
    state.ghostVersion = Number(ghostSelect.value)
    if (state.ghost) syncGhost()
    else renderReview()
  })
  sectionToggle.addEventListener('click', () => setSection(!state.section.on))
  measureToggle.addEventListener('click', () => setMeasure(!state.measure))
  measureClear.addEventListener('click', () => clearMeasure())
  dimensionRefresh.addEventListener('click', () => {
    if (state.dimensionFeature) loadDimensions(state.dimensionFeature)
  })
  planJobCancel.addEventListener('click', () => cancelJob())
  docNew.addEventListener('click', () => { createModel().catch((error) => toast(error.message, 'error')) })
  docDelete.addEventListener('click', () => {
    if (docDelete.dataset.armed === 'true') {
      clearTimeout(Number(docDelete.dataset.timer || 0))
      docDelete.dataset.armed = 'false'
      docDelete.textContent = '删除当前模型'
      deleteCurrentDocument()
      return
    }
    docDelete.dataset.armed = 'true'
    docDelete.textContent = '确认删除'
    docDelete.dataset.timer = String(setTimeout(() => {
      docDelete.dataset.armed = 'false'
      docDelete.textContent = '删除当前模型'
    }, 3000))
  })

  const toggleHistory = () => openHistory(!state.historyOpen)
  dockAgent.addEventListener('click', toggleHistory)
  checkBadge.addEventListener('click', () => setInspector(!state.inspector))
  modelsClose.addEventListener('click', () => setModels(false))
  historyToggle.addEventListener('click', toggleHistory)
  let peekTimer = null
  const hidePeek = () => {
    clearTimeout(peekTimer)
    historyPeek.hidden = true
  }
  const showPeek = () => {
    if (state.historyOpen) return
    peekTimer = setTimeout(() => {
      const summary = state.dockQuestion
        ? state.dockQuestionText
        : state.modeling
          ? 'Agent 正在建模，完整过程在历史中。'
          : state.plan?.plan?.goal
            ? `当前计划：${state.plan.plan.goal}`
            : '点击查看完整 Agent 历史'
      historyPeek.textContent = String(summary || '').slice(0, 180)
      historyPeek.hidden = false
    }, 420)
  }
  historyToggle.addEventListener('mouseenter', showPeek)
  historyToggle.addEventListener('mouseleave', hidePeek)
  historyToggle.addEventListener('focus', showPeek)
  historyToggle.addEventListener('blur', hidePeek)
  activeAction.addEventListener('click', () => {
    if (state.dockQuestion) openHistory(true)
    else if (state.modeling) openHistory(true)
    else setInspector(true)
  })
  modelsNew.addEventListener('click', createModel)
  structureButton.addEventListener('click', () => setModels(shell.dataset.models === 'off'))
  leftResizer.addEventListener('pointerdown', (event) => startResize(event, 'left'))
  rightResizer.addEventListener('pointerdown', (event) => startResize(event, 'right'))
  const keyboardResize = (event, side) => {
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return
    event.preventDefault()
    const amount = event.key === 'ArrowRight' ? 16 : -16
    if (side === 'left') setLeftWidth(state.leftWidth + amount)
    else setRightWidth(state.rightWidth - amount)
  }
  leftResizer.addEventListener('keydown', (event) => keyboardResize(event, 'left'))
  rightResizer.addEventListener('keydown', (event) => keyboardResize(event, 'right'))

  const post = (type, payload) => {
    try {
      frame.contentWindow?.postMessage({ from: 'brepx-workbench', type, ...payload }, '*')
    } catch (error) { /* frame may be between navigations */ }
  }

  const pushDesign = (fit = false) => {
    if (!state.current || !state.ready) return
    if (state.current.vacant) {
      post('clear', {})
      return
    }
    state.designStarted = performance.now()
    post('theme', readTheme())
    post('design', {
      documentId: state.docId,
      version: state.version,
      requestId: ++state.request,
      prefetch: null,
      fit,
      simplified: state.simplified,
    })
  }

  const previousVersion = () => {
    const milestones = state.current?.milestones || []
    const latest = milestones[milestones.length - 1]
    if (Number.isInteger(latest?.parent_version)) return latest.parent_version
    return state.version > 0 ? state.version - 1 : null
  }

  const measureTextFor = (result) => {
    if (!result) return '在画布上点两处'
    const parts = [
      `距离 ${Number(result.distance).toFixed(2)} mm`,
      `Δx ${Number(result.dx).toFixed(2)} · Δy ${Number(result.dy).toFixed(2)} · Δz ${Number(result.dz).toFixed(2)}`,
    ]
    if (result.angle != null) parts.push(`夹角 ${Number(result.angle).toFixed(1)}°`)
    return parts.join(' · ')
  }

  const renderMeasure = () => {
    const visible = state.measure || Boolean(state.measureResult)
    measureInspector.hidden = !visible
    if (!visible) return
    measureText.textContent = state.measureResult ? measureTextFor(state.measureResult) : '在画布上点两处取距离与夹角'
  }

  const renderGhostSelect = () => {
    const milestones = (state.current?.milestones || [])
      .filter((item) => Number(item.version) > 0 && Number(item.version) < state.version)
      .sort((a, b) => b.version - a.version)
    const chosen = state.ghostVersion ?? previousVersion()
    ghostSelect.textContent = ''
    if (!milestones.length) {
      ghostSelect.append(el('option', { value: '' }, '无历史版本'))
      ghostSelect.disabled = true
      return
    }
    for (const item of milestones) {
      ghostSelect.append(el('option', { value: String(item.version) }, `v${item.version} · ${item.title || '里程碑'}`))
    }
    ghostSelect.disabled = false
    ghostSelect.value = chosen != null ? String(chosen) : String(milestones[0].version)
  }

  const renderReview = () => {
    ghostToggle.setAttribute('aria-pressed', state.ghost ? 'true' : 'false')
    ghostToggle.textContent = state.ghost ? '关闭残影' : '开启残影'
    const version = state.ghostVersion ?? previousVersion()
    ghostMeta.textContent = state.ghost && version != null ? `v${version}` : ''
    renderGhostSelect()
    sectionToggle.setAttribute('aria-pressed', state.section.on ? 'true' : 'false')
    sectionToggle.textContent = state.section.on ? '关闭剖切' : '开启剖切'
    sectionControls.hidden = !state.section.on
    sectionRange.disabled = !state.section.on
    for (const [name, node] of Object.entries(sectionAxisButtons)) {
      node.setAttribute('aria-pressed', name === state.section.axis ? 'true' : 'false')
    }
    measureToggle.setAttribute('aria-pressed', state.measure ? 'true' : 'false')
    measureToggle.textContent = state.measure ? '结束测量' : '开始测量'
    renderMeasure()
  }

  const syncGhost = () => {
    if (!state.ghost) return
    const version = state.ghostVersion ?? previousVersion()
    if (version == null || version === 0) return
    state.ghostVersion = version
    post('ghost', { on: true, documentId: state.docId, version })
    ghostMeta.textContent = `v${version}`
    if (ghostSelect.value !== String(version)) ghostSelect.value = String(version)
  }

  const setGhost = (on) => {
    const next = Boolean(on)
    const version = state.ghostVersion ?? previousVersion()
    if (next && (version == null || version === 0)) {
      toast('没有可对比的历史版本', 'info', 3)
      return
    }
    state.ghost = next
    if (next) state.ghostVersion = version
    renderReview()
    if (state.ghost) syncGhost()
    else post('ghost', { on: false })
  }

  const setSection = (on) => {
    state.section.on = Boolean(on)
    renderReview()
    post('section', { ...state.section })
  }

  const clearMeasure = () => {
    state.measure = false
    state.measureResult = null
    renderReview()
    measureInspector.hidden = true
    post('measure', { on: false })
  }

  const setMeasure = (on) => {
    state.measure = Boolean(on)
    if (!state.measure) state.measureResult = null
    renderReview()
    post('measure', { on: state.measure })
    if (state.measure) {
      setInspector(true)
      toast('测量已开启：在画布上点两处', 'info', 3)
      closeReviewMenu()
    }
  }

  const downloadExport = async (format) => {
    if (!state.docId) return
    const extension = { step: 'step', stl: 'stl', glb: 'glb', cfd: 'json' }[format] || format
    const name = String(state.current?.document?.name || state.docId).replace(/[\\/:*?"<>|]/g, '_')
    try {
      const response = await fetch(`${base}/api/docs/${state.docId}/export/${format}?version=${state.version}`)
      if (!response.ok) {
        let message = `${response.status} ${response.statusText}`
        try { message = (await response.text()) || message } catch (error) { /* keep status */ }
        throw new Error(message)
      }
      const blob = await response.blob()
      const href = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = href
      anchor.download = `${name}-v${state.version}.${extension}`
      anchor.rel = 'noopener'
      document.body.append(anchor)
      anchor.click()
      anchor.remove()
      setTimeout(() => URL.revokeObjectURL(href), 30000)
      toast(`已导出 ${format.toUpperCase()}`, 'info', 3)
    } catch (error) {
      toast(`导出失败：${error.message}`, 'error', 6)
    }
  }

  const closeReviewMenu = () => {
    reviewMenu.hidden = true
    reviewScrim.hidden = true
    reviewButton.setAttribute('aria-expanded', 'false')
  }

  const openReviewMenu = () => {
    closeViewMenu()
    renderReview()
    reviewMenu.hidden = false
    reviewScrim.hidden = false
    reviewButton.setAttribute('aria-expanded', 'true')
  }

  const resetReviewTools = () => {
    state.ghost = false
    state.ghostVersion = null
    state.section.on = false
    state.measure = false
    state.measureResult = null
    post('ghost', { on: false })
    post('section', { on: false })
    post('measure', { on: false })
    renderReview()
  }

  const FOCUS_LABELS = {
    size: '尺寸', length: '长度', width: '宽度', height: '高度', radius: '半径',
    diameter: '直径', thickness: '壁厚', depth: '深度', count: '数量',
    angular_range: '角度范围', angle: '角度', amount: '长度',
    dx: 'X 偏移', dy: 'Y 偏移', dz: 'Z 偏移',
    x: 'X 位置', y: 'Y 位置', z: 'Z 位置',
  }
  const FOCUS_UNITS = { copies: '个', deg: '°', mm: 'mm' }
  const focusRows = new Map()
  let focusSignature = ''
  let focusTimer = null
  let focusRunning = false
  const focusPending = new Map()

  const focusLabel = (param) => `${FOCUS_LABELS[param.param] || param.param} · ${param.feature_id}`
  const focusLimit = (value) => {
    if (value == null || value === '') return null
    return Number.isFinite(Number(value)) ? Number(value) : null
  }

  const focusBounds = (param) => {
    const value = Number(param.value) || 0
    const span = Math.max(4, Math.abs(value) * 2)
    const backendMin = focusLimit(param.minimum)
    const backendMax = focusLimit(param.maximum)
    let min = backendMin != null ? Math.max(backendMin, value - span) : value - span
    let max = backendMax != null ? Math.min(backendMax, value + span) : value + span
    const signed = ['x', 'y', 'z', 'dx', 'dy', 'dz'].includes(param.param)
    if (backendMin == null && value >= 0 && !signed) min = Math.max(0, value - span)
    if (!(max > min)) {
      min = value - span
      max = value + span
    }
    const integer = param.param === 'count' || param.unit === 'copies' || param.unit === 'deg'
    return { min, max, step: integer ? 1 : 0.1 }
  }

  const scheduleFocus = (param, value, entry) => {
    focusPending.set(`${param.feature_id}.${param.param}`, {
      featureId: param.feature_id, param: param.param, value, entry,
    })
    clearTimeout(focusTimer)
    focusTimer = setTimeout(runFocus, 120)
  }

  const refreshFocusState = async () => {
    if (!state.docId) return
    const view = await api(`${base}/api/docs/${state.docId}/state`)
    if (!view?.document || view.document.id !== state.docId) return
    state.current = view
    state.version = view.document.version
    renderState()
  }

  const runFocus = async () => {
    if (focusRunning) {
      focusTimer = setTimeout(runFocus, 120)
      return
    }
    const jobs = [...focusPending.values()].filter((job) => job.value !== job.entry.lastValue)
    focusPending.clear()
    if (!jobs.length || !state.docId) return
    focusRunning = true
    for (const job of jobs) job.entry.row.dataset.busy = 'true'
    const summary = jobs.map((job) => `${job.featureId}.${job.param}`).join(' · ')
    try {
      await api(`${base}/api/docs/${state.docId}/tweak`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          base_version: state.version,
          changes: jobs.map((job) => ({
            feature_id: job.featureId,
            params: { [job.param]: job.value },
          })),
          title: `微调 ${jobs.map((job) => `${job.param}=${job.value}`).join(', ')}`,
        }),
      })
      for (const job of jobs) job.entry.lastValue = job.value
      toast(`已微调 ${summary}`, 'info', 2)
      await refreshFocusState().catch((error) => toast(`已提交，但刷新失败：${error.message}`, 'error', 5))
    } catch (error) {
      for (const job of jobs) {
        job.entry.number.value = String(job.entry.lastValue)
        job.entry.range.value = String(job.entry.lastValue)
      }
      toast(`微调失败：${error.message}${error.hint ? ` · ${error.hint}` : ''}`, 'error', 6)
      await refreshFocusState().catch(() => {})
    } finally {
      for (const job of jobs) job.entry.row.dataset.busy = 'false'
      focusRunning = false
      if (focusPending.size) focusTimer = setTimeout(runFocus, 120)
    }
  }

  const renderFocus = () => {
    const params = (state.current?.focus_params || []).slice(0, 4)
    if (!params.length) {
      focusSection.hidden = true
      focusList.textContent = ''
      focusRows.clear()
      focusSignature = ''
      return
    }
    focusSection.hidden = false
    const signature = params.map((param) => `${param.feature_id}.${param.param}`).join('|')
    if (signature !== focusSignature) {
      focusList.textContent = ''
      focusRows.clear()
      for (const param of params) {
        const bounds = focusBounds(param)
        const row = el('div', { className: 'bxw-focus-row' })
        const head = el('div', { className: 'bxw-focus-head' })
        const label = el('span', {}, focusLabel(param))
        label.title = `${param.feature_id}.${param.param}`
        const number = el('input', {
          type: 'number', className: 'bxw-focus-number', step: String(bounds.step),
          value: String(param.value),
        })
        number.setAttribute('aria-label', focusLabel(param))
        const unit = el('span', { className: 'bxw-focus-unit' }, FOCUS_UNITS[param.unit] || param.unit || '')
        head.append(label, number, unit)
        const range = el('input', {
          type: 'range', className: 'bxw-focus-range',
          min: String(bounds.min), max: String(bounds.max), step: String(bounds.step),
          value: String(param.value),
        })
        range.setAttribute('aria-label', `${focusLabel(param)} 滑块`)
        const entry = { row, number, range, bounds, lastValue: Number(param.value) }
        const apply = (raw) => {
          const value = raw === '' ? NaN : Number(raw)
          if (!Number.isFinite(value)) return
          number.value = String(value)
          if (value >= entry.bounds.min && value <= entry.bounds.max) {
            range.value = String(value)
          }
          if (value === entry.lastValue) {
            focusPending.delete(`${param.feature_id}.${param.param}`)
            if (!focusPending.size) clearTimeout(focusTimer)
            return
          }
          scheduleFocus(param, value, entry)
        }
        range.addEventListener('input', () => apply(range.value))
        number.addEventListener('input', () => apply(number.value))
        number.addEventListener('change', () => apply(number.value))
        const compareAction = el('button', {
          type: 'button', className: 'bxw-focus-compare', title: '生成不同取值的方案对比',
        }, '比较方案')
        compareAction.addEventListener('click', (event) => {
          event.stopPropagation()
          createVariants(param)
        })
        const actions = el('div', { className: 'bxw-focus-actions' })
        actions.append(compareAction)
        row.append(head, range, actions)
        focusList.append(row)
        focusRows.set(`${param.feature_id}.${param.param}`, entry)
      }
      focusSignature = signature
    }
    for (const param of params) {
      const entry = focusRows.get(`${param.feature_id}.${param.param}`)
      if (!entry) continue
      entry.bounds = focusBounds(param)
      entry.lastValue = Number(param.value)
      entry.number.value = String(param.value)
      entry.range.min = String(entry.bounds.min)
      entry.range.max = String(entry.bounds.max)
      entry.range.step = String(entry.bounds.step)
      entry.range.value = String(param.value)
    }
  }

  let variantRequest = 0

  const variantValues = (param) => {
    const base = Number(param.value) || 0
    const integer = param.param === 'count' || param.unit === 'copies' || param.unit === 'deg'
    const signed = ['x', 'y', 'z', 'dx', 'dy', 'dz'].includes(param.param)
    const step = integer ? 1 : Math.max(0.1, Math.abs(base) * 0.2)
    const raw = [base - step, base + step]
    if (!signed) raw[0] = Math.max(0, raw[0])
    const backendMin = focusLimit(param.minimum)
    const backendMax = focusLimit(param.maximum)
    const values = []
    const add = (value) => {
      const rounded = integer ? Math.round(value) : Math.round(value * 10) / 10
      if (rounded === base || (!signed && rounded < 0) || values.includes(rounded)) return
      if (backendMin != null && rounded < backendMin) return
      if (backendMax != null && rounded > backendMax) return
      values.push(rounded)
    }
    raw.forEach(add)
    let extra = 2
    while (values.length < 2 && extra < 6) {
      add(base + step * extra)
      extra += 1
    }
    return values.slice(0, 2)
  }

  const createVariants = async (param) => {
    if (!state.docId || state.variantBusy) return
    closeCandidates()
    const values = variantValues(param)
    if (!values.length) {
      toast('没有可比较的取值', 'info', 3)
      return
    }
    const token = ++variantRequest
    state.variantBusy = true
    state.variantSet = null
    state.variantPreview = null
    renderVariants()
    try {
      const response = await api(`${base}/api/docs/${state.docId}/variants`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          feature: param.feature_id,
          params: { [param.param]: values },
          include_base: true,
          base_version: state.version,
          thumbs: true,
        }),
      })
      if (token !== variantRequest) return
      state.variantSet = response
      state.variantBusy = false
      renderVariants()
      if (response.all_failed) toast('所有方案都构建失败', 'error', 5)
    } catch (error) {
      if (token !== variantRequest) return
      state.variantBusy = false
      state.variantSet = null
      renderVariants()
      toast(`生成方案失败：${error.message}${error.hint ? ` · ${error.hint}` : ''}`, 'error', 6)
    }
  }

  const previewVariant = (variant) => {
    if (!variant?.ok || !variant.step || state.variantApplying != null) return
    post('preview', { url: `${base}${variant.step}`, label: variant.label })
    state.variantPreview = variant.index
    renderVariants()
  }

  const exitVariantPreview = () => {
    if (state.variantPreview == null) return
    state.variantPreview = null
    renderVariants()
    pushDesign(false)
  }

  const closeVariants = () => {
    variantRequest += 1
    const previewing = state.variantPreview != null
    state.variantBusy = false
    state.variantApplying = null
    state.variantPreview = null
    state.variantSet = null
    renderVariants()
    if (previewing) pushDesign(false)
  }

  const applyVariant = async (variant) => {
    if (!state.variantSet || state.variantApplying != null || !variant?.ok) return
    const docId = state.docId
    if (Number(state.variantSet.base_version) !== state.version) {
      toast('模型已更新，请重新生成方案', 'error', 5)
      return
    }
    if ((variant.checks || []).some((check) => !check.ok)) {
      toast('该方案未通过检查，不能采纳', 'error', 4)
      return
    }
    if (!(variant.ops?.length)) {
      toast('当前方案没有可采纳的修改', 'info', 3)
      return
    }
    state.variantApplying = variant.index
    renderVariants()
    try {
      await api(`${base}/api/variants/${state.variantSet.set}/${variant.index}/apply`, { method: 'POST' })
      state.variantApplying = null
      state.variantPreview = null
      state.variantSet = null
      renderVariants()
      toast(`已采纳方案 ${variant.label}`, 'info', 3)
      if (state.docId === docId) await loadDocument(docId, true)
    } catch (error) {
      state.variantApplying = null
      renderVariants()
      toast(`采纳方案失败：${error.message}${error.hint ? ` · ${error.hint}` : ''}`, 'error', 6)
    }
  }

  const renderVariants = () => {
    const set = state.variantSet
    const visible = state.variantBusy || Boolean(set)
    variantPanel.hidden = !visible
    if (!visible) return
    const stale = set ? Number(set.base_version) !== state.version : false
    variantBack.hidden = state.variantPreview == null
    const busy = state.variantBusy
    const applying = state.variantApplying != null
    const details = busy
      ? '正在构建方案…'
      : `${set.label ? `${set.label} · ` : ''}${set.variants.length} 个`
        + `${stale ? ' · 已过期' : set.all_failed ? ' · 全部失败' : ''}${applying ? ' · 采纳中…' : ''}`
    variantMeta.textContent = details
    variantGrid.textContent = ''
    if (busy) {
      variantGrid.append(el('div', { className: 'bxw-variants-loading' }, '正在构建候选方案，缩略图和检查完成后会显示在这里。'))
      return
    }
    for (const variant of set.variants) {
      const failedChecks = (variant.checks || []).filter((check) => !check.ok).length
      const adoptable = Boolean(variant.ok && !failedChecks && (variant.ops?.length)
        && !stale && !applying)
      const card = el('article', {
        className: 'bxw-variant',
        tabindex: variant.ok && !applying ? '0' : '-1',
      })
      if (state.variantPreview === variant.index) card.dataset.active = 'true'
      if (!variant.ok) card.dataset.failed = 'true'
      card.setAttribute('aria-label', variant.ok ? `预览方案 ${variant.label}` : `方案 ${variant.label} 构建失败`)
      const thumbUrl = variant.thumb ? `${base}${variant.thumb}` : null
      let thumb
      if (thumbUrl) {
        thumb = el('img', { className: 'bxw-variant-thumb', src: thumbUrl, alt: variant.label })
        thumb.loading = 'lazy'
        thumb.addEventListener('error', () => {
          thumb.replaceWith(el('div', { className: 'bxw-variant-thumb empty' }, '缩略图不可用'))
        })
      } else {
        thumb = el('div', { className: 'bxw-variant-thumb empty' }, variant.ok ? '无缩略图' : '构建失败')
      }
      const body = el('div', { className: 'bxw-variant-body' })
      const label = el('div', { className: 'bxw-variant-label' }, variant.label || `方案 ${variant.index}`)
      const intro = el('div', { className: 'bxw-variant-meta' }, variant.ok
        ? `${fmt(variant.faces)} 面 · ${fmt(variant.volume, 1)} mm³`
        : '—')
      let statusText = '检查通过'
      if (!variant.ok) {
        statusText = variant.error?.hint || variant.error?.message || '构建失败'
      } else if (failedChecks) {
        statusText = `检查 ${(variant.checks || []).length - failedChecks}/${(variant.checks || []).length} 通过`
      } else if ((variant.checks || []).length) {
        statusText = `检查 ${variant.checks.length}/${variant.checks.length} 通过`
      }
      const status = el('div', {
        className: 'bxw-variant-status',
        'data-ok': String(Boolean(variant.ok && !failedChecks)),
      }, statusText)
      status.title = statusText
      body.append(label, intro, status)
      const buttons = el('div', { className: 'bxw-variant-buttons' })
      if (variant.ok) {
        const previewButton = el('button', { type: 'button', disabled: applying }, '预览')
        previewButton.addEventListener('click', (event) => {
          event.stopPropagation()
          previewVariant(variant)
        })
        buttons.append(previewButton)
      }
      if (adoptable) {
        const applyButton = el('button', { type: 'button', disabled: applying }, '采纳')
        applyButton.addEventListener('click', (event) => {
          event.stopPropagation()
          applyVariant(variant)
        })
        buttons.append(applyButton)
      }
      card.append(thumb, body)
      if (buttons.childElementCount) card.append(buttons)
      if (variant.ok) {
        card.addEventListener('click', () => previewVariant(variant))
        card.addEventListener('keydown', (event) => {
          if (event.key !== 'Enter' && event.key !== ' ') return
          event.preventDefault()
          previewVariant(variant)
        })
      }
      variantGrid.append(card)
    }
  }

  const resetVariants = () => {
    variantRequest += 1
    state.variantSet = null
    state.variantPreview = null
    state.variantBusy = false
    state.variantApplying = null
    renderVariants()
  }

  const CANDIDATE_TYPES = {
    hole: '孔', solid_box: '板', solid_cylinder: '圆柱', chamfer: '倒角',
    fillet: '圆角', shell: '抽壳', extrude: '拉伸', revolve_profile: '旋转',
    hub_revolve: '轮毂', sweep: '扫掠', pattern: '阵列', blend_group: '圆角组',
    k_cylinder: '圆柱', k_box: '方块', k_chamfer: '倒角', k_fillet: '圆角',
    k_extrude: '拉伸', k_revolve: '旋转', k_rotate: '旋转', k_shell: '抽壳',
    k_cut: '切除', k_fuse: '合并', k_translate: '平移', k_move_faces: '面调整',
  }
  const candidateCenters = new Map()
  let candidateRequest = 0
  let candidateHover = 0

  const featureCenters = async (featureId) => {
    const key = `${state.docId}:${state.version}:${featureId}`
    if (candidateCenters.has(key)) return candidateCenters.get(key)
    try {
      const scene = await api(`${base}/api/docs/${state.docId}/scene?feature=${encodeURIComponent(featureId)}`)
      const centers = (scene.faces || []).map((face) => face.center).filter(Array.isArray)
      candidateCenters.set(key, centers)
      return centers
    } catch (error) {
      candidateCenters.set(key, [])
      return []
    }
  }

  const resolveCandidates = async (phrase) => {
    if (!state.docId || !phrase) return
    closeVariants()
    closeCandidates()
    const token = ++candidateRequest
    state.candidateBusy = true
    state.candidates = { phrase, matches: [], question: '', confident: false }
    renderCandidates()
    try {
      const result = await api(`${base}/api/docs/${state.docId}/resolve?q=${encodeURIComponent(phrase)}`)
      if (token !== candidateRequest) return
      state.candidates = result
      state.candidateBusy = false
      renderCandidates()
      if (!result.matches?.length) toast('没有找到匹配的特征', 'info', 4)
    } catch (error) {
      if (token !== candidateRequest) return
      state.candidateBusy = false
      state.candidates = null
      renderCandidates()
      toast(`解析指代失败：${error.message}${error.hint ? ` · ${error.hint}` : ''}`, 'error', 6)
    }
  }

  const closeCandidates = () => {
    candidateRequest += 1
    candidateHover += 1
    state.candidates = null
    state.candidateBusy = false
    renderCandidates()
    if (!state.reference) post('highlight', { centers: [] })
  }

  const highlightCandidate = async (candidate, card) => {
    const token = ++candidateHover
    const status = card.querySelector('.bxw-candidate-status')
    const centers = await featureCenters(candidate.id)
    if (token !== candidateHover) return
    if (!centers.length) {
      card.dataset.locate = 'failed'
      if (status) {
        status.dataset.failed = 'true'
        status.textContent = '没有可定位的独立面'
      }
      return
    }
    card.dataset.locate = 'ok'
    if (status) {
      status.dataset.failed = 'false'
      status.textContent = `已定位 ${centers.length} 个面`
    }
    post('highlight', { centers, seconds: 0, tone: 'change' })
  }

  const chooseCandidate = async (candidate) => {
    const centers = await featureCenters(candidate.id)
    if (!centers.length) {
      toast(`无法定位 ${candidate.id} 的面，未选择`, 'error', 5)
      return
    }
    clearSelection()
    state.reference = {
      id: candidate.id,
      type: candidate.type,
      what: candidate.what,
      reasons: candidate.reasons || [],
      version: state.version,
    }
    state.candidates = null
    state.candidateBusy = false
    candidateHover += 1
    renderCandidates()
    renderSelection()
    post('highlight', { centers, seconds: 0, tone: 'selection' })
    toast(`已引用 ${candidate.what}`, 'info', 2)
    input.focus()
  }

  const renderCandidates = () => {
    const data = state.candidates
    const visible = state.candidateBusy || Boolean(data)
    candidatePanel.hidden = !visible
    if (!visible) return
    candidateNote.hidden = true
    candidateNote.textContent = ''
    candidateGrid.textContent = ''
    if (state.candidateBusy) {
      candidateMeta.textContent = data?.phrase ? `正在解析「${data.phrase}」…` : '正在解析…'
      candidateNote.hidden = false
      candidateNote.textContent = '正在匹配文档里的特征…'
      return
    }
    const matches = (data.matches || []).slice(0, 4)
    candidateMeta.textContent = matches.length
      ? `「${data.phrase}」 · ${matches.length} 个候选`
      : `「${data.phrase}」 · 没有候选`
    if (!matches.length) {
      candidateNote.hidden = false
      candidateNote.textContent = data.question || '没有找到对应的特征，请换一种说法。'
      return
    }
    if (!data.confident) {
      candidateNote.hidden = false
      candidateNote.textContent = '找到多个特征，选择后会把特征引用带入下一条指令。'
    }
    for (const candidate of matches) {
      const card = el('button', { type: 'button', className: 'bxw-candidate' })
      card.append(
        el('span', { className: 'bxw-candidate-id' }, candidate.id),
        el('span', { className: 'bxw-candidate-what' }, candidate.what || candidate.type),
        el('span', { className: 'bxw-candidate-type' },
          `类型 ${CANDIDATE_TYPES[candidate.type] || candidate.type}`),
      )
      const reasons = (candidate.reasons || []).slice(0, 2).join('；')
      card.append(el('span', { className: 'bxw-candidate-reasons' }, reasons || '按特征匹配'))
      card.append(el('span', { className: 'bxw-candidate-status' }, `匹配度 ${candidate.score ?? '—'}`))
      card.title = [candidate.id, candidate.what, ...(candidate.reasons || [])].join('\n')
      card.addEventListener('mouseenter', () => { highlightCandidate(candidate, card) })
      card.addEventListener('focus', () => { highlightCandidate(candidate, card) })
      const leave = () => {
        candidateHover += 1
        if (!state.reference && !state.selection) post('highlight', { centers: [] })
      }
      card.addEventListener('mouseleave', leave)
      card.addEventListener('blur', leave)
      card.addEventListener('click', () => { chooseCandidate(candidate) })
      candidateGrid.append(card)
    }
  }

  const resetCandidates = () => {
    candidateRequest += 1
    candidateHover += 1
    candidateCenters.clear()
    state.candidates = null
    state.candidateBusy = false
    renderCandidates()
  }

  const renderDocuments = () => {    docSelect.textContent = ''
    if (!state.documents.length) {
      docSelect.append(el('option', { value: '' }, '没有模型'))
      docSelect.disabled = true
      return
    }
    docSelect.disabled = false
    for (const doc of state.documents) {
      docSelect.append(el('option', { value: doc.id }, `${doc.name || doc.id} · v${doc.version ?? 0}`))
    }
    if (state.docId) docSelect.value = state.docId
  }

  const renderPlan = () => {
    structureList.textContent = ''
    const plan = state.plan?.plan
    const nodes = plan?.nodes || []
    const features = state.current?.features || []
    structureMeta.textContent = plan?.revision != null ? `rev ${plan.revision}` : 'rev —'
    structureProgress.hidden = !state.modeling
    structureProgress.textContent = ''
    if (state.modeling) {
      const done = nodes.filter((node) => node.status === 'done').length
      structureProgress.append(el('b', {}, `构建中 ${done}/${nodes.length || '—'}`))
    }
    const entries = features.length
      ? features.slice(-80).map((feature) => ({
          key: feature.id,
          title: feature.id,
          meta: `${feature.type || 'feature'}${feature.actor ? ` · ${feature.actor}` : ''}`,
          status: nodes.find((node) => node.id === feature.id)?.status || (feature.enabled === false ? 'pending' : 'done'),
          error: feature.error,
        }))
      : nodes.slice(-40).map((node) => ({
          key: node.id,
          title: node.title || node.id,
          meta: `${node.action || node.kind || ''}${node.id ? ` · ${node.id}` : ''}`,
          status: node.status || 'pending',
          error: node.error,
        }))
    if (!entries.length) {
      structureList.append(el('div', { className: 'bxw-structure-empty' }, state.current ? '这个模型还没有特征' : '选择一个模型查看结构'))
      return
    }
    for (const entry of entries) {
      const node = nodes.find((item) => item.id === entry.key || item.feature_id === entry.key)
      const row = el('div', { className: 'bxw-structure-row', tabindex: '0' })
      row.dataset.key = entry.key
      if (node) row.dataset.node = node.id
      if (state.selectedNode && (node?.id === state.selectedNode || entry.key === state.selectedNode)) {
        row.dataset.selected = 'true'
      }
      const dot = el('span', { className: 'bxw-dot' })
      dot.dataset.state = entry.status
      const main = el('div', { className: 'bxw-structure-main' })
      main.append(el('b', {}, entry.title), el('span', {}, entry.meta))
      row.append(dot, main)
      row.title = entry.error || `${entry.title}\n${entry.meta}`
      if (node) {
        const activate = () => selectPlanNode(node.id)
        row.addEventListener('click', activate)
        row.addEventListener('keydown', (event) => {
          if (event.key !== 'Enter' && event.key !== ' ') return
          event.preventDefault()
          activate()
        })
      }
      structureList.append(row)
    }
  }

  const checkItems = (checks) => {
    if (!checks) return []
    if (Array.isArray(checks.items)) return checks.items
    const items = []
    for (const feature of checks.features || []) {
      for (const check of feature.checks || []) {
        items.push({ feature_id: feature.id, ...check })
      }
    }
    return items
  }

  const checkValue = (value) => {
    if (value == null || value === '') return ''
    if (typeof value === 'string') return value
    try { return JSON.stringify(value) } catch (error) { return String(value) }
  }

  const renderChecks = () => {
    checkList.textContent = ''
    const checks = state.checks
    if (!checks) {
      checkSummary.textContent = '暂无检查'
      checkSummary.dataset.ok = 'true'
      return
    }
    const items = checkItems(checks)
    checkSummary.textContent = `${checks.passed}/${checks.total} 通过`
    checkSummary.dataset.ok = checks.ok ? 'true' : 'false'
    for (const item of items.slice(0, 200)) {
      const row = el('li', { className: 'bxw-row', tabindex: item.ok ? '-1' : '0', 'data-ok': String(Boolean(item.ok)) })
      const dot = el('span', { className: 'bxw-dot' })
      dot.dataset.state = item.ok ? 'done' : 'failed'
      const text = el('div', { className: 'bxw-row-main' })
      text.append(el('b', {}, `${item.feature_id || 'model'} · ${item.name}`), el('span', {}, item.expected || ''))
      const observed = checkValue(item.observed)
      if (observed) text.append(el('div', { className: 'bxw-check-observed' }, observed))
      if (!item.ok && item.hint) text.append(el('div', { className: 'bxw-check-observed' }, item.hint))
      row.append(dot, text)
      row.title = [item.feature_id, item.name, item.expected, observed, item.hint].filter(Boolean).join('\n')
      if (!item.ok && item.feature_id) {
        row.addEventListener('click', () => selectPlanNodeForFeature(item.feature_id))
        row.addEventListener('keydown', (event) => {
          if (event.key !== 'Enter' && event.key !== ' ') return
          event.preventDefault()
          selectPlanNodeForFeature(item.feature_id)
        })
      }
      checkList.append(row)
    }
    if (items.length > 200) {
      checkList.append(el('li', { className: 'bxw-row bxw-check' }, `还有 ${items.length - 200} 条检查`))
    }
  }

  const planNodes = () => state.plan?.plan?.nodes || []

  const stopJobPoll = () => {
    if (state.jobTimer) clearInterval(state.jobTimer)
    state.jobTimer = null
  }

  const planNodeStatus = (node) => {
    const status = node?.status || 'pending'
    return status === 'failed' ? '失败' : status === 'done' ? '完成'
      : status === 'running' ? '运行中' : status === 'ready' ? '就绪' : '待运行'
  }

  const renderJob = () => {
    const job = state.job
    planJob.hidden = !job
    if (!job) return
    const terminal = ['done', 'failed', 'cancelled'].includes(job.status)
    const elapsed = job.elapsed_ms != null ? `${(job.elapsed_ms / 1000).toFixed(1)}s` : ''
    planJobText.textContent = `异步 · ${job.node_id} · ${job.status}${elapsed ? ` · ${elapsed}` : ''}`
      + (job.error ? ` · ${job.error}` : '')
    planJobText.title = planJobText.textContent
    planJobCancel.hidden = terminal
    planJobCancel.disabled = terminal || job.status === 'cancelling'
  }

  const pollJob = async () => {
    if (!state.job) return
    try {
      const job = await api(`${base}/api/jobs/${state.job.job_id}`)
      state.job = job
      renderJob()
      if (['done', 'failed', 'cancelled'].includes(job.status)) {
        stopJobPoll()
        if (job.status === 'done') {
          toast(`节点 ${job.node_id} 已完成`, 'info', 3)
          await loadDocument(state.docId, true)
        } else {
          toast(job.error || `节点 ${job.node_id} ${job.status}`, job.status === 'failed' ? 'error' : 'info', 6)
          await refreshPlan()
        }
      }
    } catch (error) {
      /* keep polling; a transient read must not lose the cancel handle */
    }
  }

  const cancelJob = async () => {
    if (!state.job) return
    try {
      state.job = await api(`${base}/api/jobs/${state.job.job_id}/cancel`, { method: 'POST' })
      renderJob()
    } catch (error) {
      toast(`取消失败：${error.message}`, 'error', 5)
    }
  }

  const refreshPlan = async () => {
    if (!state.docId) return
    try {
      state.plan = await api(`${base}/api/docs/${state.docId}/plan`)
      renderPlan()
      renderPlanInspector()
    } catch (error) {
      toast(`读取计划失败：${error.message}`, 'error', 5)
    }
  }

  const runPlanNode = async (node, asyncMode = false) => {
    if (!state.docId || state.busy) return
    if (state.job && !['done', 'failed', 'cancelled'].includes(state.job.status)) {
      toast('已有异步任务在运行，请先取消或等待', 'info', 3)
      return
    }
    try {
      if (asyncMode) {
        state.job = await api(`${base}/api/docs/${state.docId}/plan/run_async`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ node_id: node.id, base_version: state.version }),
        })
        stopJobPoll()
        state.jobTimer = setInterval(pollJob, 700)
        renderJob()
        return
      }
      const result = await api(`${base}/api/docs/${state.docId}/plan/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ node_id: node.id, base_version: state.version }),
      })
      state.plan = result
      toast(`节点 ${node.id} 已运行`, 'info', 2)
      await loadDocument(state.docId, true)
    } catch (error) {
      toast(`节点运行失败：${error.message}${error.hint ? ` · ${error.hint}` : ''}`, 'error', 7)
      await refreshPlan()
    }
  }

  const removePlanNode = async (node) => {
    const plan = state.plan?.plan
    if (!plan) return
    try {
      state.plan = await api(`${base}/api/docs/${state.docId}/plan/edit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ops: [{ op: 'remove_node', id: node.id }],
          base_revision: plan.revision,
        }),
      })
      state.selectedNode = null
      renderPlan()
      renderPlanInspector()
      toast(`已从计划移除 ${node.id}`, 'info', 3)
    } catch (error) {
      toast(`移除节点失败：${error.message}${error.hint ? ` · ${error.hint}` : ''}`, 'error', 6)
    }
  }

  const revertToVersion = async (version) => {
    if (!state.docId || version === state.version) return
    try {
      await api(`${base}/api/docs/${state.docId}/revert`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_version: version, title: `回滚到 v${version}` }),
      })
      toast(`已回滚到 v${version}`, 'info', 3)
      await loadDocument(state.docId, true)
    } catch (error) {
      toast(`回滚失败：${error.message}${error.hint ? ` · ${error.hint}` : ''}`, 'error', 6)
    }
  }

  const selectPlanNode = (nodeId) => {
    state.selectedNode = nodeId
    setInspector(true)
    renderPlan()
    renderPlanInspector()
  }

  const selectPlanNodeForFeature = (featureId) => {
    const node = planNodes().find((item) => item.id === featureId || item.feature_id === featureId)
    if (node) selectPlanNode(node.id)
    else toast(`计划中没有 ${featureId} 节点`, 'info', 3)
  }

  const expectedText = (expect) => {
    if (!expect) return '—'
    const value = expect.value == null ? '' : ` ${expect.value}`
    return `${expect.metric || expect.name || 'metric'} ${expect.op || ''}${value}`
  }

  const observedText = (node, expect) => {
    const observed = node?.observed?.[expect?.metric]
    if (observed == null) return ''
    if (typeof observed === 'object' && 'observed' in observed) return checkValue(observed.observed)
    return checkValue(observed)
  }

  const renderPlanInspector = () => {
    const nodes = planNodes()
    if (!nodes.length) {
      planSection.hidden = true
      planJob.hidden = true
      return
    }
    planSection.hidden = false
    let node = nodes.find((item) => item.id === state.selectedNode)
    if (!node) {
      node = nodes.find((item) => item.status === 'failed') || nodes[nodes.length - 1]
      state.selectedNode = node.id
    }
    planTitle.textContent = node.title || node.id
    planTitle.title = `${node.id} · ${node.action || node.kind || ''}`
    const signature = nodes.map((item) => item.id).join('|')
    if (planPicker.dataset.signature !== signature) {
      planPicker.textContent = ''
      for (const item of nodes) {
        planPicker.append(el('option', { value: item.id },
          `${item.id} · ${planNodeStatus(item)} · ${item.title || ''}`))
      }
      planPicker.dataset.signature = signature
    }
    planPicker.value = node.id
    planStatus.textContent = planNodeStatus(node)
    planStatus.dataset.state = node.status || 'pending'
    planActions.textContent = ''
    const addAction = (label, title, handler, disabled = false) => {
      const button = el('button', { type: 'button', title, disabled }, label)
      button.addEventListener('click', handler)
      planActions.append(button)
      return button
    }
    const runnable = node.kind !== 'goal' && node.status !== 'done'
    addAction(node.status === 'failed' ? '重试' : '运行', '同步运行该节点', () => runPlanNode(node), !runnable)
    addAction('异步运行', '后台运行并显示进度', () => runPlanNode(node, true), !runnable)
    if (node.status === 'failed') {
      const remove = addAction('移除节点', '从计划中删除失败节点', () => {
        if (remove.dataset.armed === 'true') {
          clearTimeout(Number(remove.dataset.timer || 0))
          removePlanNode(node)
          return
        }
        remove.dataset.armed = 'true'
        remove.textContent = '确认移除'
        remove.dataset.timer = String(setTimeout(() => {
          remove.dataset.armed = 'false'
          remove.textContent = '移除节点'
        }, 3000))
      })
    }
    addAction('回滚上一版本', '回退当前文档一个里程碑', () => {
      if (state.version <= 0) return
      const button = planActions.querySelector('button:last-child')
      if (button.dataset.armed === 'true') {
        clearTimeout(Number(button.dataset.timer || 0))
        button.dataset.armed = 'false'
        button.textContent = '回滚上一版本'
        revertToVersion(state.version - 1)
        return
      }
      button.dataset.armed = 'true'
      button.textContent = '确认回滚'
      button.dataset.timer = String(setTimeout(() => {
        button.dataset.armed = 'false'
        button.textContent = '回滚上一版本'
      }, 3000))
    }, state.version <= 0)
    planDetails.textContent = ''
    const meta = el('div', { className: 'bxw-node-meta' },
      `${node.kind || 'feature'} · ${node.action || '—'}`
      + (node.milestone_version != null ? ` · v${node.milestone_version}` : ''))
    planDetails.append(meta)
    if (node.deps?.length) {
      const deps = el('div', { className: 'bxw-node-deps' })
      for (const dep of node.deps) deps.append(el('span', { className: 'bxw-node-dep' }, dep))
      planDetails.append(deps)
    }
    const refs = Object.entries(node.refs || {})
    if (refs.length) {
      const summary = refs.map(([key, value]) => Array.isArray(value)
        ? `${key} × ${value.length}`
        : `${key} ← ${value?.source || '—'}`).join(' · ')
      planDetails.append(el('div', { className: 'bxw-node-meta' }, `引用 ${summary}`))
    }
    if (node.params && Object.keys(node.params).length) {
      planDetails.append(el('div', { className: 'bxw-node-block' }, JSON.stringify(node.params, null, 2)))
    }
    for (const expect of node.expect || []) {
      const actual = observedText(node, expect)
      const row = el('div', { className: 'bxw-node-meta' },
        `期望 ${expectedText(expect)}${actual ? ` · 实测 ${actual}` : ''}`)
      planDetails.append(row)
    }
    if (node.error) {
      planDetails.append(el('div', { className: 'bxw-node-block', style: 'color: var(--bxw-bad)' }, node.error))
    }
    renderJob()
  }

  const showGhostVersion = (version) => {
    state.ghostVersion = version
    state.ghost = true
    renderReview()
    syncGhost()
    toast(`残影 v${version}`, 'info', 2)
  }

  const compareVersion = async (version) => {
    if (!state.docId || version <= 0) return
    try {
      const diff = await api(`${base}/api/docs/${state.docId}/diff?base=${version - 1}&target=${version}`)
      const changed = diff.changed_face_indices?.length || 0
      const added = diff.doc_diff?.added?.length || 0
      const removed = diff.doc_diff?.removed?.length || 0
      const delta = diff.metrics_delta?.volume_delta
      toast(`v${version - 1} → v${version} · +${added}/-${removed} 特征 · ${changed} 面变化`
        + (delta != null ? ` · 体积 ${delta >= 0 ? '+' : ''}${fmt(delta, 1)} mm³` : ''), 'info', 8)
      if (diff.changed_face_centers?.length) {
        post('highlight', { centers: diff.changed_face_centers, seconds: 4, tone: 'change' })
      }
    } catch (error) {
      toast(`版本对比失败：${error.message}`, 'error', 5)
    }
  }

  const renderReferences = () => {
    const imports = (state.current?.features || []).filter((feature) => feature.type === 'import_base')
    referenceSection.hidden = !imports.length
    referenceList.textContent = ''
    for (const feature of imports) {
      const row = el('div', { className: 'bxw-history-row' })
      row.append(el('b', {}, feature.id))
      row.append(el('small', {}, feature.note || '导入基准体'))
      referenceList.append(row)
    }
  }

  const renderHistory = () => {
    const milestones = state.current?.milestones || []
    historySection.hidden = !milestones.length
    historyList.textContent = ''
    for (const milestone of [...milestones].slice(-8).reverse()) {
      const row = el('div', { className: 'bxw-history-row' })
      row.append(el('b', {}, `v${milestone.version} · ${milestone.title || '里程碑'}`))
      row.append(el('small', {}, milestone.actor || ''))
      const diff = el('button', { type: 'button', title: '对比上一版本' }, '对比')
      diff.addEventListener('click', () => compareVersion(milestone.version))
      const ghost = el('button', { type: 'button', title: '叠加该版本残影' }, '残影')
      ghost.addEventListener('click', () => showGhostVersion(milestone.version))
      const revert = el('button', { type: 'button', title: '回滚到该版本' }, '回滚')
      const revertArmed = () => {
        if (revert.dataset.armed === 'true') {
          clearTimeout(Number(revert.dataset.timer || 0))
          revertToVersion(milestone.version)
          return
        }
        revert.dataset.armed = 'true'
        revert.textContent = '确认'
        revert.dataset.timer = String(setTimeout(() => {
          revert.dataset.armed = 'false'
          revert.textContent = '回滚'
        }, 3000))
      }
      revert.addEventListener('click', revertArmed)
      revert.disabled = milestone.version === state.version
      row.append(diff, ghost, revert)
      historyList.append(row)
    }
  }
  const renderTiming = () => {
    const parts = []
    if (state.timings?.state) parts.push(`加载 ${(state.timings.state / 1000).toFixed(1)}s`)
    if (state.parseMs != null) parts.push(`解析 ${(state.parseMs / 1000).toFixed(1)}s`)
    if (state.edgesMs != null) parts.push(`边 ${(state.edgesMs / 1000).toFixed(1)}s`)
    if (state.renderMs != null) parts.push(`渲染 ${(state.renderMs / 1000).toFixed(1)}s`)
    const total = [state.timings?.state, state.parseMs, state.edgesMs, state.renderMs]
      .reduce((sum, value) => sum + (Number(value) || 0), 0)
    captionTiming.textContent = total ? `${(total / 1000).toFixed(1)}s` : ''
    caption.title = parts.join(' · ')
  }

  const renderState = () => {
    if (!state.current) return
    const doc = state.current.document || {}
    const metrics = state.current.metrics || {}
    docSelect.value = state.docId
    version.textContent = `v${doc.version ?? 0}`
    const checks = state.current.checks
    if (checks) {
      checkBadge.textContent = checks.ok ? `检查 ${checks.passed}/${checks.total}` : `检查 ${checks.passed}/${checks.total}`
      checkBadge.dataset.tone = checks.ok ? 'ok' : 'bad'
    } else {
      checkBadge.textContent = '暂无检查'
      checkBadge.dataset.tone = ''
    }
    metricBadge.textContent = metrics.volume != null ? `${fmt(metrics.volume, 0)} mm³` : '—'
    metricNodes.faces.textContent = fmt(metrics.faces)
    metricNodes.volume.textContent = fmt(metrics.volume, 1)
    metricNodes.area.textContent = fmt(metrics.area, 1)
    metricNodes.watertight.textContent = metrics.watertight ? '是' : '否'
    captionFaces.textContent = `${fmt(metrics.faces)} 面`
    captionTight.textContent = metrics.watertight ? '水密' : '非水密'
    empty.dataset.on = 'false'
    state.version = doc.version ?? 0
    state.simplified = false
    const known = state.documents.find((item) => item.id === state.docId)
    if (known) {
      known.version = state.version
      known.name = doc.name || known.name
    }
    const selected = docSelect.selectedOptions?.[0]
    if (selected) selected.textContent = `${doc.name || state.docId} · v${state.version}`
    if (state.selection?.version != null && state.selection.version !== state.version) clearSelection()
    if (state.reference?.version != null && state.reference.version !== state.version) clearSelection()
    if (state.variantPreview != null) state.variantPreview = null
    if (state.ghost) syncGhost()
    renderReview()
    renderPlan()
    renderPlanInspector()
    renderChecks()
    renderFocus()
    renderVariants()
    renderReferences()
    renderHistory()
    renderTiming()
    pushDesign(false)
  }

  const readBinding = (sessionId) => {
    if (!sessionId) return null
    try {
      const raw = localStorage.getItem(`cadview.document.${sessionId}`)
      if (!raw) return null
      const parsed = JSON.parse(raw)
      if (parsed && typeof parsed === 'object' && parsed.id) {
        return { id: parsed.id, manual: Boolean(parsed.manual) }
      }
      return { id: raw, manual: false }
    } catch (error) {
      return null
    }
  }
  const writeBinding = (sessionId, docId, manual) => {
    if (!sessionId || !docId) return
    try { localStorage.setItem(`cadview.document.${sessionId}`, JSON.stringify({ id: docId, manual: Boolean(manual) })) } catch (error) { /* private mode */ }
  }

  const loadDocument = async (docId, force = false, manual = false) => {
    if (!docId) {
      stopJobPoll()
      state.job = null
      state.selectedNode = null
      state.current = null
      state.plan = null
      state.checks = null
      pickSeq += 1
      state.selection = null
      state.reference = null
      renderSelection()
      post('highlight', { centers: [] })
      resetReviewTools()
      resetVariants()
      resetCandidates()
      dimensionSeq += 1
      handleSeq += 1
      state.dimensions = null
      state.dimensionFeature = null
      state.handle = null
      renderDimensions()
      post('handle', null)
      empty.dataset.on = 'true'
      return
    }
    if (docId === state.docId && state.current && !force) return
    stopModelingProgress()
    stopJobPoll()
    state.job = null
    if (docId !== state.docId) state.selectedNode = null
    state.docId = docId
    state.current = null
    pickSeq += 1
    state.selection = null
    state.reference = null
    renderSelection()
    post('highlight', { centers: [] })
    resetReviewTools()
    resetVariants()
    resetCandidates()
    dimensionSeq += 1
    handleSeq += 1
    state.dimensions = null
    state.dimensionFeature = null
    state.handle = null
    renderDimensions()
    post('handle', null)
    setLoading(true)
    const startedAt = performance.now()
    const loadTimer = setInterval(() => {
      if (empty.dataset.on !== 'true') return
      emptyBody.textContent = `正在读取几何、计划和检查结果… ${((performance.now() - startedAt) / 1000).toFixed(1)}s`
    }, 250)
    const timed = async (path) => {
      const start = performance.now()
      const value = await api(path)
      return { value, ms: performance.now() - start }
    }
    try {
      const [stateResult, planResult, checksResult] = await Promise.all([
        timed(`${base}/api/docs/${docId}/state`),
        timed(`${base}/api/docs/${docId}/plan`).catch(() => ({ value: null, ms: 0 })),
        timed(`${base}/api/docs/${docId}/checks`).catch(() => ({ value: null, ms: 0 })),
      ])
      const stateView = stateResult.value
      const plan = planResult.value
      const checks = checksResult.value
      state.timings = { state: stateResult.ms, plan: planResult.ms, checks: checksResult.ms }
      state.renderMs = null
      state.current = stateView
      state.plan = plan
      state.checks = checks ? { ...checks, items: checkItems(checks) } : null
      state.version = stateView.document.version
      empty.dataset.on = stateView.vacant ? 'true' : 'false'
      emptySpinner.hidden = true
      clearInterval(loadTimer)
      if (stateView.vacant) {
        emptyTitle.textContent = '空白模型'
        emptyBody.textContent = '在下方描述要创建的零件，或选择另一个已有模型。'
        emptyButton.hidden = false
      }
      renderState()
      const sessionId = state.sessionId || options.getSessionId?.()
      if (sessionId) {
        state.sessionId = sessionId
        if (manual) writeBinding(sessionId, docId, true)
        else if (!readBinding(sessionId)?.manual) writeBinding(sessionId, docId, false)
      }
    } catch (error) {
      clearInterval(loadTimer)
      state.current = null
      emptySpinner.hidden = true
      emptyTitle.textContent = '加载失败'
      emptyBody.textContent = error.message
      emptyButton.hidden = false
      empty.dataset.on = 'true'
      toast(`加载模型失败：${error.message}`, 'error', 6)
      throw error
    }
  }

  const resolveDocument = async (sessionId) => {
    const stored = readBinding(sessionId)
    const valid = (id) => id && state.documents.some((doc) => doc.id === id)
    if (stored?.manual && valid(stored.id)) return { id: stored.id, manual: true }
    if (valid(stored?.id)) return { id: stored.id, manual: Boolean(stored.manual) }
    return null
  }

  const withTimeout = (promise, ms) => Promise.race([
    promise,
    new Promise((resolve) => setTimeout(() => resolve(null), ms)),
  ])

  const chooseDocument = async () => {
    state.documents = await api(`${base}/api/docs`)
    renderDocuments()
    const stored = readBinding(state.sessionId)
    const bound = stored?.manual
      ? stored
      : await withTimeout(resolveDocument(state.sessionId), 1400).catch(() => null)
    const preferred = [bound?.id, stored?.id, options.documentId, state.docId, ...state.documents.map((doc) => doc.id)]
      .find((id) => id && state.documents.some((doc) => doc.id === id))
    state.docId = preferred || state.documents[0]?.id || null
    renderDocuments()
    if (state.docId) await loadDocument(state.docId, true, Boolean(bound?.id === state.docId && bound?.manual))
    else empty.dataset.on = 'true'
  }

  docSelect.addEventListener('change', () => {
    if (!docSelect.value) return
    loadDocument(docSelect.value, true, true).catch(() => {})
  })
  emptyButton.addEventListener('click', createModel)

  const resizeInput = () => {
    input.style.height = 'auto'
    input.style.height = `${Math.min(input.scrollHeight, 120)}px`
  }
  input.addEventListener('input', resizeInput)

  composer.addEventListener('submit', async (event) => {
    event.preventDefault()
    if (state.busy) return
    const text = input.value.trim()
    if (!text) return
    if (runCommand(text)) {
      input.value = ''
      resizeInput()
      return
    }
    if (!state.docId) return
    if (state.selection?.pending) {
      toast('正在解析拾取，稍候再发送', 'info', 2)
      return
    }
    const selected = state.selection ? `[${formatSelection(state.selection)}] ` : ''
    const reference = state.reference
      ? `[特征 ${state.reference.id} · ${state.reference.what}] ` : ''
    const doc = state.current?.document || {}
    const docName = doc.name ? ` · ${doc.name}` : ''
    const docTag = `[当前文档 ${state.docId}${docName} v${doc.version ?? state.version}] `
    const message = docTag + reference + selected + text
    if (state.variantPreview != null) exitVariantPreview()
    state.busy = true
    send.disabled = true
    try {
      await api(`${base}/api/docs/${state.docId}/intents`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: message, base_version: state.version }),
      })
      const sessionId = state.sessionId || options.getSessionId?.()
      if (!sessionId) throw new Error('没有活动会话；请先选择一个会话')
      await options.sendPrompt?.(sessionId, message)
      input.value = ''
      resizeInput()
      toast('已提交给 Agent')
      startModelingProgress()
      renderDock()
      setTimeout(() => { loadThread() }, 2500)
      setTimeout(() => { loadThread() }, 6000)
    } catch (error) {
      toast(`发送失败：${error.message}`, 'error', 7)
    } finally {
      state.busy = false
      send.disabled = false
      input.focus()
    }
  })
  input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      composer.requestSubmit()
    }
  })
  const onGlobalKey = (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault()
      input.focus()
      return
    }
    if (event.key === 'Escape') closeViewMenu()
  }
  document.addEventListener('keydown', onGlobalKey)

  const onMessage = (event) => {
    const data = event.data
    if (!data || data.from !== 'brepx-viewport') return
    if (data.type === 'ready') {
      state.ready = true
      state.shown = -1
      pushDesign(true)
      startWatchdog()
    } else if (data.type === 'shown') {
      state.shown = data.version
      if (state.designStarted != null) {
        state.renderMs = performance.now() - state.designStarted
        state.designStarted = null
        state.parseMs = data.timings?.parseMs ?? null
        state.edgesMs = data.timings?.edgesMs ?? null
        renderTiming()
      }
    } else if (data.type === 'pick') {
      applyPick(data.pick || null)
    } else if (data.type === 'handleMove') {
      state.drag = data
      if (state.handle) {
        const unit = DIMENSION_UNITS[state.handle.unit] || state.handle.unit
          || (ANGLE_DIMENSIONS.has(state.handle.param) ? '°'
            : LINEAR_DIMENSIONS.has(state.handle.param) ? 'mm' : '')
        dimensionHint.textContent = `拖动 ${dimensionLabel(state.handle.param, state.handle.label)}：`
          + `${data.value}${unit}`
        setHandleHint(state.handle, data.value)
      }
    } else if (data.type === 'handleCommit') {
      commitHandleValue(data)
    } else if (data.type === 'handleCancel') {
      state.drag = null
      if (state.handle) setHandleHint(state.handle)
      toast('已取消拖动，模型未改变', 'info', 2)
    } else if (data.type === 'measure' && data.result) {
      state.measureResult = data.result
      state.measure = true
      renderReview()
      setInspector(true)
      toast(measureTextFor(data.result), 'info', 8)
    } else if (data.type === 'error') {
      toast(`视图错误：${data.text}`, 'error', 6)
    }
  }
  window.addEventListener('message', onMessage)

  let watchdog = null
  const startWatchdog = () => {
    if (watchdog) return
    watchdog = setInterval(() => {
      if (!state.ready || !state.current) return
      if (state.shown === state.version) return
      pushDesign(false)
    }, 1500)
  }
  frame.addEventListener('load', () => {
    state.ready = false
    state.shown = -1
  })

  const onTheme = () => { if (state.ready) post('theme', readTheme()) }
  const observer = new MutationObserver(onTheme)
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class', 'style', 'data-theme'] })

  let questionScanFrame = 0
  const scanDockQuestion = () => {
    const node = agentSlot.querySelector('[data-question-key]')
    const text = node ? node.textContent.replace(/\s+/g, ' ').trim().slice(0, 180) : ''
    setDockQuestion(Boolean(node), text)
  }
  const dockObserver = new MutationObserver(() => {
    cancelAnimationFrame(questionScanFrame)
    questionScanFrame = requestAnimationFrame(scanDockQuestion)
  })
  dockObserver.observe(agentSlot, { childList: true, subtree: true })

  try {
    const savedLayout = JSON.parse(localStorage.getItem('cadview.layout') || '{}')
    if (Number.isFinite(savedLayout.left)) state.leftWidth = Math.max(220, Math.min(380, savedLayout.left))
    if (Number.isFinite(savedLayout.right)) state.rightWidth = Math.max(240, Math.min(480, savedLayout.right))
  } catch (error) { /* private mode */ }
  shell.style.setProperty('--bxw-left-width', `${state.leftWidth}px`)
  shell.style.setProperty('--bxw-right-width', `${state.rightWidth}px`)
  setInspector(false)
  shell.dataset.models = 'off'
  setModels(false)
  menuModels.setAttribute('aria-checked', 'false')
  renderSelection()
  renderReview()
  openHistory(false)
  loadThread()
  options.onFocus?.()
  chooseDocument().catch((error) => toast(`无法加载模型库：${error.message}`, 'error', 8))

  const threadPoll = setInterval(() => { loadThread() }, 3000)

  const sessionPoll = setInterval(() => {
    const next = options.getSessionId?.()
    if (next && next !== state.sessionId) {
      setSession(next)
    }
  }, 1000)

  return {
    dispose() {
      clearInterval(watchdog)
      clearInterval(sessionPoll)
      clearInterval(threadPoll)
      stopModelingProgress()
      clearTimeout(toastTimer)
      observer.disconnect()
      dockObserver.disconnect()
      dockResize.disconnect()
      inspectorResize.disconnect()
      cancelAnimationFrame(questionScanFrame)
      document.body.classList.remove('bxw-workbench')
      window.removeEventListener('message', onMessage)
      document.removeEventListener('keydown', onGlobalKey)
      document.removeEventListener('click', closeViewMenu)
      shell.remove()
    },
    setSession(sessionId) {
      if (!sessionId || sessionId === state.sessionId) return
      state.sessionId = sessionId
      loadThread()
      withTimeout(resolveDocument(sessionId), 1200)
        .catch(() => null)
        .then((bound) => {
          if (bound) loadDocument(bound.id, true, bound.manual).catch(() => {})
        })
        .catch(() => {})
    },
  }
}
