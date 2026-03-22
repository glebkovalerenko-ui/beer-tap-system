import { writable } from 'svelte/store';
import { auditTrailStore } from './auditTrailStore.js';

const STORAGE_KEY = 'admin_role';

const ROLES = {
  operator: {
    label: 'Оператор',
    permissions: {
      today: true,
      taps: true,
      sessions: true,
      cardsGuests: true,
      inventory: false,
      incidents: true,
      tapScreens: false,
      system: false,
      investorPanel: false,
      emergency: false,
    },
  },
  shift_lead: {
    label: 'Старший смены',
    permissions: {
      today: true,
      taps: true,
      sessions: true,
      cardsGuests: true,
      inventory: true,
      incidents: true,
      tapScreens: true,
      system: false,
      investorPanel: false,
      emergency: true,
    },
  },
  engineer_owner: {
    label: 'Инженер / владелец',
    permissions: {
      today: true,
      taps: true,
      sessions: true,
      cardsGuests: true,
      inventory: true,
      incidents: true,
      tapScreens: true,
      system: true,
      investorPanel: true,
      emergency: true,
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
