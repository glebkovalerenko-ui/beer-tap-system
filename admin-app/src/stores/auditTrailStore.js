import { writable } from 'svelte/store';

function createAuditTrailStore() {
  const { subscribe, update } = writable([]);

  return {
    subscribe,
    add: (event, details = '') => {
      const item = {
        id: crypto.randomUUID ? crypto.randomUUID() : String(Date.now() + Math.random()),
        event,
        details,
        timestamp: new Date().toISOString(),
      };
      update((items) => [item, ...items].slice(0, 30));
    }
  };
}

export const auditTrailStore = createAuditTrailStore();
