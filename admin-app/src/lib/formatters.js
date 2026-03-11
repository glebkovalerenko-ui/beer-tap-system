const MONEY_FORMATTER = new Intl.NumberFormat('ru-RU', {
  style: 'currency',
  currency: 'RUB',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const DATE_FORMATTER = new Intl.DateTimeFormat('ru-RU', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
});

const TIME_FORMATTER = new Intl.DateTimeFormat('ru-RU', {
  hour: '2-digit',
  minute: '2-digit',
});

const DATE_TIME_FORMATTER = new Intl.DateTimeFormat('ru-RU', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
});

const DECIMAL_NUMBER_FORMATTER = new Intl.NumberFormat('ru-RU', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

const TAP_STATUS_LABELS = {
  active: 'Активен',
  locked: 'Заблокирован',
  cleaning: 'На промывке',
  empty: 'Пуст',
};

const VISIT_STATUS_LABELS = {
  active: 'Активен',
  closed: 'Закрыт',
};

const CARD_STATUS_LABELS = {
  active: 'Активна',
  blocked: 'Заблокирована',
  lost: 'Потеряна',
};

const KEG_STATUS_LABELS = {
  new: 'Новая',
  full: 'Полная',
  in_use: 'Подключена',
  empty: 'Пустая',
};

const SHIFT_REPORT_STATUS_LABELS = {
  pending_sync: 'Ожидают синхронизации',
  reconciled: 'Сверены вручную',
  mismatch: 'С расхождением',
};

function normalizeNumber(value) {
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : 0;
  }

  if (typeof value === 'string') {
    const normalized = value.trim().replace(',', '.');
    const parsed = Number.parseFloat(normalized);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  return 0;
}

function asDate(value) {
  if (!value) return null;
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function toMinorUnits(value) {
  return Math.round(normalizeNumber(value) * 100);
}

export function formatMinorUnitsRub(minorUnits) {
  return MONEY_FORMATTER.format(normalizeNumber(minorUnits) / 100);
}

export function formatRubAmount(value) {
  return formatMinorUnitsRub(toMinorUnits(value));
}

export function formatVolumeRu(volumeMl) {
  const ml = Math.max(0, Math.round(normalizeNumber(volumeMl)));
  if (ml < 1000) {
    return `${ml} мл`;
  }

  return `${DECIMAL_NUMBER_FORMATTER.format(ml / 1000)} л`;
}

export function formatVolumeRangeRu(currentMl, totalMl) {
  return `${formatVolumeRu(currentMl)} из ${formatVolumeRu(totalMl)}`;
}

export function formatDateRu(value) {
  const date = asDate(value);
  return date ? DATE_FORMATTER.format(date) : '-';
}

export function formatTimeRu(value) {
  const date = asDate(value);
  return date ? TIME_FORMATTER.format(date) : '-';
}

export function formatDateTimeRu(value) {
  const date = asDate(value);
  return date ? DATE_TIME_FORMATTER.format(date) : '-';
}

export function formatDurationRu(durationMs) {
  const totalSeconds = Math.max(0, Math.round(normalizeNumber(durationMs) / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes === 0) {
    return `${seconds} с`;
  }

  return seconds === 0 ? `${minutes} мин` : `${minutes} мин ${seconds} с`;
}

export function formatTapStatus(status) {
  return TAP_STATUS_LABELS[status] || status || '-';
}

export function formatVisitStatus(status) {
  return VISIT_STATUS_LABELS[status] || status || '-';
}

export function formatCardStatus(status) {
  return CARD_STATUS_LABELS[status] || status || '-';
}

export function formatKegStatus(status) {
  return KEG_STATUS_LABELS[status] || status || '-';
}

export function formatShiftReportMetricLabel(metric) {
  return SHIFT_REPORT_STATUS_LABELS[metric] || metric || '-';
}
