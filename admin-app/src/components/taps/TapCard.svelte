<script>
  import { createEventDispatcher } from 'svelte';

  import { formatDateTimeRu, formatRubAmount, formatVolumeRangeRu, formatVolumeRu } from '../../lib/formatters.js';

  export let tap;
  export let canControl = false;
  export let canMaintain = false;
  export let canDisplayOverride = false;

  const dispatch = createEventDispatcher();

  const productStateTheme = {
    ready: 'ok',
    pouring: 'live',
    needs_help: 'warn',
    unavailable: 'muted',
    syncing: 'sync',
    no_keg: 'muted',
  };

  $: operations = tap.operations || {};
  $: keg = tap.keg;
  $: session = operations.activeSessionSummary;
  $: productState = operations.productState || 'needs_help';
  $: stateTheme = productStateTheme[productState] || 'muted';
  $: statusPills = [
    { label: 'Controller', value: operations.controllerStatus?.label, tone: operations.controllerStatus?.state },
    { label: 'Display', value: operations.displayStatus?.label, tone: operations.displayStatus?.state },
    { label: 'Reader', value: operations.readerStatus?.label, tone: operations.readerStatus?.state },
  ];
  $: actionCount = [
    true,
    tap.keg_id ? canControl : canMaintain || canControl,
    tap.keg_id && canMaintain,
    tap.keg_id && canControl,
    (tap.status === 'cleaning' || tap.status === 'empty') && canMaintain,
    canDisplayOverride,
  ].filter(Boolean).length;

  function emit(name) {
    dispatch(name, { tap });
  }

</script>

