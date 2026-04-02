import { TAP_SCREENS_COPY } from './operatorLabels.js';

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

const PRICE_DISPLAY_MODE_LABELS = {
  per_100ml: '₽ / 100 мл',
  per_liter: '₽ / л',
  auto: 'Авто',
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
  const inventoryLabels = {
    available: 'Доступна в пуле',
    assigned_to_visit: 'Назначена на визит',
    returned_to_pool: 'Возвращена в пул',
    retired: 'Выведена из пула',
  };
  return inventoryLabels[status] || CARD_STATUS_LABELS[status] || status || '-';
}

export function formatKegStatus(status) {
  return KEG_STATUS_LABELS[status] || status || '-';
}

export function formatShiftReportMetricLabel(metric) {
  return SHIFT_REPORT_STATUS_LABELS[metric] || metric || '-';
}

export function formatPriceDisplayMode(mode, fallback = '-') {
  const normalized = typeof mode === 'string' ? mode.trim() : '';
  return PRICE_DISPLAY_MODE_LABELS[normalized] || fallback;
}

const DEFAULT_TAP_DISPLAY_COPY = {
  fallbackTitle: 'Кран недоступен',
  fallbackSubtitle: 'Обратитесь к оператору',
  maintenanceTitle: 'Кран временно недоступен',
  maintenanceSubtitle: 'Обратитесь к оператору',
};

function compactText(value) {
  const normalized = String(value ?? '').trim();
  return normalized || null;
}

function chooseScenario(productState, enabled) {
  if (enabled === false) return 'display_disabled';
  if (productState === 'pouring') return 'pouring';
  if (productState === 'ready') return 'beverage_spotlight';
  if (productState === 'no_keg') return 'fallback_empty';
  if (productState === 'syncing') return 'syncing';
  return 'maintenance';
}

export function buildTapGuestDisplaySnapshot(tap, displayConfig = null) {
  const operations = tap?.operations || {};
  const beverage = tap?.keg?.beverage || null;
  const config = displayConfig || {};
  const displayEnabled = config.enabled ?? tap?.display_enabled ?? true;
  const scenario = chooseScenario(operations.productState, displayEnabled);

  const titleCandidates = {
    display_disabled: [
      config.maintenance_title,
      config.fallback_title,
      beverage?.display_brand_name,
      beverage?.name,
    ],
    fallback_empty: [
      config.fallback_title,
      config.maintenance_title,
      beverage?.display_brand_name,
      beverage?.name,
    ],
    maintenance: [
      config.maintenance_title,
      config.fallback_title,
      beverage?.display_brand_name,
      beverage?.name,
    ],
    syncing: [
      beverage?.display_brand_name,
      beverage?.name,
      config.maintenance_title,
      config.fallback_title,
    ],
    pouring: [
      beverage?.display_brand_name,
      beverage?.name,
      config.maintenance_title,
    ],
    beverage_spotlight: [
      beverage?.display_brand_name,
      beverage?.name,
      config.fallback_title,
    ],
  };

  const subtitleCandidates = {
    display_disabled: [
      config.maintenance_subtitle,
      config.fallback_subtitle,
      operations.operatorStateReason,
      operations.liveStatus,
    ],
    fallback_empty: [
      config.fallback_subtitle,
      operations.operatorStateReason,
      operations.liveStatus,
      beverage?.description_short,
    ],
    maintenance: [
      config.maintenance_subtitle,
      operations.operatorStateReason,
      operations.liveStatus,
      beverage?.description_short,
    ],
    syncing: [
      operations.liveStatus,
      operations.operatorStateReason,
      beverage?.description_short,
    ],
    pouring: [
      operations.liveStatus,
      operations.operatorStateReason,
      beverage?.description_short,
    ],
    beverage_spotlight: [
      beverage?.description_short,
      [beverage?.style, beverage?.brewery].filter(Boolean).join(' · '),
      operations.liveStatus,
    ],
  };

  const title = titleCandidates[scenario]?.map(compactText).find(Boolean)
    || DEFAULT_TAP_DISPLAY_COPY.fallbackTitle;
  const subtitle = subtitleCandidates[scenario]?.map(compactText).find(Boolean)
    || (scenario === 'beverage_spotlight' || scenario === 'pouring'
      ? DEFAULT_TAP_DISPLAY_COPY.fallbackSubtitle
      : DEFAULT_TAP_DISPLAY_COPY.maintenanceSubtitle);

  return {
    enabled: displayEnabled,
    scenario,
    scenarioLabel: {
      display_disabled: 'Экран отключён для гостей',
      beverage_spotlight: 'Гость видит карточку напитка',
      pouring: 'Гость видит активный налив',
      fallback_empty: 'Гость видит экран пустого крана',
      syncing: 'Гость видит бренд до подтверждения синхронизации',
      maintenance: 'Гость видит сервисный экран',
    }[scenario] || 'Сценарий уточняется',
    title,
    subtitle,
    brandingSummary: [
      beverage?.display_brand_name ? `Бренд: ${beverage.display_brand_name}` : null,
      beverage?.name ? `Напиток: ${beverage.name}` : null,
      beverage?.style ? `Стиль: ${beverage.style}` : null,
      beverage?.brewery ? `Пивоварня: ${beverage.brewery}` : null,
    ].filter(Boolean).join(' · ') || 'Гостевой контент без бренд-метаданных.',
    background: {
      present: Boolean(config.override_background_asset_id || beverage?.background_asset_id),
      source: config.override_background_asset_id
        ? 'Фон переопределён на уровне крана'
        : beverage?.background_asset_id
          ? 'Фон наследуется от напитка'
          : 'Фон не задан',
    },
    logo: {
      present: Boolean(beverage?.logo_asset_id),
      source: beverage?.logo_asset_id ? 'Логотип напитка доступен' : 'Логотип не задан',
    },
    runtimeSummary: operations.displayStatus?.label || operations.liveStatus || 'Нет данных о состоянии экрана',
    runtimeTone: operations.displayStatus?.state || 'unknown',
    operatorSummary: [
      displayEnabled ? TAP_SCREENS_COPY.displayEnabled : TAP_SCREENS_COPY.displayDisabled,
      operations.productStateLabel ? `Состояние крана: ${operations.productStateLabel}` : null,
      operations.operatorStateReason || null,
      operations.liveStatus || null,
    ].filter(Boolean),
  };
}
