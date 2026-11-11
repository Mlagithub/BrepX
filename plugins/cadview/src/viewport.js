/**
 * BrepX canvas: a full-bleed model view with a floating dock, a visual diff
 * layer and one bottom hub that carries the intent, the milestone chain and the
 * focus sliders. Nothing here invents state: every version fact comes from the
 * engine's state projection or its event stream.
 */
const STYLE_ID = 'brepx-style'

const style = () => {
  if (document.getElementById(STYLE_ID)) return
  const tag = document.createElement('style')
  tag.id = STYLE_ID
  tag.textContent = `
    .bx-root{
      --bx-bg: var(--dsw-alias-bg-base, #0b0e13);
      --bx-panel: var(--dsw-alias-bg-layer-1, #11151c);
      --bx-panel-2: var(--dsw-alias-bg-layer-2, #151a23);
      --bx-line: var(--dsw-alias-border-l2, #232d3d);
      --bx-fg: var(--dsw-alias-label-primary, #e8eef8);
      --bx-fg-2: var(--dsw-alias-label-secondary, #a9b7ca);
      --bx-fg-3: var(--dsw-alias-label-tertiary, #6d7d94);
      --bx-accent: var(--dsw-alias-state-business-primary, #4c9aff);
      --bx-ok: var(--dsw-alias-state-success-primary, #3ecf8e);
      --bx-warn: var(--dsw-alias-state-warn-primary, #ffb454);
      --bx-bad: var(--dsw-alias-state-error-primary, #ff5f7e);
      --bx-r-sm: var(--dsw-radius-sm, 6px);
      --bx-r-md: var(--dsw-radius-md, 9px);
      --bx-font: var(--dsw-font-family, system-ui, sans-serif);
      --bx-mono: ui-monospace, "Cascadia Mono", Consolas, monospace;
      position: relative; display: flex; flex-direction: column; height: 100%; min-height: 0;
      background: var(--bx-bg); color: var(--bx-fg); font: 12px/1.5 var(--bx-font); overflow: hidden
    }
    .bx-root button{font:inherit;color:var(--bx-fg-2);background:var(--bx-panel-2);
      border:1px solid var(--bx-line);border-radius:var(--bx-r-sm);height:26px;padding:0 9px;
      cursor:pointer;transition:background .12s,border-color .12s,color .12s;white-space:nowrap}
    .bx-root button:hover{background:var(--bx-panel);border-color:var(--bx-accent);color:var(--bx-fg)}
    .bx-root button:disabled{opacity:.42;cursor:not-allowed}
    .bx-root button.on{border-color:var(--bx-accent);color:var(--bx-fg);
      background:color-mix(in srgb, var(--bx-accent) 16%, transparent)}
    .bx-root button.primary{background:var(--bx-accent);border-color:transparent;color:#08131f;font-weight:600}
    .bx-root select,.bx-root input,.bx-root textarea{font:inherit;color:var(--bx-fg);
      background:var(--bx-bg);border:1px solid var(--bx-line);border-radius:var(--bx-r-sm);height:26px;
      padding:0 7px}
    .bx-root textarea{height:auto;padding:6px 7px;resize:none}
    .bx-root select:focus,.bx-root input:focus,.bx-root textarea:focus{outline:none;border-color:var(--bx-accent)}

    .bx-top{display:flex;align-items:center;gap:9px;padding:5px 10px;background:var(--bx-panel);
      border-bottom:1px solid var(--bx-line);flex:0 0 auto;min-height:32px}
    .bx-brand{font-weight:650;letter-spacing:.05em}
    .bx-doc{color:var(--bx-fg-3);font:11px/1 var(--bx-mono);white-space:nowrap;overflow:hidden;
      text-overflow:ellipsis;max-width:190px}
    .bx-badge{font:10px/16px var(--bx-mono);height:16px;padding:0 6px;border-radius:999px;
      border:1px solid var(--bx-line);color:var(--bx-fg-3)}
    .bx-badge.ok{color:var(--bx-ok);border-color:color-mix(in srgb, var(--bx-ok) 45%, transparent)}
    .bx-badge.bad{color:var(--bx-bad);border-color:color-mix(in srgb, var(--bx-bad) 45%, transparent)}
    .bx-metric{color:var(--bx-fg-3);font:11px/1 var(--bx-mono);margin-left:auto;white-space:nowrap}

    .bx-stage{position:relative;flex:1;min-height:0;background:var(--bx-bg)}
    .bx-stage iframe{position:absolute;inset:0;width:100%;height:100%;border:0;display:block}

    .bx-dock{position:absolute;top:8px;right:8px;z-index:12;display:flex;flex-wrap:wrap;
      gap:4px;justify-content:flex-end;max-width:calc(100% - 24px);pointer-events:none}
    .bx-dock > *{pointer-events:auto}
    .bx-dock .group{display:flex;gap:3px;padding:3px;border-radius:var(--bx-r-md);
      background:color-mix(in srgb, var(--bx-panel) 88%, transparent);border:1px solid var(--bx-line);
      backdrop-filter:blur(8px)}
    .bx-dock .group button{height:24px;padding:0 7px;font-size:11px;background:transparent;border-color:transparent}
    .bx-dock .group button:hover{background:var(--bx-panel-2);border-color:var(--bx-line)}
    .bx-dock .group button.on{background:color-mix(in srgb, var(--bx-accent) 22%, transparent);border-color:var(--bx-accent)}

    .bx-section{position:absolute;top:44px;right:8px;z-index:12;display:none;align-items:center;gap:6px;
      padding:4px 7px;border-radius:var(--bx-r-md);background:color-mix(in srgb, var(--bx-panel) 92%, transparent);
      border:1px solid var(--bx-line);backdrop-filter:blur(8px)}
    .bx-section.on{display:flex}
    .bx-section input[type=range]{width:110px;height:20px;padding:0;border:0;background:transparent;
      accent-color:var(--bx-accent)}

    .bx-vacant{position:absolute;inset:0;z-index:10;display:none;align-items:center;justify-content:center;
      flex-direction:column;gap:12px;pointer-events:none;
      color:var(--bx-fg-3);text-align:center;padding:24px}
    .bx-vacant.on{display:flex}
    .bx-vacant-card{pointer-events:auto;display:flex;flex-direction:column;align-items:center;gap:10px;
      padding:18px 22px;border-radius:var(--bx-r-md);border:1px solid var(--bx-line);
      background:color-mix(in srgb, var(--bx-panel) 84%, transparent);backdrop-filter:blur(8px)}
    .bx-vacant strong{font-size:15px;color:var(--bx-fg);font-weight:600}
    .bx-vacant p{margin:0;max-width:420px;line-height:1.7}
    .bx-vacant .row{display:flex;gap:8px;flex-wrap:wrap;justify-content:center}

    .bx-replay{position:absolute;top:8px;left:8px;z-index:13;display:none;align-items:center;gap:8px;
      padding:4px 8px;border-radius:var(--bx-r-md);background:color-mix(in srgb, var(--bx-warn) 18%, var(--bx-panel));
      border:1px solid color-mix(in srgb, var(--bx-warn) 55%, transparent);color:var(--bx-fg);font-size:11px}
    .bx-replay.on{display:flex}

    .bx-hub{position:absolute;left:50%;bottom:10px;transform:translateX(-50%);z-index:14;
      display:flex;flex-direction:column;gap:6px;width:min(820px, calc(100% - 18px));pointer-events:none}
    .bx-hub > *{pointer-events:auto}
    .bx-row{display:flex;align-items:center;gap:6px;padding:5px 8px;border-radius:var(--bx-r-md);
      border:1px solid var(--bx-line);background:color-mix(in srgb, var(--bx-panel) 93%, transparent);
      backdrop-filter:blur(9px);flex-wrap:wrap}
    .bx-banner{display:none;border-color:color-mix(in srgb, var(--bx-bad) 55%, transparent);
      background:color-mix(in srgb, var(--bx-bad) 14%, var(--bx-panel));color:var(--bx-fg);font-size:11px}
    .bx-banner.on{display:flex}
    .bx-banner .grow{flex:1;min-width:120px}
    .bx-stepper{overflow-x:auto;scrollbar-width:thin}
    .bx-chip{height:24px;padding:0 8px;border-radius:999px;border:1px solid var(--bx-line);
      background:var(--bx-bg);color:var(--bx-fg-2);font:11px/1 var(--bx-mono);cursor:pointer;
      display:inline-flex;align-items:center;gap:6px;white-space:nowrap}
    .bx-chip:hover{border-color:var(--bx-accent);color:var(--bx-fg)}
    .bx-chip.current{border-color:var(--bx-accent);color:var(--bx-fg);
      background:color-mix(in srgb, var(--bx-accent) 16%, transparent)}
    .bx-chip.viewing{border-color:var(--bx-warn);color:var(--bx-fg);
      background:color-mix(in srgb, var(--bx-warn) 16%, transparent)}
    .bx-chip .meta{color:var(--bx-fg-3);font-size:10px}
    .bx-chip .actor{width:5px;height:5px;border-radius:50%;background:var(--bx-fg-3)}
    .bx-chip .actor.agent{background:var(--bx-accent)}
    .bx-chip .actor.human{background:var(--bx-ok)}
    .bx-mutes{gap:5px;font-size:11px;color:var(--bx-fg-3)}
    .bx-mute{display:inline-flex;align-items:center;gap:5px;border:1px solid var(--bx-line);
      border-radius:999px;padding:1px 7px;background:var(--bx-bg);cursor:pointer;font-size:11px;
      color:var(--bx-fg-2)}
    .bx-mute:hover{border-color:var(--bx-accent)}
    .bx-mute.off{opacity:.55;text-decoration:line-through}
    .bx-mute.locked{cursor:not-allowed;opacity:.4;text-decoration:none}

    .bx-card{display:none;flex-direction:column;gap:6px;padding:7px 9px;border-radius:var(--bx-r-md);
      border:1px solid var(--bx-line);background:color-mix(in srgb, var(--bx-panel) 93%, transparent);
      backdrop-filter:blur(9px)}
    .bx-card.on{display:flex}
    .bx-card-head{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}
    .bx-card-title{font-weight:600;color:var(--bx-fg)}
    .bx-card-delta{color:var(--bx-fg-3);font:11px/1.4 var(--bx-mono);margin-left:auto}
    .bx-focus{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center}
    .bx-focus label{display:flex;align-items:center;gap:6px;color:var(--bx-fg-3);font-size:11px;
      padding:2px 6px;border-radius:var(--bx-r-sm);background:color-mix(in srgb, var(--bx-bg) 70%, transparent)}
    .bx-focus input[type=range]{width:92px;height:20px;padding:0;border:0;background:transparent;
      accent-color:var(--bx-accent)}
    .bx-focus input[type=number]{width:64px;height:22px;font:11px/1 var(--bx-mono)}
    .bx-focus b{font:11px/1 var(--bx-mono);color:var(--bx-fg);min-width:40px;text-align:right}
    .bx-focus .unit{color:var(--bx-fg-3);font-size:10px}

    .bx-variants{display:none;gap:8px;overflow-x:auto;padding:7px 9px;border-radius:var(--bx-r-md);
      border:1px solid var(--bx-line);background:color-mix(in srgb, var(--bx-panel) 94%, transparent);
      align-items:stretch}
    .bx-variants.on{display:flex}
    .bx-variant{min-width:148px;max-width:176px;display:flex;flex-direction:column;gap:5px;align-items:stretch;
      padding:6px 8px;border-radius:var(--bx-r-sm);border:1px solid var(--bx-line);background:var(--bx-bg);
      color:var(--bx-fg-2);font-size:11px;overflow:hidden}
    .bx-variant.selected{border-color:var(--bx-accent);
      background:color-mix(in srgb, var(--bx-accent) 10%, var(--bx-bg))}
    .bx-variant img{display:block;width:100%;height:68px;object-fit:contain;border-radius:4px;
      background:var(--bx-panel-2)}
    .bx-root button.bx-variant-preview{display:flex;flex-direction:column;gap:3px;align-items:flex-start;
      width:100%;height:auto;padding:0;border:0;background:transparent;text-align:left;white-space:normal}
    .bx-root button.bx-variant-preview:hover{background:transparent;border-color:transparent}
    .bx-variant b{color:var(--bx-fg);font-weight:600;font-size:11px}
    .bx-variant span{font:10px/1.4 var(--bx-mono);color:var(--bx-fg-3)}
    .bx-variant-actions{display:flex;gap:4px;margin-top:auto}
    .bx-root .bx-variant-actions button{height:22px;padding:0 8px;font-size:10px;flex:1}

    .bx-composer{display:flex;flex-direction:column;gap:5px;padding:6px 8px;border-radius:var(--bx-r-md);
      border:1px solid var(--bx-line);background:color-mix(in srgb, var(--bx-panel) 95%, transparent);
      backdrop-filter:blur(10px)}
    .bx-pills{display:flex;flex-wrap:wrap;gap:4px}
    .bx-pill{display:inline-flex;align-items:center;gap:5px;height:20px;padding:0 6px;border-radius:999px;
      border:1px solid color-mix(in srgb, var(--bx-accent) 45%, transparent);color:var(--bx-fg);
      background:color-mix(in srgb, var(--bx-accent) 12%, transparent);font:10px/1 var(--bx-mono)}
    .bx-pill button{height:14px;padding:0 3px;border:0;background:transparent;color:var(--bx-fg-3);font-size:10px}
    .bx-pill button:hover{color:var(--bx-bad);background:transparent}
    .bx-inputrow{display:flex;gap:6px;align-items:flex-end}
    .bx-inputrow textarea{flex:1;min-height:34px;max-height:96px;line-height:1.5}
    .bx-hint{color:var(--bx-fg-3);font:10px/1.4 var(--bx-mono)}
    .bx-intent{display:none;align-items:center;gap:6px;font-size:11px;color:var(--bx-fg-3)}
    .bx-intent.on{display:flex}
    .bx-intent .steps{display:flex;gap:5px;flex-wrap:wrap}
    .bx-step{padding:0 6px;height:18px;border-radius:999px;border:1px solid var(--bx-line);
      font:10px/18px var(--bx-mono);color:var(--bx-fg-3)}
    .bx-step.done{color:var(--bx-ok);border-color:color-mix(in srgb, var(--bx-ok) 40%, transparent)}
    .bx-step.running{color:var(--bx-fg);border-color:var(--bx-accent)}
    .bx-step.skipped{text-decoration:line-through}
  `
  document.head.appendChild(tag)
}

