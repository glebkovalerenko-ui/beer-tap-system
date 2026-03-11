<script>
  import { onMount, onDestroy, createEventDispatcher } from 'svelte';
  import { listen } from '@tauri-apps/api/event';
  import Modal from '../common/Modal.svelte';
  import { nfcReaderStore } from '../../stores/nfcReaderStore.js';

  const dispatch = createEventDispatcher();

  export let externalError = '';

  let status = 'waiting';
  let cardUid = null;
  let errorMessage = null;
  let helperMessage = 'Поднесите RFID-карту к считывателю.';
  let unlisten = null;
  let closeTimer = null;

  function clearCloseTimer() {
    if (closeTimer) {
      clearTimeout(closeTimer);
      closeTimer = null;
    }
  }

  function syncWithReaderState() {
    if (status === 'success' || externalError) {
      return;
    }

    if ($nfcReaderStore.status === 'recovering') {
      status = 'recovering';
      errorMessage = null;
      helperMessage = $nfcReaderStore.message || 'Восстанавливаем подключение к NFC-считывателю.';
      return;
    }

    if ($nfcReaderStore.status === 'disconnected') {
      status = 'reader-unavailable';
      errorMessage = null;
      helperMessage = $nfcReaderStore.message || 'Считыватель NFC отключен. Подключите устройство.';
      return;
    }

    if ($nfcReaderStore.status === 'error') {
      status = 'error';
      errorMessage = $nfcReaderStore.error || $nfcReaderStore.message || 'Ошибка NFC-считывателя.';
      return;
    }

    status = 'waiting';
    errorMessage = null;
    helperMessage = 'Поднесите RFID-карту к считывателю.';
  }

  onMount(async () => {
    status = 'waiting';
    cardUid = null;
    errorMessage = null;
    helperMessage = 'Поднесите RFID-карту к считывателю.';
    syncWithReaderState();

    try {
      unlisten = await listen('card-status-changed', (event) => {
        if (status === 'success' || externalError) return;

        if (event.payload.error) {
          syncWithReaderState();
          if (status !== 'recovering' && status !== 'reader-unavailable') {
            status = 'error';
            errorMessage = event.payload.error;
          }
          return;
        }

        if (event.payload.uid) {
          status = 'success';
          cardUid = event.payload.uid;

          dispatch('uid-read', { uid: cardUid });

          if (!externalError) {
            clearCloseTimer();
            closeTimer = setTimeout(() => {
              dispatch('close');
            }, 1500);
          }
          return;
        }

        syncWithReaderState();
      });
    } catch (error) {
      status = 'error';
      errorMessage = 'Не удалось подписаться на события NFC. Проверьте лог приложения.';
      console.error(error);
    }
  });

  onDestroy(() => {
    if (unlisten) unlisten();
    clearCloseTimer();
  });

  $: if (externalError) {
    status = 'error';
    errorMessage = externalError;
    clearCloseTimer();
  }

  $: readerStateSnapshot = `${$nfcReaderStore.status}|${$nfcReaderStore.message || ''}|${$nfcReaderStore.error || ''}`;
  $: if (!externalError) {
    readerStateSnapshot;
    syncWithReaderState();
  }
</script>

<Modal on:close={() => dispatch('close')}>
  <div class="nfc-modal-content">
    {#if status === 'waiting'}
      <div class="status-icon">...</div>
      <h2>Ожидание карты</h2>
      <p>{helperMessage}</p>
    {:else if status === 'recovering'}
      <div class="status-icon">...</div>
      <h2>Восстановление считывателя</h2>
      <p>{helperMessage}</p>
    {:else if status === 'reader-unavailable'}
      <div class="status-icon">...</div>
      <h2>Считыватель не подключен</h2>
      <p>{helperMessage}</p>
    {:else if status === 'success'}
      <div class="status-icon">OK</div>
      <h2>Карта успешно считана</h2>
      <p class="uid-display">UID: <strong>{cardUid}</strong></p>
    {:else if status === 'error'}
      <div class="status-icon">ERR</div>
      <h2>Ошибка</h2>
      <p class="error-message">{errorMessage}</p>
    {/if}

    <button on:click={() => dispatch('close')} class="close-button">
      {#if status === 'success'}
        Готово
      {:else}
        Отмена
      {/if}
    </button>
  </div>
</Modal>

<style>
  .nfc-modal-content {
    text-align: center;
    padding: 1rem;
  }
  .status-icon {
    font-size: 2.5rem;
    margin-bottom: 1rem;
    font-weight: 700;
    color: #355070;
  }
  h2 {
    margin: 0 0 0.5rem 0;
  }
  p {
    margin: 0 0 1.5rem 0;
    color: #555;
  }
  .uid-display {
    font-family: monospace;
    background-color: #f0f0f0;
    padding: 0.5rem;
    border-radius: 4px;
    word-break: break-all;
  }
  .error-message {
    color: #d32f2f;
    font-weight: bold;
  }
  .close-button {
    background-color: #eee;
    border: 1px solid #ccc;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    cursor: pointer;
  }
</style>
