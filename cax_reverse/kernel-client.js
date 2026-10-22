export class KernelClient {
  constructor(progress) { this.progress = progress; this.module = null; this.worker = null; this.workerURL = null; }
  async init() {
    this.progress('正在加载建模程序…');
    const sourceURL = new URL('./geometry-worker.js', import.meta.url);
    const workerResponse = await fetch(sourceURL);
    if (!workerResponse.ok) throw Error(`Worker 下载失败：HTTP ${workerResponse.status}`);
    const source = await workerResponse.text();
    const importLine = source.match(/^import createSMLib from ['"]([^'"]+)['"];$/m);
    if (!importLine) throw Error('Worker 加载程序格式无效');
    const loaderResponse = await fetch(new URL(importLine[1], sourceURL));
    if (!loaderResponse.ok) throw Error(`内核加载程序下载失败：HTTP ${loaderResponse.status}`);
    // Blob URLs keep all operation code in memory. New Workers never refetch scripts.
    const loaderURL = URL.createObjectURL(new Blob([await loaderResponse.text()], {type:'text/javascript'}));
    this.workerURL = URL.createObjectURL(new Blob([
      source.replace(importLine[0], `import createSMLib from ${JSON.stringify(loaderURL)};`)
    ], {type:'text/javascript'}));
    this.progress('正在下载建模内核…');
    const response = await fetch(new URL('./kernel/smlib.8ff7d050f38c00d4.wasm', import.meta.url));
    if (!response.ok) throw Error(`内核下载失败：HTTP ${response.status}`);
    const length = response.headers.get('Content-Encoding') ? 0 : Number(response.headers.get('Content-Length'));
    const reader = response.body.getReader(), chunks = []; let received = 0;
    while (true) {
      const {done, value} = await reader.read(); if (done) break;
      chunks.push(value); received += value.length;
      this.progress(`正在下载内核 ${length ? Math.min(100, Math.round(received / length * 100))+'%' : (received/1048576).toFixed(1)+' MB'}`);
    }
    const bytes = new Uint8Array(received); let offset = 0;
    for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
    this.progress('正在编译浏览器建模内核…');
    this.module = await WebAssembly.compile(bytes);
    const health = await this.run({action:'health'});
    if (health.kernel !== 'SMLib' || health.usd !== false) throw Error('内核身份检查失败');
    this.progress('SMLib 已就绪 · 本机计算');
    return health;
  }
  async run(request, inputs = []) {
    const telemetry = globalThis.smlibTelemetry, started = performance.now();
    let operation;
    try { operation = telemetry?.begin(request.action, {...request, inputCount:inputs.length}); } catch { /* Diagnostics never block modeling. */ }
    try {
      const result = await this.execute(request, inputs);
      try { telemetry?.end(operation, request.action, started, null, result); } catch { /* Optional diagnostics. */ }
      return result;
    } catch (error) {
      try { telemetry?.end(operation, request.action, started, error); } catch { /* Preserve the actual kernel error. */ }
      throw error;
    }
  }
  execute(request, inputs = []) {
    if (!this.module) return Promise.reject(Error('建模内核尚未就绪'));
    if (this.worker) return Promise.reject(Error('请等待当前操作完成'));
    return new Promise((resolve, reject) => {
      const worker = new Worker(this.workerURL, {type:'module'});
      this.worker = worker;
      const finish = (error, result) => {
        clearTimeout(timer); worker.terminate(); this.worker = null; this.cancel = null;
        if (error) reject(error); else resolve(result);
      };
      const timer = setTimeout(() => finish(Error('运算超过 45 秒，已停止。原模型已保留。')), 45000);
      this.cancel = () => finish(Error('操作已取消，原模型已保留。'));
      worker.onerror = event => finish(Error(event.message || '内核运算异常，原模型已保留。'));
      worker.onmessage = ({data}) => data.ok ? finish(null, data) : finish(Error(data.error || 'SMLib 运算失败'));
      worker.postMessage({module:this.module, request, inputs});
    });
  }
}