<div class="tap-card" role="button" tabindex="0" on:click={() => emit('open-detail')} on:keydown={(event) => (event.key === 'Enter' || event.key === ' ' ) && emit('open-detail')}>
  <div class="card-header">
    <div>
      <div class="eyebrow">Tap #{tap.tap_id}</div>
      <h3>{tap.display_name}</h3>
    </div>
    <div class="state-badge {stateTheme}">
      <span>{operations.productStateLabel}</span>
    </div>
  </div>

  <div class="card-body">
    <section class="hero">
      <div>
        <strong>{operations.beverageName}</strong>
        <p>{operations.beverageStyle || 'Без стиля / контента'}</p>
      </div>
      <div class="meta-block">
        <span class="meta-label">Live status</span>
        <strong>{operations.liveStatus}</strong>
      </div>
    </section>

    <section class="keg-section">
      <div class="section-title-row">
        <span class="section-title">Остаток</span>
        <span class="percent">{operations.remainingPercent || 0}%</span>
      </div>
      <div class="progress-container" title={formatVolumeRangeRu(operations.remainingVolumeMl, operations.initialVolumeMl)}>
        <div class="progress-bar" style={`width: ${operations.remainingPercent || 0}%`} class:low={(operations.remainingPercent || 0) < 15}></div>
      </div>
      <div class="volume-row">
        <span>{keg ? formatVolumeRu(operations.remainingVolumeMl) : 'Нет подключённой кеги'}</span>
        {#if keg}
          <span class="muted">из {formatVolumeRu(operations.initialVolumeMl)}</span>
        {/if}
      </div>
    </section>

    <section class="systems-grid">
      {#each statusPills as item}
        <article class={`system-pill ${item.tone || 'ok'}`}>
          <span>{item.label}</span>
          <strong>{item.value || 'Нет данных'}</strong>
        </article>
      {/each}
    </section>

    {#if session}
      <section class="session-summary">
        <div class="section-title-row compact">
          <span class="section-title">Активная сессия</span>
          <span class="muted">{session.cardUid || 'без карты'}</span>
        </div>
        <strong>{session.guestName}</strong>
        <div class="session-grid">
          <span>{session.lockedAt ? `Lock ${formatDateTimeRu(session.lockedAt)}` : 'Ожидает lock'}</span>
          <span>{operations.currentPour?.volumeMl ? formatVolumeRu(operations.currentPour.volumeMl) : '0 мл'}</span>
          <span>{operations.currentPour?.amount ? formatRubAmount(operations.currentPour.amount) : '0 ₽'}</span>
        </div>
      </section>
    {/if}

    <section class="footer-meta">
      <span>Heartbeat: {operations.heartbeat?.minutesAgo != null ? `${operations.heartbeat.minutesAgo} мин назад` : 'нет данных'}</span>
      <span>Sync: {operations.syncState?.label || 'нет данных'}</span>
    </section>
  </div>

  <div class="card-actions" class:multi-line={actionCount > 2}>
    <button class="cta primary" on:click|stopPropagation={() => emit('open-detail')}>Открыть</button>

    {#if tap.keg_id}
      {#if canControl}
        <button class="cta" on:click|stopPropagation={() => emit('toggle-lock')}>
          {tap.status === 'active' ? 'Блокировать' : 'Открыть линию'}
        </button>
      {/if}
      {#if canMaintain}
        <button class="cta" on:click|stopPropagation={() => emit('cleaning')}>Промывка</button>
      {/if}
      {#if canControl}
        <button class="cta danger" on:click|stopPropagation={() => emit('unassign')}>Снять кегу</button>
      {/if}
    {:else}
      {#if canMaintain}
        <button class="cta" on:click|stopPropagation={() => emit('cleaning')}>Промывка</button>
      {/if}
      {#if canControl}
        <button class="cta" on:click|stopPropagation={() => emit('assign')}>Назначить кегу</button>
      {/if}
    {/if}

    {#if canMaintain && (tap.status === 'cleaning' || tap.status === 'empty')}
      <button class="cta success" on:click|stopPropagation={() => emit('mark-ready')}>Вернуть в готовность</button>
    {/if}

    {#if canDisplayOverride}
      <button class="cta" on:click|stopPropagation={() => emit('display-settings')}>Экран</button>
    {/if}
  </div>
</div>

<style>
  .tap-card {
    width: 100%;
    border: 1px solid var(--border-soft, #dde3ea);
    border-radius: 18px;
    background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(246,248,251,0.94));
    padding: 1rem;
    display: grid;
    gap: 1rem;
    text-align: left;
    cursor: pointer;
  }
  .tap-card:hover { box-shadow: 0 10px 28px rgba(15, 23, 42, 0.08); }
  .card-header, .hero, .section-title-row, .footer-meta { display: flex; justify-content: space-between; gap: 1rem; }
  .eyebrow, .meta-label, .section-title, .muted { color: var(--text-secondary, #64748b); font-size: 0.82rem; }
  h3, p, strong { margin: 0; }
  .hero { align-items: flex-start; }
  .meta-block { text-align: right; }
  .state-badge { border-radius: 999px; padding: 0.45rem 0.7rem; font-weight: 700; font-size: 0.8rem; white-space: nowrap; }
  .state-badge.ok { background: #dcfce7; color: #166534; }
  .state-badge.live { background: #fee2e2; color: #b91c1c; }
  .state-badge.warn { background: #fef3c7; color: #b45309; }
  .state-badge.sync { background: #dbeafe; color: #1d4ed8; }
  .state-badge.muted { background: #e5e7eb; color: #475569; }
  .card-body { display: grid; gap: 0.9rem; }
  .progress-container { height: 9px; background: #e5e7eb; border-radius: 999px; overflow: hidden; }
  .progress-bar { height: 100%; background: linear-gradient(90deg, #22c55e, #16a34a); }
  .progress-bar.low { background: linear-gradient(90deg, #f59e0b, #d97706); }
  .volume-row { display: flex; justify-content: space-between; gap: 0.8rem; font-size: 0.9rem; }
  .systems-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 0.6rem; }
  .system-pill { border-radius: 12px; padding: 0.7rem; border: 1px solid #e2e8f0; background: #fff; display: grid; gap: 0.25rem; }
  .system-pill.ok { background: #f8fafc; }
  .system-pill.warning { background: #fffbeb; }
  .system-pill.busy { background: #eff6ff; }
  .session-summary { border: 1px solid #f1f5f9; border-radius: 14px; padding: 0.8rem; background: rgba(255,255,255,0.85); display: grid; gap: 0.45rem; }
  .session-grid { display: flex; flex-wrap: wrap; gap: 0.75rem; color: var(--text-secondary, #64748b); font-size: 0.84rem; }
  .footer-meta { flex-wrap: wrap; color: var(--text-secondary, #64748b); font-size: 0.82rem; }
  .card-actions { display: flex; flex-wrap: wrap; gap: 0.55rem; }
  .cta { border: 1px solid #cbd5e1; background: #fff; color: #0f172a; border-radius: 10px; padding: 0.6rem 0.8rem; font-weight: 600; }
  .cta.primary { background: #1d4ed8; color: #fff; border-color: #1d4ed8; }
  .cta.danger { color: #b91c1c; border-color: #fecaca; }
  .cta.success { color: #166534; border-color: #bbf7d0; }
  @media (max-width: 900px) {
    .systems-grid { grid-template-columns: 1fr; }
  }
</style>
