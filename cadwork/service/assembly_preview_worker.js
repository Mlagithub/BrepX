"use strict";

/*
 * Decode one derived assembly-preview bundle off the main thread.
 *
 * The bundle is untrusted display data: every structural check runs before a
 * prototype array is exposed. A malformed bundle must produce one stable error
 * code instead of a partially decoded preview, because a partially accepted
 * mesh would render a wrong model as if it were authoritative.
 *
 * The manifest is parsed here, never in the viewport. Prototype arrays are
 * copied out of the bundle so every returned typed array owns its buffer and
 * can be transferred to the main thread.
 */

const MAGIC_0 = 0x42;
const MAGIC_1 = 0x50;
const MAGIC_2 = 0x58;
const MAGIC_3 = 0x56;
const FORMAT_VERSION = 1;
const HEADER_SIZE = 16;
const ALIGNMENT = 8;
const MANIFEST_SCHEMA = "brepx-assembly-preview";
const SCHEMA_VERSION = 1;
const MANIFEST_UNITS = "mm";
const MAX_MANIFEST_BYTES = 16 * 1024 * 1024;
const MAX_BUNDLE_BYTES = 512 * 1024 * 1024;
const MAX_PROTOTYPES = 1024;
const MAX_INSTANCES = 65536;
const MAX_LEAVES = 65536;
const KEY_PATTERN = /^[0-9a-f]{64}$/;
const COLOR_PATTERN = /^#[0-9a-fA-F]{6}$/;

const fail = (code, message) => {
  const error = new Error(message);
  error.code = code;
  throw error;
};

const align8 = (value) => (value + ALIGNMENT - 1) & ~(ALIGNMENT - 1);

const isCount = (value) => typeof value === "number" && Number.isInteger(value) && value >= 0;

const readCount = (value, field, limit) => {
  if (!isCount(value)) fail("BAD_MANIFEST_FIELD", field + " must be a non-negative integer");
  if (limit != null && value > limit) fail("COUNT_LIMIT", field + " exceeds " + limit);
  return value;
};

const readText = (value, field, allowEmpty = false) => {
  if (typeof value !== "string" || (!allowEmpty && value.length === 0)) {
    fail("BAD_MANIFEST_FIELD", field + " must be a " + (allowEmpty ? "" : "non-empty ") + "string");
  }
  return value;
};

const readKey = (value, field) => {
  if (typeof value !== "string" || !KEY_PATTERN.test(value)) {
    fail("BAD_KEY", field + " must be 64 lowercase hexadecimal characters");
  }
  return value;
};

const readObject = (value, field) => {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    fail("BAD_MANIFEST_FIELD", field + " must be an object");
  }
  return value;
};

const readArray = (value, field) => {
  if (!Array.isArray(value)) fail("BAD_MANIFEST_FIELD", field + " must be an array");
  return value;
};

const readFinite = (value, field) => {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    fail("BAD_MANIFEST_FIELD", field + " must be a finite number");
  }
  return value;
};

const readVector3 = (value, field) => {
  if (!Array.isArray(value) || value.length !== 3) {
    fail("BAD_MANIFEST_FIELD", field + " must have 3 components");
  }
  return [readFinite(value[0], field + "[0]"), readFinite(value[1], field + "[1]"), readFinite(value[2], field + "[2]")];
};

const prototypeBlobSize = (positionCount, indexCount, edgePointCount) => {
  readCount(positionCount, "positionCount");
  readCount(indexCount, "indexCount");
  readCount(edgePointCount, "edgePointCount");
  if (indexCount % 3 !== 0) fail("BAD_INDEX_COUNT", "indexCount is not divisible by 3");
  if (edgePointCount % 2 !== 0) fail("BAD_EDGE_COUNT", "edgePointCount is odd");
  return positionCount * 3 * 4 + indexCount * 4 + (indexCount / 3) * 4 + edgePointCount * 3 * 4;
};

