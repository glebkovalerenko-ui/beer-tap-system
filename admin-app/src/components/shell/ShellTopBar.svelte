<script>
  import { onMount } from 'svelte';
  import { sessionStore } from '../../stores/sessionStore.js';
  import { roleStore } from '../../stores/roleStore.js';
  import { guestContextStore } from '../../stores/guestContextStore.js';
  import { shiftStore } from '../../stores/shiftStore.js';
  import { systemStore } from '../../stores/systemStore.js';
  import { uiStore } from '../../stores/uiStore.js';
  import { formatDateTimeRu, formatTimeRu } from '../../lib/formatters.js';
  import { confirmShiftAction } from '../../lib/shiftActionConfirm.js';
  import { formatHealthPill, healthStateLabel, healthTone } from '../../lib/healthStatus.js';

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

  $: primaryHealthPills = $systemStore.health.primaryPills || [];
  $: overallState = $systemStore.health.overall || 'unknown';
  $: overallStateLabel = healthStateLabel(overallState, 'overall');
</script>

<header class="topbar ui-card">
  <section class="topbar-block shift-block" aria-label="Смена и время">
    <div class="block-head">
      <p class="eyebrow">Смена / время</p>
      <strong>{$shiftStore.isOpen ? 'Смена открыта' : 'Смена закрыта'}</strong>
    </div>
    <p class="supporting-text">{shiftStatusText()}</p>
    <div class="time-row">
      <span class="time-value">{formatTimeRu(now.toISOString())}</span>
      <span class="time-date">{formatDateTimeRu(now.toISOString())}</span>
    </div>
    <div class="shift-actions">
      {#if $shiftStore.isOpen}
        <button on:click={handleCloseShift} disabled={$shiftStore.loading}>Закрыть смену</button>
      {:else}
        <button on:click={handleOpenShift} disabled={$shiftStore.loading}>Открыть смену</button>
      {/if}
      <button class="ghost" on:click={() => sessionStore.logout()}>Выйти</button>
    </div>
  </section>

  <section class="topbar-block health-block" aria-label="Общий health">
    <div class="block-head">
      <p class="eyebrow">Общий health</p>
      <strong class:ok={healthTone(overallState) === 'ok'} class:warn={healthTone(overallState) === 'warn'} class:error={healthTone(overallState) === 'error'}>
        {overallStateLabel}
      </strong>
    </div>
    <div class="health-pills">
      {#each primaryHealthPills as item (item.key)}
        <span class="pill" class:ok={healthTone(item.state) === 'ok'} class:warn={healthTone(item.state) === 'warn'} class:error={healthTone(item.state) === 'error'} title={item.detail}>
          {formatHealthPill(item)}
        </span>
      {/each}
    </div>
    <p class="supporting-text">{$systemStore.openIncidentCount} открытых инцидентов · экстренная остановка {$systemStore.emergencyStop ? 'включена' : 'выключена'}</p>
  </section>

  <section class="topbar-block actions-block" aria-label="Быстрые действия оператора">
    <div class="block-head">
      <p class="eyebrow">Быстрые действия</p>
      <strong>Операционный контекст</strong>
    </div>
    <div class="quick-actions">
      {#if $roleStore.permissions.incidents_view}
        <button class="ghost" on:click={() => navigateTo('/incidents')}>Инциденты</button>
      {/if}
      <button class="ghost" on:click={() => navigateTo('/taps')}>Краны</button>
    </div>
    <div class="guest-context">
      <span class="guest-label">Guest context</span>
      <div class="guest-chip">
        <strong>{$guestContextStore.guestName || 'Гость не выбран'}</strong>
        <span>{($guestContextStore.cardUid ? `****${$guestContextStore.cardUid.slice(-4)}` : 'без карты')} · {$guestContextStore.isActive === null ? '—' : ($guestContextStore.isActive ? 'активен' : 'заблокирован')}</span>
      </div>
    </div>
  </section>
</header>

<style>
  .topbar {
    margin: 12px;
    padding: 12px 14px;
    display: grid;
    grid-template-columns: minmax(260px, 0.9fr) minmax(340px, 1.3fr) minmax(260px, 0.9fr);
    gap: 12px;
    border-radius: 14px;
    align-items: start;
  }
  .topbar-block {
    display: grid;
    gap: 10px;
    padding: 4px;
    min-width: 0;
  }
  .block-head {
    display: grid;
    gap: 4px;
  }
  .eyebrow {
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text-secondary);
    margin: 0;
  }
  .supporting-text, .time-date, .guest-chip span {
    margin: 0;
    color: var(--text-secondary);
    font-size: 0.84rem;
  }
  .time-row {
    display: grid;
    gap: 2px;
  }
  .time-value {
    font-size: 1.45rem;
    font-weight: 700;
  }
  .shift-actions, .quick-actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }
  .health-pills {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 8px;
  }
  .pill {
    border-radius: 999px;
    padding: 6px 10px;
    font-size: 0.78rem;
    background: #eef2f8;
    color: #29405f;
    border: 1px solid #d7e2f1;
    min-width: 0;
    white-space: normal;
    line-height: 1.3;
  }
  .ok { color: #116d3a; }
  .warn { color: #8d5b00; }
  .error { color: #9e1f2c; }
  .pill.ok { background: #e9f8ef; border-color: #bde8cc; }
  .pill.warn { background: #fff8e9; border-color: #ffe1a3; }
  .pill.error { background: #ffeef0; border-color: #ffc6cc; }
  .ghost { background: #edf2fb; color: #23416b; }
  .guest-context {
    display: grid;
    gap: 6px;
  }
  .guest-label {
    font-size: 0.76rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text-secondary);
  }
  .guest-chip {
    display: grid;
    gap: 2px;
    padding: 10px 12px;
    border-radius: 12px;
    background: var(--bg-surface-muted);
    border: 1px solid var(--border-soft);
  }
  @media (max-width: 1240px) {
    .topbar {
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    }

    .actions-block {
      grid-column: 1 / -1;
    }
  }

  @media (max-width: 820px) {
    .topbar {
      grid-template-columns: 1fr;
    }

    .health-pills {
      grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
    }
  }
</style>
