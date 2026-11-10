/**
 * The CAD workbench, in the host's own visual language.
 *
 * Colour, radius and type come from the host's `--dsw-*` tokens, so the panel
 * flips with the light/dark theme and never looks bolted on. Two densities:
 * narrow (the sidebar tab) stacks; wide (the tab fullscreen) is a three-pane
 * workspace — parts and features, the model, properties and checks.
 *
 * The model is the kernel's own page in an iframe (the kernel must not be
 * bundled); this module talks to it over postMessage.
 */
const STYLE_ID = 'cadview-style'

const style = () => {
  if (document.getElementById(STYLE_ID)) return
  const tag = document.createElement('style')
  tag.id = STYLE_ID
  tag.textContent = `
    .cv-root{
      --cv-bg: var(--dsw-alias-bg-base, #0b0e13);
      --cv-panel: var(--dsw-alias-bg-layer-1, #11151c);
      --cv-panel-2: var(--dsw-alias-bg-layer-2, #151a23);
      --cv-line: var(--dsw-alias-border-l2, #232d3d);
      --cv-line-soft: var(--dsw-alias-border-l1, #1a2230);
      --cv-fg: var(--dsw-alias-label-primary, #e8eef8);
      --cv-fg-2: var(--dsw-alias-label-secondary, #a9b7ca);
      --cv-fg-3: var(--dsw-alias-label-tertiary, #6d7d94);
      --cv-accent: var(--dsw-alias-state-business-primary, #4c9aff);
      --cv-ok: var(--dsw-alias-state-success-primary, #3ecf8e);
      --cv-warn: var(--dsw-alias-state-warn-primary, #ffb454);
      --cv-bad: var(--dsw-alias-state-error-primary, #ff5f7e);
      --cv-r-sm: var(--dsw-radius-sm, 6px);
      --cv-r-md: var(--dsw-radius-md, 9px);
      --cv-font: var(--dsw-font-family, system-ui, sans-serif);
      --cv-mono: ui-monospace, "Cascadia Mono", Consolas, monospace;
      position: relative; display: flex; flex-direction: column; height: 100%; min-height: 0;
      background: var(--cv-bg); color: var(--cv-fg); font: 12px/1.5 var(--cv-font)
    }
    .cv-root button{font:inherit;color:var(--cv-fg-2);background:var(--cv-panel-2);
      border:1px solid var(--cv-line);border-radius:var(--cv-r-sm);height:26px;padding:0 9px;cursor:pointer;
      transition:background .12s,border-color .12s,color .12s}
    .cv-root button:hover{background:var(--cv-panel);border-color:var(--cv-accent);color:var(--cv-fg)}
    .cv-root button:disabled{opacity:.45;cursor:not-allowed}
    .cv-root button.primary{background:var(--cv-accent);border-color:transparent;color:#08131f;font-weight:600}
    .cv-root select,.cv-root input{font:inherit;color:var(--cv-fg);background:var(--cv-bg);
      border:1px solid var(--cv-line);border-radius:var(--cv-r-sm);height:26px;padding:0 7px}
    .cv-root select:focus,.cv-root input:focus{outline:none;border-color:var(--cv-accent)}

    /* header */
    .cv-head{display:flex;align-items:center;gap:8px;padding:6px 10px;border-bottom:1px solid var(--cv-line);
      background:var(--cv-panel);flex:0 0 auto;flex-wrap:wrap}
    .cv-title{font-weight:650;color:var(--cv-fg);letter-spacing:.04em}
    .cv-meta{color:var(--cv-fg-3);font:11px/1 var(--cv-mono);white-space:nowrap;overflow:hidden;
      text-overflow:ellipsis;max-width:150px}
    .cv-meta.wide-only{flex:1}
    .cv-head .grow{flex:1}

    /* body layout */
    .cv-main{flex:1;min-height:0;display:flex;flex-direction:column}
    .cv-rail{display:none;min-height:0;flex-direction:column;width:230px;border-right:1px solid var(--cv-line);
      background:var(--cv-panel)}
    .cv-view{position:relative;flex:1;min-height:220px;background:var(--cv-bg)}
    .cv-view iframe{display:block;width:100%;height:100%;border:0}
    .cv-insp{display:none;width:290px;min-height:0;flex-direction:column;border-left:1px solid var(--cv-line);
      background:var(--cv-panel)}
    .cv-checks{flex:0 0 auto;max-height:96px;overflow:auto;border-top:1px solid var(--cv-line);
      background:var(--cv-panel);padding:5px 10px;font-size:11px;line-height:1.5}
    .cv-checks-head{color:var(--cv-ok)}
    .cv-checks-head.bad{color:var(--cv-bad)}
    .cv-checks ul{margin:3px 0 0;padding-left:16px;color:var(--cv-bad)}

    /* wide workspace */
    .cv-root.wide .cv-main{flex-direction:row}
    .cv-root.wide .cv-rail{display:flex}
    .cv-root.wide .cv-insp{display:flex}
    .cv-root.wide .cv-checks{display:none}
    .cv-root.wide .cv-meta{max-width:none}

    /* panel sections */
    .cv-section{display:flex;flex-direction:column;min-height:0}
    .cv-section + .cv-section{border-top:1px solid var(--cv-line)}
    .cv-section-head{display:flex;align-items:center;gap:6px;height:28px;padding:0 9px;color:var(--cv-fg-3);
      font-size:10.5px;letter-spacing:.08em;text-transform:uppercase}
    .cv-section-head .count{font:10.5px/1 var(--cv-mono);letter-spacing:0;color:var(--cv-fg-3)}
    .cv-section-body{flex:1;min-height:0;overflow:auto;padding:3px 5px 6px}

    /* parts */
    .cv-part{display:grid;grid-template-columns:40px minmax(0,1fr);gap:8px;align-items:center;padding:5px;
      border-radius:var(--cv-r-sm);border:1px solid transparent;cursor:pointer;background:none;height:auto;
      width:100%;text-align:left;min-height:46px;overflow:hidden}
    .cv-part:hover{background:var(--cv-panel-2);border-color:var(--cv-line)}
    .cv-part.sel{background:var(--cv-panel-2);border-color:var(--cv-accent)}
    .cv-part .thumb{width:40px;height:32px;border-radius:4px;object-fit:cover;background:var(--cv-panel-2);
      border:1px solid var(--cv-line-soft);align-self:center}
    .cv-part b{display:block;font-size:12px;font-weight:600;line-height:1.3;color:var(--cv-fg);white-space:nowrap;
      overflow:hidden;text-overflow:ellipsis}
    .cv-part span{font:10.5px/1.3 var(--cv-mono);color:var(--cv-fg-3)}

    /* features */
    .cv-feat{display:grid;grid-template-columns:14px minmax(0,1fr) auto;gap:7px;align-items:center;padding:4px 6px;
      border-radius:var(--cv-r-sm);border:1px solid transparent;cursor:pointer;background:none;height:auto;
      width:100%;text-align:left;color:var(--cv-fg-2)}
    .cv-feat:hover{background:var(--cv-panel-2);border-color:var(--cv-line)}
    .cv-feat.sel{background:var(--cv-panel-2);border-color:var(--cv-accent);color:var(--cv-fg)}
    .cv-feat .dot{width:6px;height:6px;border-radius:50%;background:var(--cv-ok);justify-self:center}
    .cv-feat.off .dot{background:var(--cv-fg-3)}
    .cv-feat.off .name{text-decoration:line-through;color:var(--cv-fg-3)}
    .cv-feat .name{font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .cv-feat .name small{font:10.5px/1 var(--cv-mono);color:var(--cv-fg-3);margin-left:5px}
    .cv-feat .sw{width:24px;height:13px;border-radius:999px;background:var(--cv-panel-2);border:1px solid var(--cv-line);
      position:relative;flex:none}
    .cv-feat .sw::after{content:"";position:absolute;top:1px;left:1px;width:9px;height:9px;border-radius:50%;
      background:var(--cv-fg-3);transition:transform .14s,background .14s}
    .cv-feat.on .sw{background:color-mix(in srgb, var(--cv-ok) 25%, transparent);border-color:var(--cv-ok)}
    .cv-feat.on .sw::after{transform:translateX(10px);background:var(--cv-ok)}

    /* inspector */
    .cv-field{display:grid;grid-template-columns:88px minmax(0,1fr);gap:7px;align-items:center;padding:3px 8px}
    .cv-field label{color:var(--cv-fg-3);font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .cv-field input,.cv-field select{height:24px;font:11.5px/1 var(--cv-mono);width:100%}
    .cv-empty{color:var(--cv-fg-3);padding:10px;font-size:11.5px;text-align:center}
    .cv-check-row{display:grid;grid-template-columns:13px minmax(0,1fr);gap:6px;padding:2px 8px;font-size:11px}
    .cv-check-row .mark{color:var(--cv-ok);font:11px/1.5 var(--cv-mono)}
    .cv-check-row.bad .mark{color:var(--cv-bad)}
    .cv-check-row .exp{color:var(--cv-fg-3);font:10px/1.35 var(--cv-mono)}

    /* viewport overlay */
    .cv-tools{position:absolute;top:8px;left:8px;display:flex;gap:4px;padding:4px;border-radius:var(--cv-r-md);
      background:color-mix(in srgb, var(--cv-panel) 88%, transparent);border:1px solid var(--cv-line);
      backdrop-filter:blur(6px)}
    .cv-tools button{height:22px;padding:0 7px;font-size:11px}
    .cv-tools .sep{width:1px;background:var(--cv-line);margin:1px 2px}
    .cv-tools button.on{background:var(--cv-accent);border-color:transparent;color:#08131f;font-weight:600}
    .cv-tools input[type=range]{width:104px;height:22px;padding:0;background:transparent;border:0;
      accent-color:var(--cv-accent)}
    .cv-readout{position:absolute;left:9px;bottom:7px;right:9px;display:flex;justify-content:space-between;gap:10px;
      pointer-events:none;font:11px/1.4 var(--cv-mono);color:var(--cv-fg-2);text-shadow:0 1px 2px #000}
    .cv-sheet{position:absolute;left:8px;right:8px;bottom:30px;z-index:15;display:flex;flex-direction:column;
      gap:7px;padding:9px 10px;border-radius:var(--cv-r-md);border:1px solid var(--cv-line);
      background:color-mix(in srgb, var(--cv-panel) 94%, transparent);backdrop-filter:blur(8px);
      box-shadow:var(--dsw-shadow-lv2, 0 10px 30px rgb(0 0 0 / .35))}
    .cv-sheet[hidden]{display:none}
    .cv-sheet-head{display:flex;align-items:center;gap:8px;font-weight:600;color:var(--cv-fg)}
    .cv-sheet-note{color:var(--cv-fg-3);font:11px/1.4 var(--cv-mono)}
    .cv-vrows{display:flex;flex-wrap:wrap;gap:6px;max-height:112px;overflow:auto}
    .cv-vrow{display:flex;align-items:baseline;gap:8px;height:auto;padding:5px 9px;border-radius:var(--cv-r-sm);
      border:1px solid var(--cv-line);background:var(--cv-bg);color:var(--cv-fg);text-align:left}
    .cv-vrow b{font-size:12px}
    .cv-vrow span{font:10.5px/1.3 var(--cv-mono);color:var(--cv-fg-3)}
    .cv-vrow.sel{border-color:var(--cv-accent);
      background:color-mix(in srgb, var(--cv-accent) 14%, transparent)}
    .cv-vrow.bad{border-color:var(--cv-bad)}
    .cv-vrow.bad b{color:var(--cv-bad)}
    .cv-status-line{padding:3px 10px;border-top:1px solid var(--cv-line);background:var(--cv-panel);
      color:var(--cv-fg-3);font:11px/1.4 var(--cv-mono);flex:0 0 auto;white-space:nowrap;overflow:hidden;
      text-overflow:ellipsis}

    /* modal (variants) */
    .cv-modal{position:absolute;inset:0;z-index:20;display:flex;align-items:flex-start;justify-content:center;
      padding:16px;overflow:auto;background:color-mix(in srgb, var(--cv-bg) 72%, transparent);backdrop-filter:blur(3px)}
    .cv-modal[hidden]{display:none}
    .cv-modal-box{width:100%;max-width:760px;display:flex;flex-direction:column;gap:9px;padding:13px;
      border-radius:var(--cv-r-md);background:var(--cv-panel);border:1px solid var(--cv-line);
      box-shadow:var(--dsw-shadow-lv2, 0 18px 48px rgb(0 0 0 / .5))}
    .cv-modal-head{display:flex;align-items:center;gap:8px;font-weight:600;color:var(--cv-fg)}
    .cv-form{display:flex;flex-wrap:wrap;align-items:center;gap:7px;color:var(--cv-fg-3)}
    .cv-form label{display:flex;align-items:center;gap:4px}
    .cv-form input[type=text]{width:150px}
      border-radius:var(--cv-r-sm);border:1px solid var(--cv-line);background:var(--cv-bg);color:var(--cv-fg)}
      var(--cv-panel), var(--cv-panel-2), var(--cv-panel));background-size:200% 100%;
      animation:cv-shimmer 1.2s linear infinite}
  `
  document.head.appendChild(tag)
}

