// src/stores/nfcReaderStore.js
import { writable } from 'svelte/store';
import { listen } from '@tauri-apps/api/event';
import { logError, normalizeError } from '../lib/errorUtils';

function toErrorMessage(context, error) {
  logError(context, error);
  return normalizeError(error);
}

function createNfcReaderStore() {
  const { subscribe, update } = writable({
    readerName: null,
    status: 'initializing',
    error: null,
    lastUid: null,
  });

  let unlisten = null;

  const handleEvent = (payload) => {
    update((currentState) => {
      if (payload.error) {
        return { ...currentState, status: 'error', error: normalizeError(payload.error), lastUid: null };
      }

      return { ...currentState, status: 'ok', error: null, lastUid: payload.uid || null };
    });
  };

  async function setupListener() {
    if (unlisten) {
      console.warn('NFC listener already running.');
      return;
    }

    console.log('Setting up NFC reader status listener...');
    try {
      unlisten = await listen('card-status-changed', (event) => {
        handleEvent(event.payload);
      });

      update((currentState) => ({
        ...currentState,
        status: 'ok',
        readerName: currentState.readerName || 'ACR122U',
      }));
    } catch (e) {
      const message = toErrorMessage('nfcReaderStore.setupListener', e);
      update((currentState) => ({
        ...currentState,
        status: 'error',
        error: message,
      }));
    }
  }

  setupListener();

  return {
    subscribe,
  };
}

export const nfcReaderStore = createNfcReaderStore();
