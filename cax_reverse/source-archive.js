const ARCHIVE_URL = './sources';

export async function retainOriginalStep(file, telemetry = globalThis.smlibTelemetry, fetchImpl = fetch) {
  let operation = '';
  try {
    operation = crypto.randomUUID().replaceAll('-', '');
    const session = telemetry?.state?.().session || '';
    const response = await fetchImpl(ARCHIVE_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/octet-stream',
        'X-Filename': encodeURIComponent(file.name),
        'X-SMLib-Session': session,
        'X-SMLib-Operation': operation,
      },
      body: file,
      credentials: 'omit',
      cache: 'no-store',
      signal: AbortSignal.timeout(120000),
    });
    const receipt = await response.json();
    if (!response.ok || receipt?.ok !== true || receipt.bytes !== file.size ||
        !/^[a-f0-9]{32}$/.test(receipt.archiveId || '') ||
        !/^[a-f0-9]{64}$/.test(receipt.sha256 || '')) {
      throw Error('archive_unconfirmed');
    }
    try { telemetry?.record?.('ui', {action:'source_archive', status:'ok', operation}); } catch { /* Optional diagnostics. */ }
    return {retained:true, archiveId:receipt.archiveId};
  } catch {
    try { telemetry?.record?.('ui', {action:'source_archive', status:'fail', operation,
      error:{category:'network', message:'Original STEP was not retained'}}); } catch { /* Optional diagnostics. */ }
    return {retained:false};
  }
}
