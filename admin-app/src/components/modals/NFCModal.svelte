<!-- src/components/modals/NFCModal.svelte -->
<script>
  import { onMount, onDestroy, createEventDispatcher } from 'svelte';
  import { listen } from '@tauri-apps/api/event';
  import Modal from '../common/Modal.svelte';

  const dispatch = createEventDispatcher();

  // --- Props ---
  // +++ НАЧАЛО ИЗМЕНЕНИЙ: Добавляем prop для внешней ошибки +++
  /**
   * Позволяет родительскому компоненту передать ошибку бизнес-логики (например, от API),
   * чтобы отобразить ее в этом модальном окне.
   * @type {string}
   */
  export let externalError = '';
  // +++ КОНЕЦ ИЗМЕНЕНИЙ +++

  // --- Состояние компонента ---
  let status = 'waiting'; // 'waiting', 'success', 'error'
  let cardUid = null;
  let errorMessage = null;
  
  // --- Переменная для хранения функции отписки от события ---
  let unlisten = null;

  // --- Переменная для таймера автозакрытия ---
  let closeTimer = null;

  // --- Жизненный цикл компонента ---
  onMount(async () => {
    status = 'waiting'; 
    cardUid = null;
    errorMessage = null;

    try {
      unlisten = await listen('card-status-changed', (event) => {
        // Игнорируем события, если мы уже в состоянии успеха или внешней ошибки
        if (status === 'success' || externalError) return;

        if (event.payload.error) {
          status = 'error';
          errorMessage = event.payload.error;
        } else if (event.payload.uid) {
          status = 'success';
          cardUid = event.payload.uid;
          
          dispatch('uid-read', { uid: cardUid });

          // Закрываем модальное окно через 1.5 секунды, но только если нет внешней ошибки
          if (!externalError) {
            closeTimer = setTimeout(() => {
              dispatch('close');
            }, 1500);
          }

        } else {
          status = 'waiting';
        }
      });
    } catch (e) {
      status = 'error';
      errorMessage = 'Не удалось подписаться на события NFC. Перезапустите приложение.';
      console.error(e);
    }
  });

  onDestroy(() => {
    if (unlisten) unlisten();
    if (closeTimer) clearTimeout(closeTimer); // Очищаем таймер при размонтировании
  });

  // +++ НАЧАЛО ИЗМЕНЕНИЙ: Реактивный блок для обработки внешней ошибки +++
  // КОММЕНТАРИЙ: Этот блок будет выполняться каждый раз, когда `externalError` изменится.
  $: if (externalError) {
    status = 'error'; // Принудительно переключаем в состояние ошибки
    errorMessage = externalError; // Показываем текст внешней ошибки
    if (closeTimer) {
      clearTimeout(closeTimer); // Отменяем автоматическое закрытие, если оно было запланировано
      closeTimer = null;
    }
  }
  // +++ КОНЕЦ ИЗМЕНЕНИЙ +++
</script>

<Modal on:close={() => dispatch('close')}>
  <div class="nfc-modal-content">
    {#if status === 'waiting'}
      <div class="status-icon">🟡</div>
      <h2>Ожидание карты</h2>
      <p>Поднесите RFID-карту к считывателю.</p>
    {:else if status === 'success'}
      <div class="status-icon">✅</div>
      <h2>Карта успешно считана!</h2>
      <p class="uid-display">UID: <strong>{cardUid}</strong></p>
    {:else if status === 'error'}
      <div class="status-icon">❌</div>
      <h2>Ошибка</h2>
      <p class="error-message">{errorMessage}</p>
    {/if}

    <button on:click={() => dispatch('close')} class="close-button">
      <!-- +++ ИЗМЕНЕНИЕ: Меняем текст кнопки в зависимости от ситуации +++ -->
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
    font-size: 3rem;
    margin-bottom: 1rem;
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