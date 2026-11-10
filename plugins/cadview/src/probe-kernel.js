/**
 * Kernel probe: the smallest possible consumer of smlibpy-three's browser
 * bridge. It exists to answer one question — does `init({ wasmBinary })`
 * resolve in a browser at all? The viewport does not import this file.
 */
import { init } from '@classcad/smlibpy-three/init'

window.__kernelProbe = async (bytes) => {
  const started = performance.now()
  const module = await init({ wasmBinary: bytes })
  return {
    milliseconds: Math.round(performance.now() - started),
    exports: Object.keys(module).length,
  }
}
