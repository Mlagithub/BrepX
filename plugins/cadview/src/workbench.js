const STYLE_ID = 'bx-workbench-style'
const THEME_ID = 'bx-workbench-theme'

const css = `
  body.bxw-workbench [data-sidebar-collapsed="true"] { grid-template-columns: 0 minmax(0, 1fr) 0 !important; }
  body.bxw-workbench [data-sidebar-collapsed="true"] > :first-child { display: none !important; }
  .bxw-shell {
    position: absolute;
    inset: 0;
    display: grid;
    grid-template-rows: 56px minmax(0, 1fr) auto;
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
  .bxw-shell button:focus-visible, .bxw-shell select:focus-visible, .bxw-shell textarea:focus-visible {
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
  .bxw-actions { display: flex; align-items: center; gap: 6px; flex: none; }
  .bxw-main { min-height: 0; display: grid; grid-template-columns: 236px minmax(0, 1fr) 292px; }
  .bxw-models { min-width: 0; min-height: 0; display: flex; flex-direction: column; border-right: 1px solid var(--bxw-line); background: var(--bxw-panel); }
  .bxw-shell[data-models="off"] .bxw-main { grid-template-columns: minmax(0, 1fr) 292px; }
  .bxw-shell[data-models="off"] .bxw-models { display: none; }
  .bxw-models-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; height: 42px; padding: 0 12px; border-bottom: 1px solid var(--bxw-line); }
  .bxw-models-head strong { font-size: 12px; font-weight: 600; }
  .bxw-models-search { margin: 9px 10px 6px; height: 28px; padding: 0 9px; border: 1px solid var(--bxw-line); border-radius: 6px; background: var(--bxw-layer); color: var(--bxw-primary); outline: 0; }
  .bxw-models-search::placeholder { color: var(--bxw-muted); }
  .bxw-model-list { flex: 1; min-height: 0; overflow-x: hidden; overflow-y: auto; padding: 4px 6px 12px; }
  .bxw-shell .bxw-model-row { height: auto; min-height: 42px; display: flex; flex-direction: column; align-items: stretch; gap: 2px; width: 100%; padding: 8px 9px; border: 1px solid transparent; border-radius: 6px; background: transparent; text-align: left; cursor: pointer; }
  .bxw-model-row:hover { background: var(--bxw-layer); }
  .bxw-model-row[data-active="true"] { border-color: color-mix(in srgb, var(--bxw-accent) 40%, var(--bxw-line)); background: color-mix(in srgb, var(--bxw-accent) 9%, transparent); }
  .bxw-model-row b { display: block; width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--bxw-primary); font-size: 12px; font-weight: 550; }
  .bxw-model-row span { color: var(--bxw-muted); font: 10px/1.35 var(--dsw-font-mono, ui-monospace, monospace); }
  .bxw-inspector-tabs { display: flex; gap: 2px; }
  .bxw-inspector-tabs button { height: 26px; padding: 0 8px; border-color: transparent; color: var(--bxw-muted); font-size: 11px; }
  .bxw-inspector-tabs button[aria-selected="true"] { color: var(--bxw-primary); background: var(--bxw-layer); border-color: var(--bxw-line); }
  .bxw-pane[hidden] { display: none; }
  .bxw-selection { display: flex; align-items: center; gap: 7px; max-width: 980px; margin: 0 auto 7px; min-height: 24px; color: var(--bxw-soft); font-size: 11px; }
  .bxw-selection[hidden] { display: none; }
  .bxw-selection-chip { display: inline-flex; align-items: center; gap: 6px; max-width: 100%; padding: 3px 7px; border: 1px solid color-mix(in srgb, var(--bxw-accent) 40%, var(--bxw-line)); border-radius: 999px; color: var(--bxw-primary); background: color-mix(in srgb, var(--bxw-accent) 9%, transparent); }
  .bxw-selection-chip button { width: 16px; height: 16px; padding: 0; border: 0; background: transparent; color: var(--bxw-muted); }
  .bxw-thread { display: flex; flex-direction: column; gap: 8px; margin: 0; padding: 0; list-style: none; }
  .bxw-thread-item { padding: 8px 9px; border: 1px solid var(--bxw-line); border-radius: 6px; background: var(--bxw-layer); }
  .bxw-thread-item[data-role="user"] { border-color: color-mix(in srgb, var(--bxw-accent) 35%, var(--bxw-line)); }
  .bxw-thread-item b { display: block; margin-bottom: 3px; color: var(--bxw-muted); font-size: 10px; font-weight: 600; letter-spacing: .4px; text-transform: uppercase; }
  .bxw-thread-item p { margin: 0; white-space: pre-wrap; word-break: break-word; }
  .bxw-plan-card { padding: 8px 9px; border: 1px solid var(--bxw-line); border-radius: 6px; background: var(--bxw-layer); }
  .bxw-plan-card-head { display: flex; align-items: center; gap: 7px; }
  .bxw-plan-card-head b { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; font-weight: 550; }
  .bxw-plan-card-meta { margin-top: 3px; color: var(--bxw-muted); font: 10px/1.4 var(--dsw-font-mono, ui-monospace, monospace); }
  .bxw-stage { position: relative; min-width: 0; min-height: 0; background: color-mix(in srgb, var(--bxw-panel) 70%, var(--bxw-bg, #101318)); }
  .bxw-frame { width: 100%; height: 100%; border: 0; display: block; }
  .bxw-tools { position: absolute; top: 12px; left: 12px; display: flex; gap: 4px; padding: 4px;
    border: 1px solid var(--bxw-line); border-radius: 8px; background: color-mix(in srgb, var(--bxw-panel) 92%, transparent);
    backdrop-filter: blur(8px); }
  .bxw-tools .bxw-sep { width: 1px; align-self: stretch; background: var(--bxw-line); margin: 2px 2px; }
  .bxw-tools button { height: 26px; padding: 0 8px; border-color: transparent; color: var(--bxw-soft); }
  .bxw-tools button:hover { color: var(--bxw-primary, #e8edf5); background: var(--bxw-layer); }
  .bxw-tools button[aria-pressed="true"] { color: var(--bxw-accent); background: color-mix(in srgb, var(--bxw-accent) 12%, transparent); }
  .bxw-caption { position: absolute; left: 16px; bottom: 12px; display: flex; align-items: center; gap: 12px;
    padding: 6px 9px; border: 1px solid var(--bxw-line); border-radius: 6px;
    background: color-mix(in srgb, var(--bxw-panel) 88%, transparent); color: var(--bxw-muted);
    font: 11px/1.3 var(--dsw-font-mono, ui-monospace, monospace); pointer-events: none; }
  .bxw-caption b { color: var(--bxw-soft); font-weight: 500; }
  .bxw-empty { position: absolute; inset: 0; display: none; place-items: center; padding: 24px; }
  .bxw-empty[data-on="true"] { display: grid; }
  .bxw-empty-card { max-width: 340px; text-align: center; }
  .bxw-empty-card h2 { margin: 0 0 6px; font-size: 18px; font-weight: 600; }
  .bxw-empty-card p { margin: 0 0 16px; color: var(--bxw-soft); }
  .bxw-spinner { width: 24px; height: 24px; margin: 0 auto 14px; border: 2px solid var(--bxw-line);
    border-top-color: var(--bxw-accent); border-radius: 50%; animation: bxw-spin .7s linear infinite; }
  @keyframes bxw-spin { to { transform: rotate(360deg); } }
  @media (prefers-reduced-motion: reduce) { .bxw-spinner { animation: none; } }
  .bxw-inspector { min-width: 0; border-left: 1px solid var(--bxw-line); background: var(--bxw-panel); overflow: auto; }
  .bxw-inspector[hidden] { display: none; }
  .bxw-inspector-head { position: sticky; top: 0; z-index: 1; display: flex; align-items: center; justify-content: space-between;
    gap: 8px; height: 42px; padding: 0 12px; border-bottom: 1px solid var(--bxw-line); background: var(--bxw-panel); }
  .bxw-inspector-head strong { font-size: 12px; font-weight: 600; letter-spacing: .2px; }
  .bxw-inspector-body { padding: 10px 12px 20px; display: flex; flex-direction: column; gap: 16px; }
  .bxw-section { display: flex; flex-direction: column; gap: 7px; }
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
  .bxw-composer { border-top: 1px solid var(--bxw-line); background: var(--bxw-panel); padding: 10px 14px 12px; }
  .bxw-composer-box { max-width: 980px; margin: 0 auto; display: flex; align-items: flex-end; gap: 8px;
    padding: 7px; border: 1px solid var(--bxw-line); border-radius: 8px; background: var(--bxw-layer); }
  .bxw-composer-box:focus-within { border-color: color-mix(in srgb, var(--bxw-accent) 70%, var(--bxw-line)); }
  .bxw-composer textarea { flex: 1; min-height: 34px; max-height: 120px; resize: none; border: 0; outline: 0;
    background: transparent; padding: 7px 8px; line-height: 1.5; }
  .bxw-composer textarea::placeholder { color: var(--bxw-muted); }
  .bxw-send { height: 34px; padding: 0 14px; border-color: color-mix(in srgb, var(--bxw-accent) 60%, transparent);
    background: color-mix(in srgb, var(--bxw-accent) 16%, transparent); color: var(--bxw-primary, #e8edf5); }
  .bxw-send:hover { background: color-mix(in srgb, var(--bxw-accent) 26%, transparent); }
  .bxw-hint { max-width: 980px; margin: 6px auto 0; color: var(--bxw-muted); font-size: 10px; }
  .bxw-toast { position: fixed; right: 20px; bottom: 92px; z-index: 30; max-width: 360px; padding: 9px 12px;
    border: 1px solid var(--bxw-line); border-radius: 7px; background: var(--bxw-panel); color: var(--bxw-soft);
    box-shadow: 0 10px 28px rgb(0 0 0 / 28%); opacity: 0; transform: translateY(6px); pointer-events: none;
    transition: opacity .16s ease, transform .16s ease; font-size: 12px; }
  .bxw-toast[data-on="true"] { opacity: 1; transform: none; }
  .bxw-toast[data-tone="error"] { border-color: color-mix(in srgb, var(--bxw-bad) 45%, var(--bxw-line)); color: var(--bxw-bad); }
  @media (max-width: 1280px) {
    .bxw-main { grid-template-columns: 210px minmax(0, 1fr) 292px; }
  }
  @media (max-width: 1080px) {
    .bxw-main { grid-template-columns: minmax(0, 1fr); }
    .bxw-models, .bxw-inspector { display: none; }
  }
  @media (max-width: 720px) {
    .bxw-brand span { display: none; }
    .bxw-context select { max-width: 44vw; }
    .bxw-actions .bxw-optional { display: none; }
  }
  @media (prefers-reduced-motion: reduce) {
    .bxw-toast { transition: none; }
  }
`