const validatePrototypeRecord = (record, index, seenKeys) => {
  const path = "prototypes[" + index + "]";
  readObject(record, path);
  const prototypeKey = readKey(record.prototypeKey, path + ".prototypeKey");
  if (seenKeys.has(prototypeKey)) {
    fail("DUPLICATE_PROTOTYPE_KEY", "duplicate prototype key " + prototypeKey);
  }
  seenKeys.add(prototypeKey);
  readText(record.sourceDocumentId, path + ".sourceDocumentId");
  readCount(record.sourceVersion, path + ".sourceVersion");
  readText(record.sourceIdentity, path + ".sourceIdentity");
  readText(record.faceKeySource, path + ".faceKeySource");
  const faceKeys = readArray(record.faceKeys, path + ".faceKeys");
  const seenFaceKeys = new Set();
  for (let faceIndex = 0; faceIndex < faceKeys.length; faceIndex += 1) {
    const faceKey = readText(faceKeys[faceIndex], path + ".faceKeys[" + faceIndex + "]");
    if (seenFaceKeys.has(faceKey)) {
      fail("DUPLICATE_FACE_KEY", "prototype " + prototypeKey + " repeats a face key");
    }
    seenFaceKeys.add(faceKey);
  }
  const bounds = record.bounds;
  if (!Array.isArray(bounds) || bounds.length !== 2) {
    fail("BAD_BOUNDS", path + ".bounds must be [min, max]");
  }
  const minimum = readVector3(bounds[0], path + ".bounds[0]");
  const maximum = readVector3(bounds[1], path + ".bounds[1]");
  for (let axis = 0; axis < 3; axis += 1) {
    if (minimum[axis] > maximum[axis]) fail("BAD_BOUNDS", "prototype " + prototypeKey + " bounds min exceeds max");
  }
  readObject(record.metrics, path + ".metrics");
  const mesh = readObject(record.mesh, path + ".mesh");
  const positionCount = readCount(mesh.positionCount, path + ".mesh.positionCount");
  const indexCount = readCount(mesh.indexCount, path + ".mesh.indexCount");
  const faceCount = readCount(mesh.faceCount, path + ".mesh.faceCount");
  const edgePointCount = readCount(mesh.edgePointCount, path + ".mesh.edgePointCount");
  if (indexCount % 3 !== 0) fail("BAD_INDEX_COUNT", "prototype " + prototypeKey + " indexCount is not divisible by 3");
  if (edgePointCount % 2 !== 0) fail("BAD_EDGE_COUNT", "prototype " + prototypeKey + " edgePointCount is odd");
  if (faceCount !== faceKeys.length) {
    fail("BAD_FACE_COUNT", "prototype " + prototypeKey + " faceCount does not match its face keys");
  }
  const offset = readCount(mesh.offset, path + ".mesh.offset");
  if (offset % ALIGNMENT !== 0) {
    fail("BAD_BLOB_ALIGNMENT", "prototype " + prototypeKey + " offset is not 8-byte aligned");
  }
  const blobLength = readCount(mesh.blobLength, path + ".mesh.blobLength");
  const exact = prototypeBlobSize(positionCount, indexCount, edgePointCount);
  if (blobLength !== align8(exact)) {
    fail("BAD_BLOB_LENGTH", "prototype " + prototypeKey + " blobLength does not match its counts");
  }
};

const validateInstanceRecord = (record, index, prototypeKeys, seenPaths) => {
  const path = "instances[" + index + "]";
  readObject(record, path);
  const instancePath = readText(record.path, path + ".path");
  if (seenPaths.has(instancePath)) {
    fail("DUPLICATE_INSTANCE_PATH", "duplicate instance path " + instancePath);
  }
  seenPaths.add(instancePath);
  const parentPath = readText(record.parentPath, path + ".parentPath", true);
  const expectedParent = instancePath.includes("/") ? instancePath.slice(0, instancePath.lastIndexOf("/")) : "";
  if (parentPath !== expectedParent) {
    fail("BAD_INSTANCE_FIELD", "instance " + instancePath + " parentPath does not match its path");
  }
  readText(record.instanceId, path + ".instanceId");
  const prototypeKey = readKey(record.prototypeKey, path + ".prototypeKey");
  if (!prototypeKeys.has(prototypeKey)) {
    fail("MISSING_PROTOTYPE", "instance " + instancePath + " references an unknown prototype");
  }
  const matrix = record.matrix;
  if (!Array.isArray(matrix) || matrix.length !== 16) {
    fail("BAD_MATRIX", path + ".matrix must have 16 entries");
  }
  for (let entry = 0; entry < 16; entry += 1) readFinite(matrix[entry], path + ".matrix[" + entry + "]");
  if (typeof record.color !== "string" || !COLOR_PATTERN.test(record.color)) {
    fail("BAD_COLOR", path + ".color must be #rrggbb");
  }
  if (typeof record.opacity !== "number" || record.opacity < 0 || record.opacity > 1) {
    fail("BAD_OPACITY", path + ".opacity must be within 0..1");
  }
  if (typeof record.visible !== "boolean") fail("BAD_INSTANCE_FIELD", path + ".visible must be a boolean");
  if (typeof record.suppressed !== "boolean") fail("BAD_INSTANCE_FIELD", path + ".suppressed must be a boolean");
  readText(record.module, path + ".module", true);
};

const validateManifest = (manifest) => {
  if (manifest.schema !== MANIFEST_SCHEMA) {
    fail("UNKNOWN_SCHEMA", "unsupported manifest schema " + String(manifest.schema));
  }
  readCount(manifest.schemaVersion, "schemaVersion");
  if (manifest.schemaVersion !== SCHEMA_VERSION) {
    fail("UNSUPPORTED_SCHEMA_VERSION", "unsupported schema version " + manifest.schemaVersion);
  }
  readKey(manifest.previewKey, "previewKey");
  const assembly = readObject(manifest.assembly, "assembly");
  readText(assembly.id, "assembly.id");
  readCount(assembly.version, "assembly.version");
  readText(assembly.configuration, "assembly.configuration");
  readText(assembly.name, "assembly.name", true);
  const generator = readObject(manifest.generator, "generator");
  readText(generator.version, "generator.version");
  readText(generator.kernel, "generator.kernel");
  readText(generator.tessellationProfile, "generator.tessellationProfile");
  if (manifest.units !== MANIFEST_UNITS) {
    fail("BAD_MANIFEST_FIELD", "units must be " + MANIFEST_UNITS);
  }
  readVector3(manifest.rootOffset, "rootOffset");
  const prototypes = readArray(manifest.prototypes, "prototypes");
  const prototypeCount = readCount(manifest.prototypeCount, "prototypeCount", MAX_PROTOTYPES);
  if (prototypeCount !== prototypes.length) {
    fail("BAD_MANIFEST_FIELD", "prototypeCount does not match prototypes");
  }
  const instances = readArray(manifest.instances, "instances");
  const instanceCount = readCount(manifest.instanceCount, "instanceCount", MAX_INSTANCES);
  if (instanceCount !== instances.length) {
    fail("BAD_MANIFEST_FIELD", "instanceCount does not match instances");
  }
  readCount(manifest.leafCount, "leafCount", MAX_LEAVES);
  const bom = readObject(manifest.bom, "bom");
  for (const field of ["rows", "quantity", "definitions"]) {
    readCount(bom[field], "bom." + field);
  }
  const prototypeKeys = new Set();
  for (let index = 0; index < prototypes.length; index += 1) {
    validatePrototypeRecord(prototypes[index], index, prototypeKeys);
  }
  const seenPaths = new Set();
  for (let index = 0; index < instances.length; index += 1) {
    validateInstanceRecord(instances[index], index, prototypeKeys, seenPaths);
  }
  return { prototypes, instances, prototypeKeys };
};

const validateArrayContents = (record, arrays) => {
  const mesh = record.mesh;
  const positionCount = mesh.positionCount;
  const faceCount = mesh.faceCount;
  for (let index = 0; index < arrays.positions.length; index += 1) {
    if (!Number.isFinite(arrays.positions[index])) {
      fail("BAD_COORDINATE", "prototype " + record.prototypeKey + " has a non-finite position");
    }
  }
  for (let index = 0; index < arrays.edges.length; index += 1) {
    if (!Number.isFinite(arrays.edges[index])) {
      fail("BAD_COORDINATE", "prototype " + record.prototypeKey + " has a non-finite edge point");
    }
  }
  for (let index = 0; index < arrays.indices.length; index += 1) {
    if (arrays.indices[index] >= positionCount) {
      fail("BAD_INDEX", "prototype " + record.prototypeKey + " has an out-of-range index");
    }
  }
  for (let index = 0; index < arrays.faceIds.length; index += 1) {
    if (arrays.faceIds[index] >= faceCount) {
      fail("BAD_FACE_ID", "prototype " + record.prototypeKey + " has an out-of-range face id");
    }
  }
};

const decodeBundle = (buffer) => {
  if (!(buffer instanceof ArrayBuffer)) fail("BUNDLE_NOT_BUFFER", "bundle payload is not an ArrayBuffer");
  const bytes = new Uint8Array(buffer);
  const view = new DataView(buffer);
  if (bytes.length < HEADER_SIZE) fail("HEADER_TRUNCATED", "need 16 header bytes");
  if (bytes[0] !== MAGIC_0 || bytes[1] !== MAGIC_1 || bytes[2] !== MAGIC_2 || bytes[3] !== MAGIC_3) {
    fail("BAD_MAGIC", "expected BPXV magic");
  }
  const formatVersion = view.getUint16(4, true);
  if (formatVersion !== FORMAT_VERSION) {
    fail("UNSUPPORTED_FORMAT_VERSION", "unsupported format version " + formatVersion);
  }
  const flags = view.getUint16(6, true);
  if (flags !== 0) fail("UNKNOWN_FLAGS", "unknown header flags 0x" + flags.toString(16));
  const manifestLength = view.getUint32(8, true);
  if (view.getUint32(12, true) !== 0) fail("RESERVED_NONZERO", "reserved header word must be zero");
  if (manifestLength === 0 || manifestLength > MAX_MANIFEST_BYTES) {
    fail("MANIFEST_LENGTH_INVALID", "manifest length is outside 1.." + MAX_MANIFEST_BYTES);
  }
  if (bytes.length > MAX_BUNDLE_BYTES) fail("BUNDLE_TOO_LARGE", "bundle exceeds the byte limit");
  const manifestEnd = HEADER_SIZE + manifestLength;
  if (manifestEnd > bytes.length) fail("BUNDLE_TRUNCATED", "manifest ends past the bundle");
  const dataBase = align8(manifestEnd);
  if (dataBase > bytes.length) fail("BUNDLE_TRUNCATED", "prototype data starts past the bundle");
  for (let index = manifestEnd; index < dataBase; index += 1) {
    if (bytes[index] !== 0) fail("PADDING_NONZERO", "header padding must be zero");
  }
  if (bytes[16] === 0xef && bytes[17] === 0xbb && bytes[18] === 0xbf) {
    fail("MANIFEST_BOM", "manifest must not start with a byte-order mark");
  }
  let text;
  try {
    text = new TextDecoder("utf-8", { fatal: true }).decode(bytes.subarray(HEADER_SIZE, manifestEnd));
  } catch (error) {
    fail("MANIFEST_NOT_UTF8", "manifest is not valid UTF-8");
  }
  let manifest;
  try {
    manifest = JSON.parse(text);
  } catch (error) {
    fail("MANIFEST_NOT_JSON", "manifest is not valid JSON");
  }
  if (manifest === null || typeof manifest !== "object" || Array.isArray(manifest)) {
    fail("MANIFEST_NOT_OBJECT", "manifest must be a JSON object");
  }
  const { prototypes: records } = validateManifest(manifest);

  const layout = [];
  for (const record of records) {
    const mesh = record.mesh;
    const start = dataBase + mesh.offset;
    const end = start + mesh.blobLength;
    const exact = prototypeBlobSize(mesh.positionCount, mesh.indexCount, mesh.edgePointCount);
    if (start < dataBase || end > bytes.length) {
      fail("BAD_BLOB_RANGE", "prototype " + record.prototypeKey + " lies outside the bundle");
    }
    layout.push({ record, start, exactEnd: start + exact, end });
  }
  layout.sort((left, right) => left.start - right.start);
  let cursor = dataBase;
  for (const range of layout) {
    if (range.start < cursor) fail("BAD_BLOB_OVERLAP", "prototype ranges overlap");
    for (let index = cursor; index < range.start; index += 1) {
      if (bytes[index] !== 0) fail("PADDING_NONZERO", "gap between prototypes must be zero");
    }
    cursor = range.end;
  }
  if (cursor < bytes.length) fail("BUNDLE_TRAILING_BYTES", "bytes follow the last prototype");

  const prototypes = [];
  for (const range of layout) {
    const record = range.record;
    const mesh = record.mesh;
    for (let index = range.exactEnd; index < range.end; index += 1) {
      if (bytes[index] !== 0) fail("PADDING_NONZERO", "prototype padding must be zero");
    }
    const positionLength = mesh.positionCount * 3;
    const indexLength = mesh.indexCount;
    const faceLength = mesh.indexCount / 3;
    const edgeLength = mesh.edgePointCount * 3;
    const positions = new Float32Array(positionLength);
    positions.set(new Float32Array(buffer, range.start, positionLength));
    const indexStart = range.start + positionLength * 4;
    const indices = new Uint32Array(indexLength);
    indices.set(new Uint32Array(buffer, indexStart, indexLength));
    const faceStart = indexStart + indexLength * 4;
    const faceIds = new Uint32Array(faceLength);
    faceIds.set(new Uint32Array(buffer, faceStart, faceLength));
    const edgeStart = faceStart + faceLength * 4;
    const edges = new Float32Array(edgeLength);
    edges.set(new Float32Array(buffer, edgeStart, edgeLength));
    const arrays = { positions, indices, faceIds, edges };
    validateArrayContents(record, arrays);
    prototypes.push({ prototypeKey: record.prototypeKey, ...arrays });
  }
  return { manifest, prototypes, dataBase, byteLength: bytes.length };
};

self.addEventListener("message", (event) => {
  const data = event.data;
  if (!data || data.type !== "assembly-preview-decode") return;
  const id = data.id;
  const started = performance.now();
  try {
    const decoded = decodeBundle(data.buffer);
    const transfers = [];
    for (const prototype of decoded.prototypes) {
      transfers.push(prototype.positions.buffer, prototype.indices.buffer, prototype.faceIds.buffer, prototype.edges.buffer);
    }
    self.postMessage({
      type: "assembly-preview-decoded",
      id,
      manifest: decoded.manifest,
      prototypes: decoded.prototypes,
      dataBase: decoded.dataBase,
      byteLength: decoded.byteLength,
      decodeMs: performance.now() - started,
    }, transfers);
  } catch (error) {
    self.postMessage({
      type: "assembly-preview-error",
      id,
      code: error && error.code ? error.code : "BUNDLE_DECODE_FAILED",
      message: error && error.message ? error.message : "bundle decode failed",
    });
  }
});
