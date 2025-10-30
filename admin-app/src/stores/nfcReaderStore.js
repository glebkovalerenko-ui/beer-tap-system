// src/stores/nfcReaderStore.js
import { writable } from 'svelte/store';
import { listen } from '@tauri-apps/api/event';

function createNfcReaderStore() {
  const { subscribe, update } = writable({
    readerName: null,
    status: 'initializing', // 'initializing', 'ok', 'error'
    error: null,
    lastUid: null,
  });

  let unlisten = null;

  const handleEvent = (payload) => {
    update(currentState => {
      // Это наша новая, более надежная логика.
      // Она всегда возвращает полный объект состояния.

      if (payload.error) {
        // Если пришла ошибка, устанавливаем статус 'error'.
        return { ...currentState, status: 'error', error: payload.error, lastUid: null };
      }
      
      // Любое событие без ошибки означает, что считыватель в порядке.
      // Мы просто обновляем UID (он будет либо строкой, либо null).
      return { ...currentState, status: 'ok', error: null, lastUid: payload.uid || null };
    });
  };

  async function setupListener() {
    if (unlisten) {
      console.warn("NFC listener already running.");
      return; 
    }

    console.log("Setting up NFC reader status listener...");
    try {
      unlisten = await listen('card-status-changed', (event) => {
        handleEvent(event.payload);
      });
      
      // После того как мы успешно подписались на события,
      // мы можем с уверенностью сказать, что начальное состояние - 'ok'.
      update(currentState => ({
        ...currentState,
        status: 'ok',
        readerName: currentState.readerName || 'ACR122U' // Сохраняем имя, если оно уже было
      }));

    } catch (e) {
      console.error("Failed to set up NFC listener:", e);
      update(currentState => ({
        ...currentState,
        status: 'error',
        error: 'Failed to initialize listener.'
      }));
    }
  }

  // Запускаем слушатель при создании стора
  setupListener();

  return {
    subscribe,
  };
}

export const nfcReaderStore = createNfcReaderStore();