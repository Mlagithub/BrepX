const STYLE_ID = 'bx-workbench-style'

const css = `
  body.bxw-workbench [data-sidebar-collapsed="true"] { grid-template-columns: 0 minmax(0, 1fr) 0 !important; }
  body.bxw-workbench [data-sidebar-collapsed="true"] > :first-child { display: none !important; }
  .bxw-shell {
    position: absolute;
    inset: 0;
    display: grid;
    grid-template-rows: minmax(56px, auto) minmax(0, 1fr);
    overflow: hidden;
    color-scheme: light dark;
    color: var(--dsw-alias-label-primary, #e8edf5);
    background: var(--dsw-alias-bg-base, #101318);
    font: .8125rem/1.45 system-ui, -apple-system, "Segoe UI", sans-serif;
    --bxw-panel: var(--dsw-alias-bg-layer-1, #15191f);
    --bxw-layer: var(--dsw-alias-bg-layer-2, #1a1f27);
    --bxw-line: var(--dsw-alias-border-l2, #2a313c);
    --bxw-soft: var(--dsw-alias-label-secondary, #9aa7b8);
    --bxw-muted: var(--dsw-alias-label-tertiary, #8795a8);
    --bxw-accent: var(--dsw-alias-state-business-primary, #4f8cff);
    --bxw-ok: var(--dsw-alias-state-success-primary, #3fb950);
    --bxw-warn: var(--dsw-alias-state-warn-primary, #d29922);
    --bxw-bad: var(--dsw-alias-state-error-primary, #f85149);
    --bxw-primary: var(--dsw-alias-label-primary, #e8edf5);
    --bxw-bg: var(--dsw-alias-bg-base, #101318);
    /* One control height for every chrome row. Rows that mix button sizes read as
       unrelated widgets, so the header, the dock bar and the composer share it. */
    --bxw-control-h: 30px;
    --bxw-badge-h: 24px;
    /* Minimum hit area. WCAG 2.5.8 needs 24px; coarse pointers get 44px below. */
    --bxw-target: 24px;
  }
  .bxw-shell *, .bxw-shell *::before, .bxw-shell *::after { box-sizing: border-box; }
  .bxw-shell [hidden] { display: none !important; }
  .bxw-shell button, .bxw-shell select, .bxw-shell textarea { font: inherit; color: inherit; }
  .bxw-shell button {
    display: inline-flex; align-items: center; justify-content: center; gap: 6px;
    min-block-size: 30px; padding: 0 10px; border: 1px solid var(--bxw-line);
    border-radius: 6px; background: transparent; cursor: pointer; white-space: nowrap;
  }
  .bxw-shell button:hover { background: var(--bxw-layer); border-color: color-mix(in srgb, var(--bxw-accent) 55%, var(--bxw-line)); }
  .bxw-shell button:focus-visible, .bxw-shell select:focus-visible {
    outline: 2px solid color-mix(in srgb, var(--bxw-accent) 70%, transparent); outline-offset: 1px;
  }
  .bxw-shell button:disabled { opacity: .5; cursor: default; }
  .bxw-icon { width: 16px; height: 16px; flex: none; }
  .bxw-header {
    display: flex; flex-wrap: wrap; align-items: center; gap: 6px 12px; min-width: 0;
    min-block-size: 56px; padding: 6px 14px;
    border-bottom: 1px solid var(--bxw-line); background: var(--bxw-panel);
  }
  /* Context, toolbar and actions each own one row height, so the row reads as one band
     instead of four widgets of different sizes. */
  .bxw-context, .bxw-toolbar { min-block-size: var(--bxw-control-h); }
  .bxw-toolbar { display: flex; align-items: center; gap: 2px; flex: none; }
  .bxw-toolbar > [role="group"] { display: flex; align-items: center; gap: 2px; min-inline-size: 0; }
  .bxw-toolbar > [role="separator"] {
    flex: none; inline-size: 1px; block-size: 16px; margin: 0 6px;
    border: 0; background: var(--bxw-line);
  }
  .bxw-brand { display: flex; align-items: center; gap: 8px; flex: none; font-weight: 650; letter-spacing: .2px; }
  .bxw-mark { width: 24px; height: 24px; display: grid; place-items: center; border-radius: 6px;
    background: color-mix(in srgb, var(--bxw-accent) 16%, transparent); color: var(--bxw-accent); }
  .bxw-context { display: flex; align-items: center; gap: 8px; min-width: 0; flex: 1; }
  .bxw-context-label { color: var(--bxw-muted); font-size: .6875rem; flex: none; }
  .bxw-doc-search { width: 120px; flex: none; min-block-size: 30px; padding: 0 8px; border: 1px solid var(--bxw-line);
    border-radius: 6px; background: var(--bxw-layer); color: var(--bxw-primary); font-size: .75rem; }
  .bxw-doc-search::placeholder { color: var(--bxw-soft); }
  .bxw-doc-search[hidden] { display: none; }
  .bxw-context { overflow: hidden; }
  .bxw-context select { flex: 1 1 auto; min-width: 0; }
  .bxw-inspector-toggle, .bxw-theme-toggle { min-inline-size: 30px; padding: 0 8px; color: var(--bxw-soft); }
  .bxw-inspector-toggle[aria-expanded="true"] { color: var(--bxw-accent);
    border-color: color-mix(in srgb, var(--bxw-accent) 45%, var(--bxw-line)); }
  .bxw-theme-toggle svg { width: 15px; height: 15px; }
  .bxw-tree-toolbar { display: flex; gap: 6px; padding: 8px 8px 0; }
  .bxw-tree-search { min-width: 0; flex: 1; min-block-size: 30px; padding: 0 8px;
    border: 1px solid var(--bxw-line); border-radius: 6px; background: var(--bxw-layer);
    color: var(--bxw-primary); font-size: .75rem; }
  .bxw-tree-search::placeholder { color: var(--bxw-soft); }
  .bxw-tree-toolbar button { flex: none; min-block-size: 30px; padding: 0 8px; font-size: .6875rem; }
  .bxw-breadcrumb { display: flex; align-items: center; gap: 3px; min-height: 28px; padding: 0 8px;
    overflow: hidden; color: var(--bxw-soft); font-size: .6875rem; }
  .bxw-breadcrumb[hidden] { display: none; }
  .bxw-breadcrumb button { min-block-size: 22px; padding: 0 5px; border-color: transparent;
    color: var(--bxw-accent); font-size: .6875rem; }
  .bxw-breadcrumb span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .bxw-breadcrumb i { color: var(--bxw-muted); font-style: normal; }
  .bxw-structure-list { flex: 1; min-height: 0; overflow: auto; padding: 6px 6px 10px; }
  .bxw-tree-toggle { flex: none; width: 18px; min-inline-size: 18px; min-block-size: 18px;
    padding: 0; border: 0; background: transparent; color: var(--bxw-muted); }
  .bxw-tree-toggle:hover { color: var(--bxw-primary); background: transparent; }
  .bxw-tree-toggle svg { width: 13px; height: 13px; transition: transform .12s ease; }
  .bxw-tree-toggle[aria-expanded="true"] svg { transform: rotate(90deg); }
  .bxw-tree-leaf { flex: none; width: 18px; }
  .bxw-tree-summary { padding: 9px 8px 3px; color: var(--bxw-muted); font-size: .6875rem; }
  .bxw-empty-actions { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; }
  .bxw-empty-hint { margin: 10px 0 0; color: var(--bxw-muted); font-size: .6875rem; line-height: 1.45; }
  .bxw-preview-progress { display: flex; align-items: center; justify-content: center; gap: 8px;
    margin: 12px 0 0; color: var(--bxw-soft); font-size: .75rem; }
  .bxw-preview-cancel { margin-top: 10px; }
  .bxw-bom-dialog { width: min(760px, calc(100vw - 32px)); max-height: min(680px, 82vh);
    padding: 0; border: 1px solid var(--bxw-line); border-radius: 12px; background: var(--bxw-panel);
    color: var(--bxw-primary); box-shadow: 0 24px 60px rgb(0 0 0 / 35%); overflow: hidden; }
  .bxw-bom-dialog::backdrop { background: rgb(0 0 0 / 48%); }
  .bxw-bom-head { display: flex; align-items: center; gap: 10px; padding: 12px 16px;
    border-bottom: 1px solid var(--bxw-line); }
  .bxw-bom-head strong { font-size: .875rem; }
  .bxw-bom-head span { color: var(--bxw-muted); font-size: .6875rem; }
  .bxw-bom-head button { margin-left: auto; }
  .bxw-bom-body { max-height: min(560px, 66vh); overflow: auto; padding: 0 16px 12px; }
  .bxw-bom-summary { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; padding: 12px 0; }
  .bxw-bom-summary div { padding: 8px 10px; border: 1px solid var(--bxw-line); border-radius: 7px;
    background: var(--bxw-layer); }
  .bxw-bom-summary span { display: block; color: var(--bxw-soft); font-size: .6875rem; }
  .bxw-bom-summary b { display: block; margin-top: 2px; font: .875rem/1.3 var(--dsw-font-mono, ui-monospace, monospace); }
  .bxw-bom-table { width: 100%; border-collapse: collapse; font-size: .75rem; }
  .bxw-bom-table th { position: sticky; top: 0; padding: 7px 6px; border-bottom: 1px solid var(--bxw-line);
    background: var(--bxw-panel); color: var(--bxw-muted); font-size: .6875rem; text-align: left; font-weight: 600; }
  .bxw-bom-table td { padding: 7px 6px; border-bottom: 1px solid color-mix(in srgb, var(--bxw-line) 65%, transparent);
    vertical-align: top; }
  .bxw-bom-table td:last-child, .bxw-bom-table th:last-child { text-align: right; font-variant-numeric: tabular-nums; }
  .bxw-bom-table small { display: block; color: var(--bxw-muted); font-size: .6875rem; }
  .bxw-bom-empty { padding: 24px 0; color: var(--bxw-soft); font-size: .8125rem; }
  .bxw-shell[data-theme="light"] {
    color-scheme: light;
    color: var(--bxw-primary);
    --bxw-panel: #ffffff;
    --bxw-layer: #f1f4f8;
    --bxw-line: #d3dbe6;
    --bxw-soft: #445268;
    --bxw-muted: #5d6b7e;
    --bxw-accent: #1f6feb;
    --bxw-ok: #187a3b;
    --bxw-warn: #8a5a00;
    --bxw-bad: #b42318;
    --bxw-primary: #141a22;
    --bxw-bg: #eef2f7;
  }
  .bxw-shell[data-theme="light"] .bxw-empty-card p,
  .bxw-shell[data-theme="light"] .bxw-check { color: var(--bxw-soft); }
  .bxw-shell[data-theme="light"] .bxw-empty-card { color: var(--bxw-primary); }
  .bxw-shell[data-theme="light"] .bxw-toast { box-shadow: 0 10px 28px rgb(20 26 34 / 15%); }

  .bxw-context select {
    max-width: min(360px, 40vw); min-block-size: var(--bxw-control-h); padding: 0 30px 0 10px; border: 1px solid var(--bxw-line);
    border-radius: 6px; background-color: var(--bxw-layer) !important; color: var(--bxw-primary) !important;
    appearance: none; -webkit-appearance: none;
    background-image: linear-gradient(45deg, transparent 50%, var(--bxw-soft) 50%), linear-gradient(135deg, var(--bxw-soft) 50%, transparent 50%);
    background-position: calc(100% - 14px) 13px, calc(100% - 9px) 13px;
    background-size: 5px 5px, 5px 5px;
    background-repeat: no-repeat;
  }
  .bxw-version { font: .6875rem/1 var(--dsw-font-mono, ui-monospace, monospace); color: var(--bxw-muted); flex: none; }
  .bxw-badge { display: inline-flex; align-items: center; gap: 5px; min-block-size: var(--bxw-badge-h); padding: 0 8px;
    border-radius: 999px; border: 1px solid var(--bxw-line); color: var(--bxw-soft); font-size: .6875rem; flex: none; }
  /* The header volume read-out is a badge, not one of the inspector stat cards; the two
     used to share the bxw-metric class, so card padding leaked into the header and the
     narrow breakpoint hid every card while trying to hide the badge. */
  .bxw-badge-metric { font-variant-numeric: tabular-nums; }
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
  .bxw-view-menu button { width: 100%; min-block-size: 32px; justify-content: flex-start; gap: 8px; padding: 0 8px;
    border-color: transparent; background: transparent; color: var(--bxw-primary); font-size: .75rem; }
  .bxw-view-menu button:hover { background: var(--bxw-layer); }
  .bxw-view-menu button::before { content: ""; width: 14px; color: var(--bxw-accent); font-weight: 700; }
  .bxw-view-menu button[aria-pressed="true"]::before { content: "✓"; }
  .bxw-menu-sep { height: 1px; margin: 4px 6px; border: 0; background: var(--bxw-line); }
  .bxw-review-menu { position: absolute; top: calc(100% + 8px); right: 0; z-index: 20; width: 304px;
    max-height: calc(100vh - 92px); max-height: calc(100dvh - 92px); overflow: auto; padding: 6px 10px;
    border: 1px solid var(--bxw-line); border-radius: 8px; background: var(--bxw-panel);
    box-shadow: 0 16px 38px rgb(0 0 0 / 22%); }
  .bxw-review-menu[hidden] { display: none; }
  .bxw-review-section { display: flex; flex-direction: column; gap: 7px; padding: 9px 2px;
    border-top: 1px solid var(--bxw-line); }
  .bxw-review-section:first-child { border-top: 0; }
  .bxw-review-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
  .bxw-review-head-actions { padding: 6px 2px 0; }
  .bxw-review-close { flex: none; width: 24px; height: 24px; padding: 0; border-color: transparent; color: var(--bxw-muted); }
  .bxw-review-close:hover { color: var(--bxw-primary); background: var(--bxw-layer); }
  .bxw-review-head h3 { margin: 0; color: var(--bxw-muted); font-size: .625rem; font-weight: 650;
    letter-spacing: .8px; text-transform: uppercase; }
  .bxw-review-meta { color: var(--bxw-muted); font: .625rem/1.3 var(--dsw-font-mono, ui-monospace, monospace); }
  .bxw-review-row { display: flex; align-items: center; gap: 7px; }
  .bxw-review-row[hidden] { display: none; }
  .bxw-review-select { flex: 1; min-width: 0; min-block-size: 26px; padding: 0 8px; border: 1px solid var(--bxw-line);
    border-radius: 5px; background: var(--bxw-layer); color: var(--bxw-primary); font-size: .6875rem; }
  .bxw-review-select:disabled { opacity: .55; }
  .bxw-review-range { flex: 1; min-width: 0; accent-color: var(--bxw-accent); }
  .bxw-review-seg { display: flex; gap: 4px; }
  .bxw-review-seg button { min-block-size: 24px; padding: 0 9px; font-size: .6875rem; }
  .bxw-review-seg button[aria-pressed="true"] { color: var(--bxw-accent);
    border-color: color-mix(in srgb, var(--bxw-accent) 45%, var(--bxw-line));
    background: color-mix(in srgb, var(--bxw-accent) 10%, transparent); }
  .bxw-review-export { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
  .bxw-review-export button { min-block-size: 28px; font-size: .6875rem; }
  .bxw-review-note { color: var(--bxw-muted); font-size: .625rem; line-height: 1.45; }
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
  .bxw-models-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; min-block-size: 42px; padding: 0 12px; border-bottom: 1px solid var(--bxw-line); }
  .bxw-models-head strong { font-size: .75rem; font-weight: 600; }
  .bxw-structure-meta { margin-left: auto; color: var(--bxw-muted); font: .625rem/1 var(--dsw-font-mono, ui-monospace, monospace); }
  .bxw-structure-list { flex: 1; min-height: 0; overflow: auto; padding: 6px; display: flex; flex-direction: column; gap: 2px; }
  .bxw-structure-progress { margin: 6px 8px 0; padding: 6px 7px; border: 1px solid color-mix(in srgb, var(--bxw-accent) 35%, var(--bxw-line));
    border-radius: 6px; color: var(--bxw-soft); font-size: .625rem; display: flex; flex-direction: column; gap: 3px; }
  .bxw-structure-progress[hidden] { display: none; }
  .bxw-structure-progress-bar { width: 100%; height: 6px; accent-color: var(--bxw-accent); }
  .bxw-structure-row { display: flex; align-items: flex-start; gap: 7px; padding: 7px;
    padding-inline-start: calc(7px + var(--bxw-depth, 0) * 11px); border-radius: 6px; cursor: default; }
  .bxw-structure-row:hover { background: var(--bxw-layer); }
  .bxw-structure-row[data-node] { cursor: pointer; }
  .bxw-structure-row:focus-visible, .bxw-row:focus-visible {
    outline: 2px solid color-mix(in srgb, var(--bxw-accent) 70%, transparent); outline-offset: -2px; }
  .bxw-structure-row[data-selected="true"] { background: color-mix(in srgb, var(--bxw-accent) 10%, transparent);
    box-shadow: inset 2px 0 0 var(--bxw-accent); }
  .bxw-structure-row[data-related="true"] { box-shadow: inset 2px 0 0 var(--bxw-warn); }
  .bxw-structure-row .bxw-dot { margin-top: 4px; }
  .bxw-structure-group { padding: 8px 7px 3px; color: var(--bxw-muted); font-size: .5625rem;
    font-weight: 650; letter-spacing: .7px; text-transform: uppercase; }
  .bxw-structure-row[data-hidden="true"] .bxw-structure-main { opacity: .55; }
  .bxw-instance-flags { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 3px; }
  .bxw-instance-flag { padding: 0 5px; border: 1px solid var(--bxw-line); border-radius: 4px;
    color: var(--bxw-muted); font: .625rem/1.6 var(--dsw-font-mono, ui-monospace, monospace); }
  .bxw-structure-row .bxw-instance-flag { font: .625rem/1.6 var(--dsw-font-mono, ui-monospace, monospace); }
  .bxw-instance-flag[data-tone="bad"] { color: var(--bxw-bad);
    border-color: color-mix(in srgb, var(--bxw-bad) 42%, transparent); }
  .bxw-instance-flag[data-tone="warn"] { color: var(--bxw-warn);
    border-color: color-mix(in srgb, var(--bxw-warn) 42%, transparent); }
  .bxw-instance-note { color: var(--bxw-soft); font-size: .625rem; line-height: 1.5;
    white-space: pre-wrap; word-break: break-word; }
  .bxw-structure-main { min-width: 0; flex: 1; }
  .bxw-structure-main b { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--bxw-primary);
    font-size: .6875rem; font-weight: 550; }
  .bxw-structure-main span { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--bxw-muted);
    font: .6875rem/1.5 var(--dsw-font-mono, ui-monospace, monospace); }
  .bxw-structure-empty { padding: 10px 8px; color: var(--bxw-muted); font-size: .6875rem; }
  .bxw-model-list { flex: 1; min-height: 0; overflow-x: hidden; overflow-y: auto; padding: 4px 6px 12px; }
  .bxw-pane[hidden] { display: none; }
  .bxw-selection { display: flex; align-items: center; gap: 7px; max-width: none; margin: 0 0 7px; min-height: 24px; color: var(--bxw-soft); font-size: .6875rem; }
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
  .bxw-plan-card-head b { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: .75rem; font-weight: 550; }
  .bxw-plan-card-meta { margin-top: 3px; color: var(--bxw-muted); font: .625rem/1.4 var(--dsw-font-mono, ui-monospace, monospace); }
  .bxw-stage { min-width: 0; min-height: 0; background: color-mix(in srgb, var(--bxw-panel) 70%, var(--bxw-bg, #101318)); }
  .bxw-frame { width: 100%; height: 100%; border: 0; display: block; }
  .bxw-handle-hint { position: absolute; top: 12px; left: 50%; transform: translateX(-50%);
    padding: 6px 10px; border: 1px solid color-mix(in srgb, var(--bxw-accent) 45%, var(--bxw-line));
    border-radius: 6px; background: color-mix(in srgb, var(--bxw-panel) 92%, transparent);
    color: var(--bxw-primary); font-size: .6875rem; pointer-events: none; z-index: 5; white-space: nowrap; }
  .bxw-handle-hint[hidden] { display: none; }
  .bxw-tools { display: flex; align-items: center; gap: 2px; flex: none; }
  .bxw-tools button { min-block-size: var(--bxw-control-h); min-inline-size: var(--bxw-target); padding: 0 7px;
    border-color: transparent; color: var(--bxw-soft); }
  .bxw-tools button:hover { color: var(--bxw-primary, #e8edf5); background: var(--bxw-layer); }
  .bxw-tools button[aria-pressed="true"] { color: var(--bxw-accent); background: color-mix(in srgb, var(--bxw-accent) 12%, transparent); }
  .bxw-scopes { display: flex; gap: 2px; padding: 2px; border-radius: 6px; background: var(--bxw-layer); }
  .bxw-scopes[hidden] { display: none; }
  .bxw-scopes button { min-block-size: var(--bxw-target); min-inline-size: var(--bxw-target); padding: 0 6px; border: 0; background: transparent;
    color: var(--bxw-muted); font-size: .625rem; }
  .bxw-scopes button[aria-pressed="true"] { color: var(--bxw-accent);
    background: color-mix(in srgb, var(--bxw-accent) 15%, transparent); }
  .bxw-caption { display: flex; flex-wrap: wrap; align-items: center; gap: 0; margin-top: 8px; min-block-size: var(--bxw-target);
    color: var(--bxw-muted); font: .6875rem/1.3 var(--dsw-font-mono, ui-monospace, monospace); }
  .bxw-caption span + span::before { content: "·"; margin: 0 6px; color: var(--bxw-line); }
  .bxw-empty { position: absolute; inset: 0; display: none; place-items: center; padding: 24px;
    background: var(--bxw-bg); }
  .bxw-empty[data-on="true"] { display: grid; }
  .bxw-empty-card { max-width: 460px; text-align: center; }
  .bxw-empty-card h2 { margin: 0 0 6px; font-size: 1.125rem; font-weight: 600; }
  .bxw-empty-card p { margin: 0 0 16px; color: var(--bxw-soft); }
  .bxw-spinner { width: 24px; height: 24px; margin: 0 auto 14px; border: 2px solid var(--bxw-line);
    border-top-color: var(--bxw-accent); border-radius: 50%; animation: bxw-spin .7s linear infinite; }
  @keyframes bxw-spin { to { transform: rotate(360deg); } }
  @media (prefers-reduced-motion: reduce) { .bxw-spinner { animation-duration: 3s; } }
  .bxw-inspector { position: absolute; z-index: 10; right: 14px; top: 14px; bottom: auto; max-height: calc(100% - 38px - var(--bxw-dock-h, 112px));
    width: min(var(--bxw-right-width, 292px), 36vw); min-width: 0; border: 1px solid var(--bxw-line);
    border-radius: 9px; background: var(--bxw-panel); overflow: auto; box-shadow: 0 12px 32px rgb(0 0 0 / 18%); }
  .bxw-inspector[hidden] { display: none; }
  .bxw-inspector-head { position: sticky; top: 0; z-index: 1; display: flex; align-items: center; justify-content: space-between;
    gap: 8px; min-block-size: 42px; padding: 0 12px; border-bottom: 1px solid var(--bxw-line); background: var(--bxw-panel); }
  .bxw-inspector-head strong { font-size: .75rem; font-weight: 600; letter-spacing: .2px; }
  .bxw-inspector-body { padding: 10px 12px 20px; display: flex; flex-direction: column; gap: 16px; }
  .bxw-section { display: flex; flex-direction: column; gap: 7px; }
  .bxw-section[hidden] { display: none; }
  .bxw-focus { display: flex; flex-direction: column; gap: 10px; }
  .bxw-focus-row { display: flex; flex-direction: column; gap: 5px; }
  .bxw-focus-row[data-busy="true"] { opacity: .6; }
  .bxw-focus-head { display: flex; align-items: center; gap: 7px; }
  .bxw-focus-head span { flex: 1; min-width: 0; color: var(--bxw-soft); font-size: .6875rem;
    line-height: 1.35; white-space: normal; }
  .bxw-focus-number { width: 76px; min-block-size: 24px; padding: 0 6px; border: 1px solid var(--bxw-line);
    border-radius: 5px; background: var(--bxw-layer); color: var(--bxw-primary);
    font: .6875rem/1 var(--dsw-font-mono, ui-monospace, monospace); }
  .bxw-focus-unit { flex: none; color: var(--bxw-muted); font: .625rem/1 var(--dsw-font-mono, ui-monospace, monospace); }
  .bxw-focus-range { width: 100%; accent-color: var(--bxw-accent); }  .bxw-focus-actions { display: flex; justify-content: flex-end; margin-top: -2px; }
  .bxw-focus-compare { min-block-size: 20px; padding: 0 4px; border: 0; background: transparent;
    color: var(--bxw-accent); font-size: .625rem; }
  .bxw-focus-compare:hover { background: color-mix(in srgb, var(--bxw-accent) 9%, transparent); }
  .bxw-node-head { display: flex; align-items: center; gap: 7px; }
  .bxw-node-head b { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .bxw-node-status { margin-left: auto; flex: none; color: var(--bxw-muted);
    font: .5625rem/1 var(--dsw-font-mono, ui-monospace, monospace); text-transform: uppercase; }
  .bxw-node-status[data-state="failed"] { color: var(--bxw-bad); }
  .bxw-node-status[data-state="done"] { color: var(--bxw-ok); }
  .bxw-node-meta { color: var(--bxw-muted); font: .625rem/1.4 var(--dsw-font-mono, ui-monospace, monospace); }
  .bxw-node-actions { display: flex; flex-wrap: wrap; gap: 5px; }
  .bxw-node-actions button { min-block-size: 24px; padding: 0 8px; font-size: .625rem; }
  .bxw-node-deps { display: flex; flex-wrap: wrap; gap: 4px; }
  .bxw-node-dep { padding: 1px 5px; border: 1px solid var(--bxw-line); border-radius: 4px;
    color: var(--bxw-soft); font: .5625rem/1.4 var(--dsw-font-mono, ui-monospace, monospace); }
  .bxw-node-block { max-height: 112px; overflow: auto; padding: 6px 7px; border: 1px solid var(--bxw-line);
    border-radius: 5px; background: var(--bxw-layer); color: var(--bxw-soft);
    font: .625rem/1.45 var(--dsw-font-mono, ui-monospace, monospace); white-space: pre-wrap; word-break: break-word; }
  .bxw-node-block[data-tone="bad"] { color: var(--bxw-bad); }
  .bxw-check-observed { color: var(--bxw-soft); font: .5625rem/1.4 var(--dsw-font-mono, ui-monospace, monospace);
    word-break: break-word; }
  .bxw-row[role="button"] { cursor: pointer; }
  .bxw-job { display: flex; align-items: center; gap: 7px; padding: 7px 8px; border: 1px solid
    color-mix(in srgb, var(--bxw-accent) 32%, var(--bxw-line)); border-radius: 6px; background: var(--bxw-layer); }
  .bxw-job[hidden] { display: none; }
  .bxw-job span { min-width: 0; flex: 1; color: var(--bxw-soft); font-size: .625rem; }
  .bxw-job button { flex: none; min-block-size: 23px; padding: 0 7px; font-size: .625rem; }
  .bxw-history-row { display: flex; align-items: center; gap: 6px; padding: 4px 0; border-top: 1px solid var(--bxw-line); }
  .bxw-history-row:first-child { border-top: 0; }
  .bxw-history-row b { min-width: 0; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    color: var(--bxw-soft); font-size: .625rem; font-weight: 500; }
  .bxw-history-row small { flex: none; color: var(--bxw-muted); font: .5625rem/1 var(--dsw-font-mono, ui-monospace, monospace); }
  .bxw-history-row button { flex: none; min-block-size: 22px; padding: 0 6px; font-size: .5625rem; }
  .bxw-doc-actions { display: flex; gap: 6px; }
  .bxw-doc-actions button { min-block-size: 25px; font-size: .625rem; }
  .bxw-dimensions { display: flex; flex-direction: column; gap: 6px; }
  .bxw-dimension { display: flex; align-items: center; gap: 6px; }
  .bxw-dimension label { min-width: 0; flex: 1; color: var(--bxw-soft); font-size: .6875rem;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .bxw-dimension input { width: 76px; min-block-size: 25px; padding: 0 6px; border: 1px solid var(--bxw-line);
    border-radius: 5px; background: var(--bxw-layer); color: var(--bxw-primary);
    font-size: .6875rem; text-align: right; }
  .bxw-dimension-unit { min-width: 26px; color: var(--bxw-muted); font-size: .5625rem; }
  .bxw-dimension button { min-block-size: 24px; padding: 0 7px; font-size: .625rem; }
  .bxw-dimension[data-busy="true"] { opacity: .55; }
  .bxw-dimension input[data-invalid="true"] { border-color: var(--bxw-bad); }
  .bxw-check[hidden] { display: none; }
  .bxw-section-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
  .bxw-section-head h3 { margin: 0; }
  .bxw-section h3 { margin: 0; color: var(--bxw-muted); font-size: .6875rem; font-weight: 650;
    letter-spacing: .9px; text-transform: uppercase; }
  .bxw-metrics { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
  .bxw-stat { padding: 8px 9px; border: 1px solid var(--bxw-line); border-radius: 6px; background: var(--bxw-layer); }
  .bxw-stat span { display: block; color: var(--bxw-muted); font-size: .6875rem; }
  .bxw-stat b { display: block; margin-top: 2px; font: .75rem/1.35 var(--dsw-font-mono, ui-monospace, monospace); font-weight: 500; }
  .bxw-list { display: flex; flex-direction: column; gap: 2px; margin: 0; padding: 0; list-style: none; }
  .bxw-row { display: flex; align-items: center; gap: 8px; min-width: 0; padding: 6px 7px; border-radius: 5px; }
  .bxw-row:hover { background: var(--bxw-layer); }
  .bxw-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--bxw-muted); flex: none; }
  .bxw-dot[data-state="done"] { background: var(--bxw-ok); }
  .bxw-dot[data-state="failed"] { background: var(--bxw-bad); }
  .bxw-dot[data-state="running"] { background: var(--bxw-warn); }
  .bxw-row-main { min-width: 0; flex: 1; }
  .bxw-row-main b { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: .75rem; font-weight: 500; }
  .bxw-row-main span { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    color: var(--bxw-muted); font: .625rem/1.35 var(--dsw-font-mono, ui-monospace, monospace); }
  .bxw-check { font-size: .6875rem; color: var(--bxw-soft); }
  .bxw-check[data-ok="false"] { color: var(--bxw-bad); }
  .bxw-dock { position: absolute; left: 50%; bottom: 12px; transform: translateX(-50%); z-index: 15;
    width: min(900px, calc(100% - 28px)); display: flex; flex-direction: column;
    min-height: 0; border: 1px solid var(--bxw-line); border-radius: 10px; background: var(--bxw-panel);
    box-shadow: 0 12px 34px rgb(0 0 0 / 14%); }
  .bxw-history-peek { position: absolute; right: 18px; bottom: calc(100% + 7px); z-index: 18; width: min(420px, 70vw);
    max-height: 120px; overflow: hidden; padding: 8px 10px; border: 1px solid var(--bxw-line); border-radius: 7px;
    background: var(--bxw-panel); color: var(--bxw-soft); box-shadow: 0 10px 26px rgb(0 0 0 / 18%); font-size: .6875rem; line-height: 1.5; }
  .bxw-history-peek[hidden] { display: none; }
  .bxw-dock-active { display: flex; align-items: center; gap: 9px; min-height: 38px; padding: 7px 18px; border-bottom: 1px solid var(--bxw-line);
    border-radius: 10px 10px 0 0;
    background: color-mix(in srgb, var(--bxw-accent) 6%, var(--bxw-panel)); }
  .bxw-dock-active[hidden] { display: none; }
  .bxw-dock-active b { color: var(--bxw-primary); font-size: .75rem; font-weight: 550; flex: none; }
  .bxw-dock-active span { min-width: 0; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--bxw-soft); font-size: .6875rem; }
  .bxw-dock-active button { flex: none; min-block-size: 26px; padding: 0 9px; font-size: .6875rem; }
  .bxw-dock-history { position: absolute; left: 50%; bottom: calc(100% + 8px); transform: translateX(-50%); z-index: 18;
    width: min(700px, calc(100vw - 48px)); height: min(360px, 44vh); height: min(360px, 44dvh); min-height: 180px; overflow: hidden; display: flex; flex-direction: column;
    border: 1px solid var(--bxw-line); border-radius: 10px; background: var(--bxw-panel); box-shadow: 0 18px 46px rgb(0 0 0 / 24%); }
  .bxw-dock-history[hidden] { display: none; }
  .bxw-dock-history .bxw-agent-slot { width: 100%; max-width: 660px; margin: 0 auto; padding: 8px 16px 12px; }
  .bxw-dock-history:has([data-question-key]) { width: min(900px, calc(100vw - 48px)); height: min(560px, 62vh); height: min(560px, 62dvh); }
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
  .bxw-variants-head strong { font-size: .6875rem; font-weight: 600; }
  .bxw-variants-head span { min-width: 0; overflow: hidden; text-overflow: ellipsis;
    white-space: nowrap; color: var(--bxw-muted); font-size: .625rem; }
  .bxw-variants-actions { display: flex; gap: 6px; margin-left: auto; }
  .bxw-variants-actions button { min-block-size: 24px; padding: 0 8px; font-size: .625rem; }
  .bxw-variants-actions button[hidden] { display: none; }
  .bxw-variants-grid { display: flex; gap: 8px; padding: 10px 12px; overflow-x: auto; }
  .bxw-variant { flex: 1 1 0; min-width: 176px; display: flex; flex-direction: column;
    border: 1px solid var(--bxw-line); border-radius: 8px; background: var(--bxw-layer);
    overflow: hidden; }
  .bxw-variant:hover { border-color: color-mix(in srgb, var(--bxw-accent) 38%, var(--bxw-line)); }
  .bxw-variant[data-active="true"] { border-color: var(--bxw-accent);
    box-shadow: 0 0 0 1px color-mix(in srgb, var(--bxw-accent) 45%, transparent); }
  .bxw-variant[data-failed="true"] { opacity: .62; cursor: default; }
  .bxw-variant-thumb { width: 100%; height: 98px; object-fit: contain;
    background: color-mix(in srgb, var(--bxw-canvas, #f2f5f9) 80%, var(--bxw-panel));
    border-bottom: 1px solid var(--bxw-line); }
  .bxw-variant-thumb.empty { display: flex; align-items: center; justify-content: center;
    color: var(--bxw-muted); font-size: .5625rem; }
  .bxw-variant-body { display: flex; flex-direction: column; gap: 3px; padding: 7px 8px 4px; }
  .bxw-variant-label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    color: var(--bxw-primary); font-size: .6875rem; font-weight: 600; }
  .bxw-variant-meta { color: var(--bxw-muted); font: .5625rem/1.35 var(--dsw-font-mono, ui-monospace, monospace); }
  .bxw-variant-status { color: var(--bxw-muted); font-size: .5625rem; line-height: 1.35; }
  .bxw-variant-status[data-ok="false"] { color: var(--bxw-danger, #c94f4f); }
  .bxw-variant-buttons { display: flex; gap: 5px; padding: 4px 8px 8px; margin-top: auto; }
  .bxw-variant-buttons button { flex: 1; min-block-size: 24px; font-size: .625rem; }
  .bxw-variants-loading { padding: 20px 14px; color: var(--bxw-muted); font-size: .6875rem; }
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
  .bxw-candidates-head strong { font-size: .6875rem; font-weight: 600; }
  .bxw-candidates-head span { min-width: 0; overflow: hidden; text-overflow: ellipsis;
    white-space: nowrap; color: var(--bxw-muted); font-size: .625rem; }
  .bxw-candidates-head button { margin-left: auto; min-block-size: 24px; padding: 0 8px; font-size: .625rem; }
  .bxw-candidates-note { padding: 8px 12px; color: var(--bxw-soft); font-size: .6875rem; line-height: 1.5; }
  .bxw-candidates-grid { display: flex; gap: 8px; padding: 10px 12px; overflow-x: auto; }
  .bxw-candidates .bxw-candidate { flex: 1 1 0; min-width: 196px; height: auto; display: flex; flex-direction: column;
    align-items: stretch; justify-content: flex-start; gap: 5px; white-space: normal;
    padding: 10px; border: 1px solid var(--bxw-line); border-radius: 8px;
    background: var(--bxw-layer); text-align: left; cursor: pointer; }
  .bxw-candidate:hover, .bxw-candidate:focus-visible { border-color: var(--bxw-accent);
    box-shadow: 0 0 0 1px color-mix(in srgb, var(--bxw-accent) 35%, transparent); }
  .bxw-candidate[data-locate="failed"] { border-color: color-mix(in srgb, var(--bxw-danger, #c94f4f) 35%, var(--bxw-line)); }
  .bxw-candidate-id { color: var(--bxw-primary); font: .6875rem/1.3 var(--dsw-font-mono, ui-monospace, monospace); font-weight: 650; }
  .bxw-candidate-what { color: var(--bxw-soft); font-size: .6875rem; line-height: 1.4; }
  .bxw-candidate-type { color: var(--bxw-muted); font-size: .5625rem; }
  .bxw-candidate-reasons { color: var(--bxw-muted); font-size: .625rem; line-height: 1.45; }
  .bxw-candidate-status { color: var(--bxw-muted); font-size: .5625rem; line-height: 1.35; }
  .bxw-candidate-status[data-failed="true"] { color: var(--bxw-danger, #c94f4f); }
  .bxw-dock-bar { min-block-size: var(--bxw-control-h); flex: none; display: flex; align-items: center; gap: 8px; padding: 0 18px; background: var(--bxw-panel);
    border-radius: 10px 10px 0 0; }
  .bxw-dock:has(.bxw-dock-active:not([hidden])) .bxw-dock-bar { border-radius: 0; }
  .bxw-dock-agent { min-block-size: 24px; padding: 0 7px; border-color: transparent; color: var(--bxw-soft); font-size: .6875rem; }
  .bxw-dock-agent svg { width: 14px; height: 14px; }
  .bxw-dock-agent[aria-pressed="true"] { color: var(--bxw-accent); background: color-mix(in srgb, var(--bxw-accent) 9%, transparent); }
  .bxw-dock-status { min-width: 0; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--bxw-muted); font-size: .6875rem; }
  .bxw-dock-history-toggle { min-block-size: 24px; padding: 0 7px; border-color: transparent; color: var(--bxw-muted); font-size: .625rem; }
  .bxw-dock-history-toggle:hover { color: var(--bxw-primary); background: var(--bxw-layer); }
  .bxw-composer { position: relative; border-top: 0; background: var(--bxw-panel); padding: 0 10px 10px; border-radius: 0 0 10px 10px; }
  .bxw-composer[data-target="agent"] { border-top-color: color-mix(in srgb, var(--bxw-accent) 45%, var(--bxw-line)); }
  .bxw-composer-command { flex: none; min-block-size: 34px; padding: 0 9px; gap: 4px; border-color: transparent;
    color: var(--bxw-soft); font-size: .6875rem; }
  .bxw-composer-command svg { width: 13px; height: 13px; transform: rotate(-90deg); }
  .bxw-composer-command[aria-expanded="true"] { color: var(--bxw-accent);
    background: color-mix(in srgb, var(--bxw-accent) 10%, transparent); }
  .bxw-command-menu { position: absolute; left: 10px; bottom: calc(100% - 2px); z-index: 22;
    width: min(340px, calc(100% - 20px)); max-height: min(300px, 46vh); overflow: auto; padding: 5px;
    border: 1px solid var(--bxw-line); border-radius: 8px; background: var(--bxw-panel);
    box-shadow: 0 14px 34px rgb(0 0 0 / 24%); }
  .bxw-command-menu[hidden] { display: none; }
  .bxw-command-list { display: flex; flex-direction: column; }
  .bxw-command-list button { justify-content: flex-start; gap: 10px; min-block-size: 30px; padding: 0 9px;
    border-color: transparent; background: transparent; font-size: .75rem; }
  .bxw-command-list button:hover, .bxw-command-list button:focus-visible { background: var(--bxw-layer); }
  .bxw-command-list code { flex: none; min-inline-size: 84px; font: .75rem/1 var(--dsw-font-mono, ui-monospace, monospace);
    color: var(--bxw-accent); }
  .bxw-command-list small { color: var(--bxw-muted); font-size: .6875rem; }
  .bxw-composer-box { max-width: none; margin: 0; display: flex; align-items: flex-end; gap: 8px;
    padding: 7px; border: 1px solid var(--bxw-line); border-radius: 8px; background: var(--bxw-layer); }
  .bxw-composer-box:focus-within { border-color: color-mix(in srgb, var(--bxw-accent) 70%, var(--bxw-line)); }
  .bxw-composer textarea { flex: 1; width: 100%; field-sizing: content; min-block-size: 34px; max-block-size: 120px;
    resize: none; border: 0; outline: 0; background: transparent; padding: 7px 8px; line-height: 1.5; }
  .bxw-composer textarea::placeholder { color: var(--bxw-muted); }
  .bxw-send { min-block-size: 34px; padding: 0 14px; border-color: color-mix(in srgb, var(--bxw-accent) 60%, transparent);
    background: color-mix(in srgb, var(--bxw-accent) 16%, transparent); color: var(--bxw-primary, #e8edf5); }
  .bxw-send:hover { background: color-mix(in srgb, var(--bxw-accent) 26%, transparent); }
  .bxw-hint { max-width: none; margin: 6px 0 0; color: var(--bxw-muted); font-size: .75rem; }
  .bxw-toasts { position: fixed; right: 20px; bottom: calc(var(--bxw-dock-h, 112px) + 24px); z-index: 30;
    display: flex; flex-direction: column; gap: 8px; max-width: 360px; pointer-events: none; }
  .bxw-toast-stack { display: flex; flex-direction: column; gap: 8px; }
  .bxw-toast { display: flex; align-items: flex-start; gap: 8px; padding: 9px 12px; border: 1px solid var(--bxw-line);
    border-radius: 7px; background: var(--bxw-panel); color: var(--bxw-soft);
    box-shadow: 0 10px 28px rgb(0 0 0 / 28%); font-size: .75rem; pointer-events: auto;
    animation: bxw-toast-in .16s ease both; }
  .bxw-toast-text { min-width: 0; }
  .bxw-toast-close { flex: none; width: 20px; height: 20px; padding: 0; border-color: transparent; color: inherit; }
  .bxw-toast-close:hover { background: var(--bxw-layer); }
  .bxw-toast[data-tone="error"] { border-color: color-mix(in srgb, var(--bxw-bad) 45%, var(--bxw-line)); color: var(--bxw-bad); }
  @keyframes bxw-toast-in { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
  .bxw-confirm { width: min(360px, calc(100vw - 32px)); padding: 16px; border: 1px solid var(--bxw-line);
    border-radius: 10px; background: var(--bxw-panel); color: var(--bxw-primary);
    box-shadow: 0 20px 50px rgb(0 0 0 / 35%); }
  .bxw-confirm::backdrop { background: rgb(0 0 0 / 45%); }
  .bxw-confirm h2 { margin: 0 0 6px; font-size: 1rem; font-weight: 600; }
  .bxw-confirm p { margin: 0 0 14px; color: var(--bxw-soft); line-height: 1.5; }
  .bxw-confirm-actions { display: flex; justify-content: flex-end; gap: 8px; }
  .bxw-confirm-danger { border-color: color-mix(in srgb, var(--bxw-bad) 55%, var(--bxw-line)); color: var(--bxw-bad); }
  /* WCAG 2.5.8: small controls keep their visual size but grow their pointer target
     to at least 24x24. The resizer's 7px bar gets a wider invisible grab zone. */
  .bxw-selection-chip button, .bxw-badge-button, .bxw-focus-compare, .bxw-toast-close {
    position: relative;
  }
  .bxw-selection-chip button::after, .bxw-badge-button::after, .bxw-toast-close::after {
    content: ""; position: absolute; top: 50%; left: 50%; width: 100%; height: 100%;
    min-width: 24px; min-height: 24px; transform: translate(-50%, -50%);
  }
  .bxw-scopes button, .bxw-history-row button, .bxw-job button, .bxw-dimension button,
  .bxw-dock-agent, .bxw-dock-history-toggle {
    position: relative;
  }
  .bxw-scopes button::after, .bxw-history-row button::after, .bxw-job button::after,
  .bxw-dimension button::after, .bxw-dock-agent::after, .bxw-dock-history-toggle::after {
    content: ""; position: absolute; inset-block: -1px; inset-inline: 0;
  }
  .bxw-focus-compare::after {
    content: ""; position: absolute; inset-block: -2px; inset-inline: 0;
  }
  .bxw-resizer::after { content: ""; position: absolute; inset-block: 0; inset-inline: -9px; }
  @media (max-width: 80em) {
    .bxw-models { width: min(var(--bxw-left-width, 210px), 38vw); }
    .bxw-inspector { width: min(var(--bxw-right-width, 292px), 42vw); }
    .bxw-resizer-left { left: calc(14px + min(var(--bxw-left-width, 210px), 38vw)); }
    .bxw-resizer-right { right: calc(14px + min(var(--bxw-right-width, 292px), 42vw)); }
  }
  @media (max-width: 73.75em) {
    .bxw-context-label, .bxw-version { display: none; }
    .bxw-context select { max-width: min(300px, 34vw); }
  }
  @media (max-width: 60em) {
    .bxw-badge-metric { display: none; }
    .bxw-tools button { padding: 0 5px; }
    .bxw-review-trigger span { display: none; }
  }
  @media (max-width: 45em) {
    .bxw-resizer { display: none; }
    .bxw-models, .bxw-inspector {
      position: absolute; top: 8px; bottom: 8px; z-index: 26;
      width: min(86vw, 320px); max-height: none;
    }
    .bxw-models { left: 8px; }
    .bxw-inspector { right: 8px; }
    .bxw-toolbar { flex: 1 1 auto; flex-wrap: wrap; }
    .bxw-brand span { display: none; }
    .bxw-context select { max-width: 32vw; }
  }
  @media (pointer: coarse) {
    .bxw-shell { --bxw-control-h: 44px; --bxw-target: 44px; }
    .bxw-shell button, .bxw-shell select, .bxw-shell input[type="number"],
    .bxw-shell input[type="range"] { min-block-size: 44px; }
    .bxw-shell button { min-inline-size: 44px; }
    .bxw-selection-chip button::after, .bxw-badge-button::after, .bxw-focus-compare::after,
    .bxw-toast-close::after, .bxw-scopes button::after, .bxw-history-row button::after,
    .bxw-job button::after, .bxw-dimension button::after, .bxw-dock-agent::after,
    .bxw-dock-history-toggle::after { display: none; }
    .bxw-resizer::after { inset-inline: -19px; }
  }
  @media (prefers-reduced-motion: reduce) {
    .bxw-toast { animation: none; }
  }
`

const svg = (path, size = 16) => `<svg class="bxw-icon" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${path}</svg>`
const ICONS = {
  cube: svg('<path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Z"/><path d="m4 7.5 8 4.5 8-4.5M12 12v9"/>'),
  chat: svg('<path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4v8Z"/>'),
  chevron: svg('<path d="m7 10 5 5 5-5"/>'),
  chevronRight: svg('<path d="m9 6 6 6-6 6"/>'),
  info: svg('<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>'),
  sun: svg('<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>'),
  moon: svg('<path d="M20 14.6A8 8 0 0 1 9.4 4 8.5 8.5 0 1 0 20 14.6Z"/>'),
  list: svg('<path d="M8 6h12M8 12h12M8 18h12"/><path d="M3 6h.01M3 12h.01M3 18h.01"/>'),
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
    else if (key === 'htmlUnsafe') node.innerHTML = value
    else if (key === 'tabindex') node.setAttribute('tabindex', value)
    else if (key.startsWith('data-')) node.setAttribute(key, value)
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
  // The viewport is served from `base`; both directions of the postMessage channel
  // are pinned to that origin so a foreign window cannot drive the state machine.
  let frameOrigin = ''
  try {
    frameOrigin = new URL(base).origin
  } catch (error) {
    frameOrigin = location.origin
  }
  const state = {
    documents: [],
    docQuery: '',
    docId: options.documentId || null,
    theme: (() => {
      try {
        const saved = localStorage.getItem('bxw-theme')
        if (saved === 'light' || saved === 'dark') return saved
      } catch (error) { /* storage can be denied */ }
      return readTheme().light ? 'light' : 'dark'
    })(),
    sessionId: options.sessionId || options.getSessionId?.() || null,
    current: null,
    plan: null,
    checks: null,
    version: 0,
    request: 0,
    shown: -1,
    ready: false,
    geometryLoading: false,
    stateBusy: false,
    checksBusy: false,
    backgroundStarted: false,
    loadToken: 0,
    loadDocId: null,
    loadTimer: null,
    loadFallback: null,
    wire: false,
    xray: false,
    pickScope: 'face',
    inspector: true,
    busy: false,
    selection: null,
    leftWidth: 260,
    rightWidth: 320,
    timings: {},
    designStarted: null,
    renderMs: null,
    fetchMs: null,
    parseMs: null,
    edgesMs: null,
    reusedScene: false,
    designPending: null,
    designFailed: null,
    designRetries: 0,
    lastDesignAt: 0,
    lastFailureAt: 0,
    lastShownMs: null,
    modeling: false,
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
    selectedBody: null,
    kind: 'part',
    assembly: null,
    assemblyScene: null,
    assemblyBusy: false,
    selectedInstance: null,
    sameDefinition: false,
    assemblyExpanded: new Set(),
    assemblyTrail: [],
    structureQuery: '',
    treeFocus: '',
    assemblyPreviewStartedAt: null,
    assemblyPreviewTimer: null,
    assemblyPreviewLabel: '',
    assemblyPreviewBuildId: null,
    assemblyPreviewPollTimer: null,
    assemblyPreviewProgress: 0,
    assemblyPreviewSeq: 0,
    assemblyPreviewAbort: null,
    assemblyPreviewKey: '',
    assemblyBundleKey: '',
    assemblyPreviewLastGood: null,
    assemblyPreviewPendingGood: null,
    assemblyPreviewPhase: 'idle',
    assemblyPreviewMessage: '',
    bom: null,
    bomBusy: false,
    bomOpen: false,
    pendingAssemblyPreview: false,
    assemblyGeometryShown: false,
    assemblyTimers: [],
    assemblyEditBusy: false,
    assemblyParameters: null,
    assemblyParametersFor: null,
    assemblyParameterBusy: false,
    assemblyReferences: null,
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
  // The workbench is injected into the dsh client, which already owns the page's
  // banner/main landmarks; a div with the same layout classes keeps this chrome from
  // duplicating them.
  const header = el('div', { className: 'bxw-header' })
  const brand = el('div', { className: 'bxw-brand' })
  brand.append(el('span', { className: 'bxw-mark', htmlUnsafe: ICONS.cube }), el('span', {}, 'BrepX'))
  // Document context is not a toolbar action: it names what the canvas is showing.
  // Keeping it outside role="toolbar" keeps the select out of the toolbar's arrow-key
  // roving focus, where it would fight the select's own arrow handling.
  const context = el('div', { className: 'bxw-context', role: 'group', 'aria-label': '文档上下文' })
  const contextLabel = el('span', { className: 'bxw-context-label' }, '模型')
  const docSearch = el('input', {
    type: 'search', className: 'bxw-doc-search', placeholder: '搜索模型', 'aria-label': '搜索模型',
    autocomplete: 'off', spellcheck: 'false', hidden: true,
  })
  const docSelect = el('select', { 'aria-label': '当前模型' })
  const version = el('span', { className: 'bxw-version' }, '')
  // The status text is separate from the inspector control: a count is not an action,
  // and naming the toggle after a changing number makes voice control unstable.
  const checkBadge = el('span', { className: 'bxw-badge' }, '检查 —')
  const metricBadge = el('span', { className: 'bxw-badge bxw-badge-metric' }, '—')
  context.append(contextLabel, docSearch, docSelect, version, checkBadge, metricBadge)
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
  const inspectorToggle = el('button', {
    type: 'button', className: 'bxw-inspector-toggle', title: '打开或收起检查器',
    'aria-label': '打开或收起检查器', 'aria-expanded': 'true', htmlUnsafe: ICONS.info,
  })
  const themeButton = el('button', {
    type: 'button', className: 'bxw-theme-toggle', title: '切换亮色/暗色',
    'aria-label': '切换亮色/暗色', htmlUnsafe: ICONS.sun,
  })
  const bomButton = el('button', {
    type: 'button', className: 'bxw-bom-trigger', title: '查看装配 BOM',
    'aria-label': '查看装配 BOM', hidden: true, htmlUnsafe: ICONS.list + '<span>BOM</span>',
  })
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
    htmlUnsafe: ICONS.panel + '<span>结构</span>',
  })
  const viewButton = el('button', {
    className: 'bxw-view-trigger',
    title: '视图与刷新',
    'aria-label': '视图与刷新',
    'aria-expanded': 'false',
    htmlUnsafe: ICONS.sliders + '<span>视图</span>' + ICONS.chevron,
  })
  // A disclosure of plain toggle buttons: no role=menu contract is promised, so
  // there is no arrow-key roving focus or Tab trapping to rebuild.
  const viewMenu = el('div', {
    className: 'bxw-view-menu',
    hidden: true,
  })
  const menuModels = el('button', { type: 'button', 'aria-pressed': 'true' }, '结构面板')
  const menuNav = el('button', { type: 'button' }, '宿主侧栏')
  const menuInspector = el('button', { type: 'button', 'aria-pressed': 'true' }, '检查器')
  const menuRefresh = el('button', { type: 'button' }, '刷新模型状态')
  viewMenu.append(menuModels, menuNav, menuInspector, el('hr', { className: 'bxw-menu-sep' }), menuRefresh)
  const reviewButton = el('button', {
    className: 'bxw-review-trigger',
    title: '审查工具',
    'aria-label': '审查工具',
    'aria-haspopup': 'dialog',
    'aria-expanded': 'false',
    htmlUnsafe: ICONS.review + '<span>审查</span>' + ICONS.chevron,
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
  const reviewHead = el('div', { className: 'bxw-review-head bxw-review-head-actions' })
  reviewHead.append(el('h3', {}, '审查工具'))
  const reviewClose = el('button', {
    type: 'button', className: 'bxw-review-close', title: '关闭审查工具',
    'aria-label': '关闭审查工具', htmlUnsafe: ICONS.close,
  })
  reviewHead.append(reviewClose)
  reviewMenu.append(reviewHead)
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
  const bomDialog = el('dialog', { className: 'bxw-bom-dialog', 'aria-label': '装配 BOM' })
  const bomHead = el('div', { className: 'bxw-bom-head' })
  bomHead.append(el('strong', {}, '装配 BOM'), el('span', {}, '按零件、版本与配置汇总'))
  const bomExport = el('button', { type: 'button' }, '导出 STEP')
  const bomClose = el('button', { type: 'button', title: '关闭 BOM', 'aria-label': '关闭 BOM', htmlUnsafe: ICONS.close })
  bomHead.append(bomExport, bomClose)
  const bomBody = el('div', { className: 'bxw-bom-body' })
  const bomSummary = el('div', { className: 'bxw-bom-summary' })
  const bomTable = el('table', { className: 'bxw-bom-table' })
  bomBody.append(bomSummary, bomTable)
  bomDialog.append(bomHead, bomBody)
  actions.append(importButton, importInput, structureButton, viewButton, bomButton,
    inspectorToggle, themeButton, reviewButton, viewMenu, reviewMenu)
  const progressLine = el('div', { className: 'bxw-progress', 'aria-hidden': 'true' })
  // One toolbar, two groups: what the viewport shows, and what acts on the document.
  // `focusgroup` gives the whole bar a single tab stop and arrow-key movement so the
  // keyboard no longer has to tab through every control to leave the header.
  const toolbar = el('div', {
    className: 'bxw-toolbar', role: 'toolbar', 'aria-label': '视图与操作',
    focusgroup: 'toolbar wrap',
  })
  const toolbarSeparator = el('span', { role: 'separator', 'aria-orientation': 'vertical' })
  actions.setAttribute('role', 'group')
  actions.setAttribute('aria-label', '操作')
  header.append(brand, context, toolbar, progressLine)

  const main = el('div', { className: 'bxw-main' })
  const stage = el('section', { className: 'bxw-stage' })
  const frame = el('iframe', { className: 'bxw-frame', title: '3D 模型', src: `${base}/api/kernel-view` })
  const tools = el('div', { className: 'bxw-tools', role: 'group', 'aria-label': '视图' })
  const toolButtons = {}
  for (const [name, label] of [['iso', '等轴'], ['front', '前'], ['top', '顶'], ['right', '右']]) {
    const button = el('button', { type: 'button', title: `${label}视图`, 'aria-label': `${label}视图` }, label)
    button.addEventListener('click', () => post('view', { name }))
    toolButtons[name] = button
    tools.append(button)
  }
  tools.append(el('span', { role: 'separator', 'aria-orientation': 'vertical' }))
  const fitButton = el('button', { type: 'button', title: '适配视图', 'aria-label': '适配视图', htmlUnsafe: ICONS.fit })
  fitButton.addEventListener('click', () => post('fit', {}))
  const wireButton = el('button', { type: 'button', title: '线框模式', 'aria-label': '线框模式', htmlUnsafe: ICONS.wire })
  wireButton.setAttribute('aria-pressed', 'false')
  wireButton.addEventListener('click', () => {
    state.wire = !state.wire
    wireButton.setAttribute('aria-pressed', state.wire ? 'true' : 'false')
    post('wire', { on: state.wire })
  })
  const xrayButton = el('button', {
    type: 'button',
    title: '透视模式：半透明显示装配，查看内部结构',
    'aria-label': '透视模式',
    'aria-pressed': 'false',
    hidden: true,
    htmlUnsafe: ICONS.ghost + '<span>透视</span>',
  })
  xrayButton.addEventListener('click', () => {
    const paths = assemblyXrayPaths()
    if (!state.xray && !paths.length) {
      toast('当前装配没有可识别的外壳，无法透视', 'info', 4)
      return
    }
    state.xray = !state.xray
    xrayButton.setAttribute('aria-pressed', state.xray ? 'true' : 'false')
    post('assembly-xray', { on: state.xray, paths: state.xray ? paths : [] })
  })
  tools.append(fitButton, wireButton, xrayButton)
  tools.append(el('span', { role: 'separator', 'aria-orientation': 'vertical' }))
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
  toolbar.append(tools, toolbarSeparator, actions)
  const empty = el('div', { className: 'bxw-empty' })
  const emptyCard = el('div', { className: 'bxw-empty-card' })
  const emptySpinner = el('div', { className: 'bxw-spinner', hidden: true })
  const emptyTitle = el('h2', {}, '选择一个模型')
  const emptyBody = el('p', {}, '新建文档或从模型库打开已有文档，画布会在这里显示。')
  emptyCard.append(emptySpinner, emptyTitle, emptyBody)
  const emptyActions = el('div', { className: 'bxw-empty-actions' })
  const emptyButton = el('button', { type: 'button', htmlUnsafe: ICONS.plus + '<span>新建模型</span>' })
  const assemblyPreviewButton = el('button', { type: 'button', hidden: true }, '显示装配几何')
  const assemblyCancelButton = el('button', { type: 'button', className: 'bxw-preview-cancel', hidden: true }, '清除预览')
  emptyActions.append(emptyButton, assemblyPreviewButton, assemblyCancelButton)
  const emptyHint = el('p', { className: 'bxw-empty-hint', hidden: true })
  emptyCard.append(emptyActions, emptyHint)
  empty.append(emptyCard)
  empty.dataset.on = 'false'
  // Only the stable lead text sits in the polite live region. The numeric read-out
  // changes on every pointermove, so it is plain text; the committed/cancelled value
  // is announced once through the toast region instead of dozens of times per drag.
  const handleChip = el('div', { className: 'bxw-handle-hint', hidden: true })
  const handleChipLead = el('span', { 'aria-live': 'polite' })
  const handleChipValue = el('span')
  const handleChipTail = el('span')
  handleChip.append(handleChipLead, handleChipValue, handleChipTail)
  stage.append(frame, empty, handleChip)

  const models = el('aside', { className: 'bxw-models', 'aria-label': '当前模型结构' })
  const modelsHead = el('div', { className: 'bxw-models-head' })
  const modelsTitle = el('strong', {}, '结构')
  const structureMeta = el('span', { className: 'bxw-structure-meta' }, 'rev —')
  const modelsNew = el('button', { type: 'button', title: '新建模型', 'aria-label': '新建模型', htmlUnsafe: ICONS.plus })
  const modelsClose = el('button', { type: 'button', title: '关闭结构面板', 'aria-label': '关闭结构面板', htmlUnsafe: ICONS.close })
  modelsHead.append(modelsTitle, structureMeta, modelsClose, modelsNew)
  const treeToolbar = el('div', { className: 'bxw-tree-toolbar', hidden: true })
  const structureSearch = el('input', {
    type: 'search', className: 'bxw-tree-search', placeholder: '搜索实例、子系统、定义',
    'aria-label': '搜索装配结构', autocomplete: 'off', spellcheck: 'false',
  })
  const treeExpand = el('button', { type: 'button', title: '展开或折叠全部模块' }, '展开')
  treeToolbar.append(structureSearch, treeExpand)
  const assemblyBreadcrumb = el('div', { className: 'bxw-breadcrumb', hidden: true, 'aria-label': '装配路径' })
  const structureProgress = el('div', { className: 'bxw-structure-progress', hidden: true })
  const structureList = el('div', { className: 'bxw-structure-list', tabindex: '-1', role: 'tree', 'aria-label': '装配结构' })
  models.append(modelsHead, treeToolbar, assemblyBreadcrumb, structureProgress, structureList)

  const inspector = el('aside', { className: 'bxw-inspector', 'aria-label': '模型检查器' })
  const inspectorHead = el('div', { className: 'bxw-inspector-head' })
  const inspectorTitle = el('strong', {}, '模型检查器')
  const inspectorClose = el('button', { type: 'button', title: '收起检查器', 'aria-label': '收起检查器', htmlUnsafe: ICONS.close })
  inspectorClose.addEventListener('click', () => setInspector(false))
  inspectorHead.append(inspectorTitle, inspectorClose)

  const inspectorBody = el('div', { className: 'bxw-inspector-body' })
  const metricsSection = el('section', { className: 'bxw-section' })
  metricsSection.append(el('h3', {}, '几何'))
  const metricsGrid = el('div', { className: 'bxw-metrics' })
  const metricNodes = {}
  for (const [key, label] of [['faces', '面'], ['volume', '体积 mm³'], ['area', '面积 mm²'], ['watertight', '水密']]) {
    const card = el('div', { className: 'bxw-stat' })
    card.append(el('span', {}, label), el('b', {}, '—'))
    metricNodes[key] = card.querySelector('b')
    metricsGrid.append(card)
  }
  metricsSection.append(metricsGrid)
  // Viewport read-out belongs with the geometry it describes. It used to sit in the
  // command bar, where render timing and face counts read as chat state.
  const caption = el('div', { className: 'bxw-caption' })
  const captionFaces = el('span', {}, '—')
  const captionTight = el('span', {}, '—')
  const captionTiming = el('span', {}, '')
  caption.append(captionFaces, captionTight, captionTiming)
  metricsSection.append(caption)

  const assemblySection = el('section', { className: 'bxw-section', hidden: true })
  assemblySection.append(el('h3', {}, '装配'))
  const assemblyGrid = el('div', { className: 'bxw-metrics' })
  const assemblyMetricNodes = {}
  for (const [key, label] of [['instances', '实例'], ['definitions', '定义'], ['parts', '零件'], ['failures', '失败']]) {
    const card = el('div', { className: 'bxw-stat' })
    card.append(el('span', {}, label), el('b', {}, '—'))
    assemblyMetricNodes[key] = card.querySelector('b')
    assemblyGrid.append(card)
  }
  const assemblyNote = el('div', { className: 'bxw-instance-note', hidden: true })
  const assemblyActions = el('div', { className: 'bxw-node-actions' })
  const showGeometryButton = el('button', {
    type: 'button', title: '在视口中显示装配几何',
  }, '显示装配几何')
  const openSubsystemButton = el('button', {
    type: 'button', title: '在独立文档中打开所选子系统', hidden: true,
  }, '打开子系统')
  const sameDefinitionButton = el('button', {
    type: 'button', title: '同时高亮使用同一零件定义的所有实例', disabled: true,
    'aria-pressed': 'false',
  }, '同定义实例')
  const updateReferencesButton = el('button', {
    type: 'button', title: '把过期实例的 pin 更新到最新版本', disabled: true,
  }, '更新引用')
  assemblyActions.append(showGeometryButton, openSubsystemButton, sameDefinitionButton, updateReferencesButton)
  assemblySection.append(assemblyGrid, assemblyNote, assemblyActions)
  structureSearch.addEventListener('input', () => {
    state.structureQuery = structureSearch.value.trim()
    assemblySignature = ''
    renderAssemblyTree()
  })
  treeExpand.addEventListener('click', () => {
    const roots = buildAssemblyTree()
    const allOpen = roots.every((root) => !root.children.length || state.assemblyExpanded.has(root.path))
    for (const root of roots) {
      if (!root.children.length) continue
      if (allOpen) state.assemblyExpanded.delete(root.path)
      else state.assemblyExpanded.add(root.path)
    }
    treeExpand.textContent = allOpen ? '展开' : '折叠'
    renderAssemblyTree()
  })
  showGeometryButton.addEventListener('click', () => showAssemblyGeometry())
  openSubsystemButton.addEventListener('click', () => openAssemblyInstance(selectedAssemblyInstance()))
  sameDefinitionButton.addEventListener('click', toggleSameDefinition)
  updateReferencesButton.addEventListener('click', () => updateAssemblyReferences())

  const assemblyEditSection = el('section', { className: 'bxw-section', hidden: true })
  assemblyEditSection.append(el('h3', {}, '实例编辑'))
  const assemblyEditBody = el('div', { className: 'bxw-focus' })
  assemblyEditSection.append(assemblyEditBody)

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
  const dimensionList = el('div', { className: 'bxw-dimensions', tabindex: '-1' })
  const DIMENSION_ERROR_ID = 'bxw-dimension-error'
  const dimensionError = el('div', {
    className: 'bxw-check', hidden: true, role: 'alert', id: DIMENSION_ERROR_ID,
  })
  dimensionSection.append(dimensionHint, dimensionList, dimensionError)

  const measureInspector = el('section', { className: 'bxw-section', hidden: true })
  const measureHead = el('div', { className: 'bxw-section-head' })
  measureHead.append(el('h3', {}, '测量'))
  const measureClear = el('button', { type: 'button', title: '清除测量', 'aria-label': '清除测量', htmlUnsafe: ICONS.close })
  measureHead.append(measureClear)
  const measureText = el('div', { className: 'bxw-check' }, '在画布上点两处')
  measureInspector.append(measureHead, measureText)
  inspectorBody.append(measureInspector)

  const checkSection = el('section', { className: 'bxw-section' })
  checkSection.append(el('h3', {}, '检查'))
  const checkSummary = el('div', { className: 'bxw-check' }, '—')
  const checkList = el('ul', { className: 'bxw-list', tabindex: '-1' })
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

  inspectorBody.append(metricsSection, assemblySection, assemblyEditSection, selectionSection, focusSection, dimensionSection, planSection,
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
  const dockAgent = el('button', { type: 'button', className: 'bxw-dock-agent', 'aria-label': '展开 Agent 历史', htmlUnsafe: ICONS.chat + '<span>Agent</span>' })
  const dockStatus = el('span', { className: 'bxw-dock-status' }, '等待指令')
  const historyToggle = el('button', { type: 'button', className: 'bxw-dock-history-toggle' }, '历史')
  dockBar.append(dockAgent, dockStatus, historyToggle)
  const historyPeek = el('div', { className: 'bxw-history-peek', hidden: true })
  dock.append(activeCard, dockBar, historyPanel, historyPeek)

  const composer = el('form', { className: 'bxw-composer' })
  const selectionBar = el('div', { className: 'bxw-selection', hidden: true })
  const composerBox = el('div', { className: 'bxw-composer-box' })
  // A real button, not a mode chip: the previous "命令" pill was aria-hidden and inert,
  // so the only way to learn the command set was to read the hint line.
  const commandButton = el('button', {
    type: 'button', className: 'bxw-composer-command', title: '查看可用命令',
    'aria-label': '命令列表', 'aria-haspopup': 'dialog', 'aria-expanded': 'false',
    htmlUnsafe: ICONS.chevronRight + '<span>命令</span>',
  })
  const input = el('textarea', {
    rows: 1,
    placeholder: '输入命令，或描述设计变更… 例如 /fit、/checks、把中心孔改为 Ø40',
    'aria-label': '命令或设计意图',
  })
  const send = el('button', { type: 'submit', className: 'bxw-send', 'aria-label': '执行或发送给 Agent', htmlUnsafe: ICONS.send + '<span>执行</span>' })
  composerBox.append(commandButton, input, send)
  composer.dataset.target = 'inspect'
  const commandMenu = el('div', {
    className: 'bxw-command-menu', role: 'dialog', 'aria-label': '命令列表', hidden: true,
  })
  const commandList = el('div', { className: 'bxw-command-list' })
  commandMenu.append(commandList)
  const COMMANDS = [
    ['/fit', '适配视图'],
    ['/iso', '等轴视图'],
    ['/top', '顶视图'],
    ['/front', '前视图'],
    ['/right', '右视图'],
    ['/wire', '线框模式'],
    ['/checks', '打开检查器'],
    ['/agent', '展开 Agent 历史'],
    ['/models', '结构面板'],
    ['/new', '新建模型'],
    ['/refresh', '刷新模型状态'],
    ['/export step', '导出当前版本'],
    ['/find ', '按描述查找特征'],
  ]
  for (const [name, description] of COMMANDS) {
    const item = el('button', { type: 'button' })
    item.append(el('code', {}, name.trim()), el('small', {}, description))
    item.addEventListener('click', () => {
      input.value = name
      closeCommands()
      input.focus()
      input.setSelectionRange(name.length, name.length)
    })
    commandList.append(item)
  }
  const closeCommands = () => {
    if (commandMenu.hidden) return
    commandMenu.hidden = true
    commandButton.setAttribute('aria-expanded', 'false')
  }
  const openCommands = () => {
    commandMenu.hidden = false
    commandButton.setAttribute('aria-expanded', 'true')
    commandList.querySelector('button')?.focus()
  }
  commandButton.addEventListener('click', () => {
    if (commandMenu.hidden) openCommands()
    else closeCommands()
  })
  commandMenu.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      event.preventDefault()
      closeCommands()
      commandButton.focus()
    }
  })
  document.addEventListener('pointerdown', (event) => {
    if (commandMenu.hidden) return
    if (commandMenu.contains(event.target) || commandButton.contains(event.target)) return
    closeCommands()
  })
  const hint = el('div', { className: 'bxw-hint' }, 'Enter 执行 · Shift+Enter 换行 · 不以 / 开头时发送给 Agent')
  composer.append(selectionBar, composerBox, commandMenu, hint)

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
    type: 'button', title: '关闭方案对比', 'aria-label': '关闭方案对比', htmlUnsafe: ICONS.close,
  })
  variantActions.append(variantBack, variantClose)
  variantHead.append(variantTitle, variantMeta, variantActions)
  const variantGrid = el('div', { className: 'bxw-variants-grid', tabindex: '-1' })
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
    type: 'button', title: '关闭消歧候选', 'aria-label': '关闭消歧候选', htmlUnsafe: ICONS.close,
  })
  candidateClose.addEventListener('click', () => closeCandidates(true))
  candidateHead.append(candidateTitle, candidateMeta, candidateClose)
  const candidateNote = el('div', { className: 'bxw-candidates-note', hidden: true })
  const candidateGrid = el('div', { className: 'bxw-candidates-grid' })
  candidatePanel.append(candidateHead, candidateNote, candidateGrid)
  const toastRegion = el('div', { className: 'bxw-toasts', role: 'region', 'aria-label': '通知' })
  const toastPolite = el('div', { className: 'bxw-toast-stack', 'aria-live': 'polite', 'aria-atomic': 'false' })
  const toastAssertive = el('div', { className: 'bxw-toast-stack', 'aria-live': 'assertive', 'aria-atomic': 'false' })
  toastRegion.append(toastPolite, toastAssertive)
  // Destructive actions confirm through the platform dialog: modal, top-layer, Esc
  // cancellable, with the safe action focused and focus returned by the browser.
  const confirmDialog = el('dialog', { className: 'bxw-confirm', 'aria-labelledby': 'bxw-confirm-title' })
  const confirmForm = el('form', { method: 'dialog' })
  const confirmTitle = el('h2', { id: 'bxw-confirm-title' }, '')
  const confirmBody = el('p', {}, '')
  const confirmActions = el('div', { className: 'bxw-confirm-actions' })
  const confirmCancel = el('button', { type: 'submit', value: 'cancel', autofocus: true }, '取消')
  const confirmOk = el('button', {
    type: 'submit', value: 'confirm', className: 'bxw-confirm-danger',
  }, '确认')
  confirmActions.append(confirmCancel, confirmOk)
  confirmForm.append(confirmTitle, confirmBody, confirmActions)
  confirmDialog.append(confirmForm)
  const menuScrim = el('div', { className: 'bxw-menu-scrim', hidden: true })
  shell.append(header, main, dock, variantPanel, candidatePanel, menuScrim, reviewScrim, toastRegion, confirmDialog, bomDialog)
  main.append(models, stage, inspector)
  const leftResizer = el('div', { className: 'bxw-resizer bxw-resizer-left', role: 'separator', tabindex: '0', 'aria-label': '调整结构栏宽度', 'aria-orientation': 'vertical' })
  const rightResizer = el('div', { className: 'bxw-resizer bxw-resizer-right', role: 'separator', tabindex: '0', 'aria-label': '调整检查器宽度', 'aria-orientation': 'vertical' })
  main.append(leftResizer, rightResizer)
  host.append(shell)
  // Chromium reads the focusgroup attribute when the element becomes connected, so the
  // value set while the tree was still detached is not picked up; applying it again
  // after insertion is what collapses the toolbar to a single tab stop.
  toolbar.setAttribute('focusgroup', 'toolbar wrap')

  const viewportTheme = () => state.theme === 'light'
    ? { background: '#eef2f7', foreground: '#141a22', light: true }
    : { background: '#0b0e13', foreground: '#e8edf5', light: false }
  const applyTheme = (theme, persist = true) => {
    state.theme = theme === 'light' ? 'light' : 'dark'
    shell.dataset.theme = state.theme
    themeButton.innerHTML = state.theme === 'light' ? ICONS.moon : ICONS.sun
    themeButton.setAttribute('aria-label',
      state.theme === 'light' ? '切换到暗色' : '切换到亮色')
    themeButton.title = themeButton.getAttribute('aria-label')
    if (persist) {
      try { localStorage.setItem('bxw-theme', state.theme) } catch (error) { /* storage can be denied */ }
      if (state.ready) post('theme', viewportTheme())
    }
  }
  applyTheme(state.theme, false)
  themeButton.addEventListener('click', () => {
    applyTheme(state.theme === 'light' ? 'dark' : 'light')
  })

  // Panels that call this are already visible, so client rects are non-empty for
  // the controls a keyboard user can actually reach.
  const firstFocusable = (container) => {
    const nodes = container.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')
    for (const node of nodes) {
      if (node.disabled || node.hidden) continue
      if (node.getClientRects().length === 0) continue
      return node
    }
    return null
  }

  // List rebuilds replace the whole subtree, which drops focus to <body>. Interactive
  // rows opt in with data-focus-key; the same key is looked up after the rebuild and
  // the scroll container is the last resort when the row no longer exists.
  const focusKeyOf = (container) => {
    const active = document.activeElement
    if (!active || !container.contains(active)) return ''
    return active.closest('[data-focus-key]')?.dataset.focusKey || ''
  }
  const restoreFocusKey = (key, fallback) => {
    if (!key) return
    const target = [...shell.querySelectorAll('[data-focus-key]')]
      .find((node) => node.dataset.focusKey === key)
    const next = target || fallback
    next?.focus()
    if (target && document.activeElement !== target) fallback?.focus()
  }

  const dockResize = new ResizeObserver(() => {
    const height = Math.ceil(dock.getBoundingClientRect().height)
    shell.style.setProperty('--bxw-dock-h', `${height}px`)
    // The dock floats over the canvas. Tell the viewport how much of its bottom edge is
    // covered so `fit` frames the model in the visible area instead of centring it
    // behind the command box.
    try {
      frame.contentWindow?.postMessage(
        { from: 'brepx-workbench', type: 'inset', bottom: height + 12 }, frameOrigin,
      )
    } catch (error) { /* the frame may be between navigations */ }
  })
  dockResize.observe(dock)
  const inspectorResize = new ResizeObserver(() => {
    shell.style.setProperty('--bxw-inspector-h', `${Math.ceil(inspector.getBoundingClientRect().height)}px`)
  })
  inspectorResize.observe(inspector)

  const toastTimers = new Set()
  const toast = (text, tone = 'info', seconds = 4) => {
    const message = String(text ?? '').trim()
    if (!message) return
    const stack = tone === 'error' ? toastAssertive : toastPolite
    const node = el('div', { className: 'bxw-toast' })
    node.dataset.tone = tone
    node.append(el('span', { className: 'bxw-toast-text' }, message))
    if (tone === 'error') {
      const close = el('button', {
        type: 'button', className: 'bxw-toast-close', title: '关闭通知', 'aria-label': '关闭通知',
        htmlUnsafe: ICONS.close,
      })
      close.addEventListener('click', () => node.remove())
      node.append(close)
    }
    stack.append(node)
    while (stack.childElementCount > 3) stack.firstElementChild?.remove()
    if (tone === 'error') return
    const timer = setTimeout(() => {
      toastTimers.delete(timer)
      node.remove()
    }, Math.max(1, Number(seconds) || 4) * 1000)
    toastTimers.add(timer)
  }

  let confirmResolve = null
  const confirmAction = ({ title, body, confirmLabel = '确认' }) => new Promise((resolve) => {
    if (confirmResolve) confirmResolve(false)
    confirmResolve = resolve
    confirmTitle.textContent = title
    confirmBody.textContent = body
    confirmOk.textContent = confirmLabel
    confirmDialog.returnValue = 'cancel'
    if (confirmDialog.open) confirmDialog.close()
    confirmDialog.showModal()
  })
  confirmDialog.addEventListener('close', () => {
    const resolve = confirmResolve
    confirmResolve = null
    resolve?.(confirmDialog.returnValue === 'confirm')
  })

  const setLoading = (on) => {
    empty.dataset.on = 'true'
    emptySpinner.hidden = !on
    emptyTitle.textContent = on ? '正在加载几何' : '选择一个模型'
    emptyBody.textContent = on
      ? '几何先显示，指标与检查随后在后台更新。'
      : '新建文档或从模型库打开已有文档，画布会在这里显示。'
    emptyButton.hidden = on
    assemblyPreviewButton.hidden = true
    assemblyCancelButton.hidden = true
    emptyHint.hidden = true
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
    inspectorToggle.setAttribute('aria-expanded', state.inspector ? 'true' : 'false')
    menuInspector.setAttribute('aria-pressed', state.inspector ? 'true' : 'false')
  }

  const saveLayout = () => {
    try {
      localStorage.setItem('cadview.layout', JSON.stringify({
        left: state.leftWidth,
        right: state.rightWidth,
      }))
    } catch (error) { /* private mode */ }
  }
  const applyLeftWidth = (width) => {
    state.leftWidth = Math.max(220, Math.min(380, Math.round(width)))
    shell.style.setProperty('--bxw-left-width', `${state.leftWidth}px`)
  }
  const applyRightWidth = (width) => {
    state.rightWidth = Math.max(240, Math.min(480, Math.round(width)))
    shell.style.setProperty('--bxw-right-width', `${state.rightWidth}px`)
  }
  const setLeftWidth = (width) => {
    applyLeftWidth(width)
    saveLayout()
  }
  const setRightWidth = (width) => {
    applyRightWidth(width)
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
      if (side === 'left') applyLeftWidth(startWidth + delta)
      else applyRightWidth(startWidth + delta)
    }
    let ended = false
    const onEnd = () => {
      if (ended) return
      ended = true
      // Persist once on release: a pointermove stream must not write localStorage per frame.
      saveLayout()
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
  let bodySeq = 0
  let loadSeq = 0
  // A dimensions refresh clears the list before the new params arrive; the key of
  // the input that had focus is held until the rebuilt rows can receive it.
  let pendingDimensionFocusKey = ''

  const selectionText = (pick) => {
    if (!pick) return ''
    if (pick.pending) return '正在解析拾取…'
    const parts = []
    if (pick.scope === 'instance') {
      const label = pick.name || pick.path || ''
      if (label) parts.push(label)
      parts.push('实例')
      if (pick.definition_id) parts.push(`${pick.definition_id} v${pick.version ?? '?'}`)
      if (pick.configuration) parts.push(pick.configuration)
      return parts.join(' · ')
    }
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

  // Parsed scenes are large (0.2-1.5 MB JSON, several MB of heap per entry), so the
  // cache is bounded and only the current version of a document is retained: picking
  // never needs an older version, and the viewport keeps its own display copy.
  const SCENE_CACHE_LIMIT = 8
  const sceneCache = new Map()
  const scenePending = new Map()
  // Selecting a feature body needs that body's own face centres for the overlay;
  // the final display mesh only knows the faces of the displayed feature.
  const BODY_SCENE_LIMIT = 4
  const bodyScenes = new Map()

  const trimSceneCache = (documentId, keepKey) => {
    for (const key of [...sceneCache.keys()]) {
      if (key.startsWith(`${documentId}:`) && key !== keepKey) sceneCache.delete(key)
    }
    while (sceneCache.size > SCENE_CACHE_LIMIT) {
      sceneCache.delete(sceneCache.keys().next().value)
    }
  }

  const sceneForDocument = async () => {
    if (!state.docId || !state.current) return null
    const documentId = state.docId
    const version = state.version
    const key = `${documentId}:${version}`
    if (sceneCache.has(key)) {
      const cached = sceneCache.get(key)
      sceneCache.delete(key)
      sceneCache.set(key, cached)
      return cached
    }
    if (scenePending.has(key)) return scenePending.get(key)
    const request = (async () => {
      const scene = await api(`${base}/api/docs/${documentId}/scene`)
      sceneCache.set(key, scene)
      trimSceneCache(documentId, key)
      return scene
    })()
    scenePending.set(key, request)
    try {
      return await request
    } finally {
      scenePending.delete(key)
    }
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

  // `/state` already carries the full checks projection; a separate `/checks` call
  // would return the same bytes again and force another list rebuild.
  const checksSnapshot = (checks) => (checks ? { ...checks, items: checkItems(checks) } : null)

  const refreshAfterCommit = async () => {
    if (!state.docId) return
    const [view, planView] = await Promise.all([
      api(`${base}/api/docs/${state.docId}/state`),
      api(`${base}/api/docs/${state.docId}/plan`),
    ])
    if (!view?.document || view.document.id !== state.docId) return
    state.current = view
    state.version = view.document.version
    state.plan = planView
    state.checks = checksSnapshot(view.checks)
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
      // The failed load leaves no rows to receive the old key; dropping it prevents a
      // later rebuild from focusing the list on behalf of an input that no longer exists.
      pendingDimensionFocusKey = ''
      state.dimensions = null
      renderDimensions()
      toast(`读取尺寸失败：${error.message}`, 'error', 4)
    }
  }

  // One error surface: the role=alert element is the only announcement channel, and
  // the field it belongs to is named by aria-describedby while it is invalid. The
  // input's other describedby ids (the unit span) are preserved.
  const setDimensionInvalid = (input, message) => {
    const ids = (input.getAttribute('aria-describedby') || '')
      .split(/\s+/).filter((id) => id && id !== DIMENSION_ERROR_ID)
    if (message) {
      input.dataset.invalid = 'true'
      input.setAttribute('aria-invalid', 'true')
      ids.push(DIMENSION_ERROR_ID)
      dimensionError.textContent = message
      dimensionError.hidden = false
    } else {
      input.dataset.invalid = 'false'
      input.removeAttribute('aria-invalid')
      dimensionError.hidden = true
      dimensionError.textContent = ''
    }
    if (ids.length) input.setAttribute('aria-describedby', ids.join(' '))
    else input.removeAttribute('aria-describedby')
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
      setDimensionInvalid(input, `${param.label || param.name}：${problem}`)
      return
    }
    if (value === param.value) {
      setDimensionInvalid(input, '')
      return
    }
    setDimensionInvalid(input, '')
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
      setDimensionInvalid(input,
        `更新失败：${error.message}${error.hint ? ` · ${error.hint}` : ''}`)
    } finally {
      state.dimensionBusy = false
      row.dataset.busy = 'false'
    }
  }

  const renderDimensions = () => {
    const featureId = state.dimensionFeature
    const focusKey = pendingDimensionFocusKey || focusKeyOf(dimensionList)
    dimensionSection.hidden = !featureId
    dimensionError.hidden = true
    dimensionError.textContent = ''
    dimensionList.textContent = ''
    if (!featureId) {
      pendingDimensionFocusKey = ''
      return
    }
    dimensionTitle.textContent = `尺寸 · ${featureId}`
    const dimensions = state.dimensions
    if (!dimensions) {
      pendingDimensionFocusKey = focusKey
      dimensionHint.textContent = '正在读取尺寸…'
      return
    }
    pendingDimensionFocusKey = ''
    dimensionHint.textContent = dimensions.feature_type || ''
    if (!dimensions.params?.length) {
      dimensionHint.textContent = '这个特征没有可直接编辑的数值参数'
      restoreFocusKey(focusKey, dimensionList)
      return
    }
    for (const param of dimensions.params) {
      const row = el('div', { className: 'bxw-dimension' })
      const range = []
      if (param.minimum != null) range.push(`≥ ${param.minimum}`)
      if (param.maximum != null) range.push(`≤ ${param.maximum}`)
      const baseLabel = DIMENSION_LABELS[param.name] || param.label || param.name
      // The id must be unique per row and stable across rebuilds so the visible
      // label (including its range hint) is the control's accessible name.
      const inputId = `dim-${String(featureId).replace(/[^A-Za-z0-9_-]/g, '-')}`
        + `-${String(param.name).replace(/[^A-Za-z0-9_-]/g, '-')}`
      const label = el('label', {
        title: param.label || param.name,
        htmlFor: inputId,
      }, baseLabel + (range.length ? ` (${range.join(' ')})` : ''))
      let unitText = DIMENSION_UNITS[param.unit] || param.unit || ''
      if (!unitText && ANGLE_DIMENSIONS.has(param.name)) unitText = '°'
      else if (!unitText && LINEAR_DIMENSIONS.has(param.name)) unitText = 'mm'
      const input = el('input', {
        type: 'number',
        id: inputId,
        value: String(param.value),
        step: param.integer ? '1' : 'any',
      })
      input.dataset.focusKey = `dim:${featureId}:${param.name}`
      if (param.minimum != null) input.min = String(param.minimum)
      if (param.maximum != null) input.max = String(param.maximum)
      const unitId = `${inputId}-unit`
      const unit = el('span', { className: 'bxw-dimension-unit', id: unitId }, unitText)
      // The unit is a description, not part of the name: the visible label already
      // carries the range hint and must stay the spoken name.
      input.setAttribute('aria-describedby', unitId)
      const apply = el('button', { type: 'button', title: '应用这个尺寸' }, '应用')
      apply.dataset.focusKey = `dim-apply:${featureId}:${param.name}`
      apply.addEventListener('click', () => applyDimension(param, input, row))
      input.addEventListener('keydown', (event) => {
        if (event.key !== 'Enter') return
        // Enter confirms an IME candidate too; committing through that key would
        // apply a partially composed number (for example 4 of 40) to the model.
        // 229 is the keyCode Safari reports for the same keystroke.
        if (event.isComposing || event.keyCode === 229) return
        event.preventDefault()
        applyDimension(param, input, row)
      })
      input.addEventListener('input', () => {
        setDimensionInvalid(input, '')
      })
      if (range.length) row.title = `范围 ${range.join(' 且 ')}`
      row.append(label, input, unit, apply)
      dimensionList.append(row)
    }
    restoreFocusKey(focusKey, dimensionList)
  }

  const dimensionLabel = (param, fallback) => DIMENSION_LABELS[param] || fallback || param

  const setHandleHint = (handle, value) => {
    if (!handle) {
      handleChip.hidden = true
      handleChipLead.textContent = ''
      handleChipValue.textContent = ''
      handleChipTail.textContent = ''
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
    const lead = `拖动 ${dimensionLabel(handle.param, handle.label)}`
    // Writing the same string is a mutation too; only touch the live node when the
    // parameter actually changes, which happens once per handle.
    if (handleChipLead.textContent !== lead) handleChipLead.textContent = lead
    handleChipValue.textContent = ` · ${current}${unit}`
    handleChipTail.textContent = ` · 沿 ${direction}`
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
    bodySeq += 1
    state.selection = null
    state.reference = null
    state.selectedBody = null
    state.selectedInstance = null
    state.sameDefinition = false
    state.handle = null
    state.dimensions = null
    state.dimensionFeature = null
    state.drag = null
    renderDimensions()
    setHandleHint(null)
    post('handle', null)
    renderSelection()
    renderStructure()
    post('highlight', { centers: [] })
  }

  const applyPick = (raw) => {
    if (!raw) {
      clearSelection()
      return
    }
    // The viewport's part-picking messages carry face indices of the displayed part
    // scene; an assembly instance is selected from the tree instead.
    if (state.kind === 'assembly') return
    if (raw.documentId && raw.documentId !== state.docId) return
    state.reference = null
    if (state.selectedBody) {
      state.selectedBody = null
      bodySeq += 1
      renderPlan()
    }
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
      selectionSummary.textContent = state.kind === 'assembly'
        ? '在结构树中点选实例'
        : '在画布上点选面或边'
      return
    }
    selectionBar.hidden = false
    if (state.reference) {
      const reference = state.reference
      const chip = el('span', { className: 'bxw-selection-chip' })
      chip.append(el('span', {}, `${reference.what} · ${reference.id}`))
      chip.title = [reference.id, reference.type, ...(reference.reasons || [])].join('\n')
      const clear = el('button', { type: 'button', title: '清除特征引用', 'aria-label': '清除特征引用', htmlUnsafe: ICONS.close })
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
    const clear = el('button', { type: 'button', title: '清除选择', 'aria-label': '清除选择', htmlUnsafe: ICONS.close })
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
    if (document.visibilityState === 'hidden') return
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

  // A 40 MB reference file becomes ~53 MB of base64. Building it in one task blocks
  // input for hundreds of milliseconds, so it is encoded in self-contained 3-byte
  // groups and the main thread is yielded every ~1 MB (scheduler.yield where present).
  const yieldToMain = () => (typeof globalThis.scheduler?.yield === 'function'
    ? globalThis.scheduler.yield()
    : new Promise((resolve) => setTimeout(resolve, 0)))

  const importReference = async (file) => {
    if (!state.docId || !file) return
    if (state.kind === 'assembly') {
      toast('装配文档不支持导入参考几何', 'info', 3)
      return
    }
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
      // btoa needs 3-byte groups: 24576 is divisible by 3, so concatenating the
      // per-chunk encodings yields the same base64 string as one whole-buffer call.
      const chunk = 3 * 8192
      let encoded = ''
      let sinceYield = 0
      for (let offset = 0; offset < bytes.length; offset += chunk) {
        const part = bytes.subarray(offset, offset + chunk)
        encoded += btoa(String.fromCharCode(...part))
        sinceYield += part.length
        if (sinceYield >= 1_000_000) {
          sinceYield = 0
          await yieldToMain()
        }
      }
      const result = await api(`${base}/api/docs/${targetId}/import/file`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: file.name, data: encoded, format }),
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
        window.open(state.kind === 'assembly'
          ? `${base}/api/assemblies/${state.docId}/export`
          : `${base}/api/docs/${state.docId}/export/${arg || 'step'}`, '_blank', 'noopener')
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
    menuModels.setAttribute('aria-pressed', on ? 'true' : 'false')
  }
  const closeViewMenu = () => {
    // Keyboard open moves focus into the menu; hiding it would drop focus to
    // <body>, so it goes back to the trigger that owns the disclosure.
    const hadFocus = viewMenu.contains(document.activeElement)
    viewMenu.hidden = true
    menuScrim.hidden = true
    viewButton.setAttribute('aria-expanded', 'false')
    if (hadFocus) viewButton.focus()
  }
  const openViewMenu = () => {
    closeReviewMenu()
    viewMenu.hidden = false
    menuScrim.hidden = false
    viewButton.setAttribute('aria-expanded', 'true')
    menuInspector.setAttribute('aria-pressed', state.inspector ? 'true' : 'false')
    menuModels.setAttribute('aria-pressed', shell.dataset.models === 'off' ? 'false' : 'true')
  }

  viewButton.addEventListener('click', (event) => {
    event.stopPropagation()
    if (!viewMenu.hidden) {
      closeViewMenu()
      return
    }
    openViewMenu()
    // detail === 0 means the button was activated from the keyboard; move focus
    // into the disclosure so the next Tab continues from the commands.
    if (event.detail === 0) menuModels.focus()
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
  reviewClose.addEventListener('click', () => closeReviewMenu(true))
  reviewScrim.addEventListener('click', () => closeReviewMenu(true))
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
  docDelete.addEventListener('click', async () => {
    const name = state.current?.document?.name || state.docId
    const ok = await confirmAction({
      title: '删除当前模型',
      body: `将删除「${name}」及其全部里程碑，此操作不可撤销。`,
      confirmLabel: '删除',
    })
    if (ok) deleteCurrentDocument()
  })

  const toggleHistory = () => openHistory(!state.historyOpen)
  dockAgent.addEventListener('click', toggleHistory)
  inspectorToggle.addEventListener('click', () => setInspector(!state.inspector))
  bomButton.addEventListener('click', () => openBom())
  bomExport.addEventListener('click', () => {
    if (state.kind !== 'assembly' || !state.docId) return
    window.open(`${base}/api/assemblies/${state.docId}/export`, '_blank', 'noopener')
  })
  bomClose.addEventListener('click', () => bomDialog.close())
  bomDialog.addEventListener('click', (event) => {
    if (event.target === bomDialog) bomDialog.close()
  })
  assemblyPreviewButton.addEventListener('click', () => showAssemblyGeometry())
  assemblyCancelButton.addEventListener('click', () => clearAssemblyPreview())
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
      frame.contentWindow?.postMessage({ from: 'brepx-workbench', type, ...payload }, frameOrigin)
    } catch (error) { /* frame may be between navigations */ }
  }

  // A design stays "in flight" until `shown`/`error` arrives or the attempt is older
  // than this budget. The viewport's scene path answers in well under 1 s and a STEP
  // fallback for a normal document takes 0.5-2 s, so 6 s distinguishes "still working"
  // from "lost" without leaving a blank canvas for long; the budget also grows with the
  // last observed post-to-shown latency, capped at 15 s for unusually large transfers.
  const DESIGN_TIMEOUT_MS = 6000
  const DESIGN_MAX_TIMEOUT_MS = 15000
  const DESIGN_BACKOFF_MS = [1500, 3000, 6000]
  const DESIGN_MAX_RETRIES = 3

  const designTimeout = () => Math.min(
    DESIGN_MAX_TIMEOUT_MS,
    Math.max(DESIGN_TIMEOUT_MS, Math.round((state.lastShownMs || 0) * 2)),
  )

  const designInFlight = () => {
    const pending = state.designPending
    if (!pending) return false
    if (pending.documentId !== state.docId || pending.version !== state.version) return false
    return performance.now() - pending.startedAt < designTimeout()
  }

  const pushDesign = (fit = false) => {
    if (!state.current || !state.ready) return false
    if (state.current.vacant) {
      post('clear', {})
      return false
    }
    if (state.designFailed) return false
    if (designInFlight()) return false
    const startedAt = performance.now()
    const requestId = ++state.request
    state.designStarted = startedAt
    state.lastDesignAt = startedAt
    state.designPending = { documentId: state.docId, version: state.version, requestId, startedAt }
    post('theme', viewportTheme())
    post('design', {
      documentId: state.docId,
      version: state.version,
      requestId,
      fit,
    })
    return true
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

  const closeReviewMenu = (restoreFocus = false) => {
    if (reviewMenu.hidden) return
    reviewMenu.hidden = true
    reviewScrim.hidden = true
    reviewButton.setAttribute('aria-expanded', 'false')
    if (restoreFocus) reviewButton.focus()
  }

  const openReviewMenu = () => {
    closeViewMenu()
    renderReview()
    reviewMenu.hidden = false
    reviewScrim.hidden = false
    reviewButton.setAttribute('aria-expanded', 'true')
    // The scrim makes the panel modal for the pointer; keyboard focus must follow
    // it into the panel instead of staying on the toolbar trigger behind it.
    firstFocusable(reviewMenu)?.focus()
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
    const focusKey = focusKeyOf(variantGrid)
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
      restoreFocusKey(focusKey, variantGrid)
      return
    }
    for (const variant of set.variants) {
      const failedChecks = (variant.checks || []).filter((check) => !check.ok).length
      const adoptable = Boolean(variant.ok && !failedChecks && (variant.ops?.length)
        && !stale && !applying)
      // The card is a plain article: focus and action stay on the real buttons inside
      // it, so no widget role or nested-interactive ambiguity is implied.
      const card = el('article', { className: 'bxw-variant' })
      if (state.variantPreview === variant.index) card.dataset.active = 'true'
      if (!variant.ok) card.dataset.failed = 'true'
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
        previewButton.dataset.focusKey = `variant-preview:${variant.index}`
        previewButton.addEventListener('click', (event) => {
          event.stopPropagation()
          previewVariant(variant)
        })
        buttons.append(previewButton)
      }
      if (adoptable) {
        const applyButton = el('button', { type: 'button', disabled: applying }, '采纳')
        applyButton.dataset.focusKey = `variant-apply:${variant.index}`
        applyButton.addEventListener('click', (event) => {
          event.stopPropagation()
          applyVariant(variant)
        })
        buttons.append(applyButton)
      }
      card.append(thumb, body)
      if (buttons.childElementCount) card.append(buttons)
      variantGrid.append(card)
    }
    restoreFocusKey(focusKey, variantGrid)
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
  const CANDIDATE_CACHE_LIMIT = 32
  const candidateCenters = new Map()
  const candidatePending = new Map()
  let candidateRequest = 0
  let candidateHover = 0
  let candidateFocusPending = false

  const featureCenters = async (featureId) => {
    const documentId = state.docId
    const version = state.version
    const key = `${documentId}:${version}:${featureId}`
    if (candidateCenters.has(key)) {
      const cached = candidateCenters.get(key)
      candidateCenters.delete(key)
      candidateCenters.set(key, cached)
      return cached
    }
    if (candidatePending.has(key)) return candidatePending.get(key)
    const request = (async () => {
      let centers = []
      try {
        const scene = await api(`${base}/api/docs/${documentId}/scene?feature=${encodeURIComponent(featureId)}`)
        centers = (scene.faces || []).map((face) => face.center).filter(Array.isArray)
      } catch (error) {
        centers = []
      }
      candidateCenters.set(key, centers)
      while (candidateCenters.size > CANDIDATE_CACHE_LIMIT) {
        candidateCenters.delete(candidateCenters.keys().next().value)
      }
      return centers
    })()
    candidatePending.set(key, request)
    try {
      return await request
    } finally {
      candidatePending.delete(key)
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

  const closeCandidates = (restoreFocus = false) => {
    const wasOpen = !candidatePanel.hidden
    candidateRequest += 1
    candidateHover += 1
    state.candidates = null
    state.candidateBusy = false
    renderCandidates()
    // The composer is the control that opened the candidates (via /find), so focus
    // goes back there instead of falling to <body> with the removed panel.
    if (restoreFocus && wasOpen) input.focus()
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
    const wasHidden = candidatePanel.hidden
    candidatePanel.hidden = !visible
    if (!visible) {
      candidateFocusPending = false
      return
    }
    if (wasHidden) candidateFocusPending = true
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
      if (candidateFocusPending) {
        candidateFocusPending = false
        candidateClose.focus()
      }
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
    if (candidateFocusPending) {
      candidateFocusPending = false
      candidateGrid.querySelector('button')?.focus()
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

  const renderDocuments = () => {
    docSelect.textContent = ''
    docSearch.hidden = state.documents.length < 12
    docSearch.value = state.docQuery
    if (!state.documents.length) {
      docSelect.append(el('option', { value: '' }, '没有模型'))
      docSelect.disabled = true
      return
    }
    docSelect.disabled = false
    const needle = state.docQuery.toLocaleLowerCase()
    const matches = state.documents.filter((doc) => !needle
      || `${doc.name || ''} ${doc.id} ${doc.kind === 'assembly' ? '装配 assembly' : '零件 part'}`
        .toLocaleLowerCase().includes(needle))
    const current = state.documents.find((doc) => doc.id === state.docId)
    if (current && !matches.some((doc) => doc.id === current.id)) matches.unshift(current)
    if (!matches.length) {
      docSelect.append(el('option', { value: '' }, '没有匹配的模型'))
      docSelect.value = ''
      return
    }
    for (const kind of ['assembly', 'part']) {
      const group = matches.filter((doc) => (doc.kind === 'assembly') === (kind === 'assembly'))
      if (!group.length) continue
      const optgroup = el('optgroup', { label: kind === 'assembly' ? '装配' : '零件' })
      for (const doc of group) {
        const name = doc.name || doc.id
        const option = el('option', { value: doc.id, title: name }, `${name} · v${doc.version ?? 0}`)
        optgroup.append(option)
      }
      docSelect.append(optgroup)
    }
    if (state.docId) docSelect.value = state.docId
  }

  const bodies = () => (state.current?.bodies || []).filter((body) => body?.feature_id)

  const bodyMeta = (body, feature) => {
    const metrics = body.metrics || {}
    const parts = [body.feature_type || 'feature']
    if (metrics.faces != null) parts.push(`${fmt(metrics.faces)} 面`)
    if (metrics.volume != null) parts.push(`${fmt(metrics.volume, 1)} mm³`)
    if (body.is_final) parts.push('最终')
    if (body.visible === false) parts.push('隐藏')
    if (feature?.actor) parts.push(feature.actor)
    return parts.join(' · ')
  }

  const bodyDetail = (body) => {
    const parts = []
    const params = Object.entries(body.params || {})
    if (params.length) {
      parts.push(`参数 ${params.map(([key, value]) => `${key}=${value}`).join(' ')}`)
    }
    if (body.inputs?.length) parts.push(`输入 ${body.inputs.join('、')}`)
    return parts.join('\n')
  }

  let planSignature = ''

  const renderPlan = () => {
    if (state.kind === 'assembly') return
    structureList.setAttribute('role', 'list')
    structureList.setAttribute('aria-label', '零件结构')
    const plan = state.plan?.plan
    const nodes = plan?.nodes || []
    const features = state.current?.features || []
    const bodyList = bodies()
    const featureById = new Map(features.map((feature) => [feature.id, feature]))
    const featureOrder = new Map(features.map((feature, index) => [feature.id, index]))
    const orderedBodies = [...bodyList].sort((left, right) => {
      const a = featureOrder.get(left.feature_id)
      const b = featureOrder.get(right.feature_id)
      if (a != null && b != null) return a - b
      if (a != null) return -1
      if (b != null) return 1
      return 0
    })
    const nodeFor = (featureId) => nodes.find((node) => node.id === featureId || node.feature_id === featureId)
    const entries = []
    if (orderedBodies.length) {
      // A built body already names its feature, so it is the feature row: listing both
      // would make one edit target appear twice in the tree.
      for (const body of orderedBodies) {
        const feature = featureById.get(body.feature_id)
        const node = nodeFor(body.feature_id)
        entries.push({
          key: body.feature_id,
          title: body.feature_id,
          meta: bodyMeta(body, feature),
          status: node?.status || (feature?.enabled === false ? 'pending' : 'done'),
          error: feature?.error || node?.error,
          detail: bodyDetail(body),
          body,
          node,
        })
      }
      for (const feature of features) {
        if (bodyList.some((body) => body.feature_id === feature.id)) continue
        entries.push({
          key: feature.id,
          title: feature.id,
          meta: `${feature.type || 'feature'}${feature.actor ? ` · ${feature.actor}` : ''}`,
          status: nodeFor(feature.id)?.status || (feature.enabled === false ? 'pending' : 'done'),
          error: feature.error,
          node: nodeFor(feature.id),
        })
      }
    } else if (features.length) {
      for (const feature of features.slice(-80)) {
        entries.push({
          key: feature.id,
          title: feature.id,
          meta: `${feature.type || 'feature'}${feature.actor ? ` · ${feature.actor}` : ''}`,
          status: nodeFor(feature.id)?.status || (feature.enabled === false ? 'pending' : 'done'),
          error: feature.error,
          node: nodeFor(feature.id),
        })
      }
    } else {
      for (const node of nodes.slice(-40)) {
        entries.push({
          key: node.id,
          title: node.title || node.id,
          meta: `${node.action || node.kind || ''}${node.id ? ` · ${node.id}` : ''}`,
          status: node.status || 'pending',
          error: node.error,
          node,
        })
      }
    }
    // Every input of the rendered rows is in the signature; unchanged state must not
    // rebuild the list, because renderState is called on every background refresh.
    const signature = JSON.stringify([
      plan?.revision ?? null,
      state.modeling,
      state.stateBusy,
      Boolean(state.current),
      state.version,
      state.selectedNode,
      state.selectedBody,
      entries.map((entry) => [
        entry.key, entry.title, entry.meta, entry.status, entry.error || '',
        entry.body?.visible ?? null, entry.body?.is_final ?? null,
        entry.node?.id ?? null, entry.detail || '',
      ]),
    ])
    if (signature === planSignature) return
    planSignature = signature
    const focusKey = focusKeyOf(structureList)
    structureMeta.textContent = plan?.revision != null ? `rev ${plan.revision}` : 'rev —'
    structureProgress.hidden = !state.modeling
    const progress = document.createDocumentFragment()
    if (state.modeling) {
      const done = nodes.filter((node) => node.status === 'done').length
      const total = nodes.length
      progress.append(el('b', {}, `构建中 ${done}/${total || '—'}`))
      // Determinate progress for assistive tech; the 2px header line stays decorative.
      const bar = el('progress', {
        className: 'bxw-structure-progress-bar',
        'aria-label': '计划构建进度',
        max: String(total || 1),
        value: String(done),
      })
      progress.append(bar)
    }
    structureProgress.replaceChildren(progress)
    const fragment = document.createDocumentFragment()
    if (!entries.length) {
      fragment.append(el('div', { className: 'bxw-structure-empty' },
        state.stateBusy ? '正在读取结构…' : state.current ? '这个模型还没有特征' : '选择一个模型查看结构'))
      structureList.replaceChildren(fragment)
      restoreFocusKey(focusKey, structureList)
      return
    }
    let group = ''
    for (const entry of entries) {
      const rowGroup = entry.body ? '实体' : (bodyList.length ? '其他特征' : '')
      if (rowGroup && rowGroup !== group) {
        group = rowGroup
        fragment.append(el('div', { className: 'bxw-structure-group' }, rowGroup))
      }
      const interactive = Boolean(entry.body || entry.node)
      // Only a row that runs an action is a control; the rest stay static and are
      // skipped by Tab instead of announcing a button that does nothing.
      const row = el('div', { className: 'bxw-structure-row', tabindex: interactive ? '0' : '-1' })
      row.dataset.key = entry.key
      row.dataset.focusKey = `structure:${entry.key}`
      if (interactive) {
        row.dataset.node = entry.body ? entry.body.feature_id : entry.node.id
        row.setAttribute('role', 'button')
      }
      if (entry.body?.visible === false) row.dataset.hidden = 'true'
      const selected = entry.body
        ? (state.selectedBody
          ? state.selectedBody === entry.body.feature_id
          : entry.node != null && state.selectedNode === entry.node.id)
        : entry.node != null && state.selectedNode === entry.node.id
      if (selected) row.dataset.selected = 'true'
      const dot = el('span', { className: 'bxw-dot' })
      dot.dataset.state = entry.status
      const main = el('div', { className: 'bxw-structure-main' })
      main.append(el('b', {}, entry.title), el('span', {}, entry.meta))
      row.append(dot, main)
      row.title = [entry.error, entry.title, entry.meta, entry.detail].filter(Boolean).join('\n')
      if (entry.body || entry.node) {
        const activate = () => {
          if (entry.body) selectBody(entry.body)
          else selectPlanNode(entry.node.id)
        }
        row.addEventListener('click', activate)
        row.addEventListener('keydown', (event) => {
          if (event.key !== 'Enter' && event.key !== ' ') return
          event.preventDefault()
          activate()
        })
      }
      fragment.append(row)
    }
    structureList.replaceChildren(fragment)
    restoreFocusKey(focusKey, structureList)
  }

  const AUTO_ASSEMBLY_PREVIEW_PARTS = 250
  // Highlight anchors are matched against every displayed face, so an unbounded
  // anchor list from a heavy definition would make selection itself the slow path.
  const ASSEMBLY_HIGHLIGHT_LIMIT = 2400

  let assemblySignature = ''
  let assemblyInspectorSignature = ''
  const assemblyCenterCache = new Map()

  const assemblyInstances = () => {
    if (state.assemblyScene?.instances?.length) return state.assemblyScene.instances
    return state.assembly?.build?.instances || []
  }

  const ASSEMBLY_XRAY_SHELL = /机匣|短舱|外涵|外壳|cowl|nacelle|casing|case|shroud|罩|整流/i
  const assemblyXrayPaths = () => assemblyInstances()
    .filter((instance) => instance.definition_kind === 'part'
      && ASSEMBLY_XRAY_SHELL.test(instance.name || ''))
    .map((instance) => instance.path)

  const assemblyName = () => state.assembly?.assembly?.name || state.assembly?.name || state.docId

  const assemblyDefinitionKey = (instance) => {
    if (!instance) return null
    if (instance.definition_key) return instance.definition_key
    if (instance.definition_kind !== 'part') return null
    return `${instance.definition_id}@${instance.version}#${instance.configuration || 'default'}`
  }

  const assemblyDefinition = (instance) => {
    const key = assemblyDefinitionKey(instance)
    return key ? state.assemblyScene?.definitions?.[key] || null : null
  }

  const assemblyDefinitionCenters = (instance) => {
    const key = assemblyDefinitionKey(instance)
    if (!key) return []
    const cached = assemblyCenterCache.get(key)
    if (cached) return cached
    const faces = state.assemblyScene?.definitions?.[key]?.faces || []
    const centers = faces.map((face) => face.center).filter(Array.isArray)
    assemblyCenterCache.set(key, centers)
    return centers
  }

  // Scene definitions are in part coordinates; instance.placement is a row-major
  // rotation plus translation, so a local point lands at R*p + t.
  const placeAssemblyPoint = (point, placement) => {
    const translation = Array.isArray(placement?.translation) ? placement.translation : [0, 0, 0]
    const rotation = Array.isArray(placement?.rotation) ? placement.rotation : null
    if (!rotation || rotation.length < 3) {
      return [point[0] + translation[0], point[1] + translation[1], point[2] + translation[2]]
    }
    return [
      rotation[0][0] * point[0] + rotation[0][1] * point[1] + rotation[0][2] * point[2] + translation[0],
      rotation[1][0] * point[0] + rotation[1][1] * point[1] + rotation[1][2] * point[2] + translation[1],
      rotation[2][0] * point[0] + rotation[2][1] * point[1] + rotation[2][2] * point[2] + translation[2],
    ]
  }

  const assemblyWorldBounds = (instance) => {
    const definition = assemblyDefinition(instance)
    const minimum = definition?.metrics?.bbox_min
    const maximum = definition?.metrics?.bbox_max
    if (!Array.isArray(minimum) || !Array.isArray(maximum)) return null
    const low = [Infinity, Infinity, Infinity]
    const high = [-Infinity, -Infinity, -Infinity]
    for (const x of [minimum[0], maximum[0]]) {
      for (const y of [minimum[1], maximum[1]]) {
        for (const z of [minimum[2], maximum[2]]) {
          const placed = placeAssemblyPoint([x, y, z], instance.placement)
          for (let axis = 0; axis < 3; axis += 1) {
            low[axis] = Math.min(low[axis], placed[axis])
            high[axis] = Math.max(high[axis], placed[axis])
          }
        }
      }
    }
    if (!low.every(Number.isFinite)) return null
    return { min: low, max: high, size: high.map((value, axis) => value - low[axis]) }
  }

  const instanceSelection = (instance) => ({
    scope: 'instance',
    path: instance.path || instance.instance_id,
    instance_id: instance.instance_id,
    name: instance.name || '',
    definition_id: instance.definition_id,
    definition_kind: instance.definition_kind,
    definition_key: assemblyDefinitionKey(instance),
    version: instance.version,
    configuration: instance.configuration || '',
    placement: instance.placement,
    suppressed: Boolean(instance.suppressed),
    visible: instance.visible !== false,
    error: instance.error || null,
    documentId: state.docId,
    assembly_version: state.version,
  })

  const sameDefinitionInstances = (instance) => {
    const key = assemblyDefinitionKey(instance)
    if (!key) return []
    return assemblyInstances().filter((item) => assemblyDefinitionKey(item) === key)
  }

  const collectAssemblyCenters = (instances) => {
    const centers = []
    for (const instance of instances) {
      if (instance.suppressed || instance.visible === false || instance.error) continue
      if (!assemblyDefinition(instance)) continue
      for (const point of assemblyDefinitionCenters(instance)) {
        centers.push(placeAssemblyPoint(point, instance.placement))
        if (centers.length >= ASSEMBLY_HIGHLIGHT_LIMIT) return { centers, truncated: true }
      }
    }
    return { centers, truncated: false }
  }

  const highlightSelection = () => {
    if (state.kind !== 'assembly') return
    const selection = state.selection?.scope === 'instance' ? state.selection : null
    if (!selection) {
      post('highlight', { centers: [] })
      return
    }
    const instance = assemblyInstances()
      .find((item) => (item.path || item.instance_id) === selection.path)
    if (!instance) return
    const targets = state.sameDefinition ? sameDefinitionInstances(instance) : [instance]
    const { centers } = collectAssemblyCenters(targets)
    post('highlight', centers.length ? { centers, seconds: 0, tone: 'selection' } : { centers: [] })
  }

  function toggleSameDefinition() {
    if (state.kind !== 'assembly') return
    const selection = state.selection?.scope === 'instance' ? state.selection : null
    if (!selection?.definition_key) return
    const instance = assemblyInstances()
      .find((item) => (item.path || item.instance_id) === selection.path)
    if (!instance) return
    state.sameDefinition = !state.sameDefinition
    renderAssemblyTree()
    renderAssemblyInspector()
    highlightSelection()
    if (state.sameDefinition) {
      toast(`已选择 ${sameDefinitionInstances(instance).length} 个同定义实例`, 'info', 2)
    }
  }

  const scheduleAssemblyHighlight = () => {
    for (const timer of state.assemblyTimers) clearTimeout(timer)
    state.assemblyTimers = [1800, 4200].map((delay) => setTimeout(() => {
      if (state.kind === 'assembly' && state.selectedInstance) highlightSelection()
    }, delay))
  }

  const selectedAssemblyInstance = () => {
    if (!state.selectedInstance) return null
    return assemblyInstances().find((item) => (item.path || item.instance_id) === state.selectedInstance) || null
  }

  const assemblyPreviewScope = () => {
    const instance = selectedAssemblyInstance()
    if (instance?.definition_kind === 'assembly'
      && instance.path === instance.instance_id
      && instance.definition_id) {
      const count = assemblyInstances().filter((item) => String(item.path || '').startsWith(`${instance.path}/`)).length
      return {
        docId: instance.definition_id,
        label: `${instanceTitle(instance)} · ${fmt(count)} 实例`,
        count,
        subsystem: true,
      }
    }
    const leaves = assemblyInstances().filter((item) => item.definition_kind === 'part').length
    return {
      docId: state.docId,
      label: `整机预览 · ${fmt(leaves)} 个零件`,
      count: leaves,
      subsystem: false,
    }
  }

  const stopAssemblyPreviewClock = () => {
    if (state.assemblyPreviewTimer) clearInterval(state.assemblyPreviewTimer)
    state.assemblyPreviewTimer = null
  }

  const startAssemblyPreviewClock = () => {
    if (!state.assemblyPreviewStartedAt) state.assemblyPreviewStartedAt = performance.now()
    if (!state.assemblyPreviewTimer) {
      state.assemblyPreviewTimer = setInterval(() => {
        if (!state.assemblyPreviewStartedAt) return
        renderAssemblyEmpty()
      }, 250)
    }
  }

  const stopAssemblyPreviewPoll = () => {
    if (state.assemblyPreviewPollTimer) clearInterval(state.assemblyPreviewPollTimer)
    state.assemblyPreviewPollTimer = null
  }

  const stopAssemblyPreviewRequest = () => {
    stopAssemblyPreviewPoll()
    state.assemblyPreviewAbort?.abort()
    state.assemblyPreviewAbort = null
    state.assemblyPreviewBuildId = null
    state.assemblyPreviewProgress = 0
    state.assemblyPreviewKey = ''
    state.assemblyBundleKey = ''
  }

  const requestAssemblyPreviewCancel = (buildId) => {
    if (!buildId) return
    fetch(`${base}/api/preview/builds/${encodeURIComponent(buildId)}/cancel`, {
      method: 'POST',
      cache: 'no-store',
    }).catch(() => {})
  }

  const cancelAssemblyPreviewBuild = () => {
    const buildId = state.assemblyPreviewBuildId
    state.assemblyPreviewSeq += 1
    stopAssemblyPreviewRequest()
    state.assemblyPreviewPendingGood = null
    requestAssemblyPreviewCancel(buildId)
  }

  const restoreAssemblyPreviewLastGood = (message, fallback = null) => {
    const saved = fallback
      ? {
          bundleKey: fallback.bundleKey || '',
          previewKey: fallback.previewKey || '',
          bundleUrl: fallback.bundleUrl
            || (fallback.bundleKey ? `${base}/api/preview/${encodeURIComponent(fallback.bundleKey)}.bpx` : ''),
          label: state.assemblyPreviewLabel || '上次完整预览',
          docId: state.docId,
          version: fallback.assemblyVersion ?? state.version,
        }
      : state.assemblyPreviewLastGood
    if (!saved?.bundleUrl || !saved?.bundleKey) return false
    state.assemblyPreviewLastGood = { ...saved }
    state.assemblyPreviewPendingGood = { ...saved }
    state.assemblyPreviewKey = saved.previewKey || ''
    state.assemblyBundleKey = saved.bundleKey
    state.assemblyPreviewPhase = 'fallback'
    state.assemblyPreviewMessage = message || ''
    state.assemblyPreviewStartedAt = null
    state.assemblyPreviewProgress = 1
    state.assemblyGeometryShown = true
    state.assemblyPreviewLabel = saved.label || '上次完整预览'
    post('assembly-preview', {
      bundleUrl: saved.bundleUrl,
      bundleKey: saved.bundleKey,
      previewKey: saved.previewKey,
      assemblyId: saved.docId || state.docId,
      version: saved.version,
      label: saved.label,
      fallback: true,
    })
    renderAssemblyEmpty()
    renderAssemblyInspector()
    if (message) toast(`新装配预览失败，保留上次完整预览：${message}`, 'warn', 7)
    return true
  }

  const failAssemblyPreviewRequest = (message, options = {}) => {
    const scope = options.scope || assemblyPreviewScope()
    stopAssemblyPreviewClock()
    stopAssemblyPreviewRequest()
    state.assemblyPreviewStartedAt = null
    state.assemblyPreviewProgress = 0
    state.assemblyPreviewBuildId = null
    state.assemblyPreviewPendingGood = null
    if (options.rollback) {
      // A deployment rollback disables the preview path; root STEP is never a
      // fallback, so only a selected subsystem may continue through STEP.
      if (scope.subsystem) {
        state.assemblyPreviewPhase = 'step'
        state.assemblyPreviewMessage = message
        state.assemblyGeometryShown = true
        state.assemblyPreviewLabel = scope.label
        post('preview', {
          url: `${base}/api/assemblies/${encodeURIComponent(scope.docId)}/export`,
          label: scope.label,
        })
        renderAssemblyEmpty()
        renderAssemblyInspector()
        toast('装配预览已停用，回退到子系统 STEP', 'warn', 7)
        return
      }
      state.assemblyPreviewPhase = 'failed'
      state.assemblyPreviewMessage = '装配预览已在服务端停用；请从结构树选择子系统预览局部 STEP。'
      state.assemblyGeometryShown = false
      state.assemblyPreviewLabel = ''
      renderAssemblyEmpty()
      renderAssemblyInspector()
      toast('装配预览已停用；整机不会回退到扁平 STEP，请选择子系统', 'warn', 8)
      return
    }
    const fallback = options.fallback || null
    const lastGood = state.assemblyPreviewLastGood
    const canRestore = Boolean(
      fallback
      || (lastGood
        && lastGood.docId === scope.docId
        && Boolean(lastGood.subsystem) === Boolean(scope.subsystem)),
    )
    if (canRestore && restoreAssemblyPreviewLastGood(message, fallback)) return
    if (scope.subsystem) {
      // A subsystem is small enough for STEP; the full root never takes this path.
      state.assemblyPreviewPhase = 'step'
      state.assemblyPreviewMessage = message
      state.assemblyGeometryShown = true
      state.assemblyPreviewLabel = scope.label
      post('preview', {
        url: `${base}/api/assemblies/${encodeURIComponent(scope.docId)}/export`,
        label: scope.label,
      })
      renderAssemblyEmpty()
      renderAssemblyInspector()
      toast(`子系统预览失败，回退到子系统 STEP：${message}`, 'warn', 7)
      return
    }
    state.assemblyPreviewPhase = 'failed'
    state.assemblyPreviewMessage = message
    state.assemblyGeometryShown = false
    state.assemblyPreviewLabel = ''
    renderAssemblyEmpty()
    renderAssemblyInspector()
    toast(`整机预览失败：${message}；请选择子系统预览局部 STEP。`, 'error', 8)
  }

  const postAssemblyPreviewBundle = (scope, previewKey, bundleKey) => {
    if (!bundleKey) {
      failAssemblyPreviewRequest('预览服务没有返回内容寻址包标识', { scope })
      return
    }
    const bundleUrl = `${base}/api/preview/${encodeURIComponent(bundleKey)}.bpx`
    state.assemblyPreviewKey = previewKey || ''
    state.assemblyBundleKey = bundleKey
    state.assemblyPreviewPendingGood = {
      bundleUrl,
      bundleKey,
      previewKey,
      label: scope.label,
      docId: scope.docId,
      version: state.version,
      subsystem: scope.subsystem,
    }
    state.assemblyPreviewPhase = 'ready'
    post('assembly-preview', {
      bundleUrl,
      bundleKey,
      previewKey,
      assemblyId: scope.docId,
      version: state.version,
      label: scope.label,
    })
  }

  const readAssemblyPreviewFailure = async (response) => {
    const text = await response.text().catch(() => '')
    let fallback = null
    let code = ''
    let message = text
    try {
      const payload = JSON.parse(text)
      const error = payload?.error || {}
      message = error.message || error.code || text
      code = error.code || ''
      fallback = error.fallback || null
    } catch {
      /* a non-JSON failure uses the response text */
    }
    return {
      message: message || `HTTP ${response.status}`,
      fallback,
      code,
    }
  }

  const applyAssemblyPreviewResponse = async (response, scope, seq) => {
    if (seq !== state.assemblyPreviewSeq) return
    if (state.docId !== scope.docId || state.kind !== 'assembly') return
    if (response.status === 200) {
      const previewKey = response.headers.get('X-Preview-Key') || ''
      const bundleKey = response.headers.get('X-Bundle-Key') || ''
      stopAssemblyPreviewClock()
      stopAssemblyPreviewPoll()
      state.assemblyPreviewStartedAt = null
      state.assemblyPreviewBuildId = null
      state.assemblyPreviewProgress = 1
      state.assemblyGeometryShown = true
      state.assemblyPreviewPhase = 'ready'
      state.assemblyPreviewLabel = scope.label
      postAssemblyPreviewBundle(scope, previewKey, bundleKey)
      renderAssemblyEmpty()
      renderAssemblyInspector()
      return
    }
    if (response.status === 202) {
      const payload = await response.json().catch(() => ({}))
      if (seq !== state.assemblyPreviewSeq) return
      state.assemblyPreviewBuildId = payload.buildId || null
      state.assemblyPreviewProgress = Number(payload.progress) || 0
      state.assemblyPreviewPhase = state.assemblyPreviewLastGood ? 'updating' : 'first'
      state.assemblyGeometryShown = true
      state.assemblyPreviewLabel = scope.label
      startAssemblyPreviewClock()
      renderAssemblyEmpty()
      renderAssemblyInspector()
      if (!state.assemblyPreviewBuildId) {
        failAssemblyPreviewRequest('预览构建没有返回任务标识', { scope })
        return
      }
      stopAssemblyPreviewPoll()
      state.assemblyPreviewPollTimer = setInterval(() => {
        pollAssemblyPreviewBuild(scope, seq)
      }, 1000)
      return
    }
    const failure = await readAssemblyPreviewFailure(response)
    if (seq !== state.assemblyPreviewSeq) return
    failAssemblyPreviewRequest(failure.message, {
      scope,
      fallback: failure.fallback,
      rollback: failure.code === 'PREVIEW_DISABLED',
    })
  }

  const pollAssemblyPreviewBuild = async (scope, seq) => {
    if (seq !== state.assemblyPreviewSeq) return
    if (state.docId !== scope.docId || state.kind !== 'assembly') return
    try {
      // Preview builds have their own registry; the generic /api/jobs endpoint
      // tracks plan jobs only. Polling the preview endpoint is the shared contract
      // and returns the bundle headers as soon as the cache entry is complete.
      const response = await fetch(
        `${base}/api/assemblies/${encodeURIComponent(scope.docId)}/preview?version=${state.version}`,
        { cache: 'no-store', signal: state.assemblyPreviewAbort?.signal },
      )
      if (seq !== state.assemblyPreviewSeq) return
      if (response.status === 202) {
        const payload = await response.json().catch(() => ({}))
        if (seq !== state.assemblyPreviewSeq) return
        state.assemblyPreviewBuildId = payload.buildId || state.assemblyPreviewBuildId
        state.assemblyPreviewProgress = Number(payload.progress) || state.assemblyPreviewProgress
        renderAssemblyEmpty()
      } else if (response.status === 200) {
        stopAssemblyPreviewPoll()
        await applyAssemblyPreviewResponse(response, scope, seq)
      } else {
        const failure = await readAssemblyPreviewFailure(response)
        if (seq !== state.assemblyPreviewSeq) return
        failAssemblyPreviewRequest(failure.message, {
          scope,
          fallback: failure.fallback,
          rollback: failure.code === 'PREVIEW_DISABLED',
        })
      }
    } catch (error) {
      if (error?.name !== 'AbortError') {
        /* transient polling failures leave the job running */
      }
    }
  }

  const loadAssemblyPreview = async (scope, seq) => {
    const controller = new AbortController()
    state.assemblyPreviewAbort = controller
    try {
      const response = await fetch(
        `${base}/api/assemblies/${encodeURIComponent(scope.docId)}/preview?version=${state.version}`,
        { cache: 'no-store', signal: controller.signal },
      )
      if (seq !== state.assemblyPreviewSeq) return
      await applyAssemblyPreviewResponse(response, scope, seq)
    } catch (error) {
      if (error?.name === 'AbortError') return
      if (seq !== state.assemblyPreviewSeq) return
      failAssemblyPreviewRequest(error?.message || '无法连接预览服务', { scope })
    }
  }

  const renderAssemblyEmpty = () => {
    if (state.kind !== 'assembly' || !state.assembly) return
    if (state.assemblyGeometryShown && !state.assemblyPreviewStartedAt) {
      empty.dataset.on = 'false'
      emptySpinner.hidden = true
      assemblyPreviewButton.hidden = true
      assemblyCancelButton.hidden = true
      emptyHint.hidden = true
      return
    }
    empty.dataset.on = 'true'
    emptyButton.hidden = true
    const instances = assemblyInstances()
    if (!instances.length) {
      emptySpinner.hidden = true
      emptyTitle.textContent = '空装配'
      emptyBody.textContent = '这个装配还没有实例；可通过装配编辑或计划添加实例。'
      assemblyPreviewButton.hidden = true
      assemblyCancelButton.hidden = true
      emptyHint.hidden = true
      return
    }
    const sceneReady = Boolean(state.assemblyScene)
    const scope = assemblyPreviewScope()
    const busy = Boolean(state.assemblyPreviewStartedAt)
    emptySpinner.hidden = !busy && sceneReady
    if (busy) {
      const elapsed = (performance.now() - state.assemblyPreviewStartedAt) / 1000
      const progress = Math.round((Number(state.assemblyPreviewProgress) || 0) * 100)
      const first = !state.assemblyPreviewLastGood
      emptyTitle.textContent = first ? '正在首次构建装配预览' : '正在更新装配预览'
      emptyBody.textContent = `${scope.label}。后台正在${first ? '首次构建' : '更新'}装配预览${progress > 0 ? ` · ${progress}%` : ''}`
      emptyHint.hidden = false
      emptyHint.textContent = first
        ? `已等待 ${elapsed.toFixed(1)}s；大装配可能需要数分钟。取消会停止后台构建。`
        : `已等待 ${elapsed.toFixed(1)}s；构建期间继续显示上次完整预览，失败时会保留它。取消会停止后台构建。`
      assemblyPreviewButton.hidden = true
      assemblyCancelButton.hidden = false
      return
    }
    if (state.assemblyPreviewPhase === 'canceled') {
      emptySpinner.hidden = true
      emptyTitle.textContent = '已取消装配预览'
      emptyBody.textContent = state.assemblyPreviewMessage || '后台预览构建已取消。'
      emptyHint.hidden = false
      emptyHint.textContent = '没有完成新的预览；可重新预览，或从结构树选择子系统查看局部 STEP。'
      assemblyPreviewButton.hidden = false
      assemblyPreviewButton.textContent = scope.subsystem
        ? `预览 ${scope.label}`
        : `重新预览整机（${fmt(scope.count)} 个零件）`
      assemblyCancelButton.hidden = true
      return
    }
    if (state.assemblyPreviewPhase === 'failed') {
      emptySpinner.hidden = true
      emptyTitle.textContent = '装配预览失败'
      emptyBody.textContent = state.assemblyPreviewMessage || '后台预览没有完成。'
      emptyHint.hidden = false
      emptyHint.textContent = scope.subsystem
        ? '可重试子系统预览，或继续使用结构树。'
        : '整机 STEP 不会作为自动回退；请从结构树选择子系统后预览局部 STEP，或重试整机预览。'
      assemblyPreviewButton.hidden = false
      assemblyPreviewButton.textContent = scope.subsystem
        ? `重试 ${scope.label}`
        : `重试整机（${fmt(scope.count)} 个零件）`
      assemblyCancelButton.hidden = true
      return
    }
    emptyTitle.textContent = '装配已载入'
    emptyBody.textContent = `${assemblyName()} · ${fmt(instances.length)} 个实例 · ${fmt(Object.keys(state.assemblyScene?.definitions || {}).length)} 个定义`
    emptyHint.hidden = false
    emptyHint.textContent = sceneReady
      ? '从结构树选择一个子系统查看几何；整机预览会一次性展开全部实例，较慢。'
      : state.assemblyBusy
        ? '装配树已可用，正在读取场景定义。'
        : '装配场景不可用；仍可选择子系统或重试整机预览。'
    assemblyPreviewButton.hidden = false
    assemblyPreviewButton.textContent = scope.subsystem
      ? `预览 ${scope.label}`
      : `预览整机（${fmt(scope.count)} 个零件）`
    assemblyCancelButton.hidden = true
  }

  const clearAssemblyPreview = () => {
    if (state.kind !== 'assembly') return
    const active = Boolean(state.assemblyPreviewStartedAt) || Boolean(state.assemblyPreviewBuildId)
    const scope = assemblyPreviewScope()
    const lastGood = state.assemblyPreviewLastGood
    const canRestore = Boolean(
      active
      && lastGood
      && lastGood.docId === scope.docId
      && Boolean(lastGood.subsystem) === Boolean(scope.subsystem),
    )
    cancelAssemblyPreviewBuild()
    stopAssemblyPreviewClock()
    state.assemblyPreviewStartedAt = null
    state.assemblyGeometryShown = false
    state.pendingAssemblyPreview = false
    state.assemblyPreviewMessage = ''
    state.assemblyPreviewProgress = 0
    if (canRestore) {
      restoreAssemblyPreviewLastGood('', null)
      toast('已取消新的预览构建，保留上次完整预览', 'info', 4)
      return
    }
    if (!active) state.assemblyPreviewLastGood = null
    state.assemblyPreviewPendingGood = null
    state.assemblyPreviewPhase = active ? 'canceled' : 'idle'
    state.assemblyPreviewMessage = active ? '后台预览构建已取消。' : ''
    state.assemblyPreviewLabel = ''
    post('clear', {})
    renderAssemblyEmpty()
    renderAssemblyInspector()
    toast(active ? '已取消后台预览构建' : '已清除装配预览', 'info', 2)
  }

  const showAssemblyGeometry = (reset = true) => {
    if (state.kind !== 'assembly' || !state.docId) return
    if (!state.ready) {
      state.pendingAssemblyPreview = true
      toast('视口尚未就绪，装配几何稍后显示', 'info', 3)
      return
    }
    const scope = assemblyPreviewScope()
    state.pendingAssemblyPreview = false
    state.assemblyPreviewLabel = scope.label
    if (scope.subsystem) {
      // A subsystem is small enough to keep using the STEP export path; the full
      // root never takes this path because flattening every instance is the slow
      // case the background preview exists to avoid.
      cancelAssemblyPreviewBuild()
      state.assemblyGeometryShown = true
      state.assemblyPreviewPhase = 'step'
      state.assemblyPreviewMessage = ''
      if (!state.assemblyPreviewStartedAt) startAssemblyPreviewClock()
      if (reset) post('clear', {})
      post('preview', { url: `${base}/api/assemblies/${scope.docId}/export`, label: scope.label })
      renderAssemblyEmpty()
      if (state.selectedInstance) scheduleAssemblyHighlight()
      renderAssemblyInspector()
      return
    }
    cancelAssemblyPreviewBuild()
    const seq = state.assemblyPreviewSeq + 1
    state.assemblyPreviewSeq = seq
    state.assemblyPreviewStartedAt = null
    state.assemblyPreviewProgress = 0
    state.assemblyPreviewPhase = state.assemblyPreviewLastGood ? 'updating' : 'first'
    state.assemblyPreviewMessage = ''
    state.assemblyGeometryShown = false
    if (reset) post('clear', {})
    renderAssemblyEmpty()
    renderAssemblyInspector()
    loadAssemblyPreview(scope, seq)
  }

  const selectInstance = (instance) => {
    if (!state.docId || !instance) return
    const path = instance.path || instance.instance_id
    if (!path) return
    pickSeq += 1
    dimensionSeq += 1
    handleSeq += 1
    state.selectedInstance = path
    const segments = String(path || '').split('/').filter(Boolean)
    let prefix = ''
    for (let index = 0; index < segments.length - 1; index += 1) {
      prefix = prefix ? `${prefix}/${segments[index]}` : segments[index]
      state.assemblyExpanded.add(prefix)
    }
    state.treeFocus = path
    state.selectedBody = null
    state.selectedNode = null
    state.sameDefinition = false
    state.selection = instanceSelection(instance)
    state.reference = null
    state.handle = null
    state.dimensions = null
    state.dimensionFeature = null
    setHandleHint(null)
    post('handle', null)
    renderDimensions()
    setInspector(true)
    renderSelection()
    renderAssemblyTree()
    renderAssemblyInspector()
    renderAssemblyEmpty()
    highlightSelection()
    if (state.assemblyGeometryShown) scheduleAssemblyHighlight()
    if ((instance.path || instance.instance_id) === instance.instance_id) {
      loadAssemblyParameters(instance)
    } else {
      assemblyParameterSeq += 1
      state.assemblyParameters = null
      state.assemblyParametersFor = null
      state.assemblyParameterBusy = false
      renderAssemblyEdit()
    }
  }

  const buildAssemblyTree = () => {
    const nodes = new Map()
    const roots = []
    for (const instance of assemblyInstances()) {
      const path = String(instance.path || instance.instance_id || '')
      if (!path) continue
      const segments = path.split('/').filter(Boolean)
      let parent = null
      let prefix = ''
      for (let index = 0; index < segments.length; index += 1) {
        prefix = prefix ? `${prefix}/${segments[index]}` : segments[index]
        let node = nodes.get(prefix)
        if (!node) {
          node = { path: prefix, depth: index, instance: null, children: [], parent }
          nodes.set(prefix, node)
          if (parent) parent.children.push(node)
          else roots.push(node)
        }
        parent = node
      }
      if (parent) parent.instance = instance
    }
    return roots
  }

  const instanceTitle = (instance) => {
    if (instance.name) return instance.name
    const path = String(instance.path || instance.instance_id || '')
    return path.split('/').filter(Boolean).pop() || path
  }

  const instanceMeta = (instance) => {
    const parts = []
    const path = instance.path || instance.instance_id || ''
    if (path && path !== instanceTitle(instance)) parts.push(path)
    if (instance.definition_id) parts.push(`${instance.definition_id} v${instance.version ?? '?'}`)
    if (instance.definition_kind === 'part' && instance.configuration) {
      parts.push(instance.configuration)
    }
    const definition = assemblyDefinition(instance)
    if (definition?.metrics?.faces != null) parts.push(`${fmt(definition.metrics.faces)} 面`)
    else if (instance.metrics?.faces != null) parts.push(`${fmt(instance.metrics.faces)} 面`)
    return parts.join(' · ')
  }

  const instanceFlags = (instance) => {
    const flags = []
    if (instance.definition_kind === 'assembly') flags.push({ label: '子系统', tone: '' })
    if (instance.suppressed) flags.push({ label: '停用', tone: 'warn' })
    if (instance.visible === false) flags.push({ label: '隐藏', tone: '' })
    const outdated = (state.assemblyReferences?.outdated || [])
      .some((row) => row.instance_id === instance.instance_id
        && (instance.path || instance.instance_id) === instance.instance_id)
    if (outdated) flags.push({ label: '过期', tone: 'warn' })
    if (instance.error) {
      flags.push({ label: '错误', tone: 'bad', title: instance.error.message || instance.error.code || '' })
    }
    return flags
  }

  const assemblyModuleCount = () => buildAssemblyTree().length

  const nodeMatches = (node, needle) => {
    if (!needle) return true
    const instance = node.instance
    const haystack = [
      node.path,
      instance?.name || '',
      instance?.definition_id || '',
      instance?.configuration || '',
      instance?.definition_kind || '',
    ].join(' ').toLocaleLowerCase()
    if (haystack.includes(needle)) return true
    return node.children.some((child) => nodeMatches(child, needle))
  }

  const nodeTitle = (node) => node.instance ? instanceTitle(node.instance)
    : node.path.split('/').filter(Boolean).pop() || node.path

  const nodeChildCount = (node) => node.children.length

  const visibleAssemblyRoots = () => {
    const needle = state.structureQuery.toLocaleLowerCase()
    if (!needle) return buildAssemblyTree()
    return buildAssemblyTree().filter((root) => nodeMatches(root, needle))
  }

  const openForSearch = (node, needle, open) => {
    if (!needle) return false
    let match = nodeMatches(node, needle)
    for (const child of node.children) {
      if (openForSearch(child, needle, open)) match = true
    }
    if (match && node.children.length) open.add(node.path)
    return match
  }

  const breadcrumbParts = () => {
    const path = state.selectedInstance
    if (!path) return []
    const tree = buildAssemblyTree()
    const parts = []
    let current = null
    for (const root of tree) {
      const found = walkPath(root, path)
      if (found) { current = found; break }
    }
    if (!current) return path.split('/').filter(Boolean)
    let node = current
    while (node) {
      parts.unshift(node)
      node = node.parent || null
    }
    return parts
  }
  function walkPath(node, path) {
    if (node.path === path) return node
    for (const child of node.children) {
      const found = walkPath(child, path)
      if (found) return found
    }
    return null
  }

  const openAssemblyInstance = (instance) => {
    if (!instance || instance.definition_kind !== 'assembly') return
    const childId = instance.definition_id
    if (!childId) return
    const current = state.documents.find((item) => item.id === state.docId)
    state.assemblyTrail.push({ id: state.docId, name: current?.name || state.docId })
    loadDocument(childId, true, true)
      .then(() => {
        if (state.kind === 'assembly' && state.docId === childId) showAssemblyGeometry()
      })
      .catch((error) => toast(`打开子系统失败：${error.message}`, 'error', 6))
  }

  const returnToParentAssembly = () => {
    const previous = state.assemblyTrail.pop()
    if (!previous) return
    loadDocument(previous.id, true, true).catch((error) => toast(`返回失败：${error.message}`, 'error', 6))
  }

  const focusTreeRow = (path) => {
    if (!path) return
    const row = [...structureList.querySelectorAll('.bxw-structure-row')]
      .find((item) => item.dataset.instance === path)
    if (!row) return
    for (const item of structureList.querySelectorAll('.bxw-structure-row')) {
      item.tabIndex = item === row ? 0 : -1
    }
    state.treeFocus = path
    row.focus()
  }

  const renderAssemblyBreadcrumb = () => {
    assemblyBreadcrumb.replaceChildren()
    if (state.kind !== 'assembly') { assemblyBreadcrumb.hidden = true; return }
    const selected = state.selectedInstance
    if (!selected && !state.assemblyTrail.length) { assemblyBreadcrumb.hidden = true; return }
    assemblyBreadcrumb.hidden = false
    if (state.assemblyTrail.length) {
      const parent = state.assemblyTrail[state.assemblyTrail.length - 1]
      const back = el('button', { type: 'button' }, `← ${parent.name}`)
      back.addEventListener('click', returnToParentAssembly)
      assemblyBreadcrumb.append(back, el('i', {}, '/'))
    }
    const parts = breadcrumbParts()
    if (!parts.length) {
      assemblyBreadcrumb.append(el('span', {}, assemblyName()))
      return
    }
    if (Array.isArray(parts) && typeof parts[0] === 'string') {
      assemblyBreadcrumb.append(el('span', {}, parts.join(' / ')))
      return
    }
    for (let index = 0; index < parts.length; index += 1) {
      const node = parts[index]
      if (index) assemblyBreadcrumb.append(el('i', {}, '/'))
      const button = el('button', { type: 'button' }, nodeTitle(node))
      button.addEventListener('click', () => {
        if (node.instance) selectInstance(node.instance)
      })
      assemblyBreadcrumb.append(button)
    }
  }

  const renderAssemblyTree = () => {
    if (state.kind !== 'assembly') return
    structureList.setAttribute('role', 'tree')
    structureList.setAttribute('aria-label', '装配结构')
    const instances = assemblyInstances()
    const selection = state.selection?.scope === 'instance' ? state.selection : null
    const needle = state.structureQuery.toLocaleLowerCase()
    const roots = visibleAssemblyRoots()
    const open = new Set(state.assemblyExpanded)
    if (needle) for (const root of buildAssemblyTree()) openForSearch(root, needle, open)
    const visible = []
    const collect = (node) => {
      visible.push(node)
      if (!open.has(node.path)) return
      for (const child of node.children) collect(child)
    }
    for (const root of roots) collect(root)
    const active = state.treeFocus && visible.some((node) => node.path === state.treeFocus)
      ? state.treeFocus
      : (state.selectedInstance || visible[0]?.path || '')
    const signature = JSON.stringify([
      state.version,
      state.selectedInstance,
      state.sameDefinition,
      state.structureQuery,
      [...open].sort(),
      selection?.definition_key || null,
      Boolean(state.assemblyScene),
      (state.assemblyReferences?.outdated || []).map((row) => row.instance_id),
      instances.map((instance) => [
        instance.path || instance.instance_id,
        instance.name || '',
        instance.definition_id || '',
        instance.definition_kind || '',
        instance.version ?? null,
        instance.configuration || '',
        Boolean(instance.suppressed),
        instance.visible !== false,
        instance.error ? `${instance.error.code || ''}:${instance.error.message || ''}` : '',
        assemblyDefinitionKey(instance),
      ]),
    ])
    if (signature === assemblySignature) return
    assemblySignature = signature
    const focusKey = focusKeyOf(structureList)
    structureProgress.hidden = true
    structureProgress.replaceChildren()
    structureMeta.textContent = state.version != null
      ? `v${state.version} · ${roots.length} 模块`
      : '—'
    const allRootsOpen = roots.every((root) => !root.children.length || state.assemblyExpanded.has(root.path))
    treeExpand.hidden = !roots.some((root) => root.children.length)
    treeExpand.textContent = allRootsOpen ? '折叠' : '展开'
    const total = assemblyInstances().length
    const fragment = document.createDocumentFragment()
    if (!instances.length) {
      fragment.append(el('div', { className: 'bxw-structure-empty' }, '这个装配还没有实例'))
      structureList.replaceChildren(fragment)
      restoreFocusKey(focusKey, structureList)
      renderAssemblyBreadcrumb()
      return
    }
    if (!visible.length) {
      fragment.append(el('div', { className: 'bxw-structure-empty' }, `没有匹配“${state.structureQuery}”的实例`))
      structureList.replaceChildren(fragment)
      restoreFocusKey(focusKey, structureList)
      renderAssemblyBreadcrumb()
      return
    }
    if (!needle) {
      fragment.append(el('div', { className: 'bxw-tree-summary' },
        `${fmt(roots.length)} 个模块 · ${fmt(total)} 个实例`))
    } else {
      fragment.append(el('div', { className: 'bxw-tree-summary' },
        `${fmt(visible.filter((node) => node.instance?.definition_kind === 'part').length)} 个匹配实例`))
    }
    const groupKey = selection?.definition_key || null
    for (const node of visible) {
      const instance = node.instance
      const children = node.children.length
      const expanded = open.has(node.path)
      const row = el('div', {
        className: 'bxw-structure-row',
        tabindex: node.path === active ? '0' : '-1',
        role: 'treeitem',
        'aria-level': String(node.depth + 1),
        'aria-selected': state.selectedInstance === node.path ? 'true' : 'false',
      })
      row.style.setProperty('--bxw-depth', String(node.depth))
      row.dataset.focusKey = `assembly:${node.path}`
      row.dataset.instance = node.path
      row.dataset.node = node.path
      if (state.selectedInstance === node.path) row.dataset.selected = 'true'
      else if (state.sameDefinition && groupKey && instance
        && assemblyDefinitionKey(instance) === groupKey) row.dataset.related = 'true'
      if (instance?.visible === false) row.dataset.hidden = 'true'
      if (children) row.setAttribute('aria-expanded', expanded ? 'true' : 'false')
      if (children) {
        const toggle = el('button', {
          type: 'button', className: 'bxw-tree-toggle',
          'aria-label': expanded ? `折叠 ${nodeTitle(node)}` : `展开 ${nodeTitle(node)}`,
          'aria-expanded': expanded ? 'true' : 'false',
          htmlUnsafe: ICONS.chevronRight,
        })
        toggle.addEventListener('click', (event) => {
          event.stopPropagation()
          if (state.assemblyExpanded.has(node.path)) state.assemblyExpanded.delete(node.path)
          else state.assemblyExpanded.add(node.path)
          renderAssemblyTree()
        })
        row.append(toggle)
      } else {
        row.append(el('span', { className: 'bxw-tree-leaf' }))
      }
      const dot = el('span', { className: 'bxw-dot' })
      dot.dataset.state = instance
        ? (instance.error ? 'failed'
          : instance.suppressed ? 'running'
            : instance.definition_kind === 'assembly' ? 'pending' : 'done')
        : 'pending'
      const main = el('div', { className: 'bxw-structure-main' })
      main.append(el('b', {}, nodeTitle(node)))
      const meta = instance ? instanceMeta(instance) : ''
      main.append(el('span', {}, children
        ? `${children} 个实例${meta ? ` · ${meta}` : ''}`
        : meta))
      if (instance) {
        const flags = instanceFlags(instance)
        if (flags.length) {
          const flagRow = el('div', { className: 'bxw-instance-flags' })
          for (const flag of flags) {
            const chip = el('i', { className: 'bxw-instance-flag', 'data-tone': flag.tone || null }, flag.label)
            if (flag.title) chip.title = flag.title
            flagRow.append(chip)
          }
          main.append(flagRow)
        }
      }
      row.append(dot, main)
      row.title = instance
        ? [
          node.path,
          instanceTitle(instance),
          instanceMeta(instance),
          instance.error ? `${instance.error.code || ''} ${instance.error.message || ''}` : '',
          Array.isArray(instance.placement?.translation)
            ? `位移 ${instance.placement.translation.map((value) => fmt(value, 1)).join(', ')}`
            : '',
        ].filter(Boolean).join('\n')
        : node.path
      row.addEventListener('click', () => {
        state.treeFocus = node.path
        if (instance) selectInstance(instance)
      })
      row.addEventListener('dblclick', () => { if (instance) openAssemblyInstance(instance) })
      row.addEventListener('keydown', (event) => {
        const rows = [...structureList.querySelectorAll('.bxw-structure-row')]
        const index = rows.indexOf(row)
        if (event.key === 'Tab') return
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault()
          if (instance) selectInstance(instance)
          return
        }
        if (event.key === 'ArrowRight') {
          event.preventDefault()
          if (children && !expanded) {
            state.assemblyExpanded.add(node.path)
            renderAssemblyTree()
          } else if (rows[index + 1]) focusTreeRow(rows[index + 1].dataset.instance)
          return
        }
        if (event.key === 'ArrowLeft') {
          event.preventDefault()
          if (children && expanded) {
            state.assemblyExpanded.delete(node.path)
            renderAssemblyTree()
          } else {
            const parentPath = node.path.includes('/')
              ? node.path.slice(0, node.path.lastIndexOf('/')) : ''
            focusTreeRow(parentPath)
          }
          return
        }
        if (event.key === 'ArrowDown' || event.key === 'ArrowUp'
          || event.key === 'Home' || event.key === 'End') {
          event.preventDefault()
          let target = null
          if (event.key === 'Home') target = rows[0]
          else if (event.key === 'End') target = rows[rows.length - 1]
          else if (event.key === 'ArrowDown') target = rows[index + 1]
          else target = rows[index - 1]
          if (target) focusTreeRow(target.dataset.instance)
        }
      })
      fragment.append(row)
    }
    structureList.replaceChildren(fragment)
    restoreFocusKey(focusKey, structureList)
    renderAssemblyBreadcrumb()
  }

  const assemblyParameterCache = new Map()
  let assemblyParameterSeq = 0
  let assemblyEditSignature = ''

  const rootAssemblyInstance = (selection) => {
    if (!selection?.instance_id) return null
    return (state.assembly?.assembly?.instances || []).find((item) => item.id === selection.instance_id) || null
  }

  const referencesFromState = (payload) => {
    const rows = payload?.references || []
    return { references: rows, outdated: rows.filter((row) => row.outdated) }
  }

  const refreshAssemblyScene = async () => {
    if (!state.docId || state.kind !== 'assembly') return
    const docId = state.docId
    try {
      const scene = await api(`${base}/api/assemblies/${docId}/scene`)
      if (state.docId !== docId || state.kind !== 'assembly') return
      state.assemblyScene = scene
      assemblyCenterCache.clear()
      assemblySignature = ''
      assemblyInspectorSignature = ''
    } catch (error) {
      toast(`刷新装配场景失败：${error.message}`, 'error', 6)
    }
  }

  const syncSelectedAssemblyInstance = () => {
    if (!state.selectedInstance) {
      renderSelection()
      return
    }
    const instance = assemblyInstances()
      .find((item) => (item.path || item.instance_id) === state.selectedInstance)
    if (instance) state.selection = instanceSelection(instance)
    else {
      state.selectedInstance = null
      state.selection = null
    }
    renderSelection()
  }

  const loadAssemblyParameters = async (instance) => {
    if (!instance || String(instance.path || instance.instance_id || '').includes('/')) {
      assemblyParameterSeq += 1
      state.assemblyParameters = null
      state.assemblyParametersFor = null
      state.assemblyParameterBusy = false
      renderAssemblyEdit()
      return
    }
    const record = rootAssemblyInstance(instanceSelection(instance))
    if (!record || record.ref?.kind !== 'part') {
      state.assemblyParameters = null
      state.assemblyParametersFor = null
      state.assemblyParameterBusy = false
      renderAssemblyEdit()
      return
    }
    const definitionId = record.ref.document_id
    const cached = assemblyParameterCache.get(definitionId)
    if (cached) {
      state.assemblyParameters = cached
      state.assemblyParametersFor = definitionId
      state.assemblyParameterBusy = false
      renderAssemblyEdit()
      renderAssemblyInspector()
      return
    }
    const seq = ++assemblyParameterSeq
    const target = instance.path || instance.instance_id
    state.assemblyParametersFor = definitionId
    state.assemblyParameters = null
    state.assemblyParameterBusy = true
    renderAssemblyEdit()
    try {
      const meta = await api(`${base}/api/docs/${definitionId}/meta`)
      if (seq !== assemblyParameterSeq || state.kind !== 'assembly'
          || state.selectedInstance !== target) return
      const payload = {
        definition_id: definitionId,
        meta_version: meta.version ?? null,
        parameters: Array.isArray(meta.parameters) ? meta.parameters : [],
      }
      assemblyParameterCache.set(definitionId, payload)
      state.assemblyParameters = payload
    } catch (error) {
      if (seq !== assemblyParameterSeq) return
      toast(`读取暴露参数失败：${error.message}`, 'error', 5)
    } finally {
      if (seq === assemblyParameterSeq) {
        state.assemblyParameterBusy = false
        renderAssemblyEdit()
        renderAssemblyInspector()
      }
    }
  }

  const editRow = (label, input, unit) => {
    const row = el('div', { className: 'bxw-dimension' })
    if (!input.id) {
      input.id = `bxw-edit-${String(input.dataset.focusKey || label)
        .replace(/[^A-Za-z0-9_-]/g, '-')}`
    }
    row.append(el('label', { htmlFor: input.id }, label), input)
    if (unit) row.append(el('span', { className: 'bxw-dimension-unit' }, unit))
    return row
  }

  const overrideInput = (spec, current, busy, path) => {
    const disabled = busy || null
    let input
    if (spec.kind === 'int' || spec.kind === 'float') {
      input = el('input', {
        type: 'number',
        step: spec.kind === 'int' ? '1' : 'any',
        value: current == null ? '' : String(current),
        disabled,
      })
      if (spec.minimum != null) input.min = String(spec.minimum)
      if (spec.maximum != null) input.max = String(spec.maximum)
    } else if (spec.kind === 'bool') {
      input = el('select', { disabled })
      input.append(el('option', { value: 'true' }, '真'), el('option', { value: 'false' }, '假'))
      input.value = current === false ? 'false' : 'true'
    } else if (spec.kind === 'vector') {
      input = el('input', {
        type: 'text',
        value: current == null ? '' : JSON.stringify(current),
        disabled,
      })
    } else {
      input = el('input', {
        type: 'text',
        value: current == null ? '' : String(current),
        disabled,
      })
    }
    input.dataset.focusKey = `assembly-edit:${path}:${spec.name}`
    return input
  }

  const parseOverrideValue = (spec, input) => {
    if (spec.kind === 'int') {
      const value = Number(input.value)
      if (!Number.isInteger(value)) throw new Error('需要整数')
      return value
    }
    if (spec.kind === 'float') {
      const value = Number(input.value)
      if (!Number.isFinite(value)) throw new Error('需要数值')
      return value
    }
    if (spec.kind === 'bool') return input.value === 'true'
    if (spec.kind === 'vector') {
      const value = JSON.parse(input.value)
      if (!Array.isArray(value)) throw new Error('需要数组')
      return value
    }
    return input.value
  }

  const renderAssemblyEdit = () => {
    if (state.kind !== 'assembly') {
      assemblyEditSection.hidden = true
      assemblyEditSignature = ''
      return
    }
    const selection = state.selection?.scope === 'instance' ? state.selection : null
    const record = selection && !String(selection.path || '').includes('/')
      ? rootAssemblyInstance(selection) : null
    const parameters = record && state.assemblyParametersFor === record.ref?.document_id
      ? state.assemblyParameters
      : null
    const signature = JSON.stringify([
      selection?.path || null,
      record ? [
        record.id, record.ref?.kind, record.ref?.version, record.ref?.configuration,
        Boolean(record.suppressed), record.placement?.translation,
        JSON.stringify(record.overrides || {}),
      ] : null,
      state.assemblyEditBusy,
      state.assemblyParameterBusy,
      state.assemblyParametersFor,
      parameters ? [parameters.meta_version, parameters.parameters] : null,
    ])
    if (signature === assemblyEditSignature) return
    assemblyEditSignature = signature
    const focusKey = focusKeyOf(assemblyEditBody)
    assemblyEditBody.replaceChildren()
    if (!selection) {
      assemblyEditSection.hidden = true
      return
    }
    assemblyEditSection.hidden = false
    assemblyEditBody.append(el('div', { className: 'bxw-instance-note' },
      `${selection.path} · ${selection.definition_id} v${selection.version}`))
    if (!record) {
      assemblyEditBody.append(el('div', { className: 'bxw-instance-note' },
        '该实例位于子装配中；编辑需在子装配文档中进行。'))
      restoreFocusKey(focusKey, assemblyEditBody)
      return
    }
    const busy = state.assemblyEditBusy
    const placement = record.placement || {}
    const translation = Array.isArray(placement.translation)
      ? placement.translation : [0, 0, 0]
    const axisInputs = []
    const transformRows = [['X', 0], ['Y', 1], ['Z', 2]].map(([label, axis]) => {
      const input = el('input', {
        type: 'number', step: 'any', value: String(translation[axis] ?? 0), disabled: busy || null,
      })
      input.dataset.focusKey = `assembly-edit:${selection.path}:position-${label}`
      axisInputs.push(input)
      return editRow(label, input, 'mm')
    })
    const applyTransform = el('button', { type: 'button', disabled: busy || null }, '应用位置')
    applyTransform.addEventListener('click', () => {
      const values = axisInputs.map((input) => Number(input.value))
      if (values.some((value) => !Number.isFinite(value))) {
        toast('位置需要有效数值', 'error', 4)
        return
      }
      const rotation = Array.isArray(placement.rotation) ? placement.rotation : undefined
      applyAssemblyEdit([{
        op: 'transform', id: record.id, placement: { rotation, translation: values },
      }], '已更新实例位置')
    })
    const suppressButton = el('button', { type: 'button', disabled: busy || null },
      record.suppressed ? '恢复实例' : '停用实例')
    suppressButton.addEventListener('click', () => {
      applyAssemblyEdit([{ op: 'suppress', id: record.id, suppressed: !record.suppressed }],
        record.suppressed ? '已恢复实例' : '已停用实例')
    })
    const transformActions = el('div', { className: 'bxw-node-actions' })
    transformActions.append(applyTransform, suppressButton)

    const pinned = record.ref || {}
    const pinVersion = el('input', {
      type: 'number', step: '1', min: '1',
      value: String(pinned.version ?? 1), disabled: busy || null,
    })
    pinVersion.dataset.focusKey = `assembly-edit:${selection.path}:pin-version`
    const pinRows = [editRow('pin 版本', pinVersion, '')]
    let pinConfig = null
    if (pinned.kind === 'part') {
      pinConfig = el('input', {
        type: 'text',
        value: pinned.configuration || 'default',
        disabled: busy || null,
      })
      pinConfig.dataset.focusKey = `assembly-edit:${selection.path}:pin-configuration`
      pinRows.push(editRow('配置', pinConfig, ''))
    }
    const applyPin = el('button', { type: 'button', disabled: busy || null }, '更新 pin')
    applyPin.addEventListener('click', () => {
      const version = Number(pinVersion.value)
      if (!Number.isInteger(version) || version < 1) {
        toast('pin 版本需要正整数', 'error', 4)
        return
      }
      const op = { op: 'update_pin', id: record.id, version }
      if (pinConfig && pinConfig.value.trim()) op.configuration = pinConfig.value.trim()
      applyAssemblyEdit([op], '已更新实例 pin')
    })
    const pinActions = el('div', { className: 'bxw-node-actions' })
    pinActions.append(applyPin)

    const parameterBlock = el('div', { className: 'bxw-focus' })
    if (pinned.kind === 'part') {
      if (state.assemblyParameterBusy) {
        parameterBlock.append(el('div', { className: 'bxw-node-meta' }, '正在读取暴露参数…'))
      } else if (!parameters) {
        parameterBlock.append(el('div', { className: 'bxw-node-meta' }, '暴露参数读取中或不可用'))
      } else {
        const specs = Array.isArray(parameters.parameters) ? parameters.parameters : []
        const overrides = record.overrides || {}
        const known = new Set(specs.map((spec) => spec.name))
        const extraKeys = Object.keys(overrides).filter((key) => !known.has(key))
        if (!specs.length && !extraKeys.length) {
          parameterBlock.append(el('div', { className: 'bxw-node-meta' }, '该零件没有暴露参数'))
        } else {
          const entries = []
          for (const spec of specs) {
            const current = Object.prototype.hasOwnProperty.call(overrides, spec.name)
              ? overrides[spec.name] : spec.default
            const input = overrideInput(spec, current, busy, selection.path)
            entries.push({ spec, input })
            const label = `${spec.name}${spec.unit ? ` (${spec.unit})` : ''}`
            parameterBlock.append(editRow(label, input, ''))
          }
          for (const key of extraKeys) {
            const input = el('input', {
              type: 'text',
              value: overrides[key] == null ? '' : JSON.stringify(overrides[key]),
              disabled: busy || null,
            })
            input.dataset.focusKey = `assembly-edit:${selection.path}:override-${key}`
            entries.push({ spec: { name: key, kind: 'any' }, input })
            parameterBlock.append(editRow(key, input, ''))
          }
          const applyOverrides = el('button', {
            type: 'button', disabled: busy || null,
          }, '应用覆盖')
          applyOverrides.addEventListener('click', () => {
            const changed = {}
            for (const { spec, input } of entries) {
              let value
              try {
                value = spec.kind === 'any'
                  ? (() => {
                    const text = input.value.trim()
                    if (!text) return ''
                    try { return JSON.parse(text) } catch (error) { return text }
                  })()
                  : parseOverrideValue(spec, input)
              } catch (error) {
                toast(`${spec.name}：${error.message}`, 'error', 4)
                return
              }
              const current = Object.prototype.hasOwnProperty.call(overrides, spec.name)
                ? overrides[spec.name] : spec.default
              if (JSON.stringify(value) !== JSON.stringify(current)) changed[spec.name] = value
            }
            if (!Object.keys(changed).length) {
              toast('覆盖没有变化', 'info', 2)
              return
            }
            applyAssemblyEdit([{ op: 'override', id: record.id, overrides: changed }],
              '已更新实例覆盖')
          })
          const overrideActions = el('div', { className: 'bxw-node-actions' })
          overrideActions.append(applyOverrides)
          parameterBlock.append(overrideActions)
        }
        if (parameters.meta_version != null && pinned.version != null
            && Number(parameters.meta_version) !== Number(pinned.version)) {
          parameterBlock.append(el('div', { className: 'bxw-node-meta' },
            `参数 schema 来自 v${parameters.meta_version}，当前 pin v${pinned.version}`))
        }
      }
    }

    assemblyEditBody.append(
      el('div', { className: 'bxw-node-meta' }, '位置（旋转保持不变）'),
      ...transformRows,
      transformActions,
      el('div', { className: 'bxw-node-meta' }, 'pin'),
      ...pinRows,
      pinActions,
    )
    if (pinned.kind === 'part') {
      assemblyEditBody.append(el('div', { className: 'bxw-node-meta' }, '暴露参数覆盖'), parameterBlock)
    }
    restoreFocusKey(focusKey, assemblyEditBody)
  }

  const applyAssemblyEdit = async (ops, title) => {
    if (state.kind !== 'assembly' || !state.assembly || state.assemblyEditBusy) return false
    const baseVersion = Number(state.assembly.assembly.version) || state.version
    state.assemblyEditBusy = true
    renderAssemblyEdit()
    renderAssemblyInspector()
    try {
      const result = await api(`${base}/api/assemblies/${state.docId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ base_version: baseVersion, ops }),
      })
      if (!result?.assembly) throw new Error('装配编辑响应缺少 assembly')
      state.assembly = result
      state.version = Number(result.assembly.version) || state.version
      state.assemblyReferences = referencesFromState(result)
      assemblyParameterCache.clear()
      await refreshAssemblyScene()
      syncSelectedAssemblyInstance()
      renderAssemblyState()
      if (state.assemblyGeometryShown) showAssemblyGeometry(false)
      if (state.selectedInstance) {
        const selected = assemblyInstances()
          .find((item) => (item.path || item.instance_id) === state.selectedInstance)
        if (selected) loadAssemblyParameters(selected)
      }
      toast(title, 'info', 2)
      return true
    } catch (error) {
      toast(`装配编辑失败：${error.message}${error.hint ? ` · ${error.hint}` : ''}`, 'error', 6)
      return false
    } finally {
      state.assemblyEditBusy = false
      renderAssemblyEdit()
      renderAssemblyInspector()
    }
  }

  const updateAssemblyReferences = async () => {
    if (state.kind !== 'assembly' || !state.assembly || state.assemblyEditBusy) return
    const outdated = state.assemblyReferences?.outdated?.length ?? 0
    if (!outdated) {
      toast('没有需要更新的引用', 'info', 2)
      return
    }
    const ok = await confirmAction({
      title: '更新装配引用',
      body: `将 ${outdated} 个过期实例的 pin 更新到最新版本；这会生成新装配版本。`,
      confirmLabel: '更新',
    })
    if (!ok) return
    const baseVersion = Number(state.assembly.assembly.version) || state.version
    state.assemblyEditBusy = true
    renderAssemblyState()
    renderAssemblyEdit()
    try {
      const result = await api(`${base}/api/assemblies/${state.docId}/update-references`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ base_version: baseVersion }),
      })
      if (!result?.assembly) throw new Error('更新引用响应缺少 assembly')
      state.assembly = result
      state.version = Number(result.assembly.version) || state.version
      state.assemblyReferences = referencesFromState(result)
      assemblyParameterCache.clear()
      await refreshAssemblyScene()
      syncSelectedAssemblyInstance()
      renderAssemblyState()
      if (state.assemblyGeometryShown) showAssemblyGeometry(false)
      if (state.selectedInstance) {
        const selected = assemblyInstances()
          .find((item) => (item.path || item.instance_id) === state.selectedInstance)
        if (selected) loadAssemblyParameters(selected)
      }
      toast(`已更新 ${outdated} 个引用`, 'info', 3)
    } catch (error) {
      toast(`更新引用失败：${error.message}${error.hint ? ` · ${error.hint}` : ''}`, 'error', 6)
    } finally {
      state.assemblyEditBusy = false
      renderAssemblyState()
      renderAssemblyEdit()
    }
  }

  const renderAssemblyInspector = () => {
    if (state.kind !== 'assembly') {
      assemblySection.hidden = true
      assemblyInspectorSignature = ''
      return
    }
    const instances = assemblyInstances()
    const metrics = state.assemblyScene?.metrics || {}
    const selection = state.selection?.scope === 'instance' ? state.selection : null
    const instance = selection
      ? instances.find((item) => (item.path || item.instance_id) === selection.path) || null
      : null
    const bounds = instance ? assemblyWorldBounds(instance) : null
    const parts = metrics.parts ?? instances.filter((item) => item.definition_kind === 'part').length
    const failures = metrics.failures ?? instances.filter((item) => item.error).length
    const noteLines = []
    if (!state.assemblyScene) {
      noteLines.push(state.assemblyBusy
        ? '正在读取装配场景…'
        : '装配场景不可用；可点“显示装配几何”重试')
    }
    if (instance) {
      noteLines.push(`路径 ${instance.path}`)
      if (instance.name) noteLines.push(`名称 ${instance.name}`)
      noteLines.push(`定义 ${instance.definition_id} v${instance.version}`
        + (instance.configuration ? ` · ${instance.configuration}` : ''))
      const translation = instance.placement?.translation
      if (Array.isArray(translation)) {
        noteLines.push(`位移 ${translation.map((value) => fmt(value, 1)).join(', ')}`)
      }
      if (bounds) noteLines.push(`范围 ${bounds.size.map((value) => fmt(value, 1)).join('×')} mm`)
      if (instance.suppressed) noteLines.push('该实例已停用，不参与几何')
      if (instance.visible === false) noteLines.push('该实例已隐藏')
      if (instance.error) {
        noteLines.push(`错误 ${instance.error.code || ''}: ${instance.error.message || ''}`)
      }
      if (state.sameDefinition) noteLines.push(`同定义实例 ${sameDefinitionInstances(instance).length} 个`)
    } else if (state.assemblyScene?.bbox) {
      const low = state.assemblyScene.bbox.min
      const high = state.assemblyScene.bbox.max
      noteLines.push(`装配范围 ${high.map((value, axis) => fmt(value - low[axis], 1)).join('×')} mm`)
    }
    if (parts > AUTO_ASSEMBLY_PREVIEW_PARTS && !state.assemblyGeometryShown) {
      noteLines.push(`零件较多（${parts} 个）；整机预览会一次性展开全部实例`)
    }
    if (state.assemblyPreviewStartedAt) {
      noteLines.push(`正在载入 ${state.assemblyPreviewLabel || '装配几何'}，可清除预览`)
    }
    const outdated = state.assemblyReferences?.outdated?.length ?? 0
    if (outdated) noteLines.push(`引用过期 ${outdated} 个`)
    const signature = JSON.stringify([
      state.version,
      state.assemblyBusy,
      Boolean(state.assemblyScene),
      metrics.instances ?? null,
      metrics.definitions ?? null,
      parts,
      failures,
      outdated,
      state.assemblyEditBusy,
      state.selectedInstance,
      state.sameDefinition,
      selection?.definition_key || null,
      state.ready,
      state.assemblyGeometryShown,
      noteLines,
    ])
    if (signature === assemblyInspectorSignature) {
      renderAssemblyEdit()
      return
    }
    assemblyInspectorSignature = signature
    assemblySection.hidden = false
    assemblyMetricNodes.instances.textContent = fmt(metrics.instances ?? instances.length)
    assemblyMetricNodes.definitions.textContent = fmt(
      metrics.definitions ?? Object.keys(state.assemblyScene?.definitions || {}).length)
    assemblyMetricNodes.parts.textContent = fmt(parts)
    assemblyMetricNodes.failures.textContent = fmt(failures)
    assemblyNote.hidden = !noteLines.length
    assemblyNote.textContent = noteLines.join('\n')
    sameDefinitionButton.disabled = !selection?.definition_key || !state.assemblyScene
    sameDefinitionButton.setAttribute('aria-pressed', state.sameDefinition ? 'true' : 'false')
    sameDefinitionButton.textContent = state.sameDefinition ? '仅此实例' : '同定义实例'
    updateReferencesButton.textContent = outdated ? `更新引用 (${outdated})` : '更新引用'
    updateReferencesButton.disabled = !outdated || state.assemblyEditBusy
    showGeometryButton.disabled = !state.ready || !state.assembly || state.assemblyEditBusy
    openSubsystemButton.hidden = !(instance?.definition_kind === 'assembly'
      && instance.path === instance.instance_id)
    const scope = assemblyPreviewScope()
    showGeometryButton.textContent = scope.subsystem ? `预览 ${scope.label}` : `预览整机（${fmt(scope.count)} 个零件）`
    renderAssemblyEdit()
  }

  const closeBom = () => {
    if (bomDialog.open) bomDialog.close()
  }

  const bomName = (documentId) => {
    const doc = state.documents.find((item) => item.id === documentId)
    return doc?.name || documentId
  }

  const renderBom = () => {
    bomSummary.replaceChildren()
    bomTable.replaceChildren()
    if (!state.bom) {
      bomTable.append(el('tr', {}, el('td', { className: 'bxw-bom-empty', colspan: '4' },
        state.bomBusy ? '正在读取 BOM…' : '没有 BOM 数据')))
      return
    }
    const summary = state.bom.summary || []
    const rows = state.bom.rows || []
    const leaves = rows.filter((row) => row.kind === 'part')
    const quantity = leaves.length
    const definitions = new Set(summary.map((row) => `${row.document_id}@${row.version}#${row.configuration || 'default'}`)).size
    for (const [label, value] of [
      ['叶子数量', fmt(quantity)],
      ['定义数', fmt(definitions)],
      ['实例行', fmt(rows.length)],
    ]) {
      const card = el('div', {})
      card.append(el('span', {}, label), el('b', {}, value))
      bomSummary.append(card)
    }
    const head = el('thead')
    const headerRow = el('tr')
    for (const label of ['零件', '版本', '配置', '数量']) headerRow.append(el('th', {}, label))
    head.append(headerRow)
    const body = el('tbody')
    const sorted = [...summary].sort((a, b) => {
      const nameA = bomName(a.document_id).toLocaleLowerCase()
      const nameB = bomName(b.document_id).toLocaleLowerCase()
      return nameA.localeCompare(nameB) || a.document_id.localeCompare(b.document_id)
    })
    for (const row of sorted) {
      const tr = el('tr')
      const name = el('td')
      name.append(el('span', {}, bomName(row.document_id)))
      name.append(el('small', {}, row.document_id))
      tr.append(name)
      tr.append(el('td', {}, `v${row.version}`))
      tr.append(el('td', {}, row.configuration || 'default'))
      tr.append(el('td', {}, fmt(row.quantity)))
      body.append(tr)
    }
    bomTable.append(head, body)
    if (!sorted.length) {
      bomTable.append(el('tbody', {}, el('tr', {}, el('td', { className: 'bxw-bom-empty', colspan: '4' },
        '这个装配还没有叶子零件'))))
    }
  }

  const openBom = async () => {
    if (state.kind !== 'assembly' || !state.docId) return
    if (!bomDialog.open) bomDialog.showModal()
    if (state.bomBusy) return
    state.bomBusy = true
    if (!state.bom) renderBom()
    try {
      const payload = await api(`${base}/api/assemblies/${state.docId}/bom`)
      if (state.kind !== 'assembly') return
      state.bom = payload
      renderBom()
    } catch (error) {
      toast(`读取 BOM 失败：${error.message}`, 'error', 6)
      state.bom = null
      renderBom()
    } finally {
      state.bomBusy = false
    }
  }

  const renderAssemblyState = () => {
    if (state.kind !== 'assembly' || !state.assembly) return
    if (state.docId) docSelect.value = state.docId
    const selectedOption = docSelect.selectedOptions?.[0]
    if (selectedOption) {
      selectedOption.textContent = `装配 · ${assemblyName()}`
    }
    docSelect.title = assemblyName()
    version.textContent = `v${state.version ?? 0}`
    const instances = assemblyInstances()
    const metrics = state.assemblyScene?.metrics || {}
    const failures = metrics.failures ?? instances.filter((item) => item.error).length
    checkBadge.hidden = true
    checkBadge.dataset.tone = failures ? 'bad' : ''
    metricBadge.hidden = true
    captionFaces.textContent = `${fmt(instances.length)} 实例`
    captionTight.textContent = `${fmt(metrics.definitions ?? 0)} 定义`
    captionTiming.textContent = ''
    caption.title = `装配 v${state.version} · ${instances.length} 个实例`
    metricsSection.hidden = true
    assemblySection.hidden = false
    scopeGroup.hidden = true
    bomButton.hidden = false
    xrayButton.hidden = false
    treeToolbar.hidden = false
    renderChecks()
    renderFocus()
    renderPlanInspector()
    renderReferences()
    renderHistory()
    renderDimensions()
    renderSelection()
    renderAssemblyInspector()
    renderAssemblyTree()
    renderAssemblyEmpty()
  }

  const renderStructure = () => {
    if (state.kind === 'assembly') renderAssemblyTree()
    else renderPlan()
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

  let checksSignature = ''

  const renderChecks = () => {
    const checks = state.checks
    const items = checks ? checkItems(checks) : []
    const signature = JSON.stringify([
      state.checksBusy,
      checks ? [checks.passed, checks.total, checks.ok] : null,
      items.map((item) => [
        item.feature_id || '', item.name || '', Boolean(item.ok),
        checkValue(item.expected), checkValue(item.observed), item.hint || '',
      ]),
    ])
    if (signature === checksSignature) return
    checksSignature = signature
    const focusKey = focusKeyOf(checkList)
    if (!checks) {
      checkSummary.textContent = state.checksBusy ? '检查中…' : '暂无检查'
      checkSummary.dataset.ok = 'true'
      checkList.replaceChildren()
      restoreFocusKey(focusKey, checkList)
      return
    }
    checkSummary.textContent = `${checks.passed}/${checks.total} 通过`
    checkSummary.dataset.ok = checks.ok ? 'true' : 'false'
    const fragment = document.createDocumentFragment()
    for (const [index, item] of items.slice(0, 200).entries()) {
      // A failing check that names a feature navigates to it; a failing check without
      // one has no action, so it is neither tabbable nor announced as a button.
      const actionable = !item.ok && Boolean(item.feature_id)
      const row = el('li', {
        className: 'bxw-row', tabindex: actionable ? '0' : '-1', 'data-ok': String(Boolean(item.ok)),
      })
      row.dataset.focusKey = `check:${item.feature_id || 'model'}:${item.name}:${index}`
      if (actionable) row.setAttribute('role', 'button')
      const dot = el('span', { className: 'bxw-dot' })
      dot.dataset.state = item.ok ? 'done' : 'failed'
      const text = el('div', { className: 'bxw-row-main' })
      text.append(el('b', {}, `${item.feature_id || 'model'} · ${item.name}`), el('span', {}, item.expected || ''))
      const observed = checkValue(item.observed)
      if (observed) text.append(el('div', { className: 'bxw-check-observed' }, observed))
      if (!item.ok && item.hint) text.append(el('div', { className: 'bxw-check-observed' }, item.hint))
      row.append(dot, text)
      row.title = [item.feature_id, item.name, item.expected, observed, item.hint].filter(Boolean).join('\n')
      if (actionable) {
        row.addEventListener('click', () => selectPlanNodeForFeature(item.feature_id))
        row.addEventListener('keydown', (event) => {
          if (event.key !== 'Enter' && event.key !== ' ') return
          event.preventDefault()
          selectPlanNodeForFeature(item.feature_id)
        })
      }
      fragment.append(row)
    }
    if (items.length > 200) {
      fragment.append(el('li', { className: 'bxw-row bxw-check' }, `还有 ${items.length - 200} 条检查`))
    }
    checkList.replaceChildren(fragment)
    restoreFocusKey(focusKey, checkList)
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
    if (document.visibilityState === 'hidden') return
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
    if (state.selectedBody) {
      state.selectedBody = null
      bodySeq += 1
      post('highlight', { centers: [] })
    }
    setInspector(true)
    renderPlan()
    renderPlanInspector()
  }

  // The body selection is the feature id, not a face: dimensions read that feature's
  // editable parameters, while the overlay is placed from the body's own scene so the
  // displayed final shape never has to be replaced.
  const bodyPick = (body) => {
    const metrics = body.metrics || {}
    const min = Array.isArray(metrics.bbox_min) ? metrics.bbox_min : null
    const max = Array.isArray(metrics.bbox_max) ? metrics.bbox_max : null
    const size = Array.isArray(metrics.bbox_size) ? metrics.bbox_size
      : min && max ? max.map((value, axis) => value - min[axis]) : undefined
    const center = min && max ? min.map((value, axis) => (value + max[axis]) / 2) : undefined
    return {
      scope: 'body',
      feature_id: body.feature_id,
      body_metrics: { faces: metrics.faces, volume: metrics.volume },
      body_bbox: size,
      center,
      version: state.version,
      pending: false,
    }
  }

  const bodyHighlightCenters = async (body) => {
    const key = `${state.docId}:${state.version}:${body.feature_id}`
    const cached = bodyScenes.get(key)
    if (cached) {
      bodyScenes.delete(key)
      bodyScenes.set(key, cached)
      return cached
    }
    const scene = await api(
      `${base}/api/docs/${state.docId}/scene?feature=${encodeURIComponent(body.feature_id)}`
      + `&version=${state.version}&edges=0`)
    const centers = (scene.faces || []).map((face) => face.center).filter(Array.isArray)
    bodyScenes.set(key, centers)
    while (bodyScenes.size > BODY_SCENE_LIMIT) bodyScenes.delete(bodyScenes.keys().next().value)
    return centers
  }

  const highlightBody = async (body) => {
    const seq = ++bodySeq
    if (body.visible === false) {
      post('highlight', { centers: [] })
      return
    }
    let centers = []
    try {
      centers = await bodyHighlightCenters(body)
    } catch (error) {
      centers = []
    }
    if (seq !== bodySeq || state.selectedBody !== body.feature_id) return
    const center = bodyPick(body).center
    const anchors = centers.length ? centers : (center ? [center] : [])
    post('highlight', anchors.length ? { centers: anchors, seconds: 0, tone: 'selection' } : { centers: [] })
  }

  const selectBody = (body) => {
    if (!state.docId || !body?.feature_id) return
    pickSeq += 1
    handleSeq += 1
    const featureId = body.feature_id
    state.reference = null
    state.handle = null
    state.selectedBody = featureId
    state.selection = bodyPick(body)
    const node = planNodes().find((item) => item.id === featureId || item.feature_id === featureId)
    state.selectedNode = node ? node.id : null
    setHandleHint(null)
    post('handle', null)
    setInspector(true)
    renderSelection()
    renderPlan()
    renderPlanInspector()
    loadDimensions(featureId)
    highlightBody(body)
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

  let planInspectorSignature = ''

  const renderPlanInspector = () => {
    const nodes = planNodes()
    if (!nodes.length) {
      planSection.hidden = true
      planJob.hidden = true
      planInspectorSignature = ''
      return
    }
    planSection.hidden = false
    let node = nodes.find((item) => item.id === state.selectedNode)
    if (!node) {
      node = nodes.find((item) => item.status === 'failed') || nodes[nodes.length - 1]
      state.selectedNode = node.id
    }
    const signature = JSON.stringify([
      state.selectedNode,
      state.version,
      nodes.map((item) => [item.id, item.status, item.title || '']),
      node.id, node.status, node.title || '', node.action || '', node.kind || '',
      node.milestone_version ?? null, node.params || null, node.expect || null,
      node.observed || null, node.refs || null, node.deps || null, node.error || '',
      state.job ? [state.job.job_id, state.job.status, state.job.elapsed_ms ?? null, state.job.error || ''] : null,
    ])
    if (signature === planInspectorSignature) return
    planInspectorSignature = signature
    planTitle.textContent = node.title || node.id
    planTitle.title = `${node.id} · ${node.action || node.kind || ''}`
    const pickerSignature = nodes.map((item) => item.id).join('|')
    if (planPicker.dataset.signature !== pickerSignature) {
      planPicker.textContent = ''
      for (const item of nodes) {
        planPicker.append(el('option', { value: item.id },
          `${item.id} · ${planNodeStatus(item)} · ${item.title || ''}`))
      }
      planPicker.dataset.signature = pickerSignature
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
      addAction('移除节点', '从计划中删除失败节点', async () => {
        const ok = await confirmAction({
          title: '移除计划节点',
          body: `将从计划中移除节点 ${node.id}。`,
          confirmLabel: '移除',
        })
        if (ok) removePlanNode(node)
      })
    }
    addAction('回滚上一版本', '回退当前文档一个里程碑', async () => {
      if (state.version <= 0) return
      const ok = await confirmAction({
        title: '回滚上一版本',
        body: `当前模型将回滚到 v${state.version - 1}；该版本与当前版本都保留在历史中。`,
        confirmLabel: '回滚',
      })
      if (ok) revertToVersion(state.version - 1)
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
      planDetails.append(el('div', { className: 'bxw-node-block', 'data-tone': 'bad' }, node.error))
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

  let referencesSignature = ''

  const renderReferences = () => {
    const imports = (state.current?.features || []).filter((feature) => feature.type === 'import_base')
    const signature = JSON.stringify(imports.map((feature) => [feature.id, feature.note || '']))
    if (signature === referencesSignature) return
    referencesSignature = signature
    referenceSection.hidden = !imports.length
    const fragment = document.createDocumentFragment()
    for (const feature of imports) {
      const row = el('div', { className: 'bxw-history-row' })
      row.append(el('b', {}, feature.id))
      row.append(el('small', {}, feature.note || '导入基准体'))
      fragment.append(row)
    }
    referenceList.replaceChildren(fragment)
  }

  let historySignature = ''

  const renderHistory = () => {
    const milestones = state.current?.milestones || []
    const recent = [...milestones].slice(-8).reverse()
    const signature = JSON.stringify([
      state.version,
      recent.map((milestone) => [milestone.version, milestone.title || '', milestone.actor || '']),
    ])
    if (signature === historySignature) return
    historySignature = signature
    historySection.hidden = !milestones.length
    const fragment = document.createDocumentFragment()
    for (const milestone of recent) {
      const row = el('div', { className: 'bxw-history-row' })
      row.append(el('b', {}, `v${milestone.version} · ${milestone.title || '里程碑'}`))
      row.append(el('small', {}, milestone.actor || ''))
      const diff = el('button', { type: 'button', title: '对比上一版本' }, '对比')
      diff.addEventListener('click', () => compareVersion(milestone.version))
      const ghost = el('button', { type: 'button', title: '叠加该版本残影' }, '残影')
      ghost.addEventListener('click', () => showGhostVersion(milestone.version))
      const revert = el('button', { type: 'button', title: '回滚到该版本' }, '回滚')
      revert.addEventListener('click', async () => {
        const ok = await confirmAction({
          title: `回滚到 v${milestone.version}`,
          body: `当前模型将回到 v${milestone.version} 的几何；后续版本仍保留在历史中。`,
          confirmLabel: '回滚',
        })
        if (ok) revertToVersion(milestone.version)
      })
      revert.disabled = milestone.version === state.version
      row.append(diff, ghost, revert)
      fragment.append(row)
    }
    historyList.replaceChildren(fragment)
  }

  const msText = (value) => {
    const ms = Number(value)
    if (!Number.isFinite(ms)) return ''
    return ms >= 1000 ? `${(ms / 1000).toFixed(2)} s` : `${Math.round(ms)} ms`
  }

  const timingValue = (value) => {
    if (value == null || value === '') return null
    const number = Number(value)
    return Number.isFinite(number) ? number : null
  }

  const renderTiming = () => {
    const fetchMs = timingValue(state.fetchMs)
    const parseReported = timingValue(state.parseMs)
    // The viewport reports parseMs from the moment it started the request, so the
    // download is already inside it; subtracting it keeps 下载/解析/建边/首帧 additive.
    const parseMs = parseReported == null ? null : Math.max(0, parseReported - (fetchMs || 0))
    const edgesMs = timingValue(state.edgesMs)
    const renderMs = timingValue(state.renderMs)
    const sceneParts = []
    if (state.reusedScene) sceneParts.push('复用已解析几何')
    if (fetchMs != null && fetchMs > 0) sceneParts.push(`场景下载 ${msText(fetchMs)}`)
    if (parseMs != null) sceneParts.push(`解析 ${msText(parseMs)}`)
    if (edgesMs != null) sceneParts.push(`建边 ${msText(edgesMs)}`)
    // renderMs measures post->shown, so the first frame is what remains after the
    // three stages above; the stages are not added to it a second time.
    const firstFrame = renderMs == null ? null : Math.max(0, renderMs - (fetchMs || 0) - (parseMs || 0) - (edgesMs || 0))
    if (firstFrame != null) sceneParts.push(`首帧 ${msText(firstFrame)} 总计 ${msText(renderMs)}`)
    const backgroundParts = []
    const backgroundState = timingValue(state.timings?.state)
    const backgroundPlan = timingValue(state.timings?.plan)
    if (backgroundState != null) backgroundParts.push(`后台状态 ${msText(backgroundState)}`)
    if (backgroundPlan != null) backgroundParts.push(`计划 ${msText(backgroundPlan)}`)
    captionTiming.textContent = firstFrame != null ? `首帧 ${msText(firstFrame)}` : ''
    caption.title = [...sceneParts, ...backgroundParts].join(' · ')
  }

  // `chromeOnly` skips the list rebuilds: the placeholder render right after `/meta`
  // has no list input yet, so the first full render waits for `/state` after `shown`.
  const renderState = (options = {}) => {
    if (!state.current) return
    closeBom()
    metricsSection.hidden = false
    assemblySection.hidden = true
    assemblyEditSection.hidden = true
    scopeGroup.hidden = false
    checkBadge.hidden = false
    metricBadge.hidden = false
    bomButton.hidden = true
    treeToolbar.hidden = true
    assemblyBreadcrumb.hidden = true
    xrayButton.hidden = true
    const doc = state.current.document || {}
    const metrics = state.current.metrics || {}
    docSelect.value = state.docId
    version.textContent = `v${doc.version ?? 0}`
    const checks = state.current.checks
    if (state.checksBusy && !state.checks) {
      checkBadge.textContent = '检查中…'
      checkBadge.dataset.tone = 'busy'
    } else if (checks) {
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
    // A geometry failure keeps the reason on screen; a background state refresh must
    // not hide the overlay before the user retries or opens another document.
    if (!state.geometryLoading && !state.designFailed) empty.dataset.on = 'false'
    state.version = doc.version ?? 0
    const known = state.documents.find((item) => item.id === state.docId)
    if (known) {
      known.version = state.version
      known.name = doc.name || known.name
    }
    const selected = docSelect.selectedOptions?.[0]
    if (selected) selected.textContent = doc.name || state.docId
    docSelect.title = doc.name || state.docId
    // An edit can remove the feature whose body is selected; the tree must not keep a
    // selection that no row can clear.
    if (state.selectedBody && !bodies().some((body) => body.feature_id === state.selectedBody)) {
      clearSelection()
    }
    if (state.selection?.version != null && state.selection.version !== state.version) clearSelection()
    if (state.reference?.version != null && state.reference.version !== state.version) clearSelection()
    if (state.variantPreview != null) state.variantPreview = null
    if (state.ghost) syncGhost()
    if (options.chromeOnly) {
      renderTiming()
      return
    }
    renderReview()
    renderPlan()
    renderPlanInspector()
    renderChecks()
    renderFocus()
    renderVariants()
    renderReferences()
    renderHistory()
    renderTiming()
    if (!state.geometryLoading && state.shown !== state.version) pushDesign(false)
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

  const stopLoadTimer = () => {
    if (state.loadTimer) {
      clearInterval(state.loadTimer)
      state.loadTimer = null
    }
  }

  const resetTimings = () => {
    state.timings = {}
    state.designStarted = null
    state.renderMs = null
    state.fetchMs = null
    state.parseMs = null
    state.edgesMs = null
    state.reusedScene = false
    renderTiming()
  }

  const hideLoadingOverlay = () => {
    state.geometryLoading = false
    stopLoadTimer()
    emptySpinner.hidden = true
    if (!state.current?.vacant) empty.dataset.on = 'false'
  }

  const markGeometryFailure = (text) => {
    const reason = String(text || '几何加载失败')
    state.designFailed = { text: reason, documentId: state.docId }
    state.designPending = null
    state.geometryLoading = false
    stopLoadTimer()
    resetTimings()
    emptySpinner.hidden = true
    emptyTitle.textContent = '几何加载失败'
    emptyBody.textContent = reason
    emptyButton.hidden = false
    empty.dataset.on = 'true'
  }

  const timedApi = async (path) => {
    const start = performance.now()
    const value = await api(path)
    return { value, ms: performance.now() - start }
  }

  const loadBackground = async (docId, token) => {
    if (!docId || token !== state.loadToken || docId !== state.docId) return
    state.stateBusy = true
    state.checksBusy = true
    renderState()
    try {
      const stateResult = await timedApi(`${base}/api/docs/${docId}/state`)
      if (token !== state.loadToken || docId !== state.docId) return
      const view = stateResult.value
      state.current = view
      state.version = view.document.version
      state.checks = checksSnapshot(view.checks)
      state.stateBusy = false
      state.checksBusy = false
      state.timings = { ...state.timings, state: stateResult.ms }
      renderState()
      if (view.vacant) {
        hideLoadingOverlay()
        emptyTitle.textContent = '空白模型'
        emptyBody.textContent = '在下方描述要创建的零件，或选择另一个已有模型。'
        emptyButton.hidden = false
        empty.dataset.on = 'true'
      }
      timedApi(`${base}/api/docs/${docId}/plan`)
        .then(({ value, ms }) => {
          if (token !== state.loadToken) return
          state.plan = value
          state.timings = { ...state.timings, plan: ms }
          renderPlan()
          renderPlanInspector()
        })
        .catch(() => {})
    } catch (error) {
      if (token !== state.loadToken) return
      state.stateBusy = false
      state.checksBusy = false
      renderState()
      if (state.geometryLoading) {
        hideLoadingOverlay()
        emptySpinner.hidden = true
        emptyTitle.textContent = '加载失败'
        emptyBody.textContent = error.message
        emptyButton.hidden = false
        empty.dataset.on = 'true'
      }
      toast(`后台加载失败：${error.message}`, 'error', 6)
    }
  }

  const loadAssembly = async (docId, force = false, manual = false) => {
    if (docId === state.docId && state.kind === 'assembly' && state.assembly && !force) return
    const previousDocId = state.docId
    const token = ++loadSeq
    state.loadToken = token
    state.loadDocId = docId
    state.docId = docId
    state.kind = 'assembly'
    stopModelingProgress()
    stopJobPoll()
    state.job = null
    state.current = null
    state.plan = null
    state.checks = null
    state.assembly = null
    state.assemblyScene = null
    state.assemblyBusy = true
    state.pendingAssemblyPreview = false
    state.assemblyGeometryShown = false
    stopAssemblyPreviewClock()
    state.assemblyPreviewStartedAt = null
    state.assemblyPreviewLabel = ''
    state.assemblyPreviewSeq += 1
    stopAssemblyPreviewPoll()
    state.assemblyPreviewAbort?.abort()
    state.assemblyPreviewAbort = null
    state.assemblyPreviewBuildId = null
    state.assemblyPreviewProgress = 0
    state.assemblyPreviewKey = ''
    state.assemblyBundleKey = ''
    state.assemblyPreviewLastGood = null
    state.assemblyPreviewPendingGood = null
    state.assemblyPreviewPhase = 'idle'
    state.assemblyPreviewMessage = ''
    for (const timer of state.assemblyTimers) clearTimeout(timer)
    state.assemblyTimers = []
    assemblyCenterCache.clear()
    assemblyParameterCache.clear()
    assemblyParameterSeq += 1
    assemblySignature = ''
    assemblyInspectorSignature = ''
    assemblyEditSignature = ''
    state.assemblyEditBusy = false
    state.assemblyParameters = null
    state.assemblyParametersFor = null
    state.assemblyParameterBusy = false
    state.assemblyReferences = null
    state.bom = null
    state.bomBusy = false
    closeBom()
    state.selectedNode = null
    state.selectedBody = null
    state.selectedInstance = null
    state.sameDefinition = false
    if (previousDocId !== docId) {
      state.assemblyExpanded.clear()
      state.treeFocus = ''
      state.structureQuery = ''
      structureSearch.value = ''
    }
    state.designPending = null
    state.designFailed = null
    state.designRetries = 0
    state.geometryLoading = false
    state.stateBusy = true
    state.checksBusy = false
    state.backgroundStarted = true
    state.shown = -1
    pickSeq += 1
    bodySeq += 1
    dimensionSeq += 1
    handleSeq += 1
    state.selection = null
    state.reference = null
    state.handle = null
    state.dimensions = null
    state.dimensionFeature = null
    stopLoadTimer()
    if (state.loadFallback) {
      clearTimeout(state.loadFallback)
      state.loadFallback = null
    }
    resetTimings()
    renderSelection()
    renderDimensions()
    setHandleHint(null)
    post('handle', null)
    post('highlight', { centers: [] })
    // Remove the previous document's display before the assembly STEP preview arrives.
    post('clear', {})
    resetReviewTools()
    resetVariants()
    resetCandidates()
    metricsSection.hidden = true
    assemblySection.hidden = false
    assemblyEditSection.hidden = true
    if (state.docId) docSelect.value = state.docId
    structureProgress.hidden = true
    structureProgress.replaceChildren()
    structureMeta.textContent = '—'
    structureList.replaceChildren(el('div', { className: 'bxw-structure-empty' }, '正在读取装配…'))
    renderAssemblyInspector()
    setLoading(true)
    emptyTitle.textContent = '正在读取装配'
    emptyBody.textContent = '正在读取装配树、版本引用与场景定义。'
    try {
      const stateResult = await api(`${base}/api/assemblies/${docId}`)
      if (token !== state.loadToken || docId !== state.docId) return
      if (!stateResult?.assembly) throw new Error('装配响应缺少 assembly')
      state.assembly = stateResult
      state.version = Number(stateResult.assembly.version) || 0
      state.assemblyReferences = referencesFromState(stateResult)
      state.stateBusy = false
      state.assemblyBusy = true
      hideLoadingOverlay()
      const known = state.documents.find((item) => item.id === docId)
      if (known) {
        known.version = state.version
        known.name = stateResult.assembly.name || known.name
        known.instances = stateResult.build?.instances?.length ?? known.instances
      }
      const sessionId = state.sessionId || options.getSessionId?.()
      if (sessionId) {
        state.sessionId = sessionId
        if (manual) writeBinding(sessionId, docId, true)
        else if (!readBinding(sessionId)?.manual) writeBinding(sessionId, docId, false)
      }
      // The instance tree comes from the build summary and is usable before the
      // definition meshes arrive; a large assembly must not wait for its scene.
      renderAssemblyState()
      api(`${base}/api/assemblies/${docId}/references`)
        .then((payload) => {
          if (token !== state.loadToken || docId !== state.docId) return
          if (payload?.references) {
            state.assemblyReferences = payload
            renderAssemblyState()
          }
        })
        .catch(() => {})
      api(`${base}/api/assemblies/${docId}/scene`)
        .then((scene) => {
          if (token !== state.loadToken || docId !== state.docId) return
          state.assemblyScene = scene
          state.assemblyBusy = false
          renderAssemblyState()
          const placed = scene?.metrics?.parts ?? 0
          if (!state.assemblyGeometryShown && placed > 0 && placed <= AUTO_ASSEMBLY_PREVIEW_PARTS) {
            if (state.ready) showAssemblyGeometry()
            else state.pendingAssemblyPreview = true
          }
        })
        .catch((error) => {
          if (token !== state.loadToken || docId !== state.docId) return
          state.assemblyBusy = false
          renderAssemblyState()
          toast(`装配场景加载失败：${error.message}`, 'error', 6)
        })
    } catch (error) {
      if (token !== state.loadToken) return
      state.assemblyBusy = false
      state.stateBusy = false
      state.geometryLoading = false
      hideLoadingOverlay()
      emptyTitle.textContent = '装配加载失败'
      emptyBody.textContent = error.message
      emptyButton.hidden = false
      empty.dataset.on = 'true'
      toast(`加载装配失败：${error.message}`, 'error', 6)
      throw error
    }
  }

  const loadDocument = async (docId, force = false, manual = false) => {
    if (!docId) {
      state.loadToken = ++loadSeq
      state.loadDocId = null
      state.backgroundStarted = false
      state.geometryLoading = false
      state.stateBusy = false
      state.checksBusy = false
      state.designPending = null
      state.designFailed = null
      state.designRetries = 0
      stopLoadTimer()
      resetTimings()
      if (state.loadFallback) {
        clearTimeout(state.loadFallback)
        state.loadFallback = null
      }
      stopJobPoll()
      state.job = null
      state.selectedNode = null
      state.selectedBody = null
      state.kind = 'part'
      state.assembly = null
      state.assemblyScene = null
      state.assemblyBusy = false
      state.selectedInstance = null
      state.sameDefinition = false
      state.pendingAssemblyPreview = false
      state.assemblyGeometryShown = false
      stopAssemblyPreviewClock()
      state.assemblyPreviewStartedAt = null
      state.assemblyPreviewLabel = ''
      state.assemblyPreviewSeq += 1
      stopAssemblyPreviewPoll()
      state.assemblyPreviewAbort?.abort()
      state.assemblyPreviewAbort = null
      state.assemblyPreviewBuildId = null
      state.assemblyPreviewProgress = 0
      state.assemblyPreviewKey = ''
      state.assemblyBundleKey = ''
      state.assemblyPreviewLastGood = null
      state.assemblyPreviewPendingGood = null
      state.assemblyPreviewPhase = 'idle'
      state.assemblyPreviewMessage = ''
      treeToolbar.hidden = true
      assemblyBreadcrumb.hidden = true
      bomButton.hidden = true
      metricBadge.hidden = false
      for (const timer of state.assemblyTimers) clearTimeout(timer)
      state.assemblyTimers = []
      assemblySection.hidden = true
      metricsSection.hidden = false
      scopeGroup.hidden = false
      assemblyEditSection.hidden = true
      state.assemblyEditBusy = false
      state.assemblyParameters = null
      state.assemblyParametersFor = null
      state.assemblyParameterBusy = false
      state.assemblyReferences = null
      state.current = null
      state.plan = null
      state.checks = null
      pickSeq += 1
      bodySeq += 1
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
      renderPlan()
      empty.dataset.on = 'true'
      return
    }
    const entry = state.documents.find((item) => item.id === docId)
    if (entry?.kind === 'assembly') {
      await loadAssembly(docId, force, manual)
      return
    }
    if (docId === state.docId && state.current && !force) return
    // A refresh of the document whose geometry is already displayed must not show the
    // geometry placeholder again: the model stays on screen, and a design the viewport
    // de-duplicates by (documentId, version) would otherwise look like a hung load.
    const displayedShown = docId === state.docId && state.current && state.shown >= 0
      && state.shown === state.version ? state.shown : -1
    const geometryDisplayed = displayedShown >= 0
    stopModelingProgress()
    stopJobPoll()
    state.job = null
    if (docId !== state.docId) state.selectedNode = null
    state.selectedBody = null
    state.kind = 'part'
    state.assembly = null
    state.assemblyScene = null
    state.assemblyBusy = false
    state.selectedInstance = null
    state.sameDefinition = false
    state.pendingAssemblyPreview = false
    state.assemblyGeometryShown = false
    stopAssemblyPreviewClock()
    state.assemblyPreviewStartedAt = null
    state.assemblyPreviewLabel = ''
    state.assemblyPreviewSeq += 1
    stopAssemblyPreviewPoll()
    state.assemblyPreviewAbort?.abort()
    state.assemblyPreviewAbort = null
    state.assemblyPreviewBuildId = null
    state.assemblyPreviewProgress = 0
    state.assemblyPreviewKey = ''
    state.assemblyBundleKey = ''
    state.assemblyPreviewLastGood = null
    state.assemblyPreviewPendingGood = null
    state.assemblyPreviewPhase = 'idle'
    state.assemblyPreviewMessage = ''
    treeToolbar.hidden = true
    assemblyBreadcrumb.hidden = true
    bomButton.hidden = true
    metricBadge.hidden = false
    for (const timer of state.assemblyTimers) clearTimeout(timer)
    state.assemblyTimers = []
    assemblySection.hidden = true
    metricsSection.hidden = false
    scopeGroup.hidden = false
    assemblyEditSection.hidden = true
    state.assemblyEditBusy = false
    state.assemblyParameters = null
    state.assemblyParametersFor = null
    state.assemblyParameterBusy = false
    state.assemblyReferences = null
    state.docId = docId
    state.current = null
    state.plan = null
    state.checks = null
    pickSeq += 1
    bodySeq += 1
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
    const token = ++loadSeq
    state.loadToken = token
    state.loadDocId = docId
    state.backgroundStarted = false
    state.shown = displayedShown
    state.designPending = null
    state.designFailed = null
    state.designRetries = 0
    state.lastFailureAt = 0
    if (!geometryDisplayed) resetTimings()
    state.stateBusy = true
    state.checksBusy = true
    state.geometryLoading = !geometryDisplayed
    stopLoadTimer()
    if (state.loadFallback) {
      clearTimeout(state.loadFallback)
      state.loadFallback = null
    }
    const startLoadOverlay = () => {
      setLoading(true)
      emptyTitle.textContent = '正在加载几何'
      emptyBody.textContent = '几何先显示；指标与检查随后在后台更新。'
      const startedAt = performance.now()
      state.loadTimer = setInterval(() => {
        if (document.visibilityState === 'hidden') return
        if (empty.dataset.on !== 'true') return
        const suffix = state.stateBusy ? ' · 结构/检查后台更新' : ''
        emptyBody.textContent = `正在加载几何… ${((performance.now() - startedAt) / 1000).toFixed(1)}s${suffix}`
      }, 250)
    }
    if (!geometryDisplayed) startLoadOverlay()
    try {
      const meta = await api(`${base}/api/docs/${docId}/meta`)
      if (token !== state.loadToken) return
      const version = Number(meta.version) || 0
      const vacant = Boolean(meta.vacant)
      const alreadyShown = geometryDisplayed && !vacant && version === displayedShown
      state.version = version
      state.current = {
        document: { id: docId, name: meta.name, version },
        vacant,
        metrics: null,
        checks: null,
        features: meta.features || [],
        milestones: meta.milestones || [],
        focus: [],
        plan: null,
      }
      state.stateBusy = !vacant
      state.checksBusy = !vacant
      state.geometryLoading = !vacant && !alreadyShown
      if (!vacant && geometryDisplayed && !alreadyShown) startLoadOverlay()
      renderState({ chromeOnly: true })
      const sessionId = state.sessionId || options.getSessionId?.()
      if (sessionId) {
        state.sessionId = sessionId
        if (manual) writeBinding(sessionId, docId, true)
        else if (!readBinding(sessionId)?.manual) writeBinding(sessionId, docId, false)
      }
      if (vacant) {
        hideLoadingOverlay()
        emptyTitle.textContent = '空白模型'
        emptyBody.textContent = '在下方描述要创建的零件，或选择另一个已有模型。'
        emptyButton.hidden = false
        empty.dataset.on = 'true'
        state.backgroundStarted = true
        loadBackground(docId, token)
        return
      }
      if (alreadyShown) {
        // Geometry for this version is already on screen; refresh state and plan only.
        state.backgroundStarted = true
        loadBackground(docId, token)
        return
      }
      pushDesign(true)
      state.loadFallback = setTimeout(() => {
        if (state.backgroundStarted || token !== state.loadToken) return
        state.backgroundStarted = true
        loadBackground(docId, token)
      }, 30000)
    } catch (error) {
      if (token !== state.loadToken) return
      state.current = null
      state.stateBusy = false
      state.checksBusy = false
      state.geometryLoading = false
      state.designPending = null
      state.designFailed = null
      stopLoadTimer()
      resetTimings()
      if (state.loadFallback) {
        clearTimeout(state.loadFallback)
        state.loadFallback = null
      }
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
    const preferred = [options.documentId, bound?.id, stored?.id, state.docId, ...state.documents.map((doc) => doc.id)]
      .find((id) => id && state.documents.some((doc) => doc.id === id))
    state.docId = preferred || state.documents[0]?.id || null
    renderDocuments()
    if (state.docId) await loadDocument(state.docId, true, Boolean(bound?.id === state.docId && bound?.manual))
    else empty.dataset.on = 'true'
  }

  docSelect.addEventListener('change', () => {
    if (!docSelect.value) return
    state.assemblyTrail = []
    loadDocument(docSelect.value, true, true).catch(() => {})
  })
  docSearch.addEventListener('input', () => {
    state.docQuery = docSearch.value.trim()
    renderDocuments()
  })
  emptyButton.addEventListener('click', createModel)

  composer.addEventListener('submit', async (event) => {
    event.preventDefault()
    if (state.busy) return
    const text = input.value.trim()
    if (!text) return
    if (runCommand(text)) {
      input.value = ''
      return
    }
    if (!state.docId) return
    if (state.kind === 'assembly') {
      toast('装配文档暂不支持在对话中编辑；点选实例可查看定义与路径', 'info', 4)
      return
    }
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
    if (event.key !== 'Enter' || event.shiftKey) return
    // The composing Enter only accepts the IME candidate. Submitting on it would
    // send the half-composed text and then clear the draft (input.value = '').
    if (event.isComposing || event.keyCode === 229) return
    event.preventDefault()
    composer.requestSubmit()
  })
  const onGlobalKey = (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault()
      input.focus()
      return
    }
    if (event.key === 'Escape') {
      // Layers close in stacking order; the panel that had focus returns it to the
      // control that opened it instead of leaving focus on a hidden node.
      if (!reviewMenu.hidden) {
        event.preventDefault()
        closeReviewMenu(true)
        return
      }
      if (!candidatePanel.hidden) {
        event.preventDefault()
        closeCandidates(true)
        return
      }
      closeViewMenu()
    }
  }
  document.addEventListener('keydown', onGlobalKey)

  const onMessage = (event) => {
    // Reject before reading event.data: only the kernel-view iframe at the configured
    // origin is allowed to report ready/shown/pick/handle messages.
    if (event.origin !== frameOrigin) return
    if (event.source !== frame.contentWindow) return
    const data = event.data
    if (!data || data.from !== 'brepx-viewport') return
    if (data.type === 'ready') {
      state.ready = true
      state.shown = -1
      state.designPending = null
      state.designFailed = null
      state.designRetries = 0
      state.lastFailureAt = 0
      post('theme', viewportTheme())
      // Sent before the first design so `fit` already knows the dock's footprint;
      // messages on the frame's channel are delivered in order.
      post('inset', { bottom: Math.ceil(dock.getBoundingClientRect().height) + 12 })
      // The frame was still loading when the dock measured itself, so the inset is
      // repeated once it can receive messages.
      dockResize.unobserve(dock)
      dockResize.observe(dock)
      if (state.kind === 'assembly') {
        if (state.assembly && (state.pendingAssemblyPreview || state.assemblyGeometryShown)) {
          showAssemblyGeometry()
        }
        renderAssemblyInspector()
      } else {
        pushDesign(true)
      }
      startWatchdog()
    } else if (data.type === 'shown') {
      // A late `shown` from a document that is no longer open must not stop the
      // current load or overwrite its timings.
      if (data.documentId !== state.docId) return
      state.shown = data.version
      state.designPending = null
      if (data.version !== state.version) return
      const wasFailed = Boolean(state.designFailed)
      state.designRetries = 0
      state.designFailed = null
      if (state.designStarted != null) {
        state.renderMs = performance.now() - state.designStarted
        state.lastShownMs = state.renderMs
        state.designStarted = null
      }
      state.fetchMs = data.timings?.fetchMs ?? null
      state.parseMs = data.timings?.parseMs ?? null
      state.edgesMs = data.timings?.edgesMs ?? null
      state.reusedScene = Boolean(data.timings?.reused || data.reused)
      if (state.geometryLoading || wasFailed) {
        hideLoadingOverlay()
        renderState()
      }
      renderTiming()
      if (!state.backgroundStarted) {
        state.backgroundStarted = true
        if (state.loadFallback) {
          clearTimeout(state.loadFallback)
          state.loadFallback = null
        }
        loadBackground(state.docId, state.loadToken)
      }
    } else if (data.type === 'preview-shown') {
      stopAssemblyPreviewClock()
      state.assemblyPreviewStartedAt = null
      if (state.kind === 'assembly') {
        state.assemblyPreviewPhase = 'step'
        state.assemblyPreviewMessage = ''
      } else {
        state.assemblyPreviewLabel = ''
      }
      renderAssemblyEmpty()
      renderAssemblyInspector()
    } else if (data.type === 'preview-error') {
      stopAssemblyPreviewClock()
      state.assemblyPreviewStartedAt = null
      state.assemblyGeometryShown = false
      state.assemblyPreviewPhase = state.kind === 'assembly' ? 'failed' : 'idle'
      state.assemblyPreviewMessage = data.text || '未知错误'
      state.assemblyPreviewLabel = ''
      renderAssemblyEmpty()
      renderAssemblyInspector()
      toast(`装配几何预览失败：${data.text || '未知错误'}`, 'error', 7)
    } else if (data.type === 'assembly-preview-ready') {
      if (!state.assemblyPreviewPendingGood) return
      stopAssemblyPreviewClock()
      state.assemblyPreviewStartedAt = null
      state.assemblyPreviewBuildId = null
      state.assemblyPreviewProgress = 1
      state.assemblyGeometryShown = true
      state.assemblyPreviewPhase = 'ready'
      state.assemblyPreviewMessage = ''
      state.assemblyPreviewLastGood = state.assemblyPreviewPendingGood
      state.assemblyPreviewPendingGood = null
      state.assemblyPreviewLabel = state.assemblyPreviewLastGood.label || ''
      const xrayPaths = assemblyXrayPaths()
      if (state.xray && xrayPaths.length) {
        post('assembly-xray', { on: true, paths: xrayPaths })
      } else if (state.xray) {
        state.xray = false
        xrayButton.setAttribute('aria-pressed', 'false')
        post('assembly-xray', { on: false })
      }
      renderAssemblyEmpty()
      renderAssemblyInspector()
    } else if (data.type === 'assembly-preview-error') {
      if (!state.assemblyPreviewKey) return
      state.assemblyPreviewPendingGood = null
      failAssemblyPreviewRequest(
        data.message || data.code || '视口无法解码预览包',
        { scope: assemblyPreviewScope() },
      )
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
      if (data.documentId && data.documentId !== state.docId) return
      const reason = String(data.text || '几何加载失败')
      // A failure belongs to the design it was requested for. The viewport drops stale
      // requests, but its catch may still report one; failing the current load on that
      // report would put a wrong reason over geometry that is still loading.
      if (data.version != null && Number(data.version) !== state.version) {
        toast(`视图错误：${reason}`, 'error', 6)
        return
      }
      // Stop retrying only for the load that is still waiting for geometry; an error
      // from a stale request must not block a document that is already displayed.
      const relevant = state.geometryLoading || designInFlight() || Boolean(state.designPending)
      if (relevant) markGeometryFailure(reason)
      else toast(`视图错误：${reason}`, 'error', 6)
      if (!state.backgroundStarted) {
        state.backgroundStarted = true
        loadBackground(state.docId, state.loadToken)
      }
    }
  }
  window.addEventListener('message', onMessage)

  const WATCHDOG_TICK_MS = 1500
  let watchdog = null
  const watchdogTick = () => {
    if (document.visibilityState === 'hidden') return
    if (!state.ready || !state.current || state.current.vacant) return
    if (state.designFailed) return
    if (state.shown === state.version) return
    if (designInFlight()) return
    // With no attempt in flight the last event that matters is whichever came later:
    // that attempt was posted, or it expired without `shown`/`error`.
    let reference = Math.max(state.lastDesignAt, state.lastFailureAt)
    const pending = state.designPending
    if (pending) {
      // The attempt expired without `shown` or `error`; the next one waits a full
      // backoff step so a slow viewport is not flooded with duplicate designs.
      state.designPending = null
      state.lastFailureAt = performance.now()
      reference = state.lastFailureAt
    }
    if (state.designRetries >= DESIGN_MAX_RETRIES) {
      markGeometryFailure(`几何加载超时：视口重试 ${DESIGN_MAX_RETRIES} 次仍无结果`)
      return
    }
    const backoff = DESIGN_BACKOFF_MS[Math.min(state.designRetries, DESIGN_BACKOFF_MS.length - 1)]
    if (performance.now() - reference < backoff) return
    state.designRetries += 1
    pushDesign(false)
  }
  const startWatchdog = () => {
    if (watchdog) return
    watchdog = setInterval(watchdogTick, WATCHDOG_TICK_MS)
  }
  frame.addEventListener('load', () => {
    state.ready = false
    state.shown = -1
    state.designPending = null
    // The frame posts ready as soon as its script runs, which can precede this
    // listener when the document is cached. A few pings make the handshake
    // independent of load/cache ordering.
    const ping = () => { if (!state.ready) post('ping', {}) }
    setTimeout(ping, 100)
    setTimeout(ping, 600)
    setTimeout(ping, 2000)
  })

  const onTheme = () => { if (state.ready) post('theme', viewportTheme()) }
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

  // `focusgroup` narrows the toolbar to one tab stop natively (Chromium). Elsewhere the
  // first control holds the stop and the arrow keys move between controls, so the
  // header does not force a Tab through every button before reaching the canvas.
  if (!('focusGroup' in HTMLElement.prototype)) {
    const toolbarItems = () => [...toolbar.querySelectorAll('button, select, input, [tabindex="0"]')]
      .filter((node) => node.offsetParent !== null)
    const setStop = (active) => {
      for (const node of toolbarItems()) node.tabIndex = node === active ? 0 : -1
    }
    setStop(toolbarItems()[0])
    toolbar.addEventListener('focusin', (event) => {
      if (!(event.target instanceof Element) || !toolbar.contains(event.target)) return
      if (!event.target.matches('button, select, input, [tabindex="0"]')) return
      setStop(event.target)
    })
    toolbar.addEventListener('keydown', (event) => {
      const items = toolbarItems()
      const index = items.indexOf(document.activeElement)
      if (index < 0) return
      const step = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0
      if (!step) return
      event.preventDefault()
      items[(index + step + items.length) % items.length].focus()
    })
  }

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
  menuModels.setAttribute('aria-pressed', 'false')
  renderSelection()
  renderReview()
  openHistory(false)
  loadThread()
  options.onFocus?.()
  chooseDocument().catch((error) => toast(`无法加载模型库：${error.message}`, 'error', 8))

  // The 1 s/3 s polls are the highest-frequency timers on the page; a hidden tab must
  // not keep fetching, and returning to the tab resumes them without touching the
  // callback logic. The remaining timers stay scheduled but return early while hidden.
  let threadPoll = null
  let sessionPoll = null
  const startPolling = () => {
    if (threadPoll || document.visibilityState === 'hidden') return
    threadPoll = setInterval(() => { loadThread() }, 3000)
    sessionPoll = setInterval(() => {
      const next = options.getSessionId?.()
      if (next && next !== state.sessionId) {
        setSession(next)
      }
    }, 1000)
  }
  const stopPolling = () => {
    if (threadPoll) clearInterval(threadPoll)
    if (sessionPoll) clearInterval(sessionPoll)
    threadPoll = null
    sessionPoll = null
  }
  const onVisibilityChange = () => {
    if (document.visibilityState === 'hidden') stopPolling()
    else startPolling()
  }
  document.addEventListener('visibilitychange', onVisibilityChange)
  startPolling()

  return {
    dispose() {
      clearInterval(watchdog)
      stopPolling()
      stopJobPoll()
      stopLoadTimer()
      for (const timer of state.assemblyTimers) clearTimeout(timer)
      state.assemblyTimers = []
      if (state.loadFallback) clearTimeout(state.loadFallback)
      state.loadFallback = null
      stopModelingProgress()
      for (const timer of toastTimers) clearTimeout(timer)
      toastTimers.clear()
      observer.disconnect()
      dockObserver.disconnect()
      dockResize.disconnect()
      inspectorResize.disconnect()
      cancelAnimationFrame(questionScanFrame)
      document.removeEventListener('visibilitychange', onVisibilityChange)
      if (confirmDialog.open) confirmDialog.close()
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
          if (!bound) return null
          // A session binding the document that is already open must not reload it:
          // the geometry, state and plan in memory are already the same document.
          if (bound.id === state.docId && (state.current || state.assembly)) {
            if (bound.manual) writeBinding(sessionId, bound.id, true)
            return null
          }
          return loadDocument(bound.id, true, bound.manual).catch(() => {})
        })
        .catch(() => {})
    },
  }
}
