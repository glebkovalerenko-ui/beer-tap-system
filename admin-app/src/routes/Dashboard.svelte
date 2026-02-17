<!-- admin-app/src/routes/Dashboard.svelte -->
 
<script>
  import { tapStore } from '../stores/tapStore.js';
  import { pourStore } from '../stores/pourStore.js';
  import { sessionStore } from '../stores/sessionStore.js';
  import { systemStore } from '../stores/systemStore.js'; // <-- Импорт системного стора

  import NfcReaderStatus from '../components/system/NfcReaderStatus.svelte';
  import TapGrid from '../components/taps/TapGrid.svelte';
  import PourFeed from '../components/pours/PourFeed.svelte';
  import Modal from '../components/common/Modal.svelte'; // <-- Импорт модального окна
  import { uiStore } from '../stores/uiStore.js';

  let initialLoadAttempted = false;
  let showConfirmModal = false; // <-- Состояние для модального окна

  $: {
    if ($sessionStore.token && !initialLoadAttempted) {
      tapStore.fetchTaps();
      initialLoadAttempted = true;
    }
  }

  // Функция для обработки включения/выключения режима ЧС
  async function handleEmergencyStopToggle() {
    const newState = !$systemStore.emergencyStop;
    try {
      await systemStore.setEmergencyStop(newState);
      showConfirmModal = false; // Закрываем модальное окно при успехе
    } catch (error) {
      // Ошибки уже логируются в сторе, можно добавить alert
      uiStore.notifyError(`Ошибка изменения состояния: ${error}`);
    }
  }
</script>

<div class="page-header">
  <h1>Дашборд</h1>
  <!-- Кнопка управления режимом ЧС -->
  <button 
    class="emergency-button" 
    class:active={$systemStore.emergencyStop}
    on:click={() => showConfirmModal = true}
    disabled={$systemStore.loading}
  >
    {#if $systemStore.loading}
      Обработка...
    {:else if $systemStore.emergencyStop}
      Отключить экстренную остановку
    {:else}
      Активировать экстренную остановку
    {/if}
  </button>
</div>

<div class="dashboard-layout">
  <!-- Основная секция -->
  <section class="main-section">
    <h2>Статус оборудования</h2>
    <div class="status-widgets-grid">
      <NfcReaderStatus />
    </div>

    {#if $tapStore.loading && $tapStore.taps.length === 0}
      <p>Загрузка статусов кранов...</p>
    {:else if $tapStore.error}
      <p class="error">Ошибка загрузки кранов: {$tapStore.error}</p>
    {:else}
      <TapGrid taps={$tapStore.taps} />
    {/if}
  </section>

  <!-- Боковая секция -->
  <aside class="sidebar-section">
    <h2>Лента наливов</h2>
    {#if $pourStore.loading && $pourStore.pours.length === 0}
      <p>Загрузка ленты наливов...</p>
    {:else if $pourStore.error}
       <p class="error">Ошибка загрузки ленты: {$pourStore.error}</p>
    {:else}
      <PourFeed pours={$pourStore.pours} />
    {/if}
  </aside>
</div>

<!-- Модальное окно подтверждения -->
{#if showConfirmModal}
  <Modal on:close={() => showConfirmModal = false}>
    <h2 slot="header">Подтверждение действия</h2>
    <p>
      Вы собираетесь 
      <b>{$systemStore.emergencyStop ? 'ОТКЛЮЧИТЬ' : 'АКТИВИРОВАТЬ'}</b> 
      режим экстренной остановки.
    </p>
    <p>
      {#if !$systemStore.emergencyStop}
        Это немедленно <b>ЗАБЛОКИРУЕТ</b> все краны и запретит новые наливы.
      {:else}
        Это <b>РАЗБЛОКИРУЕТ</b> систему и вернет нормальное функционирование.
      {/if}
    </p>
    <p>Вы уверены, что хотите продолжить?</p>
    <div slot="footer" class="modal-actions">
      <button on:click={() => showConfirmModal = false}>Отмена</button>
      <button 
        class="confirm-button" 
        class:danger={!$systemStore.emergencyStop}
        on:click={handleEmergencyStopToggle}
      >
        Да, продолжить
      </button>
    </div>
  </Modal>
{/if}


<style>
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
  }
  .page-header h1 {
    margin: 0;
  }
  .emergency-button {
    background-color: #f0ad4e;
    color: white;
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 5px;
    cursor: pointer;
    font-weight: bold;
  }
  .emergency-button.active {
    background-color: #d9534f;
  }
  .emergency-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  /* Остальные стили без изменений */
  .dashboard-layout { display: grid; grid-template-columns: 2fr 1fr; gap: 1.5rem; height: calc(100vh - 8rem); }
  .status-widgets-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
  .main-section h2, .sidebar-section h2 { margin-top: 0; margin-bottom: 1rem; }
  .sidebar-section { display: flex; flex-direction: column; }
  .error { color: red; }
  .modal-actions { display: flex; justify-content: flex-end; gap: 1rem; }
  .confirm-button.danger { background-color: #d9534f; color: white; }
</style>