<script>
  import { onMount } from 'svelte';
  import { incidentStore } from '../stores/incidentStore.js';
  import { pourStore } from '../stores/pourStore.js';
  import { shiftStore } from '../stores/shiftStore.js';
  import { sessionStore } from '../stores/sessionStore.js';
  import { systemStore } from '../stores/systemStore.js';
  import { tapStore } from '../stores/tapStore.js';
  import { visitStore } from '../stores/visitStore.js';
  import EventFeed from '../components/pours/EventFeed.svelte';
  import { formatDateTimeRu, formatTimeRu } from '../lib/formatters.js';
  import { formatHealthPill, healthStateLabel, healthTone } from '../lib/healthStatus.js';
  import { navigateWithFocus } from '../lib/actionRouting.js';
  import { uiStore } from '../stores/uiStore.js';
  import { roleStore } from '../stores/roleStore.js';
  import { buildTodayRouteModel } from '../lib/operator/todayModel.js';

  let now = new Date();
  let dismissedEventIds = new Set();
  let dismissedAttentionKeys = new Set();
  let initialLoadAttempted = false;

  function openTap(item) {
    navigateWithFocus({ target: 'tap', tapId: item.tap_id, source: item.tap_name || item.title });
    uiStore.notifySuccess(`Переход к крану ${item.tap_name || item.title || item.tap_id || ''}`.trim());
  }

  function openSession(item) {
    const visitId = item.visit_id || item.active_session?.visit_id || item.operations?.activeSessionSummary?.visitId || null;
    navigateWithFocus({ target: 'session', visitId, source: item.tap_name || item.title });
  }

  function openActionTarget(item) {
    if (!item) return;

    navigateWithFocus({
      target: item.target,
      tapId: item.tapId || item.tap_id,
      visitId: item.visitId,
      source: item.systemSource || item.title || item.label,
      incidentId: item.incidentId,
      href: item.href || '/today',
    });
  }

  function dismissEvent(item) {
    dismissedEventIds = new Set([...dismissedEventIds, item.item_id]);
  }

  function dismissAttention(item) {
    dismissedAttentionKeys = new Set([...dismissedAttentionKeys, item.key]);
  }

  function shiftSummary() {
    if ($shiftStore.isOpen) {
      return $shiftStore.shift?.opened_at ? `Открыта с ${formatDateTimeRu($shiftStore.shift.opened_at)}` : 'Смена открыта';
    }
    if ($shiftStore.shift?.closed_at) {
      return `Закрыта ${formatDateTimeRu($shiftStore.shift.closed_at)}`;
    }
    return 'Смена закрыта';
  }


  onMount(() => {
    const timer = setInterval(() => {
      now = new Date();
    }, 1000);

    return () => clearInterval(timer);
  });

  $: if ($sessionStore.token && !initialLoadAttempted) {
    tapStore.fetchTaps();
    visitStore.fetchActiveVisits();
    shiftStore.fetchCurrent();
    initialLoadAttempted = true;
  }

  $: tapStore.setOperationalContext({
    activeVisits: $visitStore.activeVisits || [],
    feedItems: $pourStore.feedItems || [],
  });

  $: activeIncidents = ($incidentStore.items || []).filter((item) => item.status !== 'closed');
  $: visibleFeedItems = ($pourStore.feedItems || []).filter((item) => !dismissedEventIds.has(item.item_id)).slice(0, 12);
  $: healthItems = $systemStore.health.primaryPills || [];
  $: todayModel = buildTodayRouteModel({
    incidents: $incidentStore.items || [],
    tapSummary: $tapStore.summary || {},
    taps: $tapStore.taps || [],
    systemHealth: $systemStore.health || {},
    todaySummary: $pourStore.todaySummary || {},
    todaySummaryError: $pourStore.todaySummaryError,
    permissions: $roleStore.permissions || {},
    dismissedAttentionKeys,
  });
  $: criticalIncidents = todayModel.criticalIncidents;
  $: sessionsToday = todayModel.sessionsToday;
  $: todaySummaryPeriod = todayModel.todaySummaryPeriod;
  $: todaySummaryWarning = todayModel.todaySummaryWarning;
  $: attentionItems = todayModel.attentionItems;
  $: operatorActionItems = todayModel.operatorActionItems;
  $: primaryActionItem = todayModel.primaryActionItem;
  $: deEmphasizeSecondaryStats = todayModel.deEmphasizeSecondaryStats;
  $: heroStats = todayModel.heroStats;
  $: secondaryActionItems = operatorActionItems.slice(1, 5);
  $: canViewIncidents = Boolean($roleStore.permissions?.incidents_view);
  $: incidentsAccessHint = 'Нет доступа к инцидентам. Нужна роль с правом incidents_view.';
  $: priorityCta = todayModel.priorityCta;
