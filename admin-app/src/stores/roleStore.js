import { writable } from 'svelte/store';
import { auditTrailStore } from './auditTrailStore.js';

const ROLES = {
  owner: {
    label: 'Владелец',
    permissions: { guests: true, taps: true, investorPanel: true, emergency: true }
  },
  manager: {
    label: 'Менеджер',
    permissions: { guests: true, taps: true, investorPanel: true, emergency: true }
  },
  bartender: {
    label: 'Бармен',
    permissions: { guests: false, taps: true, investorPanel: false, emergency: false }
  },
};

function createRoleStore() {
  const initialRole = localStorage.getItem('admin_role') || 'owner';
  const { subscribe, set } = writable({ key: initialRole, ...ROLES[initialRole] });

  return {
    subscribe,
    roles: ROLES,
    setRole: (roleKey) => {
      if (!ROLES[roleKey]) return;
      localStorage.setItem('admin_role', roleKey);
      set({ key: roleKey, ...ROLES[roleKey] });
      auditTrailStore.add('role_changed', `Роль изменена на: ${ROLES[roleKey].label}`);
    }
  };
}

export const roleStore = createRoleStore();
