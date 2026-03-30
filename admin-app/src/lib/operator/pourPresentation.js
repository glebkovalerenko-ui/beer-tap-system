function normalizeText(value) {
  return String(value || '').trim().toLowerCase();
}

function technicalDetail(value) {
  const normalized = normalizeText(value);
  return normalized ? `Технический код: ${normalized}` : '';
}

function withFallback(label, rawValue, fallbackLabel) {
  const normalized = normalizeText(rawValue);
  if (!normalized) {
    return {
      label: fallbackLabel,
      technicalDetail: '',
    };
  }

  return {
    label,
    technicalDetail: label === fallbackLabel ? technicalDetail(normalized) : '',
  };
}

const SYNC_LABELS = {
  synced: 'Синхронизирован',
  pending_sync: 'Ждёт синхронизации',
  rejected: 'Нужна проверка синхронизации',
  reconciled: 'Сверен вручную',
  accounted: 'Учтён системой',
  failed: 'Ошибка синхронизации',
  not_started: 'Нет данных о синхронизации',
};

const COMPLETION_LABELS = {
  controller_timeout: 'Остановлен по таймауту контроллера',
  timeout: 'Остановлен по таймауту',
  timeout_close: 'Остановлен по таймауту',
  sync_timeout: 'Остановлен без подтверждения синхронизации',
  card_removed_close: 'Остановлен после снятия карты',
  card_removed: 'Карта была убрана во время налива',
  guest_checkout: 'Гость завершил визит',
  operator_close: 'Визит закрыт оператором',
  manual_close: 'Остановлен вручную',
  denied_insufficient_funds: 'Недостаточно средств',
  blocked_insufficient_funds: 'Налив заблокирован из-за недостатка средств',
  blocked_lost_card: 'Карта помечена потерянной',
  blocked_card_in_use: 'Карта уже используется на другом кране',
  no_card_no_session: 'Карта не считана, визит не открыт',
  no_card_with_session: 'Карта не считана, но визит уже был открыт',
  flow_detected_when_valve_closed_without_active_session: 'Поток зафиксирован без открытого визита',
  non_sale_flow: 'Служебный налив без продажи',
  accounted: 'Учтён системой',
};

const FLOW_STATE_LABELS = {
  authorized_session: 'Визит подтверждён',
  no_card_no_session: 'Карта не считана, визит не открыт',
  no_card_with_session: 'Карта не считана, но визит уже открыт',
  active_session: 'Есть активный визит',
};

const LIFECYCLE_LABELS = {
  authorize: 'Карта подтверждена',
  reader: 'Карта у считывателя',
  start: 'Налив начался',
  stop: 'Налив завершён',
  sync: 'Учёт и синхронизация',
  deny: 'Почему налив не начался',
};

export function formatPourSyncState(value) {
  const normalized = normalizeText(value);
  return withFallback(
    SYNC_LABELS[normalized] || 'Нужна проверка синхронизации',
    normalized,
    'Нет данных о синхронизации',
  );
}

export function formatPourCompletionReason(value) {
  const normalized = normalizeText(value);
  return withFallback(
    COMPLETION_LABELS[normalized] || 'Нужна проверка причины остановки',
    normalized,
    'Причина не указана',
  );
}

export function formatPourLifecycleValue(step = {}, detail = null) {
  const sourceKind = normalizeText(detail?.summary?.source_kind || detail?.summary?.sourceKind);
  const normalizedValue = normalizeText(step.value);

  if (step.key === 'reader') {
    return {
      label: normalizedValue === 'yes' ? 'Да' : normalizedValue === 'no' ? 'Нет' : 'Нет данных',
      technicalDetail: normalizedValue && !['yes', 'no'].includes(normalizedValue) ? technicalDetail(normalizedValue) : '',
    };
  }

  if (step.key === 'sync') {
    return formatPourSyncState(step.value);
  }

  if (step.key === 'stop' || step.key === 'deny') {
    return formatPourCompletionReason(step.value);
  }

  if (sourceKind === 'flow' && step.key === 'start') {
    return withFallback(
      FLOW_STATE_LABELS[normalizedValue] || 'Нужна проверка запуска',
      normalizedValue,
      'Нет данных о запуске',
    );
  }

  if (step.key === 'authorize') {
    return withFallback(step.value ? `Карта ${step.value}` : 'Карта не указана', step.value, 'Карта не указана');
  }

  return withFallback(step.value || 'Без дополнительной отметки', normalizedValue, 'Без дополнительной отметки');
}

export function presentPourLifecycle(detail = null) {
  return (detail?.lifecycle || []).map((step) => {
    const value = formatPourLifecycleValue(step, detail);
    return {
      ...step,
      operatorLabel: LIFECYCLE_LABELS[step.key] || step.label || 'Этап',
      operatorValue: value.label,
      technicalDetail: value.technicalDetail,
    };
  });
}

export function buildOperatorPourPresentation(detail = null) {
  const summary = detail?.summary || {};
  return {
    sync: formatPourSyncState(summary.sync_state),
    completion: formatPourCompletionReason(summary.completion_reason),
    lifecycle: presentPourLifecycle(detail),
  };
}