</script>

<section class="today-page">
  <section class="top-strip ui-card">
    <article>
      <span class="eyebrow">Текущая смена</span>
      <strong>{$shiftStore.isOpen ? 'Открыта' : 'Закрыта'}</strong>
      <small>{shiftSummary()}</small>
    </article>
    <article>
      <span class="eyebrow">Текущее время</span>
      <strong>{formatTimeRu(now.toISOString())}</strong>
      <small>{formatDateTimeRu(now.toISOString())}</small>
    </article>
    <article class="health-overview" data-tone={$systemStore.health.overall}>
      <span class="eyebrow">Состояние системы</span>
      <strong>{healthStateLabel($systemStore.health.overall, 'overall')}</strong>
      <div class="health-pills">
        {#each healthItems as item}
          <span class="health-pill {healthTone(item.state)}">{formatHealthPill(item)}</span>
        {/each}
      </div>
    </article>
  </section>

  <section class="hero ui-card">
    <div class="hero-copy">
      <span class="eyebrow">Сегодня</span>
      <h1>Сегодня</h1>
      <p>Сначала — живое операционное состояние, затем дневные итоги по продажам и наливам.</p>
    </div>
    <div class="hero-actions">
      {#if canViewIncidents}
        <a class="cta-button incidents-entry" href="#/incidents">Инциденты</a>
      {:else}
        <button
          class="cta-button incidents-entry"
          type="button"
          disabled
          title={incidentsAccessHint}
          aria-label={incidentsAccessHint}
        >
          Инциденты
        </button>
      {/if}
      <button class="cta-button contextual" on:click={() => openActionTarget(priorityCta)}>{priorityCta.label}</button>
      <a class="cta-button secondary" href="#/taps">Все краны</a>
    </div>
    <div class="stats" data-muted={deEmphasizeSecondaryStats}>
      {#each heroStats as item}
        <article data-tone={item.tone} data-emphasis={item.emphasis}>
          <span>{item.label}</span>
          <strong>{item.value}</strong>
        </article>
      {/each}
    </div>
  </section>

  {#if todaySummaryWarning}
    <div class="summary-warning" role="status">
      <strong>Сводка KPI неполная.</strong>
      <span>{todaySummaryWarning}</span>
    </div>
  {/if}

  <div class="content-grid">
    <aside class="ui-card panel attention-panel priority-panel">
      <div class="section-head">
        <div>
          <h2>Что требует действия сейчас</h2>
          <p>Один главный шаг для оператора сверху, ниже — короткий список вторичных задач без конкуренции с обзорной лентой.</p>
        </div>
        <span class="count">{attentionItems.length}</span>
      </div>

      <section class="next-actions">
        <div class="next-actions-head">
          <h3>Приоритетное действие</h3>
          <span>{primaryActionItem ? 1 : 0}</span>
        </div>
        {#if !primaryActionItem}
          <p>Критичных действий сейчас нет — можно работать по обычному регламенту смены.</p>
        {:else}
          <button class="next-action primary" data-severity={primaryActionItem.severity} on:click={() => openActionTarget(primaryActionItem)}>
            <span>{primaryActionItem.title}</span>
            <small>{primaryActionItem.description}</small>
            <strong>{primaryActionItem.actionLabel}</strong>
          </button>
        {/if}
      </section>

      {#if secondaryActionItems.length > 0}
        <section class="secondary-actions">
          <div class="next-actions-head compact">
            <h3>Следом проверить</h3>
            <span>{secondaryActionItems.length}</span>
          </div>
          <div class="secondary-actions-list">
            {#each secondaryActionItems as item}
              <button class="secondary-action" data-severity={item.severity} on:click={() => openActionTarget(item)}>
                <div>
                  <span>{item.title}</span>
                  <small>{item.description}</small>
                </div>
                <strong>{item.actionLabel}</strong>
              </button>
            {/each}
          </div>
        </section>
      {/if}

      {#if attentionItems.length === 0}
        <p>Сейчас нет задач, требующих немедленного внимания.</p>
      {:else}
        <div class="attention-list">
          {#each attentionItems as item}
            <article class="attention-item" data-severity={item.severity}>
              <div>
                <span class="attention-category">{item.category}</span>
                <strong>{item.actionTitle || item.title}</strong>
                <p>{item.description}</p>
              </div>
              <div class="attention-actions">
                <button on:click={() => openActionTarget(item)}>{item.actionLabel}</button>
                <button class="subtle" on:click={() => dismissAttention(item)}>Скрыть</button>
              </div>
            </article>
          {/each}
        </div>
      {/if}
    </aside>

    <section class="ui-card panel feed-panel">
      <div class="section-head">
        <div>
          <h2>Обзорная лента событий</h2>
          <p>{sessionsToday} сессий за {todaySummaryPeriod === 'shift' ? 'смену' : 'день'} · {$tapStore.summary?.pouringCount || 0} кранов льют прямо сейчас</p>
        </div>
      </div>

      {#if $pourStore.loading && visibleFeedItems.length === 0}
        <p>Загрузка ленты событий...</p>
      {:else if $pourStore.error}
        <p class="error">Ошибка загрузки ленты: {$pourStore.error}</p>
      {:else}
        <EventFeed
          items={visibleFeedItems}
          title="Обзорная лента событий"
          emptyMessage="Нет событий, требующих показа в ленте."
          onOpenTap={openTap}
          onOpenSession={openSession}
          onDismiss={dismissEvent}
        />
      {/if}
    </section>
  </div>
</section>

<style>
  .today-page{display:grid;gap:1rem}.ui-card{padding:1rem}.eyebrow{font-size:.8rem;color:var(--text-secondary);text-transform:uppercase}.top-strip{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1rem}.top-strip article{display:flex;flex-direction:column;gap:.35rem}.health-pills{display:flex;flex-wrap:wrap;gap:.5rem}.health-pill{padding:.3rem .55rem;border-radius:999px;background:var(--state-neutral-bg);font-size:.8rem}.health-pill.ok{background:var(--state-success-bg);color:var(--state-success-text)}.health-pill.warning,.health-pill.unknown,.health-pill.degraded{background:var(--state-warning-bg);color:var(--state-warning-text)}.health-pill.critical,.health-pill.error,.health-pill.offline{background:var(--state-critical-bg);color:var(--state-critical-text)}.hero{display:grid;grid-template-columns:1.4fr auto;gap:1rem;align-items:start}.hero h1{margin:.25rem 0}.hero-copy p{margin:.25rem 0 0}.hero-actions{display:flex;gap:.75rem;justify-content:flex-end;flex-wrap:wrap}.cta-button{display:inline-flex;align-items:center;justify-content:center;padding:.7rem 1rem;border-radius:.8rem;background:var(--accent-color,#1d4ed8);color:#fff;text-decoration:none;font-weight:600;border:0}.cta-button.incidents-entry{background:var(--state-critical-text)}.cta-button.contextual{background:var(--accent-color,#1d4ed8)}.cta-button.secondary{background:var(--state-neutral-bg);color:var(--state-neutral-text)}.cta-button:disabled{opacity:.65;cursor:not-allowed}.stats{grid-column:1 / -1;display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:.85rem}.stats article{padding:.85rem;border-radius:.8rem;background:var(--surface-secondary,#f8fafc);transition:opacity .2s ease,transform .2s ease}.stats article[data-tone='warning']{background:var(--state-warning-bg)}.stats[data-muted='true'] article[data-emphasis='secondary']{opacity:.62;transform:scale(.98)}.stats article span{display:block;color:var(--text-secondary);margin-bottom:.2rem}.stats article strong{display:block}.summary-warning{display:grid;gap:.35rem;padding:.9rem 1rem;border:1px solid var(--state-warning-border);background:var(--state-warning-bg);color:var(--state-warning-text);border-radius:16px}.content-grid{display:grid;grid-template-columns:minmax(360px,.95fr) minmax(0,1.45fr);gap:1rem;align-items:start}.section-head{display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;margin-bottom:1rem}.section-head h2,.section-head p{margin:0}.section-head p{margin-top:.25rem;color:var(--text-secondary)}.feed-panel{min-height:540px}.priority-panel{position:sticky;top:1rem}.attention-panel .count,.next-actions-head span{padding:.35rem .65rem;border-radius:999px;background:var(--state-neutral-bg);font-weight:700}.next-actions,.secondary-actions{display:grid;gap:.75rem;margin-bottom:1rem;padding:.9rem;border-radius:.9rem;background:#f8fafc}.next-actions{border:1px solid var(--state-neutral-border)}.next-actions-head{display:flex;justify-content:space-between;gap:1rem;align-items:center}.next-actions-head.compact h3{font-size:1rem}.next-actions-head h3{margin:0}.next-action,.secondary-action{display:grid;gap:.35rem;text-align:left;padding:.8rem .9rem;border-radius:.8rem;border:1px solid var(--state-neutral-border);background:#fff;cursor:pointer}.next-action.primary{gap:.4rem;padding:1rem}.next-action.primary strong,.secondary-action strong{font-size:.85rem;color:var(--state-neutral-text)}.next-action[data-severity='critical'],.secondary-action[data-severity='critical']{border-color:var(--state-critical-border);background:var(--state-critical-bg)}.next-action[data-severity='warning'],.secondary-action[data-severity='warning']{border-color:var(--state-warning-border);background:var(--state-warning-bg)}.next-action span,.secondary-action span{font-weight:700}.next-action small,.secondary-action small{color:var(--text-secondary)}.secondary-actions-list{display:grid;gap:.5rem}.secondary-action{grid-template-columns:minmax(0,1fr) auto;align-items:center}.attention-list{display:grid;gap:.75rem}.attention-item{display:grid;gap:.75rem;padding:.9rem;border:1px solid #e5e7eb;border-radius:.9rem}.attention-item[data-severity='critical']{border-color:var(--state-critical-border);background:var(--state-critical-bg)}.attention-item[data-severity='warning']{border-color:var(--state-warning-border);background:var(--state-warning-bg)}.attention-category{display:block;font-size:.75rem;text-transform:uppercase;color:var(--text-secondary);margin-bottom:.25rem}.attention-actions{display:flex;gap:.5rem;flex-wrap:wrap}.attention-actions button{border:1px solid #d1d5db;background:#fff;border-radius:999px;padding:.45rem .8rem;cursor:pointer}.attention-actions .subtle{color:var(--text-secondary)}.error{color:var(--state-critical-text)}@media (max-width: 960px){.top-strip,.hero,.content-grid,.secondary-action{grid-template-columns:1fr}.hero-actions{justify-content:flex-start;gap:.5rem}.hero-actions .cta-button{flex:1 1 calc(50% - .5rem);min-width:140px}.priority-panel{position:static}}
</style>
