import { writable } from 'svelte/store';

const STORAGE_KEY = 'admin_shift_state_v1';

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function createShiftStore() {
  const initial = loadState() || {
    isOpen: false,
    shiftId: null,
    openedAt: null,
    closedAt: null,
    topUpsCount: 0,
    topUpsAmount: 0,
  };

  const { subscribe, set, update } = writable(initial);

  const persist = (next) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    set(next);
  };

  return {
    subscribe,
    openShift: (operator = 'Кассир') => {
      const now = new Date();
      const shiftId = `SHIFT-${now.toISOString().slice(0, 10)}-${now.getHours()}${now.getMinutes()}`;
      persist({
        isOpen: true,
        shiftId,
        openedAt: now.toISOString(),
        closedAt: null,
        operator,
        topUpsCount: 0,
        topUpsAmount: 0,
      });
    },
    closeShift: () => {
      update((state) => {
        const next = { ...state, isOpen: false, closedAt: new Date().toISOString() };
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
        return next;
      });
    },
    recordTopUp: (amount) => {
      update((state) => {
        if (!state.isOpen) return state;
        const value = Number(amount) || 0;
        const next = {
          ...state,
          topUpsCount: state.topUpsCount + 1,
          topUpsAmount: Number((state.topUpsAmount + value).toFixed(2)),
        };
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
        return next;
      });
    },
  };
}

export const shiftStore = createShiftStore();
