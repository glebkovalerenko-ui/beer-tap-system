export const ACTION_LABELS = {
  tap: 'Открыть кран',
  visit: 'Открыть визит',
  guest: 'Открыть гостя',
  pour: 'Открыть налив',
  incident: 'Открыть инцидент',
  assignOwner: 'Взять в работу',
  checkSync: 'Открыть систему',
  system: 'Открыть систему',
  context: 'Открыть контекст',
};

const ACTION_MAP = {
  no_keg: {
    primaryTarget: 'tap',
    primaryCta: ACTION_LABELS.tap,
    secondaryCta: { target: 'incident', label: ACTION_LABELS.incident },
    recommendedOwnerState: 'Нужен ответственный',
    recommendedActionState: 'Открыть кран и назначить кегу',
  },
  stale_heartbeat: {
    primaryTarget: 'tap',
    primaryCta: ACTION_LABELS.tap,
    secondaryCta: { target: 'incident', label: ACTION_LABELS.assignOwner },
    recommendedOwnerState: 'Нужен ответственный',
    recommendedActionState: 'Проверить связь на месте и зафиксировать шаг',
  },
  unsynced_flow: {
    primaryTarget: 'system',
    primaryCta: ACTION_LABELS.checkSync,
    secondaryCta: { target: 'incident', label: ACTION_LABELS.incident },
    recommendedOwnerState: 'Ответственный по смене',
    recommendedActionState: 'Проверить синхронизацию и влияние на продажи',
  },
  reader_offline: {
    primaryTarget: 'tap',
    primaryCta: ACTION_LABELS.tap,
    secondaryCta: { target: 'system', label: ACTION_LABELS.checkSync },
    recommendedOwnerState: 'Нужен ответственный',
    recommendedActionState: 'Проверить считыватель и его связь',
  },
  display_offline: {
    primaryTarget: 'tap',
    primaryCta: ACTION_LABELS.tap,
    secondaryCta: { target: 'system', label: ACTION_LABELS.checkSync },
    recommendedOwnerState: 'Нужен ответственный',
    recommendedActionState: 'Проверить экран и синхронизацию контента',
  },
  controller_offline: {
    primaryTarget: 'tap',
    primaryCta: ACTION_LABELS.tap,
    secondaryCta: { target: 'incident', label: ACTION_LABELS.assignOwner },
    recommendedOwnerState: 'Нужен ответственный',
    recommendedActionState: 'Проверить контроллер и перевести кейс в работу',
  },
  backend_offline: {
    primaryTarget: 'incident',
    primaryCta: ACTION_LABELS.incident,
    secondaryCta: { target: 'system', label: ACTION_LABELS.checkSync },
    recommendedOwnerState: 'Назначить ответственного',
    recommendedActionState: 'Зафиксировать инцидент и проверить систему',
  },
  sync_offline: {
    primaryTarget: 'system',
    primaryCta: ACTION_LABELS.checkSync,
    secondaryCta: { target: 'incident', label: ACTION_LABELS.incident },
    recommendedOwnerState: 'Ответственный по смене',
    recommendedActionState: 'Проверить синхронизацию и эскалировать при задержке',
  },
  incident: {
    primaryTarget: 'incident',
    primaryCta: ACTION_LABELS.incident,
    secondaryCta: { target: 'tap', label: ACTION_LABELS.tap },
    recommendedOwnerState: 'Назначить ответственного',
    recommendedActionState: 'Перевести инцидент в работу и зафиксировать шаг',
  },
  default: {
    primaryTarget: 'system',
    primaryCta: ACTION_LABELS.system,
    secondaryCta: { target: 'incident', label: ACTION_LABELS.incident },
    recommendedOwnerState: 'Нужен ответственный',
    recommendedActionState: 'Открыть контекст и выбрать следующий шаг',
  },
};

export function getActionPlan(problemKind = 'default') {
  return ACTION_MAP[problemKind] || ACTION_MAP.default;
}

function setSessionStorageValue(key, value) {
  if (value == null || value === '') {
    return;
  }
  sessionStorage.setItem(key, String(value));
}

export function navigateWithFocus({
  target,
  tapId = null,
  visitId = null,
  guestId = null,
  cardUid = null,
  pourRef = null,
  kegId = null,
  source = null,
  incidentId = null,
  route = null,
  href = null,
} = {}) {
  setSessionStorageValue('incidents.focusTapId', tapId);
  setSessionStorageValue('visits.lookupVisitId', visitId);
  setSessionStorageValue('visits.focusVisitId', visitId);
  setSessionStorageValue('sessions.history.visitId', visitId);
  setSessionStorageValue('sessions.history.tapId', tapId);
  setSessionStorageValue('guests.focusGuestId', guestId);
  setSessionStorageValue('guests.focusCardUid', cardUid);
  setSessionStorageValue('pours.focusPourRef', pourRef);
  setSessionStorageValue('kegsBeverages.focusKegId', kegId);
  setSessionStorageValue('kegsBeverages.focusTapId', tapId);
  setSessionStorageValue('tapScreens.focusTapId', tapId);
  setSessionStorageValue('system.focusSource', source);
  setSessionStorageValue('incidents.focusSource', source);
  setSessionStorageValue('incidents.focusIncidentId', incidentId);

  const directRoute = route || href;
  if (directRoute) {
    window.location.hash = directRoute.startsWith('#') ? directRoute.slice(1) : directRoute;
    return;
  }

  if (target === 'tap') {
    window.location.hash = '/taps';
    return;
  }
  if (target === 'visit' || target === 'session') {
    window.location.hash = '/visits';
    return;
  }
  if (target === 'guest') {
    window.location.hash = '/guests';
    return;
  }
  if (target === 'pour') {
    window.location.hash = '/pours';
    return;
  }
  if (target === 'incident') {
    window.location.hash = '/incidents';
    return;
  }
  if (target === 'system') {
    window.location.hash = '/system';
    return;
  }

  window.location.hash = '/shift';
}
