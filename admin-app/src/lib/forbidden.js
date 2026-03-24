import { uiStore } from '../stores/uiStore.js';

const FORBIDDEN_EXPLANATION = 'Действие недоступно для текущей роли';

export function isForbiddenError(error) {
  if (!error) return false;
  const text = typeof error === 'string'
    ? error
    : error?.message || error?.detail || JSON.stringify(error);
  return /HTTP\s*403|forbidden|Недостаточно прав/i.test(String(text || ''));
}

export function notifyForbiddenIfNeeded(error) {
  if (!isForbiddenError(error)) {
    return false;
  }
  uiStore.notifyError(FORBIDDEN_EXPLANATION);
  return true;
}

export { FORBIDDEN_EXPLANATION };
