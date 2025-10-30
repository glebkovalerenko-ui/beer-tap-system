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

  let initialLoadAttempted = false;
  let showConfirmModal = false; // <-- Состояние для модального окна

  $: {
    if ($sessionStore.token && !initialLoadAttempted) {
      console.log("Dashboard: токен доступен, инициируем загрузку данных для кранов.");
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
      alert(`Failed to change state: ${error}`);
    }
  }
</script>

<div class="page-header">
  <h1>Dashboard</h1>
  <!-- Кнопка управления режимом ЧС -->
  <button 
    class="emergency-button" 
    class:active={$systemStore.emergencyStop}
    on:click={() => showConfirmModal = true}
    disabled={$systemStore.loading}
  >
    {#if $systemStore.loading}
      Processing...
    {:else if $systemStore.emergencyStop}
      Deactivate Emergency Stop
    {:else}
      Activate Emergency Stop
    {/if}
  </button>
</div>

<div class="dashboard-layout">
  <!-- Основная секция -->
  <section class="main-section">
    <h2>Equipment Status</h2>
    <div class="status-widgets-grid">
      <NfcReaderStatus />
    </div>

    {#if $tapStore.loading && $tapStore.taps.length === 0}
      <p>Loading tap statuses...</p>
    {:else if $tapStore.error}
      <p class="error">Error loading taps: {$tapStore.error}</p>
    {:else}
      <TapGrid taps={$tapStore.taps} />
    {/if}
  </section>

  <!-- Боковая секция -->
  <aside class="sidebar-section">
    {#if $pourStore.loading && $pourStore.pours.length === 0}
      <p>Loading live feed...</p>
    {:else if $pourStore.error}
       <p class="error">Error loading feed: {$pourStore.error}</p>
    {:else}
      <PourFeed pours={$pourStore.pours} />
    {/if}
  </aside>
</div>

<!-- Модальное окно подтверждения -->
{#if showConfirmModal}
  <Modal on:close={() => showConfirmModal = false}>
    <h2 slot="header">Confirm Action</h2>
    <p>
      You are about to 
      <b>{$systemStore.emergencyStop ? 'DEACTIVATE' : 'ACTIVATE'}</b> 
      the emergency stop mode.
    </p>
    <p>
      {#if !$systemStore.emergencyStop}
        This will immediately <b>LOCK</b> all taps and prevent any new pours.
      {:else}
        This will <b>UNLOCK</b> the system and allow normal operation.
      {/if}
    </p>
    <p>Are you sure you want to proceed?</p>
    <div slot="footer" class="modal-actions">
      <button on:click={() => showConfirmModal = false}>Cancel</button>
      <button 
        class="confirm-button" 
        class:danger={!$systemStore.emergencyStop}
        on:click={handleEmergencyStopToggle}
      >
        Yes, proceed
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