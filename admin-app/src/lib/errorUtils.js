const DEFAULT_ERROR_MESSAGE = 'Неизвестная ошибка (детали в логах)';

export function normalizeErrorMessage(error, fallback = DEFAULT_ERROR_MESSAGE) {
  let message = '';

  if (typeof error === 'string') {
    message = error;
  } else if (error instanceof Error) {
    message = error.message || '';
  } else if (error && typeof error === 'object') {
    if (typeof error.message === 'string') {
      message = error.message;
    } else if (typeof error.detail === 'string') {
      message = error.detail;
    }
  }

  if (!message && error && typeof error.toString === 'function') {
    const asString = error.toString();
    if (asString && asString !== '[object Object]') {
      message = asString;
    }
  }

  message = (message || '').trim();
  return message || fallback;
}

export function logError(context, error) {
  console.error(`[${context}]`, error);
}

export { DEFAULT_ERROR_MESSAGE };
