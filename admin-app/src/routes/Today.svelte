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
  import { formatDateTimeRu, formatTimeRu, formatVolumeRu } from '../lib/formatters.js';
  import { uiStore } from '../stores/uiStore.js';

  let now = new Date();
  let dismissedEventIds = new Set();
  let dismissedAttentionKeys = new Set();
  let initialLoadAttempted = false;

  const severityWeight = { critical: 0, warning: 1, info: 2 };

  function navigateTo(path) {
    window.location.hash = path;
  }

  function openTap(item) {
    navigateTo('#/taps');
    uiStore.notifySuccess(`Переход к крану ${item.tap_name || item.title || item.tap_id || ''}`.trim());
  }

  function openSession(item) {
    const visitId = item.visit_id || item.active_session?.visit_id || item.operations?.activeSessionSummary?.visitId || null;
    if (visitId) {
      sessionStorage.setItem('visits.lookupVisitId', visitId);
    }
    navigateTo('#/sessions');
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
  $: poursToday = ($pourStore.pours || []).filter((item) => {
    if (!item.poured_at) return false;
    const date = new Date(item.poured_at);
    return date.getFullYear() === now.getFullYear() && date.getMonth() === now.getMonth() && date.getDate() === now.getDate();
  });
  $: sessionsToday = new Set(poursToday.map((item) => item.visit_id).filter(Boolean)).size;
  $: volumeTodayMl = poursToday.reduce((sum, item) => sum + Number(item.volume_ml || 0), 0);
  $: heroStats = [
    { label: 'Активные визиты', value: ($visitStore.activeVisits || []).length },
    { label: 'Наливы сегодня', value: poursToday.length },
    { label: 'Объём сегодня', value: formatVolumeRu(volumeTodayMl) },
    { label: 'Открытые инциденты', value: activeIncidents.length },
  ];
  $: healthItems = [
    { key: 'backend', label: 'Backend', ...$systemStore.health.backend },
    { key: 'controller', label: 'Controller', ...$systemStore.health.controller },
    { key: 'display', label: 'Display-agent', ...$systemStore.health.displayAgent },
  ];
  $: attentionItems = [
    ...(($tapStore.summary?.attentionItems || []).map((item) => ({ ...item, category: item.kind.replaceAll('_', ' ') }))),
    ...healthItems
      .filter((item) => ['warning', 'critical', 'error', 'offline', 'unknown', 'degraded'].includes(item.state))
      .map((item) => ({
        key: `system-${item.key}`,
        kind: `${item.key}_offline`,
        severity: item.state === 'critical' || item.state === 'error' ? 'critical' : 'warning',
        title: item.label,
        description: item.detail,
        href: item.key === 'backend' ? '#/system' : '#/taps',
        actionLabel: item.key === 'backend' ? 'Открыть систему' : 'Открыть кран',
        category: item.key,
      })),
  ]
    .filter((item) => !dismissedAttentionKeys.has(item.key))
    .sort((left, right) => (severityWeight[left.severity] ?? 9) - (severityWeight[right.severity] ?? 9));
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
      <span class="eyebrow">Health</span>
      <strong>{$systemStore.health.overall}</strong>
      <div class="health-pills">
        {#each healthItems as item}
          <span class="health-pill {item.state}">{item.label}: {item.state}</span>
        {/each}
      </div>
    </article>
  </section>

  <section class="hero ui-card">
    <div class="hero-copy">
      <span class="eyebrow">Today</span>
      <h1>Операционный срез смены</h1>
      <p>Короткий путь от текущего состояния системы к следующему действию оператора.</p>
    </div>
    <div class="hero-actions">
      <a class="cta-button" href="#/incidents">Инциденты</a>
      <a class="cta-button secondary" href="#/taps">Все краны</a>
    </div>
    <div class="stats">
      {#each heroStats as item}
        <article>
          <span>{item.label}</span>
          <strong>{item.value}</strong>
        </article>
      {/each}
    </div>
  </section>

  <div class="content-grid">
    <section class="ui-card panel feed-panel">
      <div class="section-head">
        <div>
          <h2>Живая лента событий</h2>
          <p>{sessionsToday} сессий с наливами сегодня · {$tapStore.summary?.pouringCount || 0} кранов льют прямо сейчас</p>
        </div>
      </div>

      {#if $pourStore.loading && visibleFeedItems.length === 0}
        <p>Загрузка ленты событий...</p>
      {:else if $pourStore.error}
        <p class="error">Ошибка загрузки ленты: {$pourStore.error}</p>
      {:else}
        <EventFeed
          items={visibleFeedItems}
          title="Живая лента событий"
          emptyMessage="Нет событий, требующих показа в ленте."
          onOpenTap={openTap}
          onOpenSession={openSession}
          onDismiss={dismissEvent}
        />
      {/if}
    </section>

    <aside class="ui-card panel attention-panel">
      <div class="section-head">
        <div>
          <h2>Требует внимания</h2>
          <p>Только actionable-состояния: heartbeat, keg, sync, reader, display, controller.</p>
        </div>
        <span class="count">{attentionItems.length}</span>
      </div>

      {#if attentionItems.length === 0}
        <p>Сейчас нет задач, требующих немедленного внимания.</p>
      {:else}
        <div class="attention-list">
          {#each attentionItems as item}
            <article class="attention-item" data-severity={item.severity}>
              <div>
                <span class="attention-category">{item.category}</span>
                <strong>{item.title}</strong>
                <p>{item.description}</p>
              </div>
              <div class="attention-actions">
                <button on:click={() => item.href === '#/sessions' ? openSession(item) : navigateTo(item.href)}>{item.actionLabel}</button>
                <button class="subtle" on:click={() => dismissAttention(item)}>Скрыть</button>
              </div>
            </article>
          {/each}
        </div>
      {/if}
    </aside>
  </div>
</section>

<style>
  .today-page{display:grid;gap:1rem}.ui-card{padding:1rem}.eyebrow{font-size:.8rem;color:var(--text-secondary);text-transform:uppercase}.top-strip{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1rem}.top-strip article{display:flex;flex-direction:column;gap:.35rem}.health-pills{display:flex;flex-wrap:wrap;gap:.5rem}.health-pill{padding:.3rem .55rem;border-radius:999px;background:#eef2ff;font-size:.8rem}.health-pill.ok{background:#e8f7ee;color:#166534}.health-pill.warning,.health-pill.unknown,.health-pill.degraded{background:#fff7e6;color:#9a6700}.health-pill.critical,.health-pill.error,.health-pill.offline{background:#fdecec;color:#b42318}.hero{display:grid;grid-template-columns:1.4fr auto;gap:1rem;align-items:start}.hero h1{margin:.25rem 0}.hero-copy p{margin:.25rem 0 0}.hero-actions{display:flex;gap:.75rem;justify-content:flex-end}.cta-button{display:inline-flex;align-items:center;justify-content:center;padding:.7rem 1rem;border-radius:.8rem;background:var(--accent-color,#1d4ed8);color:#fff;text-decoration:none;font-weight:600}.cta-button.secondary{background:#eef2ff;color:#1e3a8a}.stats{grid-column:1 / -1;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1rem}.stats article{padding:.85rem;border-radius:.8rem;background:var(--surface-secondary,#f8fafc)}.stats article span{display:block;color:var(--text-secondary)}.content-grid{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(320px,.9fr);gap:1rem}.section-head{display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;margin-bottom:1rem}.section-head h2,.section-head p{margin:0}.section-head p{margin-top:.25rem;color:var(--text-secondary)}.feed-panel{min-height:540px}.attention-panel .count{padding:.35rem .65rem;border-radius:999px;background:#eef2ff;font-weight:700}.attention-list{display:grid;gap:.75rem}.attention-item{display:grid;gap:.75rem;padding:.9rem;border:1px solid #e5e7eb;border-radius:.9rem}.attention-item[data-severity='critical']{border-color:#fda29b;background:#fff5f5}.attention-item[data-severity='warning']{border-color:#facc15;background:#fffdf2}.attention-category{display:block;font-size:.75rem;text-transform:uppercase;color:var(--text-secondary);margin-bottom:.25rem}.attention-actions{display:flex;gap:.5rem;flex-wrap:wrap}.attention-actions button{border:1px solid #d1d5db;background:#fff;border-radius:999px;padding:.45rem .8rem;cursor:pointer}.attention-actions .subtle{color:var(--text-secondary)}.error{color:#b42318}@media (max-width: 960px){.top-strip,.hero,.content-grid,.stats{grid-template-columns:1fr}.hero-actions{justify-content:flex-start}}
</style>
