import { writable } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';

import { auditTrailStore } from './auditTrailStore.js';
import { sessionStore } from './sessionStore.js';
import { decodeJwtClaims, mapBackendClaimsToRoleState } from '../lib/permissionsAdapter.js';

const PERMISSIONS = {
  taps_view: 'Доступ к обзору кранов и рабочему экрану оператора.',
  taps_control: 'Оперативное управление линиями, кегами и выдачей.',
  sessions_view: 'Просмотр и сопровождение активных визитов.',
  cards_lookup: 'Поиск по карте, UID или гостю и просмотр безопасного контекста гостя.',
  cards_open_active_session: 'Переход в активную сессию из сценария карты или гостя.',
  cards_history_view: 'Просмотр истории по карте или гостю без управляющих действий.',
  cards_top_up: 'Пополнение баланса после идентификации гостя.',
  cards_block_manage: 'Блокировка гостя и связанные ограничительные действия.',
  cards_reissue_manage: 'Отметка потерянной карты, снятие отметки потери, перевыпуск карты и перенос активной сессии.',
  incidents_view: 'Доступ только для просмотра к очереди инцидентов, фильтрам и переходам в связанный контекст.',
  incidents_manage: 'Назначение, эскалация, заметки и закрытие инцидентов.',
  inventory_view: 'Просмотр раздела «Кеги и напитки» в режиме только для чтения без изменения каталога и инвентаря.',
  kegs_manage: 'Операционные действия по кегам: подключение/отключение и изменение физического инвентаря.',
  beverages_catalog_manage: 'Редактирование каталога напитков и карточек для гостевого экрана.',
  system_health_view: 'Обзор состояния системы, устройств и синхронизации без сервисных изменений.',
  system_engineering_actions: 'Инженерные действия и углублённая техническая диагностика в разделе «Система».',
  maintenance_actions: 'Опасные сервисные действия: разблокировки, промывка, стопы.',
  display_override: 'Переопределение контента и сценариев экрана крана.',
  settings_manage: 'Изменение системных настроек и управляющих инструментов.',
  debug_tools: 'Скрытая служебная точка входа для деморежима и настроек сервера.',
  role_switch: 'Переключение рабочей роли без доступа к остальным debug-инструментам.',
};

const ROLES = Object.freeze({
  operator: { label: 'Оператор' },
  shift_lead: { label: 'Старший смены' },
  engineer_owner: { label: 'Инженер' },
});

const EMPTY_ROLE_STATE = mapBackendClaimsToRoleState({ role: 'operator', permissions: [] });

function createRoleStore() {
  const { subscribe, set, update } = writable({
    ...EMPTY_ROLE_STATE,
    source: 'bootstrap',
  });

  let activeToken = null;

  async function hydrateFromBackend(token) {
    if (!token) {
      set({ ...EMPTY_ROLE_STATE, source: 'anonymous' });
      return;
    }

    activeToken = token;
    const jwtClaims = decodeJwtClaims(token);
    if (jwtClaims) {
      set({
        ...mapBackendClaimsToRoleState(jwtClaims),
        source: 'jwt',
      });
    }

    try {
      const profile = await invoke('get_current_user_profile', { token });
      if (activeToken !== token) {
        return;
      }
      set({
        ...mapBackendClaimsToRoleState(profile),
        source: 'backend_profile',
      });
    } catch {
      // JWT fallback already applied.
    }
  }

  sessionStore.subscribe((session) => {
    hydrateFromBackend(session?.token || null);
  });

  return {
    subscribe,
    roles: ROLES,
    permissions: PERMISSIONS,
    hasPermission: (roleState, permissionKey) => Boolean(roleState?.permissions?.[permissionKey]),
    setRole: (roleKey) => {
      update((state) => {
        if (!state.permissions?.role_switch) {
          return state;
        }
        const next = mapBackendClaimsToRoleState({ role: roleKey, permissions: state.profile?.permissions || [] });
        auditTrailStore.add('Смена роли (локальный override)', `Активная рабочая роль: ${next.label}`);
        return {
          ...next,
          source: 'local_override',
          profile: {
            ...(state.profile || {}),
            role: next.key,
          },
        };
      });
    },
    refresh: async () => {
      await hydrateFromBackend(activeToken);
    },
  };
}

export const roleStore = createRoleStore();
