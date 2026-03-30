<script>
  import DataFreshnessChip from '../components/common/DataFreshnessChip.svelte';
  import EventFeed from '../components/pours/EventFeed.svelte';
  import { navigateWithFocus } from '../lib/actionRouting.js';
  import { buildTodayFeedItems } from '../lib/operator/todayFeedModel.js';
  import { buildShiftKpis, buildTodayRouteModel } from '../lib/operator/todayModel.js';
  import { canonicalVisitStatusLabel, resolveCanonicalVisitStatus } from '../lib/operator/visitStatus.js';
  import { ROUTE_COPY } from '../lib/operator/routeCopy.js';
  import { incidentStore } from '../stores/incidentStore.js';
  import { operatorConnectionStore } from '../stores/operatorConnectionStore.js';
  import { pourStore } from '../stores/pourStore.js';
  import { roleStore } from '../stores/roleStore.js';
  import { systemStore } from '../stores/systemStore.js';
  import { tapStore } from '../stores/tapStore.js';
  import { visitStore } from '../stores/visitStore.js';

  let dismissedEventIds = new Set();
  let dismissedAttentionKeys = new Set();

  function openTap(item) {
    navigateWithFocus({ target: 'tap', tapId: item.tap_id || item.tapId, visitId: item.visit_id || item.visitId, source: item.tap_name || item.title });
  }

  function openVisit(item) {
    const visitId = item.visit_id || item.active_session?.visit_id || item.operations?.activeSessionSummary?.visitId || item.visitId || null;
    navigateWithFocus({ target: 'visit', visitId, tapId: item.tap_id || item.tapId, source: item.tap_name || item.title || item.guest_full_name });
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

  function visitNextStep(item) {
    const status = resolveCanonicalVisitStatus(item);
    if (status === 'blocked') return 'Проверить блокировку и карту';
    if (status === 'needs_attention') return 'Проверить инцидент или синхронизацию';
    if (status === 'awaiting_action') return 'Нужно действие по визиту';
    if (status === 'pouring_now') return 'Следить за наливом';
    return 'Открыть визит';
  }

  function visitMeta(item) {
    const taps = item.active_tap_id ? `кран #${item.active_tap_id}` : item.taps?.length ? `краны: ${item.taps.join(', ')}` : 'кран не выбран';
    return `${canonicalVisitStatusLabel(resolveCanonicalVisitStatus(item))} · ${item.card_uid || 'без карты'} · ${taps}`;
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
  $: activeVisits = ($visitStore.activeVisits || []).slice(0, 8);
  $: problemVisits = activeVisits.filter((item) => ['awaiting_action', 'needs_attention', 'blocked'].includes(resolveCanonicalVisitStatus(item))).slice(0, 6);
  $: pouringVisits = activeVisits.filter((item) => resolveCanonicalVisitStatus(item) === 'pouring_now').slice(0, 6);
  $: kpis = buildShiftKpis({
    activeVisitCount: ($visitStore.activeVisits || []).length,
    pouringCount: Number($tapStore.summary?.pouringCount || 0),
    openIncidentCount: ($incidentStore.items || []).filter((item) => item.status !== 'closed').length,
    volumeMl: Number($pourStore.todaySummary?.volume_ml || 0),
    revenue: Number($pourStore.todaySummary?.revenue || 0),
  });
  $: routeReadOnlyReason = $operatorConnectionStore.readOnly
    ? ($operatorConnectionStore.reason || 'Сервер отвечает нестабильно. Обзор смены доступен, но действия лучше выполнять после обновления данных.')
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
        label="Смена"
        lastFetchedAt={$pourStore.lastFetchedAt}
        staleAfterMs={$pourStore.staleTtlMs}
        mode={$operatorConnectionStore.mode}
        transport={$operatorConnectionStore.transport}
        reason={$operatorConnectionStore.reason}
      />
      <button on:click={() => (window.location.hash = '/visits')}>Визиты</button>
      <button class="secondary" on:click={() => (window.location.hash = '/incidents')}>Инциденты</button>
      <button class="secondary" on:click={() => (window.location.hash = '/taps')}>Краны</button>
    </div>
  </div>

  {#if routeReadOnlyReason}
    <div class="banner warning">
      <strong>Только просмотр.</strong>
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
          <h2>Что требует действия</h2>
          <p>Сначала показываем только то, что реально тормозит гостя, визит или работу крана прямо сейчас.</p>
        </div>
        <span class="counter">{attentionItems.length}</span>
      </div>

      {#if attentionItems.length === 0}
        <p class="muted">Срочных действий сейчас нет. Смена идёт штатно.</p>
      {:else}
        <div class="attention-list">
          {#each attentionItems as item}
            <article class="attention-item" data-severity={item.severity}>
              <div class="attention-copy">
                <div class="attention-meta">
                  <span class="category">{item.category || 'операционный сигнал'}</span>
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
          <h2>События смены</h2>
          <p>Здесь только важные сигналы для смены, а не бесконечный технический лог.</p>
        </div>
      </div>

      {#if $pourStore.loading && liveEventItems.length === 0}
        <p>Загрузка событий...</p>
      {:else if $pourStore.error}
        <p class="error">{$pourStore.error}</p>
      {:else}
        <EventFeed
          items={liveEventItems}
          title="События смены"
          emptyMessage="Свежих событий, требующих внимания, сейчас нет."
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
          <h3>Проблемные визиты</h3>
          <p>Кого нужно открыть первым, чтобы не потерять контекст гостя.</p>
        </div>
        <span class="counter">{problemVisits.length}</span>
      </div>
      {#if problemVisits.length === 0}
        <p class="muted">Сейчас нет визитов, которые ждут срочного действия.</p>
      {:else}
        <div class="compact-list">
          {#each problemVisits as item}
            <button class="compact-item" on:click={() => openVisit(item)}>
              <strong>{item.guest_full_name || 'Гость без имени'}</strong>
              <small>{visitMeta(item)}</small>
              <small class="next-step">{visitNextStep(item)}</small>
            </button>
          {/each}
        </div>
      {/if}
    </article>

    <article class="ui-card compact-panel">
      <div class="section-head compact">
        <div>
          <h3>Льют сейчас</h3>
          <p>Кто сейчас у крана и где оператору важно не потерять визит.</p>
        </div>
        <span class="counter">{pouringVisits.length}</span>
      </div>
      {#if pouringVisits.length === 0}
        <p class="muted">Прямо сейчас активных наливов нет.</p>
      {:else}
        <div class="compact-list">
          {#each pouringVisits as item}
            <button class="compact-item" on:click={() => openVisit(item)}>
              <strong>{item.guest_full_name || 'Гость без имени'}</strong>
              <small>{visitMeta(item)}</small>
              <small class="next-step">Открыть визит и следить за наливом</small>
            </button>
          {/each}
        </div>
      {/if}
    </article>

    <article class="ui-card compact-panel">
      <div class="section-head compact">
        <div>
          <h3>Активные визиты</h3>
          <p>Быстрый переход к гостю и открытому визиту без ухода в диагностику.</p>
        </div>
        <span class="counter">{activeVisits.length}</span>
      </div>
      {#if activeVisits.length === 0}
        <p class="muted">Активных визитов сейчас нет.</p>
      {:else}
        <div class="compact-list">
          {#each activeVisits.slice(0, 6) as item}
            <button class="compact-item" on:click={() => openVisit(item)}>
              <strong>{item.guest_full_name || 'Гость без имени'}</strong>
              <small>{visitMeta(item)}</small>
              <small class="next-step">{visitNextStep(item)}</small>
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
  .kpi-strip { display: grid; gap: 0.65rem; grid-template-columns: repeat(5, minmax(0, 1fr)); }
  .kpi-card {
    padding: 0.7rem 0.85rem;
    border-radius: 12px;
    border: 1px solid var(--border-soft);
    background: var(--bg-surface-muted);
    display: grid;
    gap: 0.2rem;
  }
  .kpi-card span, .category, .counter { color: var(--text-secondary); font-size: 0.82rem; }
  .kpi-card strong { font-size: 1.05rem; }
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
    padding: 0.8rem;
    background: #fff;
    color: inherit;
    text-align: left;
    display: grid;
    gap: 0.55rem;
  }
  .attention-item[data-severity='critical'] { background: var(--state-critical-bg); border-color: var(--state-critical-border); }
  .attention-item[data-severity='warning'] { background: var(--state-warning-bg); border-color: var(--state-warning-border); }
  .attention-meta { display: grid; gap: 0.25rem; }
  .attention-actions { flex-wrap: wrap; }
  .bottom-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .compact-item small, .muted, .error { color: var(--text-secondary); }
  .compact-item .next-step { font-weight: 600; color: var(--text-primary); }
  .subtle, .secondary { background: #edf2fb; color: #23416b; }
  .error { color: var(--state-critical-text); }
  @media (max-width: 1100px) {
    .kpi-strip, .main-grid, .bottom-grid { grid-template-columns: 1fr; }
    .page-header, .section-head, .attention-actions { flex-direction: column; align-items: stretch; }
    .header-actions { justify-content: flex-start; }
  }
</style>
