<script>
  import { createEventDispatcher } from 'svelte';

  import { formatDateTimeRu, formatRubAmount, formatVolumeRangeRu, formatVolumeRu } from '../../lib/formatters.js';

  export let tap;
  export let canControl = false;
  export let canMaintain = false;
  export let canDisplayOverride = false;

  const dispatch = createEventDispatcher();

  $: operations = tap.operations || {};
  $: keg = tap.keg;
  $: session = operations.activeSessionSummary;
  $: operatorState = operations.operatorState || operations.productState || 'needs_help';
  $: operatorMeta = operations.operatorStateMeta || { key: 'needs_help', tone: 'muted', icon: '?', shortLabel: 'Нет данных', eyebrow: 'Статус не определён', layout: 'stacked', headline: 'Состояние не определено', badgeStyle: 'callout', iconShape: 'alert', containerStyle: 'alert' };
  $: stateTheme = operatorMeta.tone || 'muted';
  $: stateKey = operatorMeta.key || operatorState || 'needs_help';
  $: isLocked = tap.status === 'locked';
  $: canShowStop = canControl && session;
  $: canShowLockToggle = canControl && tap.keg_id;
  $: canShowScreen = canDisplayOverride;
  $: canShowKegAction = canControl;
  $: canShowHistory = Boolean(tap?.tap_id);
  $: statusPills = [
    { label: 'Controller', value: operations.controllerStatus?.label, tone: operations.controllerStatus?.state },
    { label: 'Display', value: operations.displayStatus?.label, tone: operations.displayStatus?.state },
    { label: 'Reader', value: operations.readerStatus?.label, tone: operations.readerStatus?.state },
  ];
  $: actionCount = [
    true,
    canShowStop,
    canShowLockToggle,
    canShowScreen,
    canShowKegAction,
    canShowHistory,
  ].filter(Boolean).length;

  function emit(name) {
    dispatch(name, { tap });
  }
</script>

<div
  class={`tap-card layout-${operatorMeta.layout || 'stacked'} tone-${stateTheme} container-${operatorMeta.containerStyle || 'alert'} badge-${operatorMeta.badgeStyle || 'callout'} icon-${operatorMeta.iconShape || 'alert'}`}
  data-state={stateKey}
  role="button"
  tabindex="0"
  on:click={() => emit('open-detail')}
  on:keydown={(event) => (event.key === 'Enter' || event.key === ' ' ) && emit('open-detail')}
