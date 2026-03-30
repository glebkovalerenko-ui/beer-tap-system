<script>
  import { createEventDispatcher } from 'svelte';

  import GuardedActionButton from '../common/GuardedActionButton.svelte';
  import { formatDateTimeRu, formatRubAmount, formatVolumeRangeRu, formatVolumeRu } from '../../lib/formatters.js';
  import { TAP_COPY } from '../../lib/operatorLabels.js';
  import { buildTapQuickActions } from '../../lib/operator/tapQuickActions.js';

  export let tap;
  export let canControl = false;
  export let canDisplayOverride = false;
  export let permissions = {};
  export let readOnlyReason = '';

  const dispatch = createEventDispatcher();

  $: operations = tap.operations || {};
  $: keg = tap.keg;
  $: session = operations.activeSessionSummary;
  $: operatorState = operations.operatorState || operations.productState || 'needs_help';
  $: operatorMeta = operations.operatorStateMeta || { key: 'needs_help', tone: 'muted', icon: '?', shortLabel: 'Нет данных', eyebrow: 'Статус не определён', layout: 'stacked', headline: 'Состояние не определено', badgeStyle: 'callout', iconShape: 'alert', containerStyle: 'alert' };
  $: stateTheme = operatorMeta.tone || 'muted';
  $: stateKey = operatorMeta.key || operatorState || 'needs_help';
  $: statusPills = [
    { label: TAP_COPY.controller, value: operations.controllerStatus?.label, tone: operations.controllerStatus?.state },
    { label: TAP_COPY.display, value: operations.displayStatus?.label, tone: operations.displayStatus?.state },
    { label: TAP_COPY.reader, value: operations.readerStatus?.label, tone: operations.readerStatus?.state },
  ];
  $: quickActions = buildTapQuickActions({
    tap,
    session,
    permissions,
    canControl,
    canDisplayOverride,
  });
  $: visibleActions = quickActions.map((action) => {
    if (!readOnlyReason || !['stop', 'toggle-lock'].includes(action.id)) {
      return action;
    }
    return {
      ...action,
      guarded: true,
      disabled: true,
      reason: readOnlyReason,
    };
  });
  $: actionCount = visibleActions.length;

  function emit(name) {
    dispatch(name, { tap });
  }
</script>

<article
  class={`tap-card layout-${operatorMeta.layout || 'stacked'} tone-${stateTheme} container-${operatorMeta.containerStyle || 'alert'} badge-${operatorMeta.badgeStyle || 'callout'} icon-${operatorMeta.iconShape || 'alert'}`}
  data-state={stateKey}