const fetchJSON = async (url, options) => {
  const response = await fetch(url, options)
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`
    try {
      const payload = await response.json()
      if (payload?.error?.message) message = payload.error.message
    } catch (error) {
      /* the status line is enough */
    }
    throw new Error(message)
  }
  return response.json()
}

const el = (tag, className, text) => {
  const node = document.createElement(tag)
  if (className) node.className = className
  if (text != null) node.textContent = text
  return node
}

/**
 * Mount the workbench in `host`.
 * @param host - element to fill.
 * @param base - cadwork service origin, e.g. http://127.0.0.1:8765
 */
export function mountViewport(host, base) {
  style()
  host.textContent = ''

  const root = el('div', 'cv-root')

  // ---------------------------------------------------------------- header
  const head = el('div', 'cv-head')
  const title = el('span', 'cv-title', 'BrepX')
  const picker = el('select')
  picker.setAttribute('aria-label', 'Sample')
  const meta = el('span', 'cv-meta', 'starting…')
  const variantsButton = el('button', null, '变体')
  variantsButton.title = '并置比较若干候选（不修改文档）'
  const buildButton = el('button', 'primary', 'Build')
  const reloadButton = el('button', null, 'Reload')
  const undoButton = el('button', null, '撤销')
  const stepButton = el('button', null, 'STEP')
  stepButton.title = '导出 STEP'
  const stlButton = el('button', null, 'STL')
  stlButton.title = '导出 STL'
  const grow = el('span', 'grow')
  const helpButton = el('button', null, '?')
  helpButton.setAttribute('aria-label', '演示与快捷键')
  helpButton.title = '演示脚本与快捷键'
  head.append(title, picker, meta, grow, variantsButton, undoButton, stepButton, stlButton,
    buildButton, reloadButton, helpButton)

  // ---------------------------------------------------------------- rail
  const rail = el('div', 'cv-rail')
  const partsSection = el('section', 'cv-section')
  const partsHead = el('div', 'cv-section-head')
  partsHead.append(el('span', null, '零件'), el('span', 'count'))
  const partsBody = el('div', 'cv-section-body')
  partsSection.append(partsHead, partsBody)
  const treeSection = el('section', 'cv-section')
  const treeHead = el('div', 'cv-section-head')
  treeHead.append(el('span', null, '特征'), el('span', 'count'))
  const treeBody = el('div', 'cv-section-body')
  treeSection.append(treeHead, treeBody)
  partsSection.style.flex = '0 0 42%'
  treeSection.style.flex = '1'
  rail.append(partsSection, treeSection)

  // ---------------------------------------------------------------- view
  const view = el('div', 'cv-view')
  const frame = el('iframe')
  frame.title = 'CAD model'
  frame.src = `${base}/api/kernel-view`
  const tools = el('div', 'cv-tools')
  for (const [label, name] of [['等轴', 'iso'], ['前', 'front'], ['顶', 'top'], ['右', 'right']]) {
    const button = el('button', null, label)
    button.setAttribute('aria-label', `视图 ${label}`)
    button.addEventListener('click', () => command('view', { name }))
    tools.append(button)
  }
  tools.append(el('span', 'sep'))
  const fitButton = el('button', null, '适配')
  fitButton.addEventListener('click', () => command('fit'))
  const wireButton = el('button', null, '线框')
  wireButton.addEventListener('click', () => command('wire'))
  tools.append(fitButton, wireButton)
  tools.append(el('span', 'sep'))
  let measuring = false
  const measureButton = el('button', null, '测量')
  measureButton.setAttribute('aria-label', '测量')
  measureButton.title = '测量：点面取尺寸，再点一处量距离 (M)'
  measureButton.addEventListener('click', () => {
    measuring = !measuring
    measureButton.classList.toggle('on', measuring)
    command('measure', { on: measuring })
  })
  let sectioning = false
  const sectionButton = el('button', null, '剖切')
  sectionButton.setAttribute('aria-label', '剖切')
  sectionButton.title = '剖切：拖动滑块移动切面 (X)'
  const sectionRange = el('input', 'cv-section-range')
  sectionRange.type = 'range'
  sectionRange.min = '0'
  sectionRange.max = '100'
  sectionRange.value = '50'
  sectionRange.hidden = true
  sectionRange.setAttribute('aria-label', '剖面位置')
  sectionRange.addEventListener('input', () => {
    command('section-t', { t: Number(sectionRange.value) / 100 })
  })
  sectionButton.addEventListener('click', () => {
    sectioning = !sectioning
    sectionButton.classList.toggle('on', sectioning)
    sectionRange.hidden = !sectioning
    command('section', { on: sectioning, t: Number(sectionRange.value) / 100 })
  })
  tools.append(measureButton, sectionButton, sectionRange)
  const readout = el('div', 'cv-readout')
  const pickText = el('span', null, '点击模型可拾取面')
  const metricsText = el('span', null, '')
  readout.append(pickText, metricsText)
  view.append(frame, tools, readout)

  // ---------------------------------------------------------------- inspector
  const insp = el('div', 'cv-insp')
  const fieldsSection = el('section', 'cv-section')
  const fieldsHead = el('div', 'cv-section-head')
  fieldsHead.append(el('span', null, '属性'), el('span', 'count'))
  const fieldsBody = el('div', 'cv-section-body')
  const applyButton = el('button', 'primary', '应用参数')
  applyButton.disabled = true
  const applyRow = el('div')
  applyRow.style.cssText = 'padding:6px 8px;border-top:1px solid var(--cv-line)'
  applyRow.append(applyButton)
  fieldsSection.append(fieldsHead, fieldsBody, applyRow)
  fieldsSection.style.flex = '1'
  const checksSection = el('section', 'cv-section')
  const checksHead = el('div', 'cv-section-head')
  checksHead.append(el('span', null, '检查'), el('span', 'count'))
  const checksBody = el('div', 'cv-section-body')
  checksSection.append(checksHead, checksBody)
  checksSection.style.flex = '0 0 38%'
  insp.append(fieldsSection, checksSection)

  // ---------------------------------------------------------------- bottom
  const checksStrip = el('div', 'cv-checks')
  const statusLine = el('div', 'cv-status-line', 'starting…')

  const main = el('div', 'cv-main')
  main.append(rail, view, insp)
  root.append(head, main, checksStrip, statusLine)
  host.append(root)

  const observer = new ResizeObserver(() => {
    root.classList.toggle('wide', root.clientWidth >= 860)
  })
  observer.observe(root)

  // ---------------------------------------------------------------- state
  let samples = []
  let catalog = null
  let currentDoc = null
  let building = false
  let polling = null
  let variantSet = null
  let selected = null

  const say = (text) => { statusLine.textContent = text }
  const command = (type, payload = {}) => {
    try { frame.contentWindow?.postMessage({ from: 'cadview-parent', type, ...payload }, '*') }
    catch (error) { /* the page may not be ready */ }
  }

  // ---------------------------------------------------------------- checks
  const renderChecks = (report) => {
    checksStrip.textContent = ''
    checksBody.textContent = ''
    if (!report) {
      checksStrip.textContent = 'checks unavailable'
      checksBody.append(el('div', 'cv-empty', '不可用'))
      return
    }
    const all = []
    for (const feature of report.features || []) {
      for (const check of feature.checks || []) all.push({ ...check, feature: feature.id })
    }
    const failed = all.filter((check) => !check.ok)
    const headText = failed.length
      ? `Checks · ${all.length - failed.length}/${all.length} ok · ${failed.length} failed`
      : `Checks · ${all.length}/${all.length} ok`
    const stripHead = el('div', failed.length ? 'cv-checks-head bad' : 'cv-checks-head', headText)
    checksStrip.append(stripHead)
    if (failed.length) {
      const list = el('ul')
      for (const item of failed) {
        list.append(el('li', null, `${item.feature}.${item.name}: ${item.hint || item.expected || 'failed'}`))
      }
      checksStrip.append(list)
    }
    for (const item of all) {
      const row = el('div', item.ok ? 'cv-check-row' : 'cv-check-row bad')
      row.append(el('span', 'mark', item.ok ? '✓' : '✗'))
      const body = el('div')
      body.append(el('div', null, `${item.feature}.${item.name}`))
      if (!item.ok && (item.hint || item.expected)) body.append(el('div', 'exp', item.hint || item.expected))
      row.append(body)
      checksBody.append(row)
    }
    checksHead.lastChild.textContent = `${all.length - failed.length}/${all.length}`
  }

  // ---------------------------------------------------------------- parts + tree
  const renderParts = (docs) => {
    partsBody.textContent = ''
    for (const doc of docs) {
      const button = el('button', doc.id === currentDoc?.id ? 'cv-part sel' : 'cv-part')
      button.setAttribute('aria-label', `零件 ${doc.name || doc.id}`)
      const image = el('img', 'thumb')
      image.loading = 'lazy'
      image.src = `${base}/api/docs/${doc.id}/render.png?view=iso`
      image.alt = ''
      const body = el('div')
      body.append(el('b', null, doc.name || doc.id), el('span', null, `v${doc.version} · ${doc.features} 特征`))
      button.append(image, body)
      button.addEventListener('click', () => { selectDocument(doc.id) })
      partsBody.append(button)
    }
    partsHead.lastChild.textContent = String(docs.length)
  }

  const renderTree = (doc) => {
    treeBody.textContent = ''
    const features = doc.features || []
    for (const feature of features) {
      const button = el('button', `cv-feat ${feature.enabled ? 'on' : 'off'}${selected === feature.id ? ' sel' : ''}`)
      button.setAttribute('aria-label', `${feature.id} ${feature.type} ${feature.enabled ? 'on' : 'off'}`)
      const dot = el('span', 'dot')
      const name = el('span', 'name')
      name.append(document.createTextNode(feature.id), el('small', null, feature.type))
      const sw = el('span', 'sw')
      button.append(dot, name, sw)
      button.addEventListener('click', (event) => {
        if (event.target === sw || sw.contains(event.target)) { toggle(feature); return }
        select(feature.id)
      })
      treeBody.append(button)
    }
    treeHead.lastChild.textContent = String(features.length)
  }

  // ---------------------------------------------------------------- inspector body
  const renderFields = (doc, featureId) => {
    fieldsBody.textContent = ''
    const feature = (doc.features || []).find((item) => item.id === featureId)
    if (!feature) {
      fieldsBody.append(el('div', 'cv-empty', '选择一个特征'))
      fieldsHead.lastChild.textContent = ''
      applyButton.disabled = true
      return
    }
    fieldsHead.lastChild.textContent = `${feature.id} · ${feature.type}`
    const inputs = {}
    for (const [key, value] of Object.entries(feature.params || {})) {
      const row = el('div', 'cv-field')
      row.append(el('label', null, key))
      const input = el('input')
      input.value = String(value)
      input.setAttribute('aria-label', `${feature.id} ${key}`)
      input.dataset.key = key
      inputs[key] = input
      row.append(input)
      fieldsBody.append(row)
    }
    applyButton.disabled = false
    applyButton.onclick = () => applyParams(feature, inputs)
  }

  const applyParams = async (feature, inputs) => {
    if (!currentDoc) return
    const params = {}
    for (const [key, input] of Object.entries(inputs)) {
      const raw = input.value.trim()
      if (raw === String(feature.params[key])) continue
      const number = Number(raw)
      params[key] = Number.isNaN(number) ? raw : number
    }
    if (!Object.keys(params).length) { say('参数没有变化'); return }
    say(`应用 ${feature.id} 的 ${Object.keys(params).join(', ')}…`)
    try {
      await fetchJSON(`${base}/api/docs/${currentDoc.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          base_version: currentDoc.version,
          ops: [{ op: 'update', id: feature.id, params }],
        }),
      })
      await reload()
      say(`已应用 ${feature.id} · v${currentDoc?.version}`)
    } catch (error) {
      say(`应用失败：${error.message}`)
    }
  }

  const select = (featureId) => {
    selected = featureId
    renderTree(currentDoc)
    renderFields(currentDoc, featureId)
  }

  const selectDocument = async (id) => {
    selected = null
    // Reload through the one path that keeps tree, fields, checks and metrics
    // in step with the document the viewport is about to show.
    await reload(id)
    frame.src = `${base}/api/kernel-view?doc=${encodeURIComponent(id)}`
    say(`已切换零件「${currentDoc?.name || id}」v${currentDoc?.version}`)
  }

  const toggle = async (feature) => {
    if (!currentDoc) return
    say(`切换 ${feature.id}…`)
    try {
      await fetchJSON(`${base}/api/docs/${currentDoc.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          base_version: currentDoc.version,
          ops: [{ op: 'update', id: feature.id, enabled: !feature.enabled }],
        }),
      })
      await reload()
    } catch (error) {
      say(`切换失败：${error.message}`)
    }
  }

  // ---------------------------------------------------------------- sample builder
  const rememberSample = (documentId, name) => {
    try { localStorage.setItem(`cadview.sample.${documentId}`, name) } catch (error) { /* private */ }
  }

  const sampleOfDocument = (doc) => {
    const label = String(doc?.name || '').toLowerCase()
    if (!label) return null
    return samples.find((sample) =>
      sample.name === label || String(sample.title).toLowerCase() === label) || null
  }

  const readParams = () => {
    const values = {}
    const row = root.querySelector('.cv-params')
    if (!row) return values
    for (const input of row.querySelectorAll('input')) {
      const spec = samples
        .find((sample) => sample.name === picker.value)
        ?.params.find((param) => param.name === input.dataset.name)
      if (!spec) continue
      values[spec.name] = spec.kind === 'int' ? parseInt(input.value, 10) : parseFloat(input.value)
    }
    return values
  }

  const renderParams = () => {
    const existing = root.querySelector('.cv-params')
    if (existing) existing.remove()
    const sample = samples.find((entry) => entry.name === picker.value)
    if (!sample) return
    const row = el('div', 'cv-params')
    row.style.cssText = 'display:flex;flex-wrap:wrap;gap:6px;padding:5px 10px;border-bottom:1px solid var(--cv-line);background:var(--cv-panel-2);align-items:center'
    for (const param of sample.params) {
      const label = el('label')
      label.style.cssText = 'display:flex;align-items:center;gap:4px;color:var(--cv-fg-3)'
      label.append(el('span', null, param.unit ? `${param.name} (${param.unit})` : param.name))
      const input = el('input')
      input.type = 'number'
      input.value = param.default
      input.min = param.min
      input.max = param.max
      input.step = param.kind === 'int' ? '1' : 'any'
      input.dataset.name = param.name
      input.setAttribute('aria-label', param.name)
      input.style.width = '66px'
      label.append(input)
      row.append(label)
    }
    head.after(row)
  }

  // ---------------------------------------------------------------- load / build
  const reload = async (targetId) => {
    try {
      const list = await fetchJSON(base + '/api/docs')
      if (!list.length) throw new Error('no documents')
      // Keep whatever the viewport is showing; only fall back to the newest
      // document when there is no current one (or it disappeared).
      const kept = currentDoc && list.find((item) => item.id === currentDoc.id)
      const chosen = targetId && list.find((item) => item.id === targetId)
      const id = (chosen || kept || list[0]).id
      const switched = Boolean(currentDoc) && currentDoc.id !== id
      const [doc, report] = await Promise.all([
        fetchJSON(`${base}/api/docs/${id}`),
        fetchJSON(`${base}/api/docs/${id}/checks`).catch(() => null),
      ])
      currentDoc = doc
      meta.textContent = `${doc.name || doc.id} · v${doc.version}`
      renderParts(list)
      renderTree(doc)
      if (selected && doc.features.some((item) => item.id === selected)) {
        renderFields(doc, selected)
      } else {
        selected = null
        renderFields(doc, null)
      }
      renderChecks(report)
      const shown = sampleOfDocument(doc)
      if (shown) {
        if (picker.value !== shown.name) { picker.value = shown.name; renderParams() }
      } else if (picker.value) {
        picker.value = ''
        renderParams()
      }
      if (switched) frame.src = `${base}/api/kernel-view?doc=${encodeURIComponent(id)}`
      const scene = await fetchJSON(`${base}/api/docs/${id}/scene`).catch(() => null)
      metricsText.textContent = scene
        ? `${scene.metrics.faces} 面 · ${Math.round(scene.metrics.volume).toLocaleString()} mm³`
        : ''
    } catch (error) {
      meta.textContent = 'service unreachable'
      say(`${error.message} — start python -m cadwork.service`)
    }
  }

  const build = async () => {
    buildButton.disabled = true
    picker.disabled = true
    building = true
    say(`构建 ${picker.value}…`)
    try {
      const doc = currentDoc || (await fetchJSON(base + '/api/docs'))[0]
      const result = await fetchJSON(`${base}/api/docs/${doc.id}/sample/${picker.value}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ params: readParams(), replace: true }),
      })
      rememberSample(doc.id, picker.value)
      await reload()
      say(`已构建 ${picker.value}${result?.document?.version ? ` · v${result.document.version}` : ''}`)
    } catch (error) {
      say(`构建失败：${error.message}`)
    } finally {
      buildButton.disabled = false
      picker.disabled = false
      building = false
    }
  }

  // ---------------------------------------------------------------- variants sheet
  // Candidates are compared in the model view itself: no thumbnails, no modal
  // over the viewport. Selecting a row loads that candidate's STEP here.
  const sheet = el('div', 'cv-sheet')
  sheet.hidden = true
  sheet.innerHTML = `
    <div class="cv-sheet-head">
      <span>变体并置</span>
      <span class="cv-sheet-note" aria-live="polite"></span>
      <button class="cv-x" aria-label="关闭变体面板" style="margin-left:auto">x</button>
    </div>
    <div class="cv-form">
      <label>特征 <select class="cv-feature" aria-label="变体特征"></select></label>
      <label>参数 <select class="cv-param" aria-label="变体参数"></select></label>
      <label>取值 <input type="text" class="cv-values" aria-label="变体取值"></label>
      <label><input type="checkbox" class="cv-base" aria-label="包含当前" checked> 含当前</label>
      <button class="primary cv-generate">生成</button>
      <button class="cv-apply" disabled>应用所选</button>
    </div>
    <div class="cv-vrows" role="list"></div>`
  view.append(sheet)

  const sheetNote = sheet.querySelector('.cv-sheet-note')
  const modalFeature = sheet.querySelector('.cv-feature')
  const modalParam = sheet.querySelector('.cv-param')
  const modalValues = sheet.querySelector('.cv-values')
  const modalBase = sheet.querySelector('.cv-base')
  const rowsBox = sheet.querySelector('.cv-vrows')
  const variantApply = sheet.querySelector('.cv-apply')

  let chosen = null

  const catalogOf = async (type) => {
    if (!catalog) catalog = await fetchJSON(base + '/api/catalog')
    return catalog.find((entry) => entry.type === type)
  }

  const suggestedValues = (spec) => {
    if (spec.choices) return spec.choices.slice(0, 3).join(', ')
    const fallback = Number(spec.default)
    const low = spec.min != null ? Number(spec.min) : fallback * 0.5
    const high = spec.max != null ? Number(spec.max) : fallback * 2
    return [...new Set([fallback * 0.6, fallback, fallback * 1.5]
      .map((value) => Math.min(Math.max(value, low), high))
      .map((value) => (spec.kind === 'int' ? Math.round(value) : Math.round(value * 100) / 100)))]
      .join(', ')
  }

  const currentFeature = () =>
    (currentDoc?.features || []).find((item) => item.id === modalFeature.value) || null

  const applySuggestion = async () => {
    const feature = currentFeature()
    if (!feature) return
    const spec = await catalogOf(feature.type)
    const param = spec?.params?.[modalParam.value]
    modalValues.value = param ? suggestedValues(param) : ''
    sheetNote.textContent = '选一个参数，给一组取值，生成后在视口里逐个看'
  }

  const fillParams = async () => {
    modalParam.textContent = ''
    const feature = currentFeature()
    if (!feature) return
    const spec = await catalogOf(feature.type)
    for (const [name, param] of Object.entries(spec?.params || {})) {
      const option = el('option', null, param.unit ? `${name} (${param.unit})` : name)
      option.value = name
      modalParam.append(option)
    }
    // A shape parameter is what people mean to vary; x/y are rarely interesting.
    const preferred = ['cb_diameter', 'cs_diameter', 'diameter', 'length', 'width',
      'height', 'thickness', 'depth', 'cb_depth', 'cs_depth', 'radius', 'amount']
    const names = Object.keys(spec?.params || {})
    const pick = preferred.find((name) => names.includes(name) && feature.params[name] != null)
      || preferred.find((name) => names.includes(name))
      || Object.keys(feature.params || {}).find((name) => names.includes(name))
    if (pick) modalParam.value = pick
    await applySuggestion()
  }

  const preview = (variant, row) => {
    for (const other of rowsBox.children) other.classList.remove('sel')
    row.classList.add('sel')
    chosen = variant
    variantApply.disabled = false
    sheetNote.textContent = `预览「${variant.label}」· 文档尚未改动`
    command('preview', { url: base + variant.step, label: `预览 ${variant.label}` })
  }

  const renderRows = () => {
    rowsBox.textContent = ''
    chosen = null
    variantApply.disabled = true
    const variants = variantSet?.variants || []
    for (const variant of variants) {
      const row = el('button', variant.ok ? 'cv-vrow' : 'cv-vrow bad')
      row.setAttribute('aria-label', `${variant.label} ${variant.ok ? '可用' : '不可用'}`)
      row.append(el('b', null, variant.label))
      row.append(el('span', null, variant.ok
        ? `${variant.faces} 面 · ${Math.round(variant.volume).toLocaleString()} mm³ · ${variant.seconds}s`
        : (variant.error?.message || '构建失败')))
      if (variant.ok && variant.step) row.addEventListener('click', () => preview(variant, row))
      rowsBox.append(row)
    }
    if (!variants.length) rowsBox.append(el('div', 'cv-empty', '还没有候选'))
    // Preview a changed candidate, not the baseline card.
    const first = variants.find((item) => item.ok && item.step && item.ops.length)
      || variants.find((item) => item.ok && item.step)
    if (first) {
      const row = [...rowsBox.children].find((child) => child.tagName === 'BUTTON')
      if (row) preview(first, row)
    }
  }

  const buildVariants = async () => {
    if (!currentDoc) return
    const raw = modalValues.value.trim().split(/[,，\s]+/).filter(Boolean)
    if (!raw.length) { sheetNote.textContent = '先给一组取值，例如 12, 18, 24'; return }
    const feature = currentFeature()
    const spec = feature ? await catalogOf(feature.type) : null
    const param = spec?.params?.[modalParam.value]
    const values = raw.map((item) => {
      const number = Number(item)
      if (Number.isNaN(number)) return item
      return param?.kind === 'int' ? Math.round(number) : number
    })
    sheetNote.textContent = '构建中…'
    try {
      variantSet = await fetchJSON(`${base}/api/docs/${currentDoc.id}/variants`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          feature: modalFeature.value,
          params: { [modalParam.value]: values },
          include_base: modalBase.checked,
          thumbs: false,
          base_version: currentDoc.version,
        }),
      })
      renderRows()
      const failed = variantSet.variants.filter((item) => !item.ok).length
      sheetNote.textContent = `${variantSet.variants.length} 个候选 · 文档未改动`
        + (failed ? ` · ${failed} 个不可用` : '')
    } catch (error) {
      rowsBox.textContent = ''
      sheetNote.textContent = `生成失败：${error.message}`
    }
  }

  const applyChosen = async () => {
    if (!chosen || !variantSet) return
    if (variantSet.document !== currentDoc?.id) {
      sheetNote.textContent = '这组候选属于另一个零件，请重新生成'
      return
    }
    const label = chosen.label
    sheetNote.textContent = `应用「${label}」…`
    try {
      await fetchJSON(`${base}/api/variants/${variantSet.set}/${chosen.index}/apply`, { method: 'POST' })
      variantSet = null
      chosen = null
      variantApply.disabled = true
      await reload()
      command('document')
      sheet.hidden = true
      say(`已应用「${label}」· v${currentDoc?.version}`)
    } catch (error) {
      sheetNote.textContent = `应用失败：${error.message}`
    }
  }

  const closeSheet = () => {
    sheet.hidden = true
    if (chosen) {
      chosen = null
      variantApply.disabled = true
      command('document')
    }
  }

  const openVariants = async () => {
    sheet.hidden = false
    if (variantSet && variantSet.document !== currentDoc?.id) {
      variantSet = null
      rowsBox.textContent = ''
    }
    modalFeature.textContent = ''
    for (const feature of currentDoc?.features || []) {
      const option = el('option', null, `${feature.id} · ${feature.type}`)
      option.value = feature.id
      modalFeature.append(option)
    }
    // Vary what is selected in the tree; the tip is only a fallback.
    const ids = [...modalFeature.options].map((option) => option.value)
    if (selected && ids.includes(selected)) {
      modalFeature.value = selected
    } else if (modalFeature.options.length) {
      modalFeature.selectedIndex = modalFeature.options.length - 1
    }
    await fillParams()
    if (variantSet) renderRows()
    else rowsBox.textContent = ''
    if (!variantSet) sheetNote.textContent = '选一个特征与参数，生成后在视口里逐个看'
  }

  variantsButton.addEventListener('click', () => { openVariants() })
  sheet.querySelector('.cv-x').addEventListener('click', closeSheet)
  modalFeature.addEventListener('change', () => { fillParams() })
  modalParam.addEventListener('change', () => { applySuggestion() })
  sheet.querySelector('.cv-generate').addEventListener('click', () => { buildVariants() })
  variantApply.addEventListener('click', () => { applyChosen() })

  // ---------------------------------------------------------------- help
  const help = el('div', 'cv-modal')
  help.hidden = true
  help.innerHTML = `
    <div class="cv-modal-box">
      <div class="cv-modal-head"><span>演示脚本与快捷键</span>
        <button class="cv-x" aria-label="关闭帮助" style="margin-left:auto">×</button></div>
      <ol style="margin:0;padding-left:18px;color:var(--cv-fg-2);line-height:1.95">
        <li>左栏选一个零件</li>
        <li>点一个特征 → 右侧改参数 → 点「应用参数」</li>
        <li>点「变体」→ 生成候选 → 点一张卡落地到文档</li>
        <li>点「STEP」导出模型</li>
        <li>点宿主右上角全屏，得到三栏工作区</li>
      </ol>
      <div style="color:var(--cv-fg-3);font-size:11px;line-height:2;border-top:1px solid var(--cv-line);padding-top:8px">
        1–4 视图 · F 适配 · W 线框 · M 测量 · X 剖切 · 空格 启停所选特征 · Ctrl+Z 撤销 · Esc 关闭
      </div>
    </div>`
  root.append(help)
  help.querySelector('.cv-x').addEventListener('click', () => { help.hidden = true })
  helpButton.addEventListener('click', () => { help.hidden = !help.hidden })

  // ---------------------------------------------------------------- keyboard
  const isTyping = (target) => {
    const tag = target?.tagName
    return tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA' || Boolean(target?.isContentEditable)
  }
  const toggleSelected = () => {
    const feature = (currentDoc?.features || []).find((item) => item.id === selected)
    if (feature) toggle(feature)
  }
  const onKey = (event) => {
    if (isTyping(event.target) || !root.isConnected) return
    if (event.ctrlKey || event.metaKey) {
      if (event.key.toLowerCase() === 'z') { event.preventDefault(); undoButton.click() }
      return
    }
    const view = { '1': 'iso', '2': 'front', '3': 'top', '4': 'right' }[event.key]
    if (view) { command('view', { name: view }); return }
    const key = event.key.toLowerCase()
    if (key === 'f') { command('fit'); return }
    if (key === 'w') { wireButton.click(); return }
    if (key === 'm') { measureButton.click(); return }
    if (key === 'x') { sectionButton.click(); return }
    if (event.key === ' ') { event.preventDefault(); toggleSelected(); return }
    if (event.key === 'Escape') { help.hidden = true; if (!sheet.hidden) closeSheet() }
  }
  document.addEventListener('keydown', onKey)

  buildButton.addEventListener('click', () => { build() })
  reloadButton.addEventListener('click', () => {
    frame.src = `${base}/api/kernel-view?t=${Date.now()}`
    reload()
  })
  undoButton.addEventListener('click', async () => {
    if (!currentDoc) return
    try {
      const result = await fetchJSON(`${base}/api/docs/${currentDoc.id}/undo`, { method: 'POST' })
      await reload()
      say(`已撤销 · v${result?.document?.version ?? currentDoc.version}`)
    } catch (error) {
      say(`撤销失败：${error.message}`)
    }
  })
  const exportAs = async (format) => {
    if (!currentDoc) return
    say(`导出 ${format.toUpperCase()}…`)
    try {
      const response = await fetch(`${base}/api/docs/${currentDoc.id}/export/${format}`)
      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`)
      const blob = await response.blob()
      const name = `${currentDoc.name || 'part'}.${format}`
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = name
      link.click()
      URL.revokeObjectURL(link.href)
      say(`已导出 ${name} · ${Math.round(blob.size / 1024)} KB`)
    } catch (error) {
      say(`导出失败：${error.message}`)
    }
  }
  stepButton.addEventListener('click', () => { exportAs('step') })
  stlButton.addEventListener('click', () => { exportAs('stl') })
  picker.addEventListener('change', () => { renderParams(); build() })

  const onMessage = (event) => {
    const data = event.data
    if (!data || data.from !== 'cadview' || typeof data.text !== 'string') return
    pickText.textContent = data.text
  }
  window.addEventListener('message', onMessage)

  // Theme: the 3D page cannot read host tokens, so pass the resolved background.
  const pushTheme = () => {
    const background = getComputedStyle(root).getPropertyValue('--cv-bg').trim() || '#0b0e13'
    const foreground = getComputedStyle(root).getPropertyValue('--cv-fg-2').trim() || '#a9b7ca'
    try {
      frame.contentWindow?.postMessage({ from: 'cadview-parent', type: 'theme',
        background, foreground }, '*')
    } catch (error) { /* not ready */ }
  }
  frame.addEventListener('load', () => {
    pushTheme()
    command('fit')
  })

  const start = async () => {
    try {
      samples = await fetchJSON(base + '/api/samples')
      picker.textContent = ''
      const custom = el('option', null, '自定义零件')
      custom.value = ''
      custom.disabled = true
      picker.append(custom)
      for (const sample of samples) {
        const option = el('option', null, sample.title)
        option.value = sample.name
        picker.append(option)
      }
      await reload()
      const match = sampleOfDocument(currentDoc)
      if (match) picker.value = match.name
      renderParams()
      say('就绪 · 选零件或特征，或点「变体」比较候选')
    } catch (error) {
      meta.textContent = 'service unreachable'
      say(`${error.message} — start python -m cadwork.service`)
    }
  }

  const watch = () => {
    if (polling) return
    polling = setInterval(async () => {
      if (document.hidden || building) return
      try {
        const list = await fetchJSON(base + '/api/docs')
        if (!list.length || !currentDoc) return
        const fresh = list.find((item) => item.id === currentDoc.id)
        if (!fresh || fresh.version !== currentDoc.version) await reload()
      } catch (error) { /* service down: the status line says so */ }
    }, 2500)
  }

  watch()
  start()

  return () => {
    if (polling) clearInterval(polling)
    observer.disconnect()
    window.removeEventListener('message', onMessage)
    document.removeEventListener('keydown', onKey)
    root.remove()
  }
}
