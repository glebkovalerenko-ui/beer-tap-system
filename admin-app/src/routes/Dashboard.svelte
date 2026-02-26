<script>
  import { tapStore } from '../stores/tapStore.js';
  import { pourStore } from '../stores/pourStore.js';
  import { sessionStore } from '../stores/sessionStore.js';
  import { systemStore } from '../stores/systemStore.js';
  import { kegStore } from '../stores/kegStore.js';
  import { roleStore } from '../stores/roleStore.js';
  import { shiftStore } from '../stores/shiftStore.js';
  import { uiStore } from '../stores/uiStore.js';
  import { normalizeErrorMessage } from '../lib/errorUtils';

  import NfcReaderStatus from '../components/system/NfcReaderStatus.svelte';
  import TapGrid from '../components/taps/TapGrid.svelte';
  import PourFeed from '../components/pours/PourFeed.svelte';
  import InvestorValuePanel from '../components/system/InvestorValuePanel.svelte';
  import Modal from '../components/common/Modal.svelte';
  import ShiftReportView from '../components/reports/ShiftReportView.svelte';

  let initialLoadAttempted = false;
  let showConfirmModal = false;
  let showReportModal = false;
  let reportTitle = '';
  let reportPayload = null;
  let reportId = null;
  let zReports = [];
  let zReportsLoading = false;
  let zFilterInitialized = false;
  let fromDate = '';
  let toDate = '';

  const todayString = () => {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  $: currentShiftId = $shiftStore.shift?.id || null;
  $: canCreateOrShowCurrentZ = !$shiftStore.isOpen && $shiftStore.shift?.status === 'closed' && !!currentShiftId;

  $: {
    if ($sessionStore.token && !initialLoadAttempted) {
      tapStore.fetchTaps();
      kegStore.fetchKegs();
      shiftStore.fetchCurrent();
      initialLoadAttempted = true;
    }
  }

  $: {
    if ($sessionStore.token && !zFilterInitialized) {
      const today = todayString();
      fromDate = today;
      toDate = today;
      zFilterInitialized = true;
      loadZReports();
    }
  }

  function openReportModal({ title, payload, id = null }) {
    reportTitle = title;
    reportPayload = payload;
    reportId = id;
    showReportModal = true;
  }

  async function handleEmergencyStopToggle() {
    const newState = !$systemStore.emergencyStop;
    try {
      await systemStore.setEmergencyStop(newState);
      showConfirmModal = false;
    } catch (error) {
      uiStore.notifyError(`Ошибка изменения состояния: ${normalizeErrorMessage(error)}`);
    }
  }

  async function openShift() {
    try {
      await shiftStore.openShift();
      uiStore.notifySuccess('Смена открыта.');
    } catch (error) {
      uiStore.notifyError(normalizeErrorMessage(error));
    }
  }

  async function closeShift() {
    try {
      await shiftStore.closeShift();
      uiStore.notifySuccess('Смена закрыта.');
    } catch (error) {
      uiStore.notifyError(normalizeErrorMessage(error));
    }
  }

  async function showXReport() {
    if (!$shiftStore.isOpen || !currentShiftId) {
      uiStore.notifyWarning('X-отчёт доступен только для активной смены.');
      return;
    }
    try {
      const payload = await shiftStore.fetchXReport(currentShiftId);
      openReportModal({ title: 'X-отчёт смены', payload });
    } catch (error) {
      uiStore.notifyError(normalizeErrorMessage(error));
    }
  }

  async function createZReport() {
    if (!canCreateOrShowCurrentZ) {
      uiStore.notifyWarning('Сначала закройте смену, затем сформируйте Z-отчёт.');
      return;
    }
    try {
      const report = await shiftStore.createZReport(currentShiftId);
      openReportModal({
        title: 'Z-отчёт смены',
        payload: report.payload,
        id: report.report_id,
      });
      await loadZReports();
    } catch (error) {
      uiStore.notifyError(normalizeErrorMessage(error));
    }
  }

  async function showCurrentZReport() {
    if (!canCreateOrShowCurrentZ) {
      uiStore.notifyWarning('Нет закрытой смены для показа Z-отчёта.');
      return;
    }
    try {
      const report = await shiftStore.fetchZReport(currentShiftId);
      openReportModal({
        title: 'Z-отчёт смены',
        payload: report.payload,
        id: report.report_id,
      });
    } catch (error) {
      uiStore.notifyError(normalizeErrorMessage(error));
    }
  }

  async function loadZReports() {
    if (!fromDate || !toDate) {
      uiStore.notifyWarning('Заполните даты фильтра для поиска Z-отчётов.');
      return;
    }
    zReportsLoading = true;
    try {
      zReports = await shiftStore.listZReports(fromDate, toDate);
    } catch (error) {
      uiStore.notifyError(normalizeErrorMessage(error));
    } finally {
      zReportsLoading = false;
    }
  }

  async function openReportFromList(item) {
    try {
      const report = await shiftStore.fetchZReport(item.shift_id);
      openReportModal({
        title: 'Z-отчёт смены',
        payload: report.payload,
        id: report.report_id,
      });
    } catch (error) {
      uiStore.notifyError(normalizeErrorMessage(error));
    }
  }
</script>

<div class="page-header">
  <h1>Дашборд</h1>
  {#if $roleStore.permissions.emergency}
    <button
      class="emergency-button"
      class:active={$systemStore.emergencyStop}
      on:click={() => (showConfirmModal = true)}
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
        Открыта с {$shiftStore.shift?.opened_at ? new Date($shiftStore.shift.opened_at).toLocaleString() : '—'}
      {:else if $shiftStore.shift?.closed_at}
        Закрыта {$shiftStore.shift?.closed_at ? new Date($shiftStore.shift.closed_at).toLocaleString() : '—'}
      {:else}
        Смена закрыта.
      {/if}
    </p>
  </div>

  <div class="shift-actions">
    {#if $shiftStore.isOpen}
      <button on:click={closeShift} disabled={$shiftStore.loading}>Закрыть смену</button>
    {:else}
      <button on:click={openShift} disabled={$shiftStore.loading}>Открыть смену</button>
    {/if}
    <button on:click={showXReport} disabled={!$shiftStore.isOpen || $shiftStore.loading}>X-отчёт</button>
    <button on:click={createZReport} disabled={!canCreateOrShowCurrentZ || $shiftStore.loading}>Сформировать Z-отчёт</button>
    <button on:click={showCurrentZReport} disabled={!canCreateOrShowCurrentZ || $shiftStore.loading}>Показать Z-отчёт</button>
  </div>
</section>

<section class="ui-card z-list-panel">
  <div class="z-list-header">
    <h2>Z-отчёты</h2>
    <button on:click={loadZReports} disabled={zReportsLoading}>Найти</button>
  </div>

  <div class="filters">
    <label>
      С даты
      <input type="date" bind:value={fromDate} />
    </label>
    <label>
      По дату
      <input type="date" bind:value={toDate} />
    </label>
  </div>

  {#if zReportsLoading}
    <p>Загрузка Z-отчётов...</p>
  {:else if zReports.length === 0}
    <p>Z-отчёты не найдены для выбранного диапазона.</p>
  {:else}
    <table class="z-table">
      <thead>
        <tr>
          <th>Сформирован</th>
          <th>Смена</th>
          <th>Объём (мл)</th>
          <th>Сумма (коп)</th>
          <th>Визиты</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {#each zReports as item}
          <tr>
            <td>{item.generated_at ? new Date(item.generated_at).toLocaleString() : '—'}</td>
            <td>{item.shift_id}</td>
            <td>{item.total_volume_ml}</td>
            <td>{item.total_amount_cents}</td>
            <td>{item.active_visits_count}/{item.closed_visits_count}</td>
            <td>
              <button on:click={() => openReportFromList(item)}>Открыть</button>
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
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

{#if showReportModal}
  <Modal on:close={() => (showReportModal = false)}>
    <div slot="header">
      <h2>{reportTitle}</h2>
    </div>
    <ShiftReportView title={reportTitle} payload={reportPayload} reportId={reportId} />
    <div slot="footer" class="modal-actions">
      <button on:click={() => (showReportModal = false)}>Закрыть</button>
    </div>
  </Modal>
{/if}

{#if showConfirmModal}
  <Modal on:close={() => (showConfirmModal = false)}>
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
      <button on:click={() => (showConfirmModal = false)}>Отмена</button>
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
  .page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
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
    gap: 1rem;
  }
  .shift-panel h2 { margin: 0 0 0.2rem; }
  .shift-panel p { margin: 0; color: var(--text-secondary); }
  .shift-actions { display: flex; flex-wrap: wrap; gap: 0.5rem; justify-content: flex-end; }

  .z-list-panel { margin-bottom: 1rem; padding: 1rem; display: grid; gap: 0.75rem; }
  .z-list-header { display: flex; justify-content: space-between; align-items: center; }
  .z-list-header h2 { margin: 0; }
  .filters { display: flex; flex-wrap: wrap; gap: 1rem; }
  .filters label { display: grid; gap: 0.3rem; font-weight: 600; }
  .z-table { width: 100%; border-collapse: collapse; }
  .z-table th, .z-table td { border-bottom: 1px solid var(--border-soft); padding: 0.45rem; text-align: left; }

  .dashboard-layout { display: grid; grid-template-columns: 2fr 1fr; gap: 1rem; min-height: 60vh; }
  .status-widgets-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 1rem; margin-bottom: 1.2rem; }
  .main-section h2, .sidebar-section h2 { margin-top: 0; margin-bottom: 1rem; }
  .sidebar-section { display: flex; flex-direction: column; }
  .error { color: #c61f35; }
  .modal-actions { display: flex; justify-content: flex-end; gap: 1rem; }
  .confirm-button.danger { background-color: #d9534f; color: white; }
</style>
