<script>
  import { onMount } from 'svelte';
  import { sessionStore } from '../../stores/sessionStore.js';
  import { roleStore } from '../../stores/roleStore.js';
  import { guestContextStore } from '../../stores/guestContextStore.js';
  import { shiftStore } from '../../stores/shiftStore.js';
  import { systemStore } from '../../stores/systemStore.js';
  import { uiStore } from '../../stores/uiStore.js';
  import { tapStore } from '../../stores/tapStore.js';
  import { formatDateTimeRu, formatTimeRu } from '../../lib/formatters.js';
  import { confirmShiftAction } from '../../lib/shiftActionConfirm.js';
  import { healthStateLabel } from '../../lib/healthStatus.js';
  import { SHELL_COPY } from '../../lib/operatorLabels.js';
  import ShellStatusPills from './ShellStatusPills.svelte';

  let now = new Date();

  function navigateTo(path) {
    window.location.hash = path;
  }

  function shiftStatusText() {
    if ($shiftStore.isOpen) {
      return $shiftStore.shift?.opened_at ? `Открыта с ${formatDateTimeRu($shiftStore.shift.opened_at)}` : 'Смена открыта';
    }

    if ($shiftStore.shift?.closed_at) {
      return `Закрыта ${formatDateTimeRu($shiftStore.shift.closed_at)}`;
    }

    return 'Смена закрыта';
  }

  async function handleOpenShift() {
    const confirmed = await confirmShiftAction({ uiStore, shiftState: $shiftStore, action: 'open' });
    if (!confirmed) return;

    try {
      await shiftStore.openShift();
      uiStore.notifySuccess('Смена открыта');
    } catch (error) {
      uiStore.notifyError(error?.message || error?.toString?.() || 'Не удалось открыть смену');
    }
  }

  async function handleCloseShift() {
    const confirmed = await confirmShiftAction({ uiStore, shiftState: $shiftStore, action: 'close' });
    if (!confirmed) return;

    try {
      await shiftStore.closeShift();
      uiStore.notifySuccess('Смена закрыта');
    } catch (error) {
      uiStore.notifyError(error?.message || error?.toString?.() || 'Не удалось закрыть смену');
    }
  }

  onMount(() => {
    const clockTimer = setInterval(() => {
      now = new Date();
    }, 1000);

    return () => clearInterval(clockTimer);
  });

  $: overallState = $systemStore.health.overall || 'unknown';
  $: overallStateLabel = healthStateLabel(overallState, 'overall');
  $: syncAttentionCount = Number($tapStore.summary?.unsyncedFlowCount || 0);
  $: openIncidentCount = Number($systemStore.openIncidentCount || 0);
  $: operatorName = $sessionStore.user?.name || $sessionStore.user?.email || 'Текущий оператор';
</script>

<header class="topbar ui-card">
  <section class="summary-block" aria-label={SHELL_COPY.operationalSummaryAria}>
    <div class="summary-heading">
      <div class="headline-group">
        <p class="eyebrow">{SHELL_COPY.operationalSummaryEyebrow}</p>
        <div class="headline-row">
          <strong>{$shiftStore.isOpen ? 'Смена открыта' : 'Смена закрыта'}</strong>
          <span class="overall-health" data-tone={overallState}>{overallStateLabel}</span>
        </div>
        <p class="supporting-text">
          {shiftStatusText()} · {openIncidentCount} откр. инцидентов · {syncAttentionCount} несинхр. проливов
        </p>
      </div>

      <div class="time-block" aria-label="Текущее время смены">
        <span class="time-value">{formatTimeRu(now.toISOString())}</span>
        <span class="time-date">{formatDateTimeRu(now.toISOString())}</span>
      </div>
    </div>

    <ShellStatusPills />
  </section>

  <section class="actions-block" aria-label="Действия и контекст оператора">
    <div class="shift-controls">
      {#if $shiftStore.isOpen}
        <button on:click={handleCloseShift} disabled={$shiftStore.loading}>Закрыть смену</button>
      {:else}
        <button on:click={handleOpenShift} disabled={$shiftStore.loading}>Открыть смену</button>
      {/if}

      {#if $roleStore.permissions.incidents_view}
        <button class="ghost" on:click={() => navigateTo('/incidents')}>Инциденты</button>
      {/if}
      <button class="ghost" on:click={() => navigateTo('/taps')}>Краны</button>
    </div>

    <div class="context-grid">
      <div class="guest-context">
        <span class="context-label">{SHELL_COPY.guestContext}</span>
        <div class="context-card">
          <strong>{$guestContextStore.guestName || 'Гость не выбран'}</strong>
          <span>{($guestContextStore.cardUid ? `****${$guestContextStore.cardUid.slice(-4)}` : 'без карты')} · {$guestContextStore.isActive === null ? '—' : ($guestContextStore.isActive ? 'активен' : 'заблокирован')}</span>
        </div>
      </div>

      <div class="operator-menu">
        <span class="context-label">Оператор</span>
        <div class="context-card operator-card">
          <div>
            <strong>{operatorName}</strong>
            <span>Роль: {$roleStore.label}</span>
          </div>
          <button class="ghost" on:click={() => sessionStore.logout()}>{SHELL_COPY.logout}</button>
        </div>
      </div>
    </div>
  </section>
</header>

<style>
  .topbar {
    margin: 12px;
    padding: 12px 14px;
    display: grid;
    grid-template-columns: minmax(0, 1.6fr) minmax(280px, 0.9fr);
    gap: 14px;
    border-radius: 14px;
    align-items: start;
  }
  .summary-block,
  .actions-block {
    display: grid;
    gap: 12px;
    min-width: 0;
  }
  .summary-heading {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    align-items: start;
  }
  .headline-group,
  .time-block,
  .context-grid,
  .guest-context,
  .operator-menu {
    display: grid;
    gap: 6px;
  }
  .headline-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
  }
  .eyebrow,
  .context-label {
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text-secondary);
    margin: 0;
  }
  .supporting-text,
  .time-date,
  .context-card span {
    margin: 0;
    color: var(--text-secondary);
    font-size: 0.84rem;
  }
  .overall-health {
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    padding: 4px 10px;
    font-size: 0.78rem;
    font-weight: 700;
    background: #eef2f8;
    border: 1px solid #d7e2f1;
    color: #29405f;
  }
  .overall-health[data-tone='ok'] { background: #e9f8ef; border-color: #bde8cc; color: #116d3a; }
  .overall-health[data-tone='warning'],
  .overall-health[data-tone='degraded'],
  .overall-health[data-tone='unknown'] { background: #fff8e9; border-color: #ffe1a3; color: #8d5b00; }
  .overall-health[data-tone='critical'],
  .overall-health[data-tone='error'],
  .overall-health[data-tone='offline'] { background: #ffeef0; border-color: #ffc6cc; color: #9e1f2c; }
  .time-block {
    text-align: right;
    justify-items: end;
  }
  .time-value {
    font-size: 1.45rem;
    font-weight: 700;
  }
  .shift-controls {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }
  .context-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .context-card {
    display: grid;
    gap: 2px;
    padding: 10px 12px;
    border-radius: 12px;
    background: var(--bg-surface-muted);
    border: 1px solid var(--border-soft);
  }
  .operator-card {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }
  .ghost { background: #edf2fb; color: #23416b; }

  @media (max-width: 1100px) {
    .topbar {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 820px) {
    .summary-heading,
    .operator-card {
      flex-direction: column;
      align-items: start;
    }

    .time-block {
      text-align: left;
      justify-items: start;
    }

    .context-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
