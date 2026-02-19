import { writable } from 'svelte/store';
import { DEMO_MODE_ENABLED_BY_DEFAULT } from '../lib/config.js';

const KEY = 'admin_demo_mode_v1';

function loadDemoMode() {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw === null) return DEMO_MODE_ENABLED_BY_DEFAULT;
    return raw === 'true';
  } catch {
    return DEMO_MODE_ENABLED_BY_DEFAULT;
  }
}

function createDemoModeStore() {
  const { subscribe, set } = writable(loadDemoMode());

  return {
    subscribe,
    set: (value) => {
      localStorage.setItem(KEY, String(value));
      set(Boolean(value));
    },
    toggle: () => {
      const next = !loadDemoMode();
      localStorage.setItem(KEY, String(next));
      set(next);
    },
  };
}

export const demoModeStore = createDemoModeStore();
