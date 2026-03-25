import { writable } from 'svelte/store';

function createOperatorActionStore() {
  const { subscribe, set } = writable({ request: null });
  let requestId = 1;
  let resolver = null;

  function closeWith(value) {
    if (resolver) {
      resolver(value);
      resolver = null;
    }
    set({ request: null });
  }

  return {
    subscribe,
    open(request) {
      return new Promise((resolve) => {
        resolver = resolve;
        set({
          request: {
            id: requestId++,
            ...request,
          },
        });
      });
    },
    resolve(result) {
      closeWith(result);
    },
    cancel() {
      closeWith(null);
    },
    reset() {
      resolver = null;
      set({ request: null });
    },
  };
}

export const operatorActionStore = createOperatorActionStore();
