import { writable } from 'svelte/store';
import { auditTrailStore } from './auditTrailStore.js';

const STORAGE_KEY = 'admin_role';

const PERMISSIONS = {
  taps_view: 'Доступ к обзору кранов и рабочему экрану оператора.',
  taps_control: 'Оперативное управление линиями, кегами и выдачей.',
  sessions_view: 'Просмотр и сопровождение активных визитов.',
  cards_manage: 'Операции с гостями, картами и LostCards.',
  incidents_manage: 'Разбор инцидентов и регламентов.',
  system_health_view: 'Read-only обзор health, устройств и синхронизации без сервисных изменений.',
  system_engineering_actions: 'Инженерные действия и углублённая техническая диагностика в разделе «Система».',
  maintenance_actions: 'Опасные сервисные действия: разблокировки, промывка, стопы.',
  display_override: 'Override контента и сценариев экрана крана.',
  settings_manage: 'Изменение системных настроек и management-инструменты.',
  debug_tools: 'Скрытая debug / management точка входа для demo-mode, role switch и server settings.',
};

const ROLES = {
  operator: {
    label: 'Оператор',
    permissions: {
      taps_view: true,
      taps_control: false,
      sessions_view: true,
      cards_manage: false,
      incidents_manage: false,
      system_health_view: true,
      system_engineering_actions: false,
      maintenance_actions: false,
      display_override: false,
      settings_manage: false,
      debug_tools: false,
    },
  },
  shift_lead: {
    label: 'Старший смены',
    permissions: {
      taps_view: true,
      taps_control: true,
      sessions_view: true,
      cards_manage: true,
      incidents_manage: true,
      system_health_view: true,
      system_engineering_actions: false,
      maintenance_actions: true,
      display_override: false,
      settings_manage: false,
      debug_tools: false,
    },
  },
  engineer_owner: {
    label: 'Инженер / владелец',
    permissions: {
      taps_view: true,
      taps_control: true,
      sessions_view: true,
      cards_manage: true,
      incidents_manage: true,
      system_health_view: true,
      system_engineering_actions: true,
      maintenance_actions: true,
      display_override: true,
      settings_manage: true,
      debug_tools: true,
    },
  },
};

function getInitialRole() {
  if (typeof localStorage === 'undefined') {
    return 'operator';
  }

  const savedRole = localStorage.getItem(STORAGE_KEY);
  return ROLES[savedRole] ? savedRole : 'operator';
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