const svg = (path, size = 16) => `<svg class="bxw-icon" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${path}</svg>`
const ICONS = {
  cube: svg('<path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Z"/><path d="m4 7.5 8 4.5 8-4.5M12 12v9"/>'),
  chat: svg('<path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4v8Z"/>'),
  panel: svg('<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M15 4v16"/>'),
  fit: svg('<path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/>'),
  wire: svg('<path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Z"/><path d="M4 7.5 12 12l8-4.5M12 12v9"/>'),
  refresh: svg('<path d="M20 11a8 8 0 1 0-2.3 5.7"/><path d="M20 4v7h-7"/>'),
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
    try {
      const payload = await response.json()
      if (payload?.error?.message) message = payload.error.message
    } catch (error) { /* status is enough */ }
    throw new Error(message)
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
    inspector: true,
    busy: false,
    tab: 'inspect',
    selection: null,
    agentLog: [],
    agentStatus: '等待指令',
    lastPlanRevision: null,
  }

  const shell = el('div', { className: 'bxw-shell' })
  const header = el('header', { className: 'bxw-header' })
  const brand = el('div', { className: 'bxw-brand' })
  brand.append(el('span', { className: 'bxw-mark', html: ICONS.cube }), el('span', {}, 'BrepX'))
  const context = el('div', { className: 'bxw-context' })
  const contextLabel = el('span', { className: 'bxw-context-label' }, '模型')
  const docSelect = el('select', { 'aria-label': '当前模型' })
  const version = el('span', { className: 'bxw-version' }, '')
  const checkBadge = el('span', { className: 'bxw-badge' }, '检查 —')
  const metricBadge = el('span', { className: 'bxw-badge' }, '—')
  context.append(contextLabel, docSelect, version, checkBadge, metricBadge)
  const actions = el('div', { className: 'bxw-actions' })
  const navButton = el('button', { title: '显示或隐藏宿主导航', 'aria-label': '显示或隐藏宿主导航', className: 'bxw-optional', html: ICONS.panel })
  const modelsButton = el('button', { title: '显示或隐藏模型导航', 'aria-label': '显示或隐藏模型导航', html: ICONS.panel })
  const refreshButton = el('button', { title: '刷新模型状态', 'aria-label': '刷新模型状态', html: ICONS.refresh })
  const inspectorButton = el('button', { title: '显示或隐藏检查器', 'aria-label': '显示或隐藏检查器', html: ICONS.panel })
  const agentButton = el('button', { title: '打开 Agent 线程', 'aria-label': '打开 Agent 线程', html: ICONS.chat + '<span>Agent</span>' })
  actions.append(navButton, modelsButton, refreshButton, inspectorButton, agentButton)
  header.append(brand, context, actions)

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
  const caption = el('div', { className: 'bxw-caption' })
  const captionFaces = el('span', {}, '—')
  const captionVolume = el('span', {}, '—')
  const captionTight = el('span', {}, '—')
  caption.append(captionFaces, captionVolume, captionTight)
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
  stage.append(frame, tools, caption, empty)

  const models = el('aside', { className: 'bxw-models', 'aria-label': '模型与项目导航' })
  const modelsHead = el('div', { className: 'bxw-models-head' })
  const modelsTitle = el('strong', {}, '模型')
  const modelsNew = el('button', { type: 'button', title: '新建模型', 'aria-label': '新建模型', html: ICONS.plus })
  modelsHead.append(modelsTitle, modelsNew)
  const modelsSearch = el('input', { className: 'bxw-models-search', placeholder: '搜索模型…', 'aria-label': '搜索模型' })
  const modelList = el('div', { className: 'bxw-model-list' })
  models.append(modelsHead, modelsSearch, modelList)

  const inspector = el('aside', { className: 'bxw-inspector', 'aria-label': '模型检查器' })
  const inspectorHead = el('div', { className: 'bxw-inspector-head' })
  const inspectorTabs = el('div', { className: 'bxw-inspector-tabs', role: 'tablist', 'aria-label': '检查器视图' })
  const inspectTab = el('button', { type: 'button', role: 'tab', 'aria-selected': 'true' }, '检查')
  const agentTab = el('button', { type: 'button', role: 'tab', 'aria-selected': 'false' }, 'Agent')
  inspectorTabs.append(inspectTab, agentTab)
  const inspectorClose = el('button', { type: 'button', title: '收起检查器', 'aria-label': '收起检查器', html: ICONS.close })
  inspectorClose.addEventListener('click', () => setInspector(false))
  inspectorHead.append(inspectorTabs, inspectorClose)

  const inspectorBody = el('div', { className: 'bxw-inspector-body' })
  const inspectPane = el('div', { className: 'bxw-pane', role: 'tabpanel' })
  const agentPane = el('div', { className: 'bxw-pane', role: 'tabpanel', hidden: true })

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

  const planSection = el('section', { className: 'bxw-section' })
  const planHead = el('h3', {}, '计划卡')
  const planList = el('div', { className: 'bxw-list' })
  planSection.append(planHead, planList)

  const checkSection = el('section', { className: 'bxw-section' })
  checkSection.append(el('h3', {}, '检查'))
  const checkSummary = el('div', { className: 'bxw-check' }, '—')
  const checkList = el('ul', { className: 'bxw-list' })
  checkSection.append(checkSummary, checkList)

  const agentSection = el('section', { className: 'bxw-section' })
  const agentSectionHead = el('div', { className: 'bxw-section-head' })
  agentSectionHead.append(el('h3', {}, 'Agent 线程'))
  const agentStatus = el('span', { className: 'bxw-check' }, '等待指令')
  agentSectionHead.append(agentStatus)
  agentSection.append(agentSectionHead)
  const agentList = el('div', { className: 'bxw-thread' })
  agentSection.append(agentList)

  inspectPane.append(metricsSection, selectionSection, planSection, checkSection)
  agentPane.append(agentSection)
  inspectorBody.append(inspectPane, agentPane)
  inspector.append(inspectorHead, inspectorBody)

  const composer = el('form', { className: 'bxw-composer' })
  const selectionBar = el('div', { className: 'bxw-selection', hidden: true })
  const composerBox = el('div', { className: 'bxw-composer-box' })
  const input = el('textarea', {
    rows: 1,
    placeholder: '输入命令，或描述设计变更… 例如 /fit、/checks、把中心孔改为 Ø40',
    'aria-label': '命令或设计意图',
  })
  const send = el('button', { type: 'submit', className: 'bxw-send', 'aria-label': '执行或发送给 Agent', html: ICONS.send + '<span>执行</span>' })
  composerBox.append(input, send)
  const hint = el('div', { className: 'bxw-hint' }, '/fit /top /front /checks /agent /new   ·   Enter 执行 · Shift+Enter 换行')
  composer.append(selectionBar, composerBox, hint)

  const toastNode = el('div', { className: 'bxw-toast', role: 'status' })
  shell.append(header, main, composer, toastNode)
  main.append(models, stage, inspector)
  host.append(shell)

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
    }
  }

  const setInspector = (on) => {
    state.inspector = Boolean(on)
    inspector.hidden = !state.inspector
    inspectorButton.setAttribute('aria-pressed', state.inspector ? 'true' : 'false')
  }

  const setTab = (tab) => {
    state.tab = tab === 'agent' ? 'agent' : 'inspect'
    inspectTab.setAttribute('aria-selected', state.tab === 'inspect' ? 'true' : 'false')
    agentTab.setAttribute('aria-selected', state.tab === 'agent' ? 'true' : 'false')
    inspectPane.hidden = state.tab !== 'inspect'
    agentPane.hidden = state.tab !== 'agent'
    setInspector(true)
    if (state.tab === 'agent') renderAgent()
  }

  const formatSelection = (pick) => {
    if (!pick?.point) return ''
    const point = pick.point.map((value) => Number(value).toFixed(2)).join(', ')
    const area = pick.area != null ? ` · ${Number(pick.area).toFixed(1)} mm²` : ''
    const face = Number.isInteger(pick.face_index) ? ` · 面 ${pick.face_index}` : ''
    return `选中 @(${point})${area}${face}`
  }

  const renderSelection = () => {
    selectionBar.textContent = ''
    if (!state.selection) {
      selectionBar.hidden = true
      selectionSummary.textContent = '在画布上点选面或边'
      return
    }
    const label = formatSelection(state.selection)
    selectionBar.hidden = false
    const chip = el('span', { className: 'bxw-selection-chip' })
    chip.append(el('span', {}, label))
    const clear = el('button', { type: 'button', title: '清除选择', 'aria-label': '清除选择', html: ICONS.close })
    clear.addEventListener('click', () => { state.selection = null; renderSelection() })
    chip.append(clear)
    selectionBar.append(el('span', {}, '上下文'), chip)
    selectionSummary.textContent = label
  }

  const agentStorageKey = () => `cadview.thread.${state.sessionId || 'local'}`
  const loadAgentLog = () => {
    try {
      const raw = JSON.parse(localStorage.getItem(agentStorageKey()) || '[]')
      state.agentLog = Array.isArray(raw) ? raw.slice(-40) : []
    } catch (error) {
      state.agentLog = []
    }
  }
  const saveAgentLog = () => {
    try { localStorage.setItem(agentStorageKey(), JSON.stringify(state.agentLog.slice(-40))) } catch (error) { /* private mode */ }
  }
  const pushAgent = (role, text) => {
    const last = state.agentLog[state.agentLog.length - 1]
    if (last && last.role === role && last.text === text) return
    state.agentLog.push({ role, text, at: Date.now() })
    state.agentLog = state.agentLog.slice(-40)
    saveAgentLog()
    renderAgent()
  }
  const renderAgent = () => {
    if (!agentList) return
    if (agentStatus) agentStatus.textContent = state.agentStatus || '等待指令'
    agentList.textContent = ''
    if (!state.agentLog.length) {
      agentList.append(el('div', { className: 'bxw-thread-item' }, '发送意图后，计划卡和执行结果会出现在这里。'))
      return
    }
    const entries = state.agentLog.filter((entry, index, list) =>
      index === 0 || entry.role !== list[index - 1].role || entry.text !== list[index - 1].text)
    for (const entry of entries.slice(-20)) {
      const item = el('div', { className: 'bxw-thread-item' })
      item.dataset.role = entry.role || 'system'
      const label = entry.role === 'user' ? '你' : entry.role === 'agent' ? 'Agent' : '工作台'
      item.append(el('b', {}, label), el('p', {}, entry.text || ''))
      agentList.append(item)
    }
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
      await loadDocument(doc.id, true)
      toast('已创建空白模型')
    } catch (error) {
      toast(`新建模型失败：${error.message}`, 'error', 6)
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
      case 'checks': setTab('inspect'); return true
      case 'agent': setTab('agent'); return true
      case 'models': shell.dataset.models = shell.dataset.models === 'off' ? 'on' : 'off'; return true
      case 'new': createModel(); return true
      case 'refresh': loadDocument(state.docId, true).catch((error) => toast(error.message, 'error')); return true
      case 'export':
        if (!state.docId) return true
        window.open(`${base}/api/docs/${state.docId}/export/${arg || 'step'}`, '_blank', 'noopener')
        return true
      case 'help':
        setTab('agent')
        pushAgent('system', '本地命令：/fit /iso /top /front /right /wire /checks /agent /models /new /refresh /export，其他文本交给 Agent。')
        return true
      default:
        toast(`未知命令：/${name}`, 'error', 4)
        return true
    }
  }

  inspectorButton.addEventListener('click', () => setInspector(!state.inspector))
  inspectTab.addEventListener('click', () => setTab('inspect'))
  agentTab.addEventListener('click', () => setTab('agent'))
  agentButton.addEventListener('click', () => setTab('agent'))
  modelsButton.addEventListener('click', () => {
    shell.dataset.models = shell.dataset.models === 'off' ? 'on' : 'off'
    modelsButton.setAttribute('aria-pressed', shell.dataset.models === 'off' ? 'false' : 'true')
  })
  modelsNew.addEventListener('click', createModel)
  navButton.addEventListener('click', () => options.onToggleNavigation?.())
  refreshButton.addEventListener('click', () => loadDocument(state.docId, true).catch((error) => toast(error.message, 'error')))

  const post = (type, payload) => {
    try {
      frame.contentWindow?.postMessage({ from: 'brepx-workbench', type, ...payload }, '*')
    } catch (error) { /* frame may be between navigations */ }
  }

  const pushDesign = (fit = false) => {
    if (!state.current || !state.ready) return
    post('theme', readTheme())
    post('design', {
      documentId: state.docId,
      version: state.version,
      requestId: ++state.request,
      prefetch: null,
      fit,
    })
  }

  const renderDocuments = () => {
    docSelect.textContent = ''
    modelList.textContent = ''
    if (!state.documents.length) {
      docSelect.append(el('option', { value: '' }, '没有模型'))
      docSelect.disabled = true
      modelList.append(el('div', { className: 'bxw-check' }, '还没有模型'))
      return
    }
    docSelect.disabled = false
    const query = modelsSearch.value.trim().toLowerCase()
    const visible = state.documents.filter((doc) =>
      !query || `${doc.name || ''} ${doc.id}`.toLowerCase().includes(query))
    for (const doc of state.documents) {
      docSelect.append(el('option', { value: doc.id }, `${doc.name || doc.id} · v${doc.version ?? 0}`))
    }
    if (state.docId) docSelect.value = state.docId
    for (const doc of visible) {
      const row = el('button', {
        type: 'button',
        className: 'bxw-model-row',
        title: doc.name || doc.id,
      })
      row.dataset.active = doc.id === state.docId ? 'true' : 'false'
      row.append(el('b', {}, doc.name || doc.id), el('span', {}, `v${doc.version ?? 0} · ${doc.id}`))
      row.addEventListener('click', () => {
        docSelect.value = doc.id
        loadDocument(doc.id, true).catch((error) => toast(`加载模型失败：${error.message}`, 'error', 6))
      })
      modelList.append(row)
    }
    if (!visible.length) modelList.append(el('div', { className: 'bxw-check' }, '没有匹配的模型'))
    modelList.scrollTop = 0
  }
  modelsSearch.addEventListener('input', renderDocuments)

  const renderPlan = () => {
    planList.textContent = ''
    const nodes = state.plan?.plan?.nodes || []
    if (!nodes.length) {
      planList.append(el('div', { className: 'bxw-check' }, '暂无计划'))
      return
    }
    for (const node of nodes.slice(-8).reverse()) {
      const card = el('div', { className: 'bxw-plan-card' })
      const head = el('div', { className: 'bxw-plan-card-head' })
      const dot = el('span', { className: 'bxw-dot' })
      dot.dataset.state = node.status || 'pending'
      head.append(dot, el('b', {}, node.title || node.id))
      const params = Object.entries(node.params || {}).slice(0, 3)
        .map(([key, value]) => `${key}=${typeof value === 'number' ? Number(value.toFixed(3)) : value}`)
        .join(' · ')
      card.append(head, el('div', { className: 'bxw-plan-card-meta' }, `${node.action || node.kind} · ${node.id}${params ? ` · ${params}` : ''}`))
      if (node.error) card.append(el('div', { className: 'bxw-check' }, node.error))
      planList.append(card)
    }
  }

  const renderChecks = () => {
    checkList.textContent = ''
    const checks = state.checks
    if (!checks) {
      checkSummary.textContent = '暂无检查'
      checkSummary.dataset.ok = 'true'
      return
    }
    checkSummary.textContent = `${checks.passed}/${checks.total} 通过`
    checkSummary.dataset.ok = checks.ok ? 'true' : 'false'
    for (const item of (checks.items || []).slice(0, 8)) {
      const row = el('li', { className: 'bxw-row' })
      const dot = el('span', { className: 'bxw-dot' })
      dot.dataset.state = item.ok ? 'done' : 'failed'
      const text = el('div', { className: 'bxw-row-main' })
      text.append(el('b', {}, `${item.feature_id || 'model'} · ${item.name}`), el('span', {}, item.expected || ''))
      row.append(dot, text)
      row.title = item.hint || item.expected || ''
      checkList.append(row)
    }
    if ((checks.items || []).length > 8) {
      checkList.append(el('li', { className: 'bxw-row bxw-check' }, `还有 ${checks.items.length - 8} 条检查`))
    }
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
    captionVolume.textContent = `${fmt(metrics.volume, 0)} mm³`
    captionTight.textContent = metrics.watertight ? '水密' : '非水密'
    empty.dataset.on = state.current.vacant ? 'true' : 'false'
    state.version = doc.version ?? 0
    renderPlan()
    renderChecks()
    const revision = state.plan?.plan?.revision
    if (revision != null && revision !== state.lastPlanRevision) {
      state.lastPlanRevision = revision
      if (state.agentLog.length) {
        const nodes = state.plan?.plan?.nodes || []
        const done = nodes.filter((node) => node.status === 'done').length
        pushAgent('agent', `计划 rev ${revision}：${done}/${nodes.length} 节点完成，检查 ${checks?.passed ?? '—'}/${checks?.total ?? '—'}。`)
      }
    }
    pushDesign(false)
  }

  const loadDocument = async (docId, force = false) => {
    if (!docId) {
      state.current = null
      state.plan = null
      state.checks = null
      empty.dataset.on = 'true'
      return
    }
    if (docId === state.docId && state.current && !force) return
    const changedDocument = state.docId !== docId
    state.docId = docId
    state.current = null
    state.selection = null
    if (changedDocument) state.lastPlanRevision = null
    renderSelection()
    setLoading(true)
    try {
      const [stateView, plan, checks] = await Promise.all([
        api(`${base}/api/docs/${docId}/state`),
        api(`${base}/api/docs/${docId}/plan`).catch(() => null),
        api(`${base}/api/docs/${docId}/checks`).catch(() => null),
      ])
      state.current = stateView
      state.plan = plan
      state.checks = checks
      state.version = stateView.document.version
      empty.dataset.on = stateView.vacant ? 'true' : 'false'
      emptySpinner.hidden = true
      if (stateView.vacant) {
        emptyTitle.textContent = '空白模型'
        emptyBody.textContent = '在下方描述要创建的零件，或选择另一个已有模型。'
        emptyButton.hidden = false
      }
      renderState()
      const sessionId = state.sessionId || options.getSessionId?.()
      if (sessionId) {
        state.sessionId = sessionId
        try { localStorage.setItem(`cadview.document.${sessionId}`, docId) } catch (error) { /* private mode */ }
      }
    } catch (error) {
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

  const chooseDocument = async () => {
    state.documents = await api(`${base}/api/docs`)
    const stored = state.sessionId ? localStorage.getItem(`cadview.document.${state.sessionId}`) : null
    const preferred = [options.documentId, stored, state.docId, ...state.documents.map((doc) => doc.id)]
      .find((id) => id && state.documents.some((doc) => doc.id === id))
    state.docId = preferred || state.documents[0]?.id || null
    renderDocuments()
    if (state.docId) await loadDocument(state.docId, true)
    else empty.dataset.on = 'true'
  }

  docSelect.addEventListener('change', () => {
    if (!docSelect.value) return
    loadDocument(docSelect.value, true).catch(() => {})
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
    const selected = state.selection ? `[${formatSelection(state.selection)}] ` : ''
    const message = selected + text
    state.busy = true
    send.disabled = true
    state.agentStatus = '已提交，等待计划更新…'
    renderAgent()
    try {
      await api(`${base}/api/docs/${state.docId}/intents`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: message }),
      })
      const sessionId = state.sessionId || options.getSessionId?.()
      if (!sessionId) throw new Error('没有活动会话；请先选择一个会话')
      await options.sendPrompt?.(sessionId, message)
      pushAgent('user', message)
      pushAgent('system', '已提交给 Agent，等待计划卡更新。')
      input.value = ''
      resizeInput()
      toast('已提交给 Agent')
      const target = state.docId
      setTimeout(() => {
        if (state.docId !== target) return
        loadDocument(target, true)
          .then(() => { state.agentStatus = '计划已同步'; renderAgent() })
          .catch(() => {})
      }, 2500)
    } catch (error) {
      state.agentStatus = '发送失败'
      renderAgent()
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
    }
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
    } else if (data.type === 'pick' && data.pick) {
      state.selection = data.pick
      renderSelection()
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

  setInspector(true)
  shell.dataset.models = 'on'
  modelsButton.setAttribute('aria-pressed', 'true')
  loadAgentLog()
  renderSelection()
  renderAgent()
  options.onFocus?.()
  chooseDocument().catch((error) => toast(`无法加载模型库：${error.message}`, 'error', 8))

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
      clearTimeout(toastTimer)
      observer.disconnect()
      document.body.classList.remove('bxw-workbench')
      window.removeEventListener('message', onMessage)
      document.removeEventListener('keydown', onGlobalKey)
      shell.remove()
    },
    setSession(sessionId) {
      if (!sessionId || sessionId === state.sessionId) return
      state.sessionId = sessionId
      loadAgentLog()
      renderAgent()
      const stored = localStorage.getItem(`cadview.document.${sessionId}`)
      if (stored) {
        loadDocument(stored, true).catch(() => {})
      } else if (state.docId) {
        try { localStorage.setItem(`cadview.document.${sessionId}`, state.docId) } catch (error) { /* private mode */ }
      }
    },
  }
}
