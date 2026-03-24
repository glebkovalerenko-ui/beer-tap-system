const DEFAULT_ERROR_MESSAGE = 'Неизвестная ошибка';
const ERROR_MESSAGE_MAP = [
  [/^Not authenticated$/i, 'Требуется повторный вход в систему'],
  [/^Authentication token not found\.?$/i, 'Требуется повторный вход в систему'],
  [/^Shift already open$/i, 'Смена уже открыта'],
  [/^Shift is already closed$/i, 'Смена уже закрыта'],
  [/^Login failed$/i, 'Не удалось выполнить вход'],
  [/^Unauthorized$/i, 'Доступ запрещён. Требуется повторный вход'],
  [/^API request failed$/i, 'Не удалось выполнить запрос к серверу'],
  [/^request failed for /i, 'Не удалось выполнить запрос к серверу'],
  [/active_visits_exist/i, 'Есть активные визиты'],
  [/pending_sync_pours_exist/i, 'Есть несинхронизированные наливы'],
  [/processing_sync/i, 'Идёт синхронизация налива. Дождитесь завершения'],
  [/insufficient_funds/i, 'Недостаточно средств для начала налива'],
  [/lost_card/i, 'Карта отмечена как потерянная'],
  [/authorize_request_failed/i, 'Не удалось связаться с сервером авторизации'],
  [/HTTP 401/i, 'Доступ запрещён. Требуется повторный вход'],
  [/HTTP 403/i, 'Действие недоступно для текущей роли'],
  [/HTTP 404/i, 'Запрошенные данные не найдены'],
  [/HTTP 409/i, 'Конфликт данных. Обновите экран и повторите действие'],
  [/HTTP 5\d\d/i, 'Ошибка сервера. Повторите попытку позже'],
];

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

function translateOperatorMessage(message) {
  const text = isNonEmptyString(message) ? message.trim() : '';
  if (!text) return '';

  for (const [pattern, replacement] of ERROR_MESSAGE_MAP) {
    if (pattern.test(text)) {
      return replacement;
    }
  }

  return text;
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
      if (fromParsed) return translateOperatorMessage(fromParsed);
    }
    return translateOperatorMessage(error);
  }

  if (error instanceof Error && isNonEmptyString(error.message)) {
    return translateOperatorMessage(error.message);
  }

  const objectMessage = fromObject(error);
  if (objectMessage) {
    return translateOperatorMessage(objectMessage);
  }

  if (error && typeof error.toString === 'function') {
    const asString = error.toString();
    if (isNonEmptyString(asString) && asString !== '[object Object]') {
      return translateOperatorMessage(asString);
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
