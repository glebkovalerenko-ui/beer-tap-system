<script>
  import DataFreshnessChip from '../components/common/DataFreshnessChip.svelte';
  import EventFeed from '../components/pours/EventFeed.svelte';
  import { navigateWithFocus } from '../lib/actionRouting.js';
  import { formatRubAmount, formatVolumeRu } from '../lib/formatters.js';
  import { buildTodayFeedItems } from '../lib/operator/todayFeedModel.js';
  import { buildTodayRouteModel } from '../lib/operator/todayModel.js';
  import { canonicalVisitStatusLabel } from '../lib/operator/visitStatus.js';
  import { ROUTE_COPY } from '../lib/operator/routeCopy.js';
  import { incidentStore } from '../stores/incidentStore.js';
  import { operatorConnectionStore } from '../stores/operatorConnectionStore.js';
  import { pourStore } from '../stores/pourStore.js';
  import { roleStore } from '../stores/roleStore.js';
  import { systemStore } from '../stores/systemStore.js';
  import { tapStore } from '../stores/tapStore.js';
  import { uiStore } from '../stores/uiStore.js';
  import { visitStore } from '../stores/visitStore.js';

  let dismissedEventIds = new Set();
  let dismissedAttentionKeys = new Set();

  function openTap(item) {
    navigateWithFocus({ target: 'tap', tapId: item.tap_id, visitId: item.visit_id, source: item.tap_name || item.title });
  }

  function openVisit(item) {
    const visitId = item.visit_id || item.active_session?.visit_id || item.operations?.activeSessionSummary?.visitId || item.visitId || null;
    navigateWithFocus({ target: 'visit', visitId, tapId: item.tap_id || item.tapId, source: item.tap_name || item.title });
  }

  function openAttentionItem(item) {
    navigateWithFocus({
      target: item.target,
      tapId: item.tapId || item.tap_id,
      visitId: item.visitId || item.visit_id,
      incidentId: item.incidentId,
      source: item.systemSource || item.title,
      href: item.href || '/shift',
    });
  }

  function dismissEvent(item) {
    const key = item.dismissKey || item.item_id || item.id;
    if (!key) return;
    dismissedEventIds = new Set([...dismissedEventIds, key]);
  }

  function dismissAttention(item) {
    dismissedAttentionKeys = new Set([...dismissedAttentionKeys, item.key]);
  }

  $: tapStore.setOperationalContext({
    activeVisits: $visitStore.activeVisits || [],
    feedItems: $pourStore.feedItems || [],
  });

  $: shiftModel = buildTodayRouteModel({
    incidents: $incidentStore.items || [],
    tapSummary: $tapStore.summary || {},
    taps: $tapStore.taps || [],
    systemHealth: $systemStore.health || {},
    todaySummary: $pourStore.todaySummary || {},
    todaySummaryError: $pourStore.todaySummaryError,
    permissions: $roleStore.permissions || {},
    dismissedAttentionKeys,
  });

  $: liveEventItems = buildTodayFeedItems($pourStore.feedItems || [], {
    dismissedEventIds,
    limit: 10,
  });
  $: attentionItems = shiftModel.attentionItems || [];
  $: activeVisits = ($visitStore.activeVisits || []).slice(0, 6);
  $: pouringTaps = ($tapStore.taps || []).filter((tap) => tap.operations?.productState === 'pouring').slice(0, 6);
  $: blockedOrNoKegTaps = ($tapStore.taps || []).filter((tap) => ['no_keg', 'needs_help', 'unavailable', 'syncing'].includes(tap.operations?.productState)).slice(0, 6);
  $: kpis = [
    { key: 'active-visits', label: 'Активные визиты', value: ($visitStore.activeVisits || []).length },
    { key: 'pouring-now', label: 'Льют сейчас', value: Number($tapStore.summary?.pouringCount || 0) },
    { key: 'incidents', label: 'Инциденты', value: ($incidentStore.items || []).filter((item) => item.status !== 'closed').length },
    { key: 'shift-volume', label: 'Объём за смену', value: formatVolumeRu(Number($pourStore.todaySummary?.volume_ml || 0)) },
    { key: 'shift-revenue', label: 'Выручка за смену', value: formatRubAmount(Number($pourStore.todaySummary?.revenue || 0)) },
  ];
  $: routeReadOnlyReason = $operatorConnectionStore.readOnly
    ? ($operatorConnectionStore.reason || 'Backend временно деградирован. Обзор смены доступен, но risky actions выполняйте только после обновления данных.')
    : '';
