/**
 * Browser half of cadview: one full-width model workspace.
 *
 * The workspace is a global main panel, so the conversation's composer is not
 * mounted beside a second composer. The workbench sends its draft through the
 * session-scoped conversation controller and uses the CAD service for geometry.
 */
window.__ModuleLoader__.load({
  id: 'cadview',
  factory: (require) => {
    const name = 'cadview'
    const inject = ['slots', 'layout', 'sessions']
    const KIND = 'cad-workbench'

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

    const currentSessionId = (ctx) => {
      try {
        const selected = ctx.sessions?.list?.getSnapshot?.()?.currentId
        if (selected) return selected
      } catch (error) {
        /* service snapshot is unavailable; fall through to the persisted selection */
      }
      try {
        const stored = JSON.parse(localStorage.getItem('dsh.sessions.current') || '{}')
        return stored.sessionId || undefined
      } catch (error) {
        return undefined
      }
    }

    const sendPrompt = async (ctx, sessionId, text) => {
      if (!sessionId) throw new Error('没有活动会话；请在左侧选择一个会话')
      const sessions = ctx.sessions
      if (!sessions || typeof sessions.using !== 'function') {
        throw new Error('当前客户端没有提供会话接口')
      }
      const requestId = globalThis.crypto && typeof globalThis.crypto.randomUUID === 'function'
        ? globalThis.crypto.randomUUID()
        : `cad-${Date.now()}-${Math.random().toString(16).slice(2)}`
      await sessions.using(sessionId, { source: 'mainView' }, async (reference) => {
        const result = await reference.binding.session.prompt(
          [{ type: 'text', text }],
          'queue',
          new AbortController().signal,
          requestId,
        )
        if (result && result.ok === false) {
          throw new Error(result.error?.message || 'Agent 拒绝了这条消息')
        }
      })
    }

    const PanelIcon = ({ size = 16 }) => {
      const React = require('react')
      return React.createElement('svg', {
        width: size,
        height: size,
        viewBox: '0 0 24 24',
        fill: 'none',
        stroke: 'currentColor',
        strokeWidth: 1.7,
        strokeLinecap: 'round',
        strokeLinejoin: 'round',
        'aria-hidden': 'true',
      },
      React.createElement('path', { d: 'm12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Z' }),
      React.createElement('path', { d: 'm4 7.5 8 4.5 8-4.5M12 12v9' }))
    }

    function makeBody(React, ctx) {
      return function CadWorkbenchBody(props) {
        const host = React.useRef(null)
        const controller = React.useRef(null)
        const sessionId = props.useSessions
          ? props.useSessions((snapshot) => snapshot.currentId)
          : currentSessionId(ctx)

        React.useEffect(() => {
          const element = host.current
          if (!element) return undefined
          let cancelled = false
          element.textContent = 'loading workbench…'
          element.style.cssText = 'position:relative;height:100%;min-height:0;overflow:hidden;' +
            'color:var(--dsw-alias-label-tertiary,#7f8ea5);font:12px/1.5 system-ui,sans-serif'

          import(`${serviceBase()}/api/plugin/workbench.mjs`)
            .then((module) => {
              if (cancelled || !host.current) return
              element.style.cssText = 'position:relative;height:100%;min-height:0;overflow:hidden'
              controller.current = module.mountWorkbench(element, {
                base: serviceBase(),
                sessionId,
                getSessionId: () => currentSessionId(ctx),
                onChat: () => ctx.layout.selectPanel(null),
                onToggleNavigation: () => ctx.layout.toggleSidebar(),
                sendPrompt: (sid, text) => sendPrompt(ctx, sid, text),
              })
            })
            .catch((error) => {
              if (host.current) {
                host.current.textContent = `workbench failed: ${error.message}`
              }
              report('workbench import', error)
            })

          return () => {
            cancelled = true
            if (controller.current && typeof controller.current.dispose === 'function') {
              controller.current.dispose()
            }
            controller.current = null
          }
        }, [])

        React.useEffect(() => {
          if (controller.current && sessionId) controller.current.setSession(sessionId)
        }, [sessionId])

        return React.createElement('div', {
          ref: host,
          style: { position: 'relative', height: '100%', minHeight: 0, overflow: 'hidden' },
        })
      }
    }

    function apply(ctx) {
      try {
        if (typeof document === 'undefined') return

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
        if (!ctx.slots || typeof ctx.slots.register !== 'function') {
          report('slots', 'ctx.slots is unavailable')
          return
        }
        if (!ctx.layout || typeof ctx.layout.selectPanel !== 'function') {
          report('layout', 'ctx.layout is unavailable')
          return
        }

        const Workbench = makeBody(React, ctx)

        ctx.effect(() => {
          let disposeMain = null
          let disposePanel = null
          try {
            disposeMain = ctx.slots.inject('main', () =>
              ctx.slots.register({ name: 'main', key: KIND }, Workbench))

            disposePanel = ctx.slots.inject('sidebar.panellist', () =>
              ctx.slots.register({
                name: 'sidebar.panellist',
                id: KIND,
                order: 0,
                label: () => '模型工作台',
              }, PanelIcon))
          } catch (error) {
            report('register workbench', error)
          }
          return () => {
            if (typeof disposePanel === 'function') disposePanel()
            if (typeof disposeMain === 'function') disposeMain()
          }
        }, 'cadview: model workbench')

        Promise.resolve()
          .then(() => {
            ctx.layout.closeRightbar()
            ctx.layout.selectPanel(KIND)
          })
          .catch((error) => report('open workbench', error))
      } catch (error) {
        report('apply', error)
      }
    }

    return { name, inject, apply }
  },
})