>
  <div class="card-header">
    <div>
      <div class="eyebrow">{TAP_COPY.tapNumber}{tap.tap_id}</div>
      <h3>{tap.display_name}</h3>
    </div>
    <div
      class="state-badge"
      aria-label={`Статус крана: ${operations.productStateLabel || 'Нет данных'}. Сигналы системы: ${operations.liveStatus || 'Нет данных'}.`}
    >
      <span class="badge-icon" aria-hidden="true">{operatorMeta.icon}</span>
      <span>{operations.productStateLabel}</span>
    </div>
  </div>

  <div class="card-body">
    <section class="hero status-hero">
      <div class="status-copy">
        <span class="hero-label">Что происходит</span>
        <strong>{operatorMeta.headline}</strong>
        <p>{operations.operatorStateReason || 'Причина не указана.'}</p>
      </div>
      <div class="meta-block live-telemetry">
        <span class="meta-label">Подтверждение статуса</span>
        <strong>{operations.liveStatus || operatorMeta.shortLabel}</strong>
        {#if operations.operatorStateTelemetry}
          <p>{operations.operatorStateTelemetry}</p>
        {/if}
      </div>
    </section>

    <section class="session-summary" class:empty={!session}>
      <div class="section-title-row compact">
        <span class="section-title">Гость и визит</span>
        <span class="muted">{session?.cardUid || 'без карты'}</span>
      </div>
      <strong>{session?.guestName || 'Сейчас у крана нет активного визита'}</strong>
      {#if session}
        <div class="session-grid">
          <span>{session.lockedAt ? `${TAP_COPY.lockAt} ${formatDateTimeRu(session.lockedAt)}` : TAP_COPY.waitingForLock}</span>
          <span>{operations.currentPour?.volumeMl ? formatVolumeRu(operations.currentPour.volumeMl) : '0 мл'}</span>
          <span>{operations.currentPour?.amount ? formatRubAmount(operations.currentPour.amount) : '0 ₽'}</span>
        </div>
      {:else}
        <p class="muted">Откройте визит, если гость уже у крана, или оставьте линию закрытой до начала обслуживания.</p>
      {/if}
    </section>

    <section class="hero beverage-hero quiet">
      <div>
        <span class="hero-label">Напиток и кега</span>
        <strong>{operations.beverageName || 'Напиток не назначен'}</strong>
        <p>{keg ? `${formatVolumeRu(operations.remainingVolumeMl)} из ${formatVolumeRu(operations.initialVolumeMl)}` : 'Кега не подключена'}</p>
      </div>
      <div class="meta-block telemetry-chip">
        <span class="meta-label">Остаток</span>
        <strong>{keg ? `${operations.remainingPercent || 0}%` : '—'}</strong>
        <p>{operations.beverageStyle || 'Без дополнительного описания'}</p>
      </div>
    </section>

    <section class="keg-section">
      <div class="section-title-row">
        <span class="section-title">Остаток кеги</span>
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
        <article
          class={`system-pill ${item.tone || 'ok'}`}
          aria-label={`${item.label}: ${item.value || 'Нет данных'}`}
        >
          <span>{item.label}</span>
          <strong>{item.value || 'Нет данных'}</strong>
        </article>
      {/each}
    </section>

    <section class="footer-meta">
      <span>{TAP_COPY.heartbeat}: {operations.heartbeat?.minutesAgo != null ? `${operations.heartbeat.minutesAgo} мин. назад` : 'нет данных'}</span>
      <span>{TAP_COPY.sync}: {operations.syncState?.label || 'нет данных'}</span>
    </section>
  </div>

  <div class="card-actions" class:multi-line={actionCount > 2}>
    {#each visibleActions as action (action.id)}
      {#if action.guarded}
        <GuardedActionButton
          className={`cta${action.tone === 'danger' ? ' danger' : action.tone === 'primary' ? ' primary' : ''}`}
          visible={true}
          disabled={action.disabled}
          reason={action.reason}
          ariaLabel={action.ariaLabel}
          on:click={() => emit(action.event)}
        >{action.title}</GuardedActionButton>
      {:else}
        <button
          class={`cta${action.tone === 'primary' ? ' primary' : ''}`}
          type="button"
          aria-label={action.ariaLabel}
          on:click={() => emit(action.event)}
        >{action.title}</button>
      {/if}
    {/each}
  </div>
</article>

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
  }
  .tap-card:hover { box-shadow: 0 10px 28px rgba(15, 23, 42, 0.08); }
  .tap-card.layout-live { border-width: 2px; }
  .tap-card.layout-empty .keg-section { opacity: 0.72; }
  .card-header, .hero, .section-title-row, .footer-meta { display: flex; justify-content: space-between; gap: 1rem; }
  .eyebrow, .meta-label, .section-title, .muted, .hero-label { color: var(--text-secondary, #64748b); font-size: 0.82rem; }
  h3, p, strong { margin: 0; }
  .hero { align-items: flex-start; }
  .status-hero,
  .session-summary,
  .beverage-hero {
    border: 1px solid var(--tap-status-hero-border, #e2e8f0);
    border-radius: var(--tap-status-hero-radius, 14px);
    padding: 0.8rem;
    background: var(--tap-status-hero-bg, rgba(255,255,255,0.88));
  }
  .beverage-hero.quiet {
    background: color-mix(in srgb, white 76%, var(--bg-surface-muted));
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
  .session-summary { display: grid; gap: 0.45rem; order: -1; }
  .session-summary.empty { background: color-mix(in srgb, white 70%, var(--bg-surface-muted)); }
  .status-hero { order: 0; }
  .beverage-hero { order: 1; }
  .meta-block p,
  .footer-meta { font-size: 0.8rem; }
  .progress-container { height: 9px; background: #e5e7eb; border-radius: 999px; overflow: hidden; }
  .progress-bar { height: 100%; background: linear-gradient(90deg, var(--state-success-border), var(--state-success-text)); }
  .progress-bar.low { background: linear-gradient(90deg, var(--state-warning-border), var(--state-warning-text)); }
  .volume-row { display: flex; justify-content: space-between; gap: 0.8rem; font-size: 0.9rem; }
  .systems-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 0.6rem; }
  .system-pill { border-radius: 12px; padding: 0.7rem; border: 1px solid var(--border-soft); background: #fff; display: grid; gap: 0.25rem; }
  .system-pill.ok { background: var(--state-success-bg); color: var(--state-success-text); border-color: var(--state-success-border); }
  .system-pill.warning { background: var(--state-warning-bg); color: var(--state-warning-text); border-color: var(--state-warning-border); }
  .system-pill.busy { background: var(--state-neutral-bg); color: var(--state-neutral-text); border-color: var(--state-neutral-border); }
  .system-pill.critical,
  .system-pill.error,
  .system-pill.offline { background: var(--state-critical-bg); color: var(--state-critical-text); border-color: var(--state-critical-border); }
  .system-pill.degraded,
  .system-pill.unknown { background: #f8fafc; color: #475569; border-color: #cbd5e1; }
  .system-pill.info,
  .system-pill.live { background: var(--state-neutral-bg); color: var(--state-neutral-text); border-color: var(--state-neutral-border); }
  .session-grid { display: flex; flex-wrap: wrap; gap: 0.75rem; color: var(--text-secondary, #64748b); font-size: 0.84rem; }
  .footer-meta { flex-wrap: wrap; color: var(--text-secondary, #64748b); font-size: 0.82rem; }
  .card-actions { display: flex; flex-wrap: wrap; gap: 0.55rem; }
  .cta { border: 1px solid #cbd5e1; background: #fff; color: #0f172a; border-radius: 10px; padding: 0.6rem 0.8rem; font-weight: 600; }
  .cta.primary { background: #1d4ed8; color: #fff; border-color: #1d4ed8; }
  .cta.danger { color: var(--state-critical-text); border-color: var(--state-critical-border); }
  .cta.success { color: var(--state-success-text); border-color: var(--state-success-border); }
  @media (max-width: 900px) {
    .systems-grid { grid-template-columns: 1fr; }
    .status-copy { max-width: none; }
    .hero { flex-direction: column; }
    .meta-block { text-align: left; }
  }
</style>
