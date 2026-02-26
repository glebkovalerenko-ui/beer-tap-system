const DEFAULT_ERROR_MESSAGE = 'Неизвестная ошибка';

function isNonEmptyString(value) {
  return typeof value === 'string' && value.trim().length > 0;
}

function safeStringify(value) {
  try {
    const serialized = JSON.stringify(value);
    if (!isNonEmptyString(serialized) || serialized === '{}' || serialized === '[]') {
      return '';
    }
    return serialized.trim();
  } catch {
    return '';
  }
}

function parseJsonIfPossible(value) {
  if (!isNonEmptyString(value)) return null;
  const trimmed = value.trim();
  if (!trimmed.startsWith('{') && !trimmed.startsWith('[')) return null;

  try {
    return JSON.parse(trimmed);
  } catch {
    return null;
  }
}

function extractStatusAndEndpoint(error) {
  if (!error || typeof error !== 'object') return '';

  const status = error.status ?? error.statusCode ?? error.code;
  const endpoint = error.endpoint ?? error.url ?? error.path;

  const statusPart = status ? `HTTP ${status}` : '';
  const endpointPart = isNonEmptyString(endpoint) ? endpoint.trim() : '';
  return [statusPart, endpointPart].filter(Boolean).join(' ').trim();
}

function fromObject(error) {
  if (!error || typeof error !== 'object') return '';

  if (isNonEmptyString(error.message)) {
    return error.message.trim();
  }

  if (isNonEmptyString(error.detail)) {
    return error.detail.trim();
  }

  if (error.detail !== undefined && error.detail !== null) {
    const detailJson = safeStringify(error.detail);
    if (detailJson) return detailJson;
  }

  if (isNonEmptyString(error.error)) {
    return error.error.trim();
  }

  if (error.error !== undefined && error.error !== null) {
    const errorJson = safeStringify(error.error);
    if (errorJson) return errorJson;
  }

  const statusAndEndpoint = extractStatusAndEndpoint(error);
  if (statusAndEndpoint) {
    return statusAndEndpoint;
  }

  const wholeObject = safeStringify(error);
  if (wholeObject) {
    return wholeObject;
  }

  return '';
}

export function normalizeError(error, fallback = DEFAULT_ERROR_MESSAGE) {
  if (isNonEmptyString(error)) {
    const parsed = parseJsonIfPossible(error);
    if (parsed) {
      const fromParsed = fromObject(parsed);
      if (fromParsed) return fromParsed;
    }
    return error.trim();
  }

  if (error instanceof Error && isNonEmptyString(error.message)) {
    return error.message.trim();
  }

  const objectMessage = fromObject(error);
  if (objectMessage) {
    return objectMessage;
  }

  if (error && typeof error.toString === 'function') {
    const asString = error.toString();
    if (isNonEmptyString(asString) && asString !== '[object Object]') {
      return asString.trim();
    }
  }

  return fallback;
}

export function normalizeErrorMessage(error, fallback = DEFAULT_ERROR_MESSAGE) {
  return normalizeError(error, fallback);
}

export function logError(context, error, fallback = DEFAULT_ERROR_MESSAGE) {
  const normalized = normalizeError(error, fallback);
  const prefix = context ? `[${context}] ` : '';
  console.error(`${prefix}${normalized}`, error);
  return normalized;
}

export { DEFAULT_ERROR_MESSAGE };
