const ROLE_LABELS = {
  operator: 'Оператор',
  shift_lead: 'Старший смены',
  engineer_owner: 'Инженер',
};

export const CRITICAL_ACTION_MATRIX = {
  stop_pour: {
    label: 'Остановить налив',
    permission: 'taps_control',
    roles: ['shift_lead', 'engineer_owner'],
    requiresTwoStep: true,
    requiresComment: false,
    uiVisibility: 'show_disabled',
    deniedReason: 'Остановить налив может только старший смены или инженер.',
  },
  block_unblock_tap: {
    label: 'Заблокировать или разблокировать кран',
    permission: 'taps_control',
    roles: ['shift_lead', 'engineer_owner'],
    requiresTwoStep: true,
    requiresComment: false,
    uiVisibility: 'show_disabled',
    deniedReason: 'Блокировка и разблокировка крана доступны только ролям с правом управления кранами.',
  },
  close_incident: {
    label: 'Закрыть инцидент',
    permission: 'incidents_manage',
    roles: ['shift_lead', 'engineer_owner'],
    requiresTwoStep: true,
    requiresComment: true,
    uiVisibility: 'show_disabled',
    deniedReason: 'Закрытие инцидента доступно только ролям с правом управления инцидентами.',
  },
  escalate_incident: {
    label: 'Эскалировать инцидент',
    permission: 'incidents_manage',
    roles: ['shift_lead', 'engineer_owner'],
    requiresTwoStep: true,
    requiresComment: true,
    uiVisibility: 'show_disabled',
    deniedReason: 'Эскалация инцидента доступна только ролям с правом управления инцидентами.',
  },
  mark_lost_reissue: {
    label: 'Потерянная карта / перевыпуск',
    permission: 'cards_reissue_manage',
    roles: ['shift_lead', 'engineer_owner'],
    requiresTwoStep: true,
    requiresComment: false,
    uiVisibility: 'show_disabled',
    deniedReason: 'Работа с потерянной картой и перевыпуск доступны только ролям с правом перевыпуска карт.',
  },
  block_unblock_card: {
    label: 'Заблокировать или разблокировать карту',
    permission: 'cards_block_manage',
    roles: ['shift_lead', 'engineer_owner'],
    requiresTwoStep: false,
    requiresComment: false,
    uiVisibility: 'show_disabled',
    deniedReason: 'Блокировка карты доступна только ролям с правом блокировки карт.',
  },
  keg_connect_disconnect: {
    label: 'Подключить или отключить кегу',
    permission: 'taps_control',
    roles: ['shift_lead', 'engineer_owner'],
    requiresTwoStep: true,
    requiresComment: false,
    uiVisibility: 'show_disabled',
    deniedReason: 'Подключать и отключать кеги могут только роли с правом управления кранами.',
  },
  display_override: {
    label: 'Переопределение экрана крана',
    permission: 'display_override',
    roles: ['engineer_owner'],
    requiresTwoStep: false,
    requiresComment: false,
    uiVisibility: 'hidden',
    deniedReason: 'Управление гостевым экраном доступно только инженеру или владельцу.',
  },
  maintenance_toggle: {
    label: 'Сервисный режим крана',
    permission: 'maintenance_actions',
    roles: ['shift_lead', 'engineer_owner'],
    requiresTwoStep: true,
    requiresComment: false,
    uiVisibility: 'show_disabled',
    deniedReason: 'Сервисные переключения доступны только сервисным ролям.',
  },
  system_diagnostics_action: {
    label: 'Инженерная диагностика',
    permission: 'system_engineering_actions',
    roles: ['engineer_owner'],
    requiresTwoStep: true,
    requiresComment: true,
    uiVisibility: 'hidden',
    deniedReason: 'Инженерная диагностика доступна только инженеру/владельцу.',
  },
};

export function getCriticalActionGuard(actionKey, permissions = {}, options = {}) {
  const spec = CRITICAL_ACTION_MATRIX[actionKey];
  if (!spec) {
    return {
      visible: true,
      disabled: false,
      reason: '',
      allowed: true,
      spec: null,
    };
  }

  const permissionAllowed = Boolean(permissions?.[spec.permission]);
  const extraAllowed = options.extraAllowed !== false;
  const allowed = permissionAllowed && extraAllowed;
  const reason = options.reason || (!permissionAllowed ? spec.deniedReason : options.extraDeniedReason || 'Действие сейчас недоступно.');

  return {
    visible: allowed || spec.uiVisibility !== 'hidden',
    disabled: !allowed,
    reason: !allowed ? reason : '',
    allowed,
    spec,
  };
}

export function buildCriticalActionRows() {
  return Object.entries(CRITICAL_ACTION_MATRIX).map(([key, spec]) => ({
    key,
    action: spec.label,
    requiredRole: spec.roles.map((role) => ROLE_LABELS[role] || role).join(' / '),
    requiresTwoStep: spec.requiresTwoStep,
    requiresComment: spec.requiresComment,
    uiVisibility: spec.uiVisibility === 'hidden' ? 'Скрыто при отсутствии прав' : 'Показывается как недоступное с пояснением',
  }));
}
