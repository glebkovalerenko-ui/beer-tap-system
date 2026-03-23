import { writable } from 'svelte/store';
import { auditTrailStore } from './auditTrailStore.js';

const STORAGE_KEY = 'admin_role';

const PERMISSIONS = {
  taps_view: 'Доступ к обзору кранов и рабочему экрану оператора.',
  taps_control: 'Оперативное управление линиями, кегами и выдачей.',
  sessions_view: 'Просмотр и сопровождение активных визитов.',
  cards_lookup: 'Lookup по карте/UID/гостю и просмотр безопасного контекста гостя.',
  cards_open_active_session: 'Переход в активную сессию из card/guest сценария.',
  cards_history_view: 'Просмотр истории по карте/гостю без management-действий.',
  cards_top_up: 'Пополнение баланса после идентификации гостя.',
  cards_block_manage: 'Блокировка гостя и связанные ограничительные действия.',
  cards_reissue_manage: 'Lost / снятие lost / перевыпуск карты и перенос активной сессии.',
  incidents_view: 'Read-only доступ к очереди инцидентов, фильтрам и переходам в связанный контекст.',
  incidents_manage: 'Назначение, эскалация, заметки и закрытие инцидентов.',
  system_health_view: 'Read-only обзор health, устройств и синхронизации без сервисных изменений.',
  system_engineering_actions: 'Инженерные действия и углублённая техническая диагностика в разделе «Система».',
  maintenance_actions: 'Опасные сервисные действия: разблокировки, промывка, стопы.',
  display_override: 'Override контента и сценариев экрана крана.',
  settings_manage: 'Изменение системных настроек и management-инструменты.',
  debug_tools: 'Скрытая debug / management точка входа для demo-mode и server settings.',
  role_switch: 'Переключение рабочей роли без доступа к остальным debug-инструментам.',
};

const ROLES = {
  operator: {
    label: 'Оператор',
    permissions: {
      taps_view: true,
      taps_control: false,
      sessions_view: true,
      cards_lookup: true,
      cards_open_active_session: true,
      cards_history_view: true,
      cards_top_up: false,
      cards_block_manage: false,
      cards_reissue_manage: false,
      incidents_view: true,
      incidents_manage: false,
      system_health_view: true,
      system_engineering_actions: false,
      maintenance_actions: false,
      display_override: false,
      settings_manage: false,
      debug_tools: false,
      role_switch: false,
    },
  },
  shift_lead: {
    label: 'Старший смены',
    permissions: {
      taps_view: true,
      taps_control: true,
      sessions_view: true,
      cards_lookup: true,
      cards_open_active_session: true,
      cards_history_view: true,
      cards_top_up: true,
      cards_block_manage: true,
      cards_reissue_manage: true,
      incidents_view: true,
      incidents_manage: true,
      system_health_view: true,
      system_engineering_actions: false,
      maintenance_actions: true,
      display_override: false,
      settings_manage: false,
      debug_tools: false,
      role_switch: false,
    },
  },
  engineer_owner: {
    label: 'Инженер / владелец',
    permissions: {
      taps_view: true,
      taps_control: true,
      sessions_view: true,
      cards_lookup: true,
      cards_open_active_session: true,
      cards_history_view: true,
      cards_top_up: true,
      cards_block_manage: true,
      cards_reissue_manage: true,
      incidents_view: true,
      incidents_manage: true,
      system_health_view: true,
      system_engineering_actions: true,
      maintenance_actions: true,
      display_override: true,
      settings_manage: true,
      debug_tools: true,
      role_switch: true,
    },
  },
};

function getInitialRole() {
  if (typeof localStorage === 'undefined') {
    return 'engineer_owner';
  }

  const savedRole = localStorage.getItem(STORAGE_KEY);
  return ROLES[savedRole] ? savedRole : 'engineer_owner';
}

function createRoleStore() {
  const initialRole = getInitialRole();
  const { subscribe, set } = writable({ key: initialRole, ...ROLES[initialRole] });

  return {
    subscribe,
    roles: ROLES,
    permissions: PERMISSIONS,
    hasPermission: (roleKey, permissionKey) => Boolean(ROLES[roleKey]?.permissions?.[permissionKey]),
    setRole: (roleKey) => {
      if (!ROLES[roleKey]) return;
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem(STORAGE_KEY, roleKey);
      }
      set({ key: roleKey, ...ROLES[roleKey] });
      auditTrailStore.add('Смена роли', `Активная рабочая роль: ${ROLES[roleKey].label}`);
    }
  };
}

export const roleStore = createRoleStore();
