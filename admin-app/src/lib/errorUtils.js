const DEFAULT_ERROR_MESSAGE = 'Неизвестная ошибка';
/** @type {Array<[RegExp, string]>} */
const ERROR_MESSAGE_MAP = [
  [/^Not authenticated$/i, 'Требуется повторный вход в систему'],
  [/^Authentication token not found\.?$/i, 'Требуется повторный вход в систему'],
  [/^Could not validate credentials\.?$/i, 'Требуется повторный вход в систему'],
  [/^Incorrect username or password$/i, 'Неверное имя пользователя или пароль'],
  [/^Shift already open$/i, 'Смена уже открыта'],
  [/^Shift is already closed$/i, 'Смена уже закрыта'],
  [/^Login failed$/i, 'Не удалось выполнить вход'],
  [/^Unauthorized$/i, 'Доступ запрещён. Требуется повторный вход'],
  [/^API request failed$/i, 'Не удалось выполнить запрос к серверу'],
  [/^request failed for /i, 'Не удалось выполнить запрос к серверу'],
  [/^Guest not found$/i, 'Гость не найден'],
  [/^Visit not found$/i, 'Визит не найден'],
  [/^Card not found$/i, 'Карта не найдена'],
  [/^Card not found or not assigned to this guest$/i, 'Карта не найдена или не привязана к этому гостю'],
  [/^Only active visit can report lost card$/i, 'Отметить потерю карты можно только у активного визита'],
  [/^Cannot restore a lost card from the lost-cards queue while the related visit is still blocked; open the visit recovery flow and reissue, cancel lost, or service-close it first\.$/i, 'Нельзя снять отметку потери из очереди потерянных карт, пока связанный визит заблокирован. Откройте раздел «Визиты» и выполните перевыпуск, снятие отметки потери или сервисное закрытие.'],
  [/^Value must be 'true' or 'false'$/i, "Значение должно быть 'true' или 'false'"],
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

/** @param {unknown} value */
function isNonEmptyString(value) {
  return typeof value === 'string' && value.trim().length > 0;
}

/** @param {unknown} value */
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

/** @param {unknown} value */
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

/** @param {unknown} error */
function extractStatusAndEndpoint(error) {
  if (!error || typeof error !== 'object') return '';

  const status = error.status ?? error.statusCode ?? error.code;
  const endpoint = error.endpoint ?? error.url ?? error.path;

  const statusPart = status ? `HTTP ${status}` : '';
  const endpointPart = isNonEmptyString(endpoint) ? endpoint.trim() : '';
  return [statusPart, endpointPart].filter(Boolean).join(' ').trim();
}

/** @param {unknown} message */
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

/** @param {unknown} error */
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

/** @param {unknown} error @param {string} [fallback=DEFAULT_ERROR_MESSAGE] */
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

/** @param {unknown} error @param {string} [fallback=DEFAULT_ERROR_MESSAGE] */
export function normalizeErrorMessage(error, fallback = DEFAULT_ERROR_MESSAGE) {
  return normalizeError(error, fallback);
}

/** @param {string} context @param {unknown} error @param {string} [fallback=DEFAULT_ERROR_MESSAGE] */
export function logError(context, error, fallback = DEFAULT_ERROR_MESSAGE) {
  const normalized = normalizeError(error, fallback);
  const prefix = context ? `[${context}] ` : '';
  console.error(`${prefix}${normalized}`, error);
  return normalized;
}

export { DEFAULT_ERROR_MESSAGE };
