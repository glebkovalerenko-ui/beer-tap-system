import { writable } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';
import { logError, normalizeError } from '../lib/errorUtils';

const READER_EVENT_DEBOUNCE_MS = 300;

const INITIAL_STATE = {
  readerName: null,
  status: 'initializing',
  lifecycleState: 'scanning',
  message: 'Инициализация NFC-считывателя...',
  error: null,
  lastUid: null,
  cardPresent: false,
  recovering: false,
};

function toErrorMessage(context, error) {
  logError(context, error);
  return normalizeError(error);
}

function normalizeReaderPayload(payload = {}) {
  const lifecycleState = payload.state || 'error';
  const readerName = payload.reader_name ?? payload.readerName ?? null;
  const message = payload.message ? String(payload.message) : null;
  const cardPresent = Boolean(payload.card_present ?? payload.cardPresent);
  const recovering = Boolean(payload.recovering);

  switch (lifecycleState) {
    case 'ready':
    case 'card_present':
      return {
        readerName,
        status: 'ok',
        lifecycleState,
        message,
        error: null,
        cardPresent,
        recovering,
      };
    case 'disconnected':
      return {
        readerName,
        status: 'disconnected',
        lifecycleState,
        message,
        error: null,
        cardPresent: false,
        recovering: false,
      };
    case 'recovering':
      return {
        readerName,
        status: 'recovering',
        lifecycleState,
        message,
        error: null,
        cardPresent: false,
        recovering: true,
      };
    case 'scanning':
      return {
        readerName,
        status: 'scanning',
        lifecycleState,
        message,
        error: null,
        cardPresent: false,
        recovering: false,
      };
    default:
      return {
        readerName,
        status: 'error',
        lifecycleState,
        message,
        error: message || 'Ошибка NFC-считывателя',
        cardPresent: false,
        recovering: false,
      };
  }
}

function areStatesEqual(left, right) {
  return (
    left.readerName === right.readerName &&
    left.status === right.status &&
    left.lifecycleState === right.lifecycleState &&
    left.message === right.message &&
    left.error === right.error &&
    left.lastUid === right.lastUid &&
    left.cardPresent === right.cardPresent &&
    left.recovering === right.recovering
  );
}

function createNfcReaderStore() {
  const { subscribe, update } = writable(INITIAL_STATE);

  let unlistenCard = null;
  let unlistenReader = null;
  let setupPromise = null;
  let readerEventDebounceTimer = null;
  let currentSnapshot = INITIAL_STATE;

  const commitState = (producer) => {
    update((currentState) => {
      const nextState = producer(currentState);
      currentSnapshot = nextState;
      return nextState;
    });
  };

  const clearReaderEventDebounce = () => {
    if (readerEventDebounceTimer) {
      clearTimeout(readerEventDebounceTimer);
      readerEventDebounceTimer = null;
    }
  };

  const applyReaderState = (next) => {
    commitState((currentState) => {
      const nextState = {
        ...currentState,
        ...next,
        lastUid:
          next.status === 'disconnected' || next.status === 'recovering' || next.status === 'error'
            ? null
            : currentState.lastUid,
      };

      return areStatesEqual(currentState, nextState) ? currentState : nextState;
    });
  };

  const handleReaderEvent = (payload) => {
    const next = normalizeReaderPayload(payload);

    if (currentSnapshot.lifecycleState === next.lifecycleState && currentSnapshot.status === next.status) {
      clearReaderEventDebounce();
      return;
    }

    if (
      next.status === 'scanning' &&
      (currentSnapshot.status === 'disconnected' || currentSnapshot.status === 'recovering')
    ) {
      clearReaderEventDebounce();
      readerEventDebounceTimer = setTimeout(() => {
        readerEventDebounceTimer = null;
        applyReaderState(next);
      }, READER_EVENT_DEBOUNCE_MS);
      return;
    }

    clearReaderEventDebounce();
    applyReaderState(next);
  };

  const handleCardEvent = (payload) => {
    commitState((currentState) => {
      let nextState;

      if (payload.error) {
        nextState = {
          ...currentState,
          error: normalizeError(payload.error),
          lastUid: null,
          cardPresent: false,
          status:
            currentState.status === 'recovering' || currentState.status === 'disconnected'
              ? currentState.status
              : 'error',
        };
      } else {
        nextState = {
          ...currentState,
          error: null,
          lastUid: payload.uid || null,
          cardPresent: Boolean(payload.uid),
        };
      }

      return areStatesEqual(currentState, nextState) ? currentState : nextState;
    });
  };

  async function setupListener() {
    if (setupPromise) {
      return setupPromise;
    }

    setupPromise = (async () => {
      if (!unlistenReader) {
        unlistenReader = await listen('reader-state-changed', (event) => {
          handleReaderEvent(event.payload);
        });
      }

      if (!unlistenCard) {
        unlistenCard = await listen('card-status-changed', (event) => {
          handleCardEvent(event.payload);
        });
      }

      const initialState = await invoke('get_nfc_reader_state');
      handleReaderEvent(initialState);
    })().catch((error) => {
      const message = toErrorMessage('nfcReaderStore.setupListener', error);
      commitState((currentState) => ({
        ...currentState,
        status: 'error',
        lifecycleState: 'error',
        error: message,
        message,
        recovering: false,
        cardPresent: false,
      }));
    });

    return setupPromise;
  }

  setupListener();

  return {
    subscribe,
  };
}

export const nfcReaderStore = createNfcReaderStore();
