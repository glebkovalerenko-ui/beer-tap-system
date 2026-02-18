import { writable } from 'svelte/store';
import { auditTrailStore } from './auditTrailStore.js';

function createDemoGuideStore() {
  const { subscribe, update } = writable({ open: false });

  return {
    subscribe,
    open: () => {
      update((s) => ({ ...s, open: true }));
      auditTrailStore.add('demo_guide_opened', 'Открыт guided demo mode');
    },
    close: () => update((s) => ({ ...s, open: false })),
  };
}

export const demoGuideStore = createDemoGuideStore();
