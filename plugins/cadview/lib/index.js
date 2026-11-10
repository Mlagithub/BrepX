/**
 * Host half: a no-op Cordis plugin. The workbench lives in the browser half
 * (`lib/client.js`), which the web client discovers through `dsh.client`.
 * This half exists so the package is one entry in the host Loader.
 */

export const name = 'cadview'

export const inject = []

export function apply() {}
