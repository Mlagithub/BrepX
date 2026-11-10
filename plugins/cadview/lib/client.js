/**
 * Browser half of cadview — the small half.
 *
 * Registers a right-sidebar tab type and its body; the body lazily imports the
 * viewport module (three.js + the SMLib kernel) from the cadwork service.
 *
 * Every step is guarded and reported: a workbench plugin must never take the
 * whole web boot down with it, and a half-finished registration should say so
 * in the page instead of disappearing into the console.
 */
window.__ModuleLoader__.load({
  id: 'cadview',
  factory: (require) => {
    const name = 'cadview'
    // Cordis throws on reading a service that is not injected.
    const inject = ['slots', 'sidebarRightTabs', 'sidebarRight']
    const KIND = 'cadview'

    const serviceBase = () => {
      try {
        return localStorage.getItem('cadview.service') || 'http://127.0.0.1:8765'
      } catch (error) {
        return 'http://127.0.0.1:8765'
      }
    }

    const banner = (text) => {
      try {
        const id = 'cadview-banner'
        let node = document.getElementById(id)
        if (!node) {
          node = document.createElement('div')
          node.id = id
          node.style.cssText = 'position:fixed;left:12px;bottom:12px;z-index:2147483647;max-width:60vw;' +
            'padding:8px 12px;border-radius:8px;background:#2a1520;color:#ffb4c8;border:1px solid #5a2536;' +
            'font:12px/1.5 system-ui,sans-serif;white-space:pre-wrap'
          document.body.appendChild(node)
        }
        node.textContent = text
      } catch (error) {
        /* a banner must never be the failure */
      }
    }

    const report = (where, error) => {
      const text = `[cadview] ${where}: ${error && error.message ? error.message : error}`
      console.error(text, error)
      banner(text)
    }

    function makeBody(React) {
      return function CadViewBody() {
        const host = React.useRef(null)
        React.useEffect(() => {
          const base = serviceBase()
          const element = host.current
          if (!element) return undefined
          let dispose = null
          let cancelled = false
          element.textContent = 'loading viewport module…'
          element.style.padding = '12px'
          element.style.color = '#7f8ea5'
          element.style.font = '12px/1.5 system-ui, sans-serif'
          import(base + '/api/plugin/viewport.mjs')
            .then((module) => {
              if (cancelled || !host.current) return
              element.style.padding = '0'
              dispose = module.mountViewport(element, base)
            })
            .catch((error) => {
              if (host.current) {
                element.textContent =
                  `viewport failed: ${error.message}` +
                  ` — is python -m cadwork.service running on 8765?`
              }
              report('viewport import', error)
            })
          return () => {
            cancelled = true
            if (typeof dispose === 'function') dispose()
          }
        }, [])
        return React.createElement('div', {
          ref: host,
          style: { height: '100%', minHeight: 0, overflow: 'hidden' },
        })
      }
    }

    function apply(ctx) {
      try {
        if (typeof document === 'undefined') return
        console.info('[cadview] apply', Object.keys(ctx || {}).length, 'services')

        let React = null
        try {
          React = require('react')
        } catch (error) {
          report('require react', error)
          return
        }
        if (!React || typeof React.createElement !== 'function') {
          report('require react', 'host returned no React')
          return
        }
        const Body = makeBody(React)

        const tabs = ctx && ctx.sidebarRightTabs
        const slots = ctx && ctx.slots
        if (!tabs || typeof tabs.register !== 'function') {
          report('sidebar tab', 'ctx.sidebarRightTabs is unavailable')
          return
        }
        if (!slots || typeof slots.register !== 'function') {
          report('sidebar tab', 'ctx.slots is unavailable')
          return
        }

        ctx.effect(() => {
          let disposeType = null
          let disposeBody = null
          try {
            disposeType = tabs.register({
              id: KIND,
              kind: KIND,
              title: () => 'CAD',
              guide: [{
                id: KIND,
                title: () => 'CAD',
                description: () => 'Model with exact B-Rep and pick faces',
              }],
            })
            console.info('[cadview] tab type registered')
            disposeBody = slots.register({ name: 'sidebar.right.pane.tab', key: KIND }, Body)
            console.info('[cadview] tab body registered')
          } catch (error) {
            report('register tab', error)
          }
          return () => {
            if (typeof disposeBody === 'function') disposeBody()
            if (typeof disposeType === 'function') disposeType()
          }
        }, 'cadview: sidebar tab')

        if (ctx.sidebarRight && typeof ctx.sidebarRight.openTab === 'function' && !globalThis.__cadviewOpened) {
          globalThis.__cadviewOpened = true
          Promise.resolve()
            .then(() => ctx.sidebarRight.openTab(KIND))
            .then(() => console.info('[cadview] tab opened'))
            .catch((error) => console.info('[cadview] openTab skipped:', error.message))
        }
      } catch (error) {
        report('apply', error)
      }
    }

    return { name, inject, apply }
  },
})
