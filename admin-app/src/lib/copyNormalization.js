const EXACT_TEXT_MAP = new Map([
  ['all core operator subsystems are responding normally.', 'Все ключевые операторские подсистемы отвечают штатно.'],
  ['operator actions are temporarily blocked until data is fresh again.', 'Операторские действия временно заблокированы, пока не вернутся свежие данные.'],
  ['controller heartbeat stale', 'Контроллер давно не выходил на связь'],
  ['controller heartbeat aging', 'Сигнал от контроллера давно не обновлялся'],
  ['controller waiting for sync', 'Контроллер ждёт синхронизации'],
  ['controllers need attention', 'Контроллеры требуют внимания'],
  ['controller responsive', 'Контроллер отвечает'],
  ['controller runtime looks healthy for operator flow.', 'Контроллер работает штатно для текущей смены.'],
  ['display assigned', 'Экран подключён'],
  ['waiting for keg', 'Ожидает назначения кеги'],
  ['reader ready', 'Считыватель готов'],
  ['reader attention', 'Считыватель требует внимания'],
  ['guest-facing screen is disabled; operator control remains available.', 'Гостевой экран отключён, но управление краном доступно.'],
  ['tap is waiting for backend confirmation of recent local activity.', 'Кран ждёт подтверждения системой недавней локальной активности.'],
  ['assign a keg to return this line to service.', 'Назначьте кегу, чтобы вернуть линию в работу.'],
  ['line is quiet and ready for the next operator action.', 'Линия готова к следующему действию оператора.'],
  ['incident mutation endpoints недоступны.', 'Действия по инцидентам временно недоступны.'],
  ['endpoint временно отключён.', 'Действие временно недоступно.'],
]);

const INCIDENT_TYPE_LABELS = {
  backend_offline: 'Система недоступна',
  closed_valve_flow: 'Поток при закрытом клапане',
  controller_offline: 'Контроллер недоступен',
  display_offline: 'Экран недоступен',
  flow_closed_valve: 'Поток при закрытом клапане',
  no_keg: 'Нет назначенной кеги',
  reader_offline: 'Считыватель недоступен',
  stale_heartbeat: 'Нет свежего сигнала',
  sync_offline: 'Сбой синхронизации',
  unsynced_flow: 'Налив ждёт синхронизации',
  visit_force_unlock: 'Принудительная разблокировка визита',
};

const INCIDENT_SOURCE_LABELS = {
  api: 'Центральный контур',
  backend: 'Центральный контур',
  controller: 'Контроллер',
  controllers: 'Контроллеры',
  display: 'Экран',
  display_agent: 'Экран',
  displays: 'Экраны',
  incident_system: 'Система инцидентов',
  nfc: 'Считыватель',
  nfc_reader: 'Считыватель',
  queue: 'Синхронизация',
  reader: 'Считыватель',
  readers: 'Считыватели',
  server: 'Центральный контур',
  sync: 'Синхронизация',
  sync_queue: 'Синхронизация',
  sync_service: 'Синхронизация',
  system: 'Система',
  system_state: 'Система',
};

const SYSTEM_BLOCKED_ACTION_LABELS = {
  emergency_stop: 'Аварийная остановка',
  incident_mutation: 'Действия по инцидентам',
  session_mutation: 'Действия по визитам',
  tap_control: 'Управление кранами',
};

const TAP_STATUS_LABELS = {
  active: 'Активен',
  cleaning: 'На промывке',
  empty: 'Пуст',
  locked: 'Заблокирован',
};

function normalizeKey(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[-\s]+/g, '_');
}

function titleCaseWords(value) {
  const text = String(value || '')
    .trim()
    .replace(/[-_]+/g, ' ')
    .replace(/\s+/g, ' ');

  if (!text) {
    return '—';
  }

  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function normalizeUserFacingBackendText(value, fallback = '') {
  const text = String(value ?? '').trim();
  if (!text) {
    return fallback;
  }

  const exact = EXACT_TEXT_MAP.get(text.toLowerCase());
  if (exact) {
    return exact;
  }

  let match = text.match(/^No heartbeat for (\d+) min$/i);
  if (match) {
    return `Нет сигнала ${match[1]} мин`;
  }

  match = text.match(/^Last heartbeat (\d+) min ago$/i);
  if (match) {
    return `Последний сигнал ${match[1]} мин назад`;
  }

  match = text.match(/^Pending sync items: (\d+)$/i);
  if (match) {
    return `Элементов в очереди синхронизации: ${match[1]}`;
  }

  match = text.match(/^Guest (.+) on this tap right now\.$/i);
  if (match) {
    return `Гость ${match[1]} сейчас обслуживается на этом кране.`;
  }

  match = text.match(/^tap_status=(.+)$/i);
  if (match) {
    const status = normalizeKey(match[1]);
    return `Статус крана: ${TAP_STATUS_LABELS[status] || titleCaseWords(status)}`;
  }

  return text;
}

export function normalizeSystemActionableStep(value) {
  const text = normalizeUserFacingBackendText(value, '');
  if (!text) {
    return '';
  }

  let match = text.match(/^Wait for backend reconnect or trigger a manual refresh before committing risky actions\.$/i);
  if (match) {
    return 'Дождитесь восстановления связи с системой или обновите сводку вручную перед рискованными действиями.';
  }

  match = text.match(/^Open the affected tap and check controller, reader, and display state on-site\.$/i);
  if (match) {
    return 'Откройте проблемный кран и проверьте на месте контроллер, считыватель и экран.';
  }

  match = text.match(/^Review sync backlog: (\d+) pending items across (\d+) sessions\.$/i);
  if (match) {
    return `Проверьте очередь синхронизации: ${match[1]} элементов в ${match[2]} визитах.`;
  }

  match = text.match(/^Inspect (\d+) stale devices from the System panel\.$/i);
  if (match) {
    return `Проверьте в разделе «Система» устройства без свежих данных: ${match[1]}.`;
  }

  match = text.match(/^No blocked actions right now; continue regular shift workflow\.$/i);
  if (match) {
    return 'Сейчас блокировок нет: продолжайте работу смены в штатном режиме.';
  }

  return text;
}

export function formatSystemBlockedActionLabel(value) {
  const key = normalizeKey(value);
  return SYSTEM_BLOCKED_ACTION_LABELS[key] || titleCaseWords(key);
}

export function humanizeIncidentType(value) {
  const key = normalizeKey(value);
  return INCIDENT_TYPE_LABELS[key] || titleCaseWords(key);
}

export function humanizeIncidentSource(value) {
  const key = normalizeKey(value);
  return INCIDENT_SOURCE_LABELS[key] || normalizeUserFacingBackendText(value, titleCaseWords(key));
}
