import { writable } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';

import { auditTrailStore } from './auditTrailStore.js';
import { sessionStore } from './sessionStore.js';
import { decodeJwtClaims, mapBackendClaimsToRoleState } from '../lib/permissionsAdapter.js';

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

const ROLES = Object.freeze({
  operator: { label: 'Оператор' },
  shift_lead: { label: 'Старший смены' },
  engineer_owner: { label: 'Инженер / владелец' },
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
