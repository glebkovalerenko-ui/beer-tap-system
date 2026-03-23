export const HEALTH_STATE_TONE = {
  ok: 'ok',
  warning: 'warn',
  degraded: 'warn',
  unknown: 'warn',
  critical: 'error',
  error: 'error',
  offline: 'error',
};

const STATE_COPY = {
  overall: {
    ok: 'Работаем штатно',
    warning: 'Нужна проверка смены',
    degraded: 'Есть риск для смены',
    critical: 'Смена под риском',
    error: 'Смена под риском',
    offline: 'Потеряна связь с контуром',
    unknown: 'Статус уточняется',
  },
  subsystem: {
    ok: 'в норме',
    warning: 'нужна проверка',
    degraded: 'работает с риском',
    critical: 'нужно срочное действие',
    error: 'есть риск простоя',
    offline: 'связь потеряна',
    unknown: 'статус уточняется',
  },
};

export function healthTone(state) {
  return HEALTH_STATE_TONE[state] || 'warn';
}

export function healthStateLabel(state, context = 'subsystem') {
  const labels = STATE_COPY[context] || STATE_COPY.subsystem;
  return labels[state] || labels.unknown;
}

export function formatHealthPill(item) {
  return `${item.label}: ${healthStateLabel(item.state, 'subsystem')}`;
}