</script>

<section class="shift-page">
  <div class="page-header">
    <div>
      <h1>{ROUTE_COPY.shift.title}</h1>
      <p>{ROUTE_COPY.shift.description}</p>
    </div>
    <div class="header-actions">
      <DataFreshnessChip
        label="Shift"
        lastFetchedAt={$pourStore.lastFetchedAt}
        staleAfterMs={$pourStore.staleTtlMs}
        mode={$operatorConnectionStore.mode}
        transport={$operatorConnectionStore.transport}
        reason={$operatorConnectionStore.reason}
      />
      <button on:click={() => (window.location.hash = '/incidents')}>Инциденты</button>
      <button class="secondary" on:click={() => (window.location.hash = '/taps')}>Все краны</button>
      <button class="secondary" on:click={() => (window.location.hash = '/visits')}>Открыть визит</button>
    </div>
  </div>

  {#if routeReadOnlyReason}
    <div class="banner warning">
      <strong>Read-only mode.</strong>
      <span>{routeReadOnlyReason}</span>
    </div>
  {/if}

  <section class="kpi-strip">
    {#each kpis as item}
      <article class="kpi-card">
        <span>{item.label}</span>
        <strong>{item.value}</strong>
      </article>
    {/each}
  </section>

  <div class="main-grid">
    <section class="ui-card attention-panel">
      <div class="section-head">
        <div>
          <h2>Требует внимания</h2>
          <p>Только actionable-объекты: проблемный визит, кран, reader, sync или инцидент.</p>
        </div>
        <span class="counter">{attentionItems.length}</span>
      </div>

      {#if attentionItems.length === 0}
        <p class="muted">Критичных действий сейчас нет. Смена идёт в штатном режиме.</p>
      {:else}
        <div class="attention-list">
          {#each attentionItems as item}
            <article class="attention-item" data-severity={item.severity}>
              <div class="attention-copy">
                <div class="attention-meta">
                  <span class="category">{item.category || 'Операционный сигнал'}</span>
                  <strong>{item.actionTitle || item.title}</strong>
                </div>
                <p>{item.description}</p>
              </div>
              <div class="attention-actions">
                <button on:click={() => openAttentionItem(item)}>{item.actionLabel}</button>
                {#if item.visitId || item.visit_id}
                  <button class="secondary" on:click={() => openVisit(item)}>Открыть визит</button>
                {:else if item.tapId || item.tap_id}
                  <button class="secondary" on:click={() => openTap(item)}>Открыть кран</button>
                {/if}
                <button class="subtle" on:click={() => dismissAttention(item)}>Скрыть</button>
              </div>
            </article>
          {/each}
        </div>
      {/if}
    </section>

    <section class="ui-card feed-panel">
      <div class="section-head">
        <div>
          <h2>Живые события</h2>
          <p>Последние значимые операционные события смены без превращения в бесконечный технический лог.</p>
        </div>
      </div>

      {#if $pourStore.loading && liveEventItems.length === 0}
        <p>Загрузка событий...</p>
      {:else if $pourStore.error}
        <p class="error">{$pourStore.error}</p>
      {:else}
        <EventFeed
          items={liveEventItems}
          title="Живые события смены"
          emptyMessage="Сейчас нет свежих операционных событий."
          onOpenTap={openTap}
          onOpenSession={openVisit}
          onDismiss={dismissEvent}
        />
      {/if}
    </section>
  </div>

  <section class="bottom-grid">
    <article class="ui-card compact-panel">
      <div class="section-head compact">
        <div>
          <h3>Активные визиты</h3>
          <p>Кого сейчас обслуживает система.</p>
        </div>
        <span class="counter">{activeVisits.length}</span>
      </div>
      {#if activeVisits.length === 0}
        <p class="muted">Активных визитов сейчас нет.</p>
      {:else}
        <div class="compact-list">
          {#each activeVisits as item}
            <button class="compact-item" on:click={() => openVisit(item)}>
              <strong>{item.guest_full_name}</strong>
              <small>{canonicalVisitStatusLabel(item.canonical_visit_status)} · {item.card_uid || 'без карты'}</small>
            </button>
          {/each}
        </div>
      {/if}
    </article>

    <article class="ui-card compact-panel">
      <div class="section-head compact">
        <div>
          <h3>Активные наливы</h3>
          <p>Краны, где прямо сейчас идёт розлив.</p>
        </div>
        <span class="counter">{pouringTaps.length}</span>
      </div>
      {#if pouringTaps.length === 0}
        <p class="muted">Прямо сейчас никто не льёт.</p>
      {:else}
        <div class="compact-list">
          {#each pouringTaps as tap}
            <button class="compact-item" on:click={() => openTap(tap)}>
              <strong>{tap.display_name}</strong>
              <small>{tap.operations?.beverageName || 'Напиток не назначен'} · {tap.active_session?.guest_full_name || 'гость не определён'}</small>
            </button>
          {/each}
        </div>
      {/if}
    </article>

    <article class="ui-card compact-panel">
      <div class="section-head compact">
        <div>
          <h3>Без кеги / заблокированы</h3>
          <p>Краны, где нужен быстрый операторский шаг.</p>
        </div>
        <span class="counter">{blockedOrNoKegTaps.length}</span>
      </div>
      {#if blockedOrNoKegTaps.length === 0}
        <p class="muted">Все краны сейчас в рабочем состоянии.</p>
      {:else}
        <div class="compact-list">
          {#each blockedOrNoKegTaps as tap}
            <button class="compact-item" on:click={() => openTap(tap)}>
              <strong>{tap.display_name}</strong>
              <small>{tap.operations?.productStateLabel || tap.status} · {tap.operations?.beverageName || 'без напитка'}</small>
            </button>
          {/each}
        </div>
      {/if}
    </article>
  </section>
</section>

<style>
  .shift-page { display: grid; gap: 1rem; }
  .page-header, .header-actions, .section-head, .attention-actions { display: flex; gap: 1rem; justify-content: space-between; align-items: flex-start; }
  .page-header p, .section-head p, .attention-item p { margin: 0.25rem 0 0; color: var(--text-secondary); }
  .header-actions { flex-wrap: wrap; justify-content: flex-end; }
  .banner { display: grid; gap: 0.35rem; padding: 0.9rem 1rem; border-radius: 16px; }
  .banner.warning { background: var(--state-warning-bg); border: 1px solid var(--state-warning-border); color: var(--state-warning-text); }
  .kpi-strip { display: grid; gap: 0.85rem; grid-template-columns: repeat(5, minmax(0, 1fr)); }
  .kpi-card {
    padding: 0.95rem 1rem;
    border-radius: 14px;
    border: 1px solid var(--border-soft);
    background: var(--bg-surface-muted);
    display: grid;
    gap: 0.35rem;
  }
  .kpi-card span, .category, .counter, .eyebrow { color: var(--text-secondary); font-size: 0.82rem; }
  .kpi-card strong { font-size: 1.2rem; }
  .main-grid { display: grid; gap: 1rem; grid-template-columns: minmax(340px, 0.95fr) minmax(0, 1.25fr); align-items: start; }
  .attention-panel, .feed-panel, .compact-panel { display: grid; gap: 1rem; }
  .section-head.compact { margin-bottom: 0; }
  .counter {
    padding: 0.35rem 0.65rem;
    border-radius: 999px;
    background: var(--bg-surface-muted);
    font-weight: 700;
  }
  .attention-list, .bottom-grid, .compact-list { display: grid; gap: 0.75rem; }
  .attention-item, .compact-item {
    border: 1px solid var(--border-soft);
    border-radius: 14px;
    padding: 0.9rem;
    background: #fff;
    color: inherit;
    text-align: left;
    display: grid;
    gap: 0.75rem;
  }
  .attention-item[data-severity='critical'] { background: var(--state-critical-bg); border-color: var(--state-critical-border); }
  .attention-item[data-severity='warning'] { background: var(--state-warning-bg); border-color: var(--state-warning-border); }
  .attention-meta { display: grid; gap: 0.25rem; }
  .attention-actions { flex-wrap: wrap; }
  .bottom-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .compact-item small, .muted, .error { color: var(--text-secondary); }
  .subtle, .secondary { background: #edf2fb; color: #23416b; }
  .error { color: var(--state-critical-text); }
  @media (max-width: 1100px) {
    .kpi-strip, .main-grid, .bottom-grid { grid-template-columns: 1fr; }
    .page-header, .section-head, .attention-actions { flex-direction: column; align-items: stretch; }
    .header-actions { justify-content: flex-start; }
  }
</style>