const fetchJSON = async (url, options) => {
  const response = await fetch(url, options)
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`
    let code = null
    let hint = null
    try {
      const payload = await response.json()
      if (payload?.error?.message) message = payload.error.message
      if (payload?.error?.code) code = payload.error.code
      if (payload?.error?.hint) hint = payload.error.hint
    } catch (error) {
      /* the status line is enough */
    }
    const err = new Error(hint ? `${message}（${hint}）` : message)
    err.status = response.status
    err.code = code
    err.hint = hint
    throw err
  }
  return response.json()
}

const el = (tag, className, text) => {
  const node = document.createElement(tag)
  if (className) node.className = className
  if (text != null) node.textContent = text
  return node
}

const num = (value, digits = 0) => {
  if (value == null || Number.isNaN(Number(value))) return '—'
  return Number(value).toLocaleString(undefined, {
    minimumFractionDigits: digits, maximumFractionDigits: digits,
  })
}

export function mountViewport(host, base) {
  style()
  host.textContent = ''

  const root = el('div', 'bx-root')

  // ---------------------------------------------------------------- header
  const head = el('div', 'bx-top')
  const brand = el('span', 'bx-brand', 'BrepX')
  const docLabel = el('span', 'bx-doc', '连接中…')
  const checkBadge = el('span', 'bx-badge', 'checks —')
  const metricText = el('span', 'bx-metric', '')
  head.append(brand, docLabel, checkBadge, metricText)
  root.append(head)

  // ---------------------------------------------------------------- stage
  const stage = el('div', 'bx-stage')
  const frame = el('iframe')
  frame.title = 'BrepX 模型'
  frame.src = `${base}/api/kernel-view`
  stage.append(frame)

  const dock = el('div', 'bx-dock')
  const viewGroup = el('div', 'group')
  const wireButton = el('button', null, '线框')
  const measureButton = el('button', null, '测量')
  const ghostButton = el('button', null, '残影')
  const deltaButton = el('button', null, '差异')
  const sectionButton = el('button', null, '剖切')
  for (const [name, label] of [['iso', '等轴'], ['front', '前'], ['top', '顶'], ['right', '右']]) {
    const button = el('button', null, label)
    button.addEventListener('click', () => post('view', { name }))
    viewGroup.append(button)
  }
  const fitButton = el('button', null, '适配')
  fitButton.addEventListener('click', () => post('fit', {}))
  viewGroup.append(fitButton, wireButton, measureButton, ghostButton, deltaButton, sectionButton)

  const exportGroup = el('div', 'group')
  const exportLinks = {}
  for (const [fmt, label] of [['step', 'STEP'], ['stl', 'STL'], ['cfd', 'CFD']]) {
    const node = el('button', null, label)
    node.title = `导出 ${label}`
    node.addEventListener('click', () => {
      if (!currentDoc) return
      const link = document.createElement('a')
      link.href = `${base}/api/docs/${currentDoc.document.id}/export/${fmt}`
      link.rel = 'noopener'
      document.body.append(link)
      link.click()
      link.remove()
    })
    exportLinks[fmt] = node
    exportGroup.append(node)
  }
  dock.append(viewGroup, exportGroup)
  stage.append(dock)

  const sectionBar = el('div', 'bx-section')
  const sectionAxis = el('select')
  for (const axis of ['X', 'Y', 'Z']) {
    const option = el('option', null, `${axis} 剖切`)
    option.value = axis
    sectionAxis.append(option)
  }
  sectionAxis.value = 'Z'
  const sectionRange = el('input')
  sectionRange.type = 'range'
  sectionRange.min = '0'
  sectionRange.max = '1'
  sectionRange.step = '0.01'
  sectionRange.value = '0.5'
  sectionRange.setAttribute('aria-label', '剖切位置')
  sectionBar.append(sectionAxis, sectionRange)
  stage.append(sectionBar)

  const vacant = el('div', 'bx-vacant')
  const vacantCard = el('div', 'bx-vacant-card')
  const vacantTitle = el('strong', null, '空白文档')
  const vacantBody = el('p', null, '直接描述你要的零件，Agent 会先拆解里程碑，再逐步生成几何。')
  const vacantRow = el('div', 'row')
  const sampleButton = el('button', 'primary', '载入叶轮样例')
  sampleButton.addEventListener('click', () => loadSample('impeller'))
  const scrollHint = el('span', 'bx-hint', '也可以在底部输入框直接向 Agent 描述需求')
  vacantRow.append(sampleButton)
  vacantCard.append(vacantTitle, vacantBody, vacantRow, scrollHint)
  vacant.append(vacantCard)
  stage.append(vacant)

  const replayBar = el('div', 'bx-replay')
  const replayText = el('span', null, '')
  const replayBack = el('button', null, '回到最新')
  replayBar.append(replayText, replayBack)
  stage.append(replayBar)

  // ---------------------------------------------------------------- hub
  const hub = el('div', 'bx-hub')
  const banner = el('div', 'bx-row bx-banner')
  const bannerText = el('span', 'grow', '')
  const bannerClose = el('button', null, '×')
  banner.append(bannerText, bannerClose)
  const stepper = el('div', 'bx-row bx-stepper')
  const mutes = el('div', 'bx-row bx-mutes')
  const card = el('div', 'bx-card')
  const variants = el('div', 'bx-variants')
  const composer = el('form', 'bx-composer')
  const pills = el('div', 'bx-pills')
  const intentBar = el('div', 'bx-intent')
  const inputRow = el('div', 'bx-inputrow')
  const prompt = el('textarea')
  prompt.placeholder = '描述要做的改动；拾取的面会作为上下文挂在前面'
  prompt.rows = 1
  prompt.setAttribute('aria-label', '设计意图')
  const sendButton = el('button', 'primary', '发送')
  sendButton.type = 'submit'
  const stopButton = el('button', null, '停止')
  stopButton.type = 'button'
  stopButton.hidden = true
  const undoButton = el('button', null, '撤销')
  undoButton.type = 'button'
  const hint = el('span', 'bx-hint', '')
  inputRow.append(prompt, sendButton, stopButton, undoButton)
  composer.append(pills, intentBar, inputRow, hint)
  hub.append(banner, stepper, mutes, card, variants, composer)
  stage.append(hub)
  root.append(stage)
  host.append(root)

  // ---------------------------------------------------------------- state
  let serviceBase = base
  let currentDoc = null
  let state = null
  let kernelReady = false
  let replayVersion = null
  let ghostOn = false
  let deltaOn = false
  let wireOn = false
  let measureOn = false
  let sectionOn = false
  let sectionAxisValue = 'Z'
  let sectionValue = 0.5
  let pendingPicks = []
  let variantSet = null
  let variantPreviewIndex = null
  let activeIntent = null
  let eventSource = null
  let bannerTimer = null
  let streamRetry = null
  let shownVersion = -1
  let watchdog = null

  const documentId = () => currentDoc?.document.id ?? null
  const liveVersion = () => currentDoc?.document.version ?? 0
  const showingVersion = () => replayVersion ?? liveVersion()

  const post = (type, payload) => {
    try {
      frame.contentWindow?.postMessage({ from: 'brepx-workbench', type, ...payload }, '*')
    } catch (error) {
      /* the frame may not be ready yet */
    }
  }

  const say = (text) => { hint.textContent = text }

  const showBanner = (text, seconds = 5) => {
    bannerText.textContent = text
    banner.classList.add('on')
    if (bannerTimer) clearTimeout(bannerTimer)
    bannerTimer = setTimeout(() => banner.classList.remove('on'), seconds * 1000)
  }
  bannerClose.addEventListener('click', () => banner.classList.remove('on'))

  const designPayload = (options = {}) => ({
    documentId: documentId(),
    version: showingVersion(),
    highlight: options.highlight,
    prefetch: options.prefetch ?? previousVersion(),
    fit: options.fit,
  })

  const parseColor = (text) => {
    const match = String(text || '').match(/rgba?\(([^)]+)\)/)
    if (!match) return null
    const [r, g, b, a = 1] = match[1].split(',').map((item) => Number(item.trim()))
    if ([r, g, b].some((value) => Number.isNaN(value)) || a === 0) return null
    return { r, g, b }
  }

  const themePayload = () => {
    const stageStyle = getComputedStyle(stage)
    const rootStyle = getComputedStyle(root)
    const background = parseColor(stageStyle.backgroundColor)
      || parseColor(rootStyle.backgroundColor)
      || parseColor(getComputedStyle(document.body).backgroundColor)
      || { r: 11, g: 14, b: 19 }
    const foreground = parseColor(rootStyle.color) || { r: 232, g: 238, b: 248 }
    const luminance = (0.299 * background.r + 0.587 * background.g + 0.114 * background.b) / 255
    return {
      background: `rgb(${background.r}, ${background.g}, ${background.b})`,
      foreground: `rgb(${foreground.r}, ${foreground.g}, ${foreground.b})`,
      light: luminance > 0.5,
    }
  }

  const pushDesign = (options = {}) => {
    if (!kernelReady) return
    post('theme', themePayload())
    post('design', designPayload(options))
  }

  // A dropped handshake message must not leave a black viewport: retry until the
  // frame reports that it shows the version the hub is asking for.
  const startWatchdog = () => {
    if (watchdog) return
    watchdog = setInterval(() => {
      if (!kernelReady) return
      if (!documentId()) return
      if (shownVersion === showingVersion()) return
      pushDesign()
    }, 1500)
  }

  frame.addEventListener('load', () => {
    kernelReady = false
    shownVersion = -1
  })

  // ---------------------------------------------------------------- render
  const renderHeader = () => {
    if (!currentDoc) {
      docLabel.textContent = 'service unreachable'
      return
    }
    docLabel.textContent = `${currentDoc.document.name || currentDoc.document.id} · v${currentDoc.document.version}`
    if (currentDoc.vacant) {
      checkBadge.textContent = '空白'
      checkBadge.className = 'bx-badge'
      metricText.textContent = ''
    } else {
      const checks = currentDoc.checks
      checkBadge.textContent = `checks ${checks.passed}/${checks.total}`
      checkBadge.className = `bx-badge ${checks.ok ? 'ok' : 'bad'}`
      const metrics = currentDoc.metrics || {}
      metricText.textContent = `${metrics.faces ?? 0} 面 · ${num((metrics.volume ?? 0) / 1000, 2)} cm³`
    }
  }

  const renderReplay = () => {
    const replaying = replayVersion !== null && replayVersion !== liveVersion()
    replayBar.classList.toggle('on', replaying)
    if (replaying) {
      replayText.textContent = `正在回放 v${replayVersion} · 只读，不写入文档`
      replayBack.textContent = `回到最新 v${liveVersion()}`
    }
  }

  const renderStepper = () => {
    stepper.textContent = ''
    if (!currentDoc || (currentDoc.vacant && replayVersion === null)) {
      stepper.hidden = true
      return
    }
    stepper.hidden = false
    const milestones = currentDoc.milestones || []
    if (!milestones.length) {
      stepper.append(el('span', 'bx-hint', '还没有里程碑'))
      return
    }
    const scrollLeft = stepper.scrollLeft
    for (const milestone of milestones) {
      const chip = el('button', 'bx-chip')
      chip.type = 'button'
      const isLive = milestone.version === liveVersion()
      const isViewing = milestone.version === showingVersion()
      chip.classList.toggle('current', isLive)
      chip.classList.toggle('viewing', !isLive && isViewing)
      chip.append(el('span', `actor ${milestone.actor || 'agent'}`))
      chip.append(document.createTextNode(milestone.title || `v${milestone.version}`))
      chip.append(el('span', 'meta', `v${milestone.version}`))
      chip.title = `查看 v${milestone.version}${milestone.parent_version != null ? `（父 v${milestone.parent_version}）` : ''}`
      chip.addEventListener('click', () => viewMilestone(milestone.version))
      stepper.append(chip)
    }
    stepper.scrollLeft = scrollLeft
  }

  const renderMutes = () => {
    mutes.textContent = ''
    const features = currentDoc?.features || []
    if (!features.length || (currentDoc?.vacant && replayVersion === null)) {
      mutes.hidden = true
      return
    }
    mutes.hidden = false
    mutes.append(el('span', 'bx-hint', '特征'))
    for (const feature of features) {
      const tag = el('button', `bx-mute${feature.enabled ? '' : ' off'}${feature.can_toggle ? '' : ' locked'}`)
      tag.type = 'button'
      tag.append(el('span', null, feature.can_toggle ? `${feature.enabled ? '👁 ' : '◌ '}${feature.id}` : feature.id))
      tag.title = feature.can_toggle
        ? `${feature.type} · 点击${feature.enabled ? '关闭' : '开启'}`
        : `${feature.type} · 有下游引用，只能通过 Agent 调整`
      tag.addEventListener('click', () => {
        if (!feature.can_toggle) {
          showBanner(`${feature.id} 仍被后续特征引用，不能单独启停`)
          return
        }
        toggleFeature(feature.id)
      })
      mutes.append(tag)
    }
  }

  const formatDelta = (milestone) => {
    const metrics = milestone?.metrics || {}
    return `体积 ${num((metrics.volume ?? 0) / 1000, 2)} cm³ · 面 ${metrics.faces ?? 0}`
  }

  const renderCard = () => {
    card.textContent = ''
    const replaying = replayVersion !== null && replayVersion !== liveVersion()
    const milestones = currentDoc?.milestones || []
    const viewed = milestones.find((item) => item.version === showingVersion())
    if (!currentDoc || currentDoc.vacant || replaying) {
      card.classList.remove('on')
      return
    }
    const focus = currentDoc.focus_params || []
    if (!focus.length) {
      card.classList.add('on')
      const headRow = el('div', 'bx-card-head')
      headRow.append(el('span', 'bx-card-title', viewed?.title || '当前版本'))
      headRow.append(el('span', 'bx-card-delta', formatDelta(viewed)))
      card.append(headRow, el('span', 'bx-hint', '这个里程碑没有可微调的数值参数'))
      return
    }
    card.classList.add('on')
    const headRow = el('div', 'bx-card-head')
    headRow.append(el('span', 'bx-card-title', viewed?.title || '当前版本'))
    headRow.append(el('span', 'bx-card-delta', formatDelta(viewed)))
    const focusRow = el('div', 'bx-focus')
    for (const item of focus.slice(0, 4)) focusRow.append(focusControl(item))
    const variantButton = el('button', null, '生成变体')
    variantButton.type = 'button'
    variantButton.title = `围绕 ${focus[0].label} 试算几个候选`
    variantButton.addEventListener('click', () => generateVariants(focus[0]))
    focusRow.append(variantButton)
    card.append(headRow, focusRow)
  }

  const focusControl = (item) => {
    const wrap = el('label')
    wrap.append(el('span', null, item.label))
    const value = Number(item.value)
    const numeric = item.value != null && Number.isFinite(value) && typeof item.value !== 'string'
    const low = item.minimum != null ? Number(item.minimum) : Math.round(value * 0.5 * 100) / 100
    const high = item.maximum != null ? Number(item.maximum) : Math.max(value * 2, low + 1)
    if (!numeric) {
      const input = el('input')
      input.type = 'text'
      input.value = String(item.value ?? '')
      input.style.width = '64px'
      input.setAttribute('aria-label', item.label)
      input.addEventListener('change', () => tweak(item, input.value))
      wrap.append(input)
      return wrap
    }
    const readout = el('b', null, num(value, Number.isInteger(value) ? 0 : 2))
    const range = el('input')
    range.type = 'range'
    range.min = String(low)
    range.max = String(high)
    const step = Number.isInteger(value)
      ? 1
      : Math.max(Math.abs(value) / 1000, (high - low) / 1000, 0.001)
    range.step = String(step)
    range.value = String(value)
    range.setAttribute('aria-label', item.label)
    let timer = null
    const commit = () => {
      const next = Number.isInteger(value)
        ? Math.round(Number(range.value))
        : Math.round(Number(range.value) * 1000) / 1000
      if (next === value) return
      tweak(item, next)
    }
    range.addEventListener('input', (event) => {
      readout.textContent = num(Number(range.value), Number.isInteger(value) ? 0 : 2)
      if (!event.isTrusted) return
      if (timer) clearTimeout(timer)
      timer = setTimeout(commit, 120)
    })
    wrap.append(range, readout)
    if (item.unit) wrap.append(el('span', 'unit', item.unit))
    return wrap
  }

  const renderVariants = () => {
    variants.textContent = ''
    if (!variantSet || replayVersion !== null) {
      variants.classList.remove('on')
      return
    }
    const options = (variantSet.variants || []).filter((item) => item.ok)
    if (!options.length) {
      variants.classList.remove('on')
      return
    }
    variants.classList.add('on')
    for (const option of options) {
      const selected = variantPreviewIndex === option.index
      const cardBox = el('div', `bx-variant${selected ? ' selected' : ''}`)
      const previewBtn = el('button', 'bx-variant-preview')
      previewBtn.type = 'button'
      if (option.thumb) {
        const img = document.createElement('img')
        img.src = option.thumb.startsWith('http') ? option.thumb : `${serviceBase}${option.thumb}`
        img.alt = option.label || `方案 ${option.index}`
        previewBtn.append(img)
      }
      previewBtn.append(el('b', null, option.label || `方案 ${option.index}`))
      const vol = option.build?.metrics?.volume ?? option.volume ?? null
      const faces = option.build?.metrics?.faces ?? option.faces ?? null
      const summary = [
        vol != null ? `体积 ${num(vol / 1000, 2)} cm³` : null,
        faces != null ? `${faces} 面` : null,
      ].filter(Boolean).join(' · ') || '可预览'
      previewBtn.append(el('span', null, summary))
      previewBtn.title = '点击在主视口预览该方案'
      previewBtn.addEventListener('click', () => previewVariant(variantSet.set, option))

      const actions = el('div', 'bx-variant-actions')
      const pickBtn = el('button', 'primary', '采纳')
      pickBtn.type = 'button'
      pickBtn.addEventListener('click', () => applyVariant(variantSet.set, option.index))
      actions.append(pickBtn)
      cardBox.append(previewBtn, actions)
      variants.append(cardBox)
    }
    const close = el('button', null, '收起')
    close.type = 'button'
    close.addEventListener('click', () => {
      variantSet = null
      variantPreviewIndex = null
      renderVariants()
      pushDesign()
    })
    variants.append(close)
  }

  const renderIntent = () => {
    intentBar.textContent = ''
    const intent = activeIntent
    if (!intent || intent.status !== 'running') {
      intentBar.classList.remove('on')
      stopButton.hidden = true
      return
    }
    intentBar.classList.add('on')
    intentBar.append(el('span', null, '意图'))
    intentBar.append(el('span', null, intent.prompt.slice(0, 40)))
    const steps = el('div', 'steps')
    for (const step of intent.steps) {
      steps.append(el('span', `bx-step ${step.status}`, `${step.index} ${step.title}`))
    }
    intentBar.append(steps)
    stopButton.hidden = false
  }

  const renderPills = () => {
    pills.textContent = ''
    for (const anchor of pendingPicks) {
      const pill = el('span', 'bx-pill', anchor.label)
      const remove = el('button', null, '×')
      remove.type = 'button'
      remove.addEventListener('click', () => {
        pendingPicks = pendingPicks.filter((item) => item !== anchor)
        renderPills()
      })
      pill.append(remove)
      pills.append(pill)
    }
  }

  const renderAll = () => {
    renderHeader()
    renderReplay()
    renderStepper()
    renderMutes()
    renderCard()
    renderVariants()
    renderIntent()
    vacant.classList.toggle('on', Boolean(currentDoc?.vacant) && replayVersion === null)
    const disabled = Boolean(currentDoc?.vacant)
    for (const button of [wireButton, measureButton, ghostButton, deltaButton, sectionButton]) {
      button.disabled = disabled
    }
    for (const node of Object.values(exportLinks)) node.disabled = disabled
    sendButton.disabled = false
    pushDesign()
  }

  // ---------------------------------------------------------------- data
  const loadState = async (documentId) => {
    currentDoc = await fetchJSON(`${serviceBase}/api/docs/${documentId}/state`)
    activeIntent = currentDoc.active_intent || null
    if (replayVersion !== null && !currentDoc.milestones.some((m) => m.version === replayVersion)) {
      replayVersion = null
    }
    renderAll()
  }

  const connect = async (documentId) => {
    if (eventSource) { eventSource.close(); eventSource = null }
    if (streamRetry) { clearTimeout(streamRetry); streamRetry = null }
    try {
      eventSource = new EventSource(`${serviceBase}/api/docs/${documentId}/events`)
      eventSource.addEventListener('state', async (event) => {
        currentDoc = JSON.parse(event.data)
        activeIntent = currentDoc.active_intent || null
        renderAll()
      })
      eventSource.addEventListener('milestone', async (event) => {
        const payload = JSON.parse(event.data)
        await loadState(documentId)
        if (payload.changed_face_centers?.length) {
          pushDesign({ highlight: payload.changed_face_centers })
        }
        const checks = currentDoc.checks
        showBanner(`v${payload.version} ${payload.title} · checks ${checks.passed}/${checks.total}`, 4)
      })
      eventSource.addEventListener('intent', (event) => {
        activeIntent = JSON.parse(event.data)
        renderIntent()
      })
      eventSource.addEventListener('variants', (event) => {
        variantSet = JSON.parse(event.data)
        renderVariants()
      })
      eventSource.addEventListener('error', (event) => {
        const payload = event.data ? JSON.parse(event.data) : null
        if (payload?.message) showBanner(`${payload.code || 'ERROR'} · ${payload.message}`)
      })
      eventSource.onerror = () => {
        eventSource?.close()
        eventSource = null
        if (streamRetry) clearTimeout(streamRetry)
        streamRetry = setTimeout(() => { if (currentDoc) connect(currentDoc.document.id) }, 2500)
      }
    } catch (error) {
      showBanner(`事件流连接失败：${error.message}`)
    }
  }

  const boot = async () => {
    try {
      const documents = await fetchJSON(`${serviceBase}/api/docs`)
      let id = documents.length ? documents[0].id : null
      if (!id) {
        const created = await fetchJSON(`${serviceBase}/api/docs`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: 'Workbench' }),
        })
        id = created.id
      }
      await loadState(id)
      connect(id)
      say('就绪 · 底部输入意图，或按住空格对比上一版本')
    } catch (error) {
      docLabel.textContent = 'service unreachable'
      say(`${error.message} — 启动 python -m cadwork.service`)
    }
  }

  // ---------------------------------------------------------------- actions
  const viewMilestone = async (version) => {
    replayVersion = version === liveVersion() ? null : version
    renderReplay()
    renderStepper()
    renderCard()
    if (version > 0) {
      const milestone = (currentDoc?.milestones || []).find((item) => item.version === version)
      const base = milestone?.parent_version ?? (version > 1 ? version - 1 : null)
      if (base != null) {
        try {
          const detail = await fetchJSON(
            `${serviceBase}/api/docs/${documentId()}/diff?base=${base}&target=${version}`,
          )
          if (detail?.changed_face_centers?.length) {
            pushDesign({ highlight: detail.changed_face_centers })
            return
          }
        } catch (error) {
          /* the diff is a nicety, never a blocker */
        }
      }
    }
    pushDesign()
  }

  const backToLive = () => {
    replayVersion = null
    renderAll()
  }
  replayBack.addEventListener('click', backToLive)

  const tweak = async (item, value) => {
    if (!currentDoc || replayVersion !== null) return
    if (value === item.value) return
    try {
      await fetchJSON(`${serviceBase}/api/docs/${documentId()}/tweak`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          base_version: liveVersion(),
          changes: [{ feature_id: item.feature_id, params: { [item.param]: value } }],
        }),
      })
      await loadState(documentId())
      say(`微调 ${item.label} → ${value}`)
    } catch (error) {
      if (error.status === 409 || error.code === 'STALE_VERSION') return
      showBanner(`微调失败 · ${error.message}`)
    }
  }

  const toggleFeature = async (featureId) => {
    if (!currentDoc || replayVersion !== null) return
    try {
      await fetchJSON(`${serviceBase}/api/docs/${documentId()}/toggle/${featureId}`, { method: 'POST' })
      await loadState(documentId())
      say(`已切换 ${featureId}`)
    } catch (error) {
      showBanner(`启停失败 · ${error.message}`)
    }
  }

  const generateVariants = async (focus) => {
    if (!currentDoc || !focus) return
    const value = Number(focus.value)
    const low = focus.minimum != null ? Number(focus.minimum) : value * 0.75
    const high = focus.maximum != null ? Number(focus.maximum) : value * 1.25
    const candidates = [value * 0.85, value * 1.15]
      .map((item) => Math.min(Math.max(item, low), high))
      .map((item) => (Number.isInteger(value) ? Math.round(item) : Math.round(item * 100) / 100))
    say('试算候选…')
    try {
      variantSet = await fetchJSON(`${serviceBase}/api/docs/${documentId()}/variants`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          feature: focus.feature_id,
          params: { [focus.param]: [...new Set(candidates)] },
          base_version: liveVersion(),
        }),
      })
      renderVariants()
      if (variantSet.all_failed) showBanner('所有候选都未通过检查，调整参数后再试')
    } catch (error) {
      showBanner(`变体失败 · ${error.message}`)
    }
  }

  const previewVariant = (setId, option) => {
    variantPreviewIndex = option.index
    renderVariants()
    const stepUrl = option.step?.startsWith('http')
      ? option.step
      : `${serviceBase}${option.step || `/api/variants/${setId}/${option.index}/step`}`
    post('preview', { url: stepUrl, label: option.label || `方案 ${option.index}` })
    say(`预览方案：${option.label || option.index}（点击「采纳」写入文档）`)
  }

  const applyVariant = async (setId, index) => {
    try {
      await fetchJSON(`${serviceBase}/api/variants/${setId}/${index}/apply`, { method: 'POST' })
      variantSet = null
      variantPreviewIndex = null
      renderVariants()
      await loadState(documentId())
      say('已采纳方案')
    } catch (error) {
      showBanner(`采纳失败 · ${error.message}`)
    }
  }

  const submitIntent = async (event) => {
    event.preventDefault()
    const text = prompt.value.trim()
    if (!currentDoc) return
    const picks = pendingPicks.map((item) => item.label).join(' ')
    const message = [picks, text].filter(Boolean).join(' ')
    if (!message) return
    sendButton.disabled = true
    const branchBase = replayVersion !== null ? replayVersion : null
    try {
      const result = await fetchJSON(`${serviceBase}/api/docs/${documentId()}/intents`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: message,
          ...(branchBase !== null ? { base_version: branchBase } : {}),
        }),
      })
      prompt.value = ''
      pendingPicks = []
      renderPills()
      say(branchBase !== null
        ? `已基于 v${branchBase} 交给 Agent · 待处理 ${result.pending}`
        : `已交给 Agent · 待处理 ${result.pending}`)
    } catch (error) {
      showBanner(`提交失败 · ${error.message}`)
    } finally {
      sendButton.disabled = false
    }
  }
  composer.addEventListener('submit', submitIntent)

  prompt.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      composer.requestSubmit()
    }
  })

  stopButton.addEventListener('click', async () => {
    if (!activeIntent || !currentDoc) return
    try {
      await fetchJSON(
        `${serviceBase}/api/docs/${documentId()}/intents/${activeIntent.intent_id}/cancel`,
        { method: 'POST' },
      )
      activeIntent = null
      renderIntent()
      say('已请求停止')
    } catch (error) {
      showBanner(`停止失败 · ${error.message}`)
    }
  })

  undoButton.addEventListener('click', async () => {
    if (!currentDoc || replayVersion !== null) return
    try {
      await fetchJSON(`${serviceBase}/api/docs/${documentId()}/undo`, { method: 'POST' })
      await loadState(documentId())
      say('已撤销一步')
    } catch (error) {
      showBanner(`撤销失败 · ${error.message}`)
    }
  })

  const loadSample = async (name) => {
    if (!currentDoc) return
    try {
      await fetchJSON(`${serviceBase}/api/docs/${documentId()}/sample/${name}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ params: {}, replace: true }),
      })
      await loadState(documentId())
      say(`已载入 ${name}`)
    } catch (error) {
      showBanner(`载入失败 · ${error.message}`)
    }
  }

  const previousVersion = () => {
    const milestones = currentDoc?.milestones || []
    const earlier = milestones.map((item) => item.version).filter((version) => version < showingVersion())
    return earlier.length ? Math.max(...earlier) : null
  }

  const toggleGhost = async (on) => {
    ghostOn = typeof on === 'boolean' ? on : !ghostOn
    ghostButton.classList.toggle('on', ghostOn)
    if (!ghostOn) {
      post('ghost', { on: false })
      return
    }
    const version = previousVersion()
    if (!version) {
      ghostOn = false
      ghostButton.classList.remove('on')
      showBanner('没有上一版本可对比')
      return
    }
    post('ghost', { on: true, documentId: documentId(), version })
  }

  const toggleDelta = async () => {
    if (deltaOn) {
      deltaOn = false
      deltaButton.classList.remove('on')
      post('highlight', { centers: [] })
      return
    }
    const version = previousVersion()
    if (!version) { showBanner('没有上一版本可比较'); return }
    say('计算差异…')
    try {
      const report = await fetchJSON(
        `${serviceBase}/api/docs/${documentId()}/diff?base=${version}&target=${showingVersion()}`,
      )
      const centers = report.changed_face_centers || []
      if (!centers.length) { showBanner('两个版本没有几何差异'); return }
      deltaOn = true
      deltaButton.classList.add('on')
      post('highlight', { centers, seconds: 8 })
      say(`差异：${report.changed_face_indices.length} 个变更面（v${version} → v${showingVersion()}）`)
    } catch (error) {
      showBanner(`差异失败 · ${error.message}`)
    }
  }

  wireButton.addEventListener('click', () => {
    wireOn = !wireOn
    wireButton.classList.toggle('on', wireOn)
    post('wire', { on: wireOn })
  })

  measureButton.addEventListener('click', () => {
    measureOn = !measureOn
    measureButton.classList.toggle('on', measureOn)
    post('measure', { on: measureOn })
  })

  ghostButton.addEventListener('click', () => toggleGhost())
  deltaButton.addEventListener('click', () => toggleDelta())

  sectionButton.addEventListener('click', () => {
    sectionOn = !sectionOn
    sectionButton.classList.toggle('on', sectionOn)
    sectionBar.classList.toggle('on', sectionOn)
    post('section', { on: sectionOn, axis: sectionAxisValue, t: sectionValue })
  })
  sectionAxis.addEventListener('change', () => {
    sectionAxisValue = sectionAxis.value
    post('section', { on: sectionOn, axis: sectionAxisValue, t: sectionValue })
  })
  sectionRange.addEventListener('input', () => {
    sectionValue = Number(sectionRange.value)
    post('section', { on: sectionOn, axis: sectionAxisValue, t: sectionValue })
  })

  const onKey = (event) => {
    const tag = event.target?.tagName
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
    if (event.code === 'Space') {
      event.preventDefault()
      if (!event.repeat) toggleGhost(true)
      return
    }
    if (event.key === 'g') { toggleGhost(); return }
    if (event.key === 'd') { toggleDelta(); return }
    if (event.key === 'Escape') {
      banner.classList.remove('on')
      sectionBar.classList.remove('on')
      return
    }
    const views = { 1: 'iso', 2: 'front', 3: 'top', 4: 'right' }
    if (views[event.key]) post('view', { name: views[event.key] })
    if (event.key === 'f') post('fit', {})
  }
  const onKeyUp = (event) => {
    const tag = event.target?.tagName
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
    if (event.code === 'Space' && ghostOn) toggleGhost(false)
  }
  document.addEventListener('keydown', onKey)
  document.addEventListener('keyup', onKeyUp)

  const resolvePick = async (rawPick) => {
    if (!currentDoc || currentDoc.vacant) return { ...rawPick, label: formatAnchor(rawPick) }
    try {
      const semantic = await fetchJSON(`${serviceBase}/api/docs/${documentId()}/pick`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          version: showingVersion(),
          point: rawPick.point,
          normal: rawPick.normal,
          area: rawPick.area,
          face_index: rawPick.face_index,
        }),
      })
      return { ...rawPick, ...semantic }
    } catch (error) {
      return { ...rawPick, label: formatAnchor(rawPick) }
    }
  }

  const onMessage = async (event) => {
    const data = event.data
    if (!data || data.from !== 'brepx-viewport') return
    if (data.type === 'ready') {
      kernelReady = true
      shownVersion = -1
      pushDesign()
      startWatchdog()
    } else if (data.type === 'shown') {
      shownVersion = data.version
    } else if (data.type === 'pick' && data.pick) {
      const anchor = await resolvePick(data.pick)
      pendingPicks = [...pendingPicks.slice(-2), anchor]
      renderPills()
      prompt.focus()
    } else if (data.type === 'status') {
      say(`视口 · ${data.text}`)
    } else if (data.type === 'error') {
      showBanner(`视口：${data.text}`)
    }
  }
  const formatAnchor = (pick) => {
    const point = pick.point.map((value) => Number(value).toFixed(1)).join(', ')
    const area = pick.area != null ? ` · ${Number(pick.area).toFixed(1)} mm²` : ''
    return `@(${point})${area}`
  }
  window.addEventListener('message', onMessage)

  const themeObserver = new MutationObserver(() => {
    if (kernelReady) post('theme', themePayload())
  })
  themeObserver.observe(document.documentElement, {
    attributes: true, attributeFilter: ['class', 'style', 'data-theme'],
  })

  boot()

  return () => {
    themeObserver.disconnect()
    if (eventSource) eventSource.close()
    if (streamRetry) clearTimeout(streamRetry)
    if (bannerTimer) clearTimeout(bannerTimer)
    if (watchdog) clearInterval(watchdog)
    document.removeEventListener('keydown', onKey)
    document.removeEventListener('keyup', onKeyUp)
    window.removeEventListener('message', onMessage)
    root.remove()
  }
}
