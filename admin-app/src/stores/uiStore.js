import { writable } from 'svelte/store';

function createUiStore() {
  const { subscribe, update, set } = writable({
    toasts: [],
    confirm: null,
  });

  let nextId = 1;
  let currentConfirmResolver = null;

  function notify(message, type = 'info', timeoutMs = 3500) {
    const id = nextId++;
    update((state) => ({ ...state, toasts: [...state.toasts, { id, message, type }] }));

    if (timeoutMs > 0) {
      setTimeout(() => dismissToast(id), timeoutMs);
    }
  }

  function dismissToast(id) {
    update((state) => ({ ...state, toasts: state.toasts.filter((toast) => toast.id !== id) }));
  }

  function confirm({ title, message, confirmText = 'Подтвердить', cancelText = 'Отмена', danger = false }) {
    return new Promise((resolve) => {
      currentConfirmResolver = resolve;
      update((state) => ({
        ...state,
        confirm: { title, message, confirmText, cancelText, danger }
      }));
    });
  }

  function resolveConfirm(value) {
    if (currentConfirmResolver) {
      currentConfirmResolver(value);
      currentConfirmResolver = null;
    }
    update((state) => ({ ...state, confirm: null }));
  }

  function reset() {
    currentConfirmResolver = null;
    set({ toasts: [], confirm: null });
  }

  return {
    subscribe,
    notify,
    notifySuccess: (message, timeoutMs) => notify(message, 'success', timeoutMs),
    notifyError: (message, timeoutMs) => notify(message, 'error', timeoutMs),
    notifyWarning: (message, timeoutMs) => notify(message, 'warning', timeoutMs),
    dismissToast,
    confirm,
    resolveConfirm,
    reset,
  };
}

export const uiStore = createUiStore();
