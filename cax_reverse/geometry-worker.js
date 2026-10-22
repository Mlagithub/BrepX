// One kernel instance per operation: termination releases its complete native heap.
import createSMLib from './kernel/smlib.5dd21e03709b46c9.js';
self.onmessage = async ({data}) => {
  try {
    const module = await createSMLib({
      instantiateWasm(imports, success) {
        WebAssembly.instantiate(data.module, imports).then(instance => success(instance, data.module)).catch(error => self.postMessage({ok:false,error:String(error)}));
        return {};
      },
      print: () => {}, printErr: text => console.debug('[SMLib]', text)
    });
    const request = {...data.request, inputs: []};
    (data.inputs || []).forEach((content, i) => {
      const path = `/input-${i}.smb`;
      module.FS.writeFile(path, content);
      request.inputs.push(path);
    });
    if (request.action !== 'health') request.output = '/result.smb';
    const start = performance.now();
    const result = JSON.parse(module.ccall('smlib_execute', 'string', ['string'], [JSON.stringify(request)]));
    if (result.ok && result.shape && request.output && !result.empty) result.brep = module.FS.readFile(request.output, {encoding:'utf8'});
    result.computeMs = performance.now() - start;
    result.heapBytes = module.HEAPU8.buffer.byteLength;
    self.postMessage(result);
  } catch(error) { self.postMessage({ok:false,error:String(error.message || error)}); }
};
