<!-- admin-app/src/routes/Dashboard.svelte -->
 
<script>
  import { tapStore } from '../stores/tapStore.js';
  import { pourStore } from '../stores/pourStore.js';
  import { sessionStore } from '../stores/sessionStore.js';
  import { systemStore } from '../stores/systemStore.js';
  import { kegStore } from '../stores/kegStore.js';
  import { roleStore } from '../stores/roleStore.js';
  import { shiftStore } from '../stores/shiftStore.js';

  import NfcReaderStatus from '../components/system/NfcReaderStatus.svelte';
  import TapGrid from '../components/taps/TapGrid.svelte';
  import PourFeed from '../components/pours/PourFeed.svelte';
  import InvestorValuePanel from '../components/system/InvestorValuePanel.svelte';
  import Modal from '../components/common/Modal.svelte';
  import { uiStore } from '../stores/uiStore.js';
  import { get } from 'svelte/store';

  let initialLoadAttempted = false;
  let showConfirmModal = false;
  let showShiftReportModal = false;
  let lastShiftReport = null;

  $: {
    if ($sessionStore.token && !initialLoadAttempted) {
      tapStore.fetchTaps();
      kegStore.fetchKegs();
      initialLoadAttempted = true;
    }
  }

  async function handleEmergencyStopToggle() {
    const newState = !$systemStore.emergencyStop;
    try {
      await systemStore.setEmergencyStop(newState);
      showConfirmModal = false;
    } catch (error) {
      uiStore.notifyError(`Ошибка изменения состояния: ${error}`);
    }
  }

  function openShift() {
    shiftStore.openShift($roleStore.roles[$roleStore.key]?.label || 'Кассир');
    uiStore.notifySuccess('Смена открыта. Можно выполнять денежные операции.');
  }

  function closeShift() {
    const currentShift = get(shiftStore);
    lastShiftReport = {
      shiftId: currentShift.shiftId,
      openedAt: currentShift.openedAt,
      closedAt: new Date().toISOString(),
      topUpsCount: currentShift.topUpsCount,
      topUpsAmount: currentShift.topUpsAmount,
    };
    shiftStore.closeShift();
    showShiftReportModal = true;
    uiStore.notifySuccess('Смена закрыта. Краткий отчет сохранен.');
  }
</script>

<div class="page-header">
  <h1>Дашборд</h1>
  {#if $roleStore.permissions.emergency}
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
  {:else}
    <p class="emergency-note">Роль не позволяет управлять экстренной остановкой.</p>
  {/if}
</div>

<section class="shift-panel ui-card">
  <div>
    <h2>Смена</h2>
    <p>
      {#if $shiftStore.isOpen}
        Открыта: {$shiftStore.shiftId} · Операций: {$shiftStore.topUpsCount} · Пополнений: {$shiftStore.topUpsAmount.toFixed(2)}
      {:else}
        Смена закрыта. Откройте смену перед пополнениями.
      {/if}
    </p>
  </div>
  {#if $shiftStore.isOpen}
    <button on:click={closeShift}>Закрыть смену</button>
  {:else}
    <button on:click={openShift}>Открыть смену</button>
  {/if}
</section>

{#if $roleStore.permissions.investorPanel}
  <InvestorValuePanel
    taps={$tapStore.taps}
    kegs={$kegStore.kegs}
    pours={$pourStore.pours}
    emergencyStop={$systemStore.emergencyStop}
  />
{/if}

<div class="dashboard-layout">
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

{#if showShiftReportModal && lastShiftReport}
  <Modal on:close={() => showShiftReportModal = false}>
    <h2 slot="header">Краткий отчет по смене</h2>
    <div class="shift-report">
      <p><strong>ID смены:</strong> {lastShiftReport.shiftId || '—'}</p>
      <p><strong>Открыта:</strong> {lastShiftReport.openedAt ? new Date(lastShiftReport.openedAt).toLocaleString() : '—'}</p>
      <p><strong>Закрыта:</strong> {new Date(lastShiftReport.closedAt).toLocaleString()}</p>
      <p><strong>Количество пополнений:</strong> {lastShiftReport.topUpsCount}</p>
      <p><strong>Сумма пополнений:</strong> {Number(lastShiftReport.topUpsAmount || 0).toFixed(2)}</p>
    </div>
    <div slot="footer" class="modal-actions">
      <button on:click={() => showShiftReportModal = false}>Закрыть</button>
    </div>
  </Modal>
{/if}

<style>
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
  }
  .page-header h1 { margin: 0; }
  .emergency-button {
    background-color: #f0ad4e;
    color: white;
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 5px;
    cursor: pointer;
    font-weight: bold;
  }
  .emergency-button.active { background-color: #d9534f; }
  .emergency-button:disabled { opacity: 0.6; cursor: not-allowed; }
  .emergency-note { color: var(--text-secondary); margin: 0; font-size: 0.9rem; }

  .shift-panel {
    padding: 1rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1rem;
  }
  .shift-panel h2 { margin: 0 0 0.2rem; }
  .shift-panel p { margin: 0; color: var(--text-secondary); }

  .dashboard-layout { display: grid; grid-template-columns: 2fr 1fr; gap: 1rem; min-height: 60vh; }
  .status-widgets-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 1rem; margin-bottom: 1.2rem; }
  .main-section h2, .sidebar-section h2 { margin-top: 0; margin-bottom: 1rem; }
  .sidebar-section { display: flex; flex-direction: column; }
  .error { color: #c61f35; }
  .modal-actions { display: flex; justify-content: flex-end; gap: 1rem; }
  .confirm-button.danger { background-color: #d9534f; color: white; }
  .shift-report { display: grid; gap: 0.35rem; }
  .shift-report p { margin: 0; }
</style>