>
  <div class="card-header">
    <div>
      <div class="eyebrow">Tap #{tap.tap_id}</div>
      <h3>{tap.display_name}</h3>
    </div>
    <div class="state-badge" aria-label={`Статус: ${operations.productStateLabel}`}>
      <span class="badge-icon" aria-hidden="true">{operatorMeta.icon}</span>
      <span>{operations.productStateLabel}</span>
    </div>
  </div>

  <div class="card-body">
    <section class="hero status-hero">
      <div class="status-copy">
        <span class="hero-label">{operatorMeta.eyebrow || 'Операторский статус'}</span>
        <strong>{operatorMeta.headline}</strong>
        <p>{operations.operatorStateReason || 'Причина не указана.'}</p>
      </div>
      <div class="meta-block live-telemetry">
        <span class="meta-label">Поддерживающая телеметрия</span>
        <strong>{operations.liveStatus}</strong>
        {#if operations.operatorStateTelemetry}
          <p>{operations.operatorStateTelemetry}</p>
        {/if}
      </div>
    </section>

    <section class="hero beverage-hero">
      <div>
        <span class="hero-label">Напиток</span>
        <strong>{operations.beverageName}</strong>
        <p>{operations.beverageStyle || 'Без стиля / контента'}</p>
      </div>
      <div class="meta-block telemetry-chip">
        <span class="meta-label">Ключевая cue</span>
        <strong>{operatorMeta.shortLabel}</strong>
        <p>{operatorMeta.eyebrow || operatorState}</p>
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

    {#if canShowStop}
      <button class="cta danger" on:click|stopPropagation={() => emit('stop-pour')}>Стоп</button>
    {/if}

    {#if canShowLockToggle}
      <button class="cta" on:click|stopPropagation={() => emit('toggle-lock')}>
        {isLocked ? 'Разблокировать' : 'Блокировать'}
      </button>
    {/if}

    {#if canShowScreen}
      <button class="cta" on:click|stopPropagation={() => emit('display-settings')}>Экран</button>
    {/if}

    {#if canShowKegAction}
      <button class="cta" on:click|stopPropagation={() => emit(tap.keg_id ? 'unassign' : 'assign')}>
        {tap.keg_id ? 'Снять кегу' : 'Назначить кегу'}
      </button>
    {/if}

    {#if canShowHistory}
      <button class="cta" on:click|stopPropagation={() => emit('open-history')}>История</button>
    {/if}
  </div>

  {#if canMaintain}
    <div class="service-actions">
      <span>Сервисные операции</span>
      <div class="service-actions-list">
        <button class="cta" on:click|stopPropagation={() => emit('cleaning')}>Промывка</button>
        {#if tap.status === 'cleaning' || tap.status === 'empty' || isLocked}
          <button class="cta success" on:click|stopPropagation={() => emit('mark-ready')}>Перевести в готовность</button>
        {/if}
      </div>
    </div>
  {/if}
</div>

<style>
  .tap-card {
    width: 100%;
    border: 1px solid var(--tap-status-card-border, var(--border-soft, #dde3ea));
    border-radius: var(--tap-status-card-radius, 18px);
    background: var(--tap-status-card-bg, linear-gradient(180deg, rgba(255,255,255,0.98), rgba(246,248,251,0.94)));
    box-shadow: var(--tap-status-card-shadow, none);
    padding: 1rem;
    display: grid;
    gap: 1rem;
    text-align: left;
    cursor: pointer;
  }
  .tap-card:hover { box-shadow: 0 10px 28px rgba(15, 23, 42, 0.08); }
  .tap-card.layout-live { border-width: 2px; }
  .tap-card.layout-empty .keg-section { opacity: 0.72; }
  .card-header, .hero, .section-title-row, .footer-meta { display: flex; justify-content: space-between; gap: 1rem; }
  .eyebrow, .meta-label, .section-title, .muted, .hero-label { color: var(--text-secondary, #64748b); font-size: 0.82rem; }
  h3, p, strong { margin: 0; }
  .hero { align-items: flex-start; }
  .status-hero {
    border: 1px solid var(--tap-status-hero-border, #e2e8f0);
    border-radius: var(--tap-status-hero-radius, 14px);
    padding: 0.8rem;
    background: var(--tap-status-hero-bg, rgba(255,255,255,0.88));
  }
  .status-copy, .live-telemetry, .telemetry-chip { display: grid; gap: 0.2rem; }
  .status-copy { max-width: 65%; }
  .meta-block { text-align: right; }
  .state-badge {
    border-radius: var(--tap-status-badge-radius, 999px);
    padding: var(--tap-status-badge-padding, 0.45rem 0.7rem);
    border: 1px solid var(--tap-status-badge-border, transparent);
    background: var(--tap-status-badge-bg, #e5e7eb);
    color: var(--tap-status-badge-text, #475569);
    font-weight: 700;
    font-size: 0.8rem;
    white-space: nowrap;
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
  }
  .badge-icon {
    width: 1.1rem;
    height: 1.1rem;
    display: inline-grid;
    place-items: center;
    border-radius: var(--tap-status-icon-radius, 999px);
    background: var(--tap-status-icon-bg, rgba(255,255,255,0.6));
    border: 1px solid var(--tap-status-icon-border, transparent);
  }
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
  .service-actions { display: grid; gap: 0.45rem; border-top: 1px dashed #cbd5e1; padding-top: 0.8rem; }
  .service-actions-list { display: flex; flex-wrap: wrap; gap: 0.55rem; }
  .cta { border: 1px solid #cbd5e1; background: #fff; color: #0f172a; border-radius: 10px; padding: 0.6rem 0.8rem; font-weight: 600; }
  .cta.primary { background: #1d4ed8; color: #fff; border-color: #1d4ed8; }
  .cta.danger { color: #b91c1c; border-color: #fecaca; }
  .cta.success { color: #166534; border-color: #bbf7d0; }
  @media (max-width: 900px) {
    .systems-grid { grid-template-columns: 1fr; }
    .status-copy { max-width: none; }
    .hero { flex-direction: column; }
    .meta-block { text-align: left; }
  }
</style>
