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
  const incidentPriorityWeight = { critical: 0, high: 1, medium: 2, low: 3 };

  function navigateTo(path) {
    window.location.hash = path;
  }

  function focusTap(tapId) {
    if (tapId) {
      sessionStorage.setItem('incidents.focusTapId', String(tapId));
    }
    navigateTo('/taps');
  }

  function focusVisit(visitId) {
    if (visitId) {
      sessionStorage.setItem('visits.lookupVisitId', visitId);
    }
    navigateTo('/sessions');
  }

  function focusSystem(source) {
    if (source) {
      sessionStorage.setItem('system.focusSource', source);
    }
    navigateTo('/system');
  }

  function openTap(item) {
    focusTap(item.tap_id);
    uiStore.notifySuccess(`Переход к крану ${item.tap_name || item.title || item.tap_id || ''}`.trim());
  }

  function openSession(item) {
    const visitId = item.visit_id || item.active_session?.visit_id || item.operations?.activeSessionSummary?.visitId || null;
    focusVisit(visitId);
  }

  function openActionTarget(item) {
    if (!item) return;

    if (item.target === 'session') {
      focusVisit(item.visitId);
      return;
    }

    if (item.target === 'system') {
      focusSystem(item.systemSource || item.title || item.label);
      return;
    }

    if (item.target === 'tap') {
      focusTap(item.tapId || item.tap_id);
      return;
    }

    if (item.target === 'incident') {
      navigateTo(item.href || '/incidents');
      return;
    }

    navigateTo(item.href || '/today');
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

  function attentionCategory(item) {
    const labels = {
      no_keg: 'кега',
      stale_heartbeat: 'связь с краном',
      unsynced_flow: 'синхронизация налива',
      reader_offline: 'считыватель',
      display_offline: 'экран крана',
      controller_offline: 'контроллер',
      backend_offline: 'бэкенд',
      sync_offline: 'синхронизация',
      controllers_offline: 'контроллеры',
      displays_offline: 'экраны',
      readers_offline: 'считыватели',
    };

    return labels[item.kind] || String(item.kind || 'операции').replaceAll('_', ' ');
  }

  function actionTitleForAttention(item) {
    const tapLabel = item.title || 'кран';

    switch (item.kind) {
      case 'unsynced_flow':
        return `Проверить зависший налив на ${tapLabel}`;
      case 'stale_heartbeat':
        return `Проверить связь с ${tapLabel}`;
      case 'reader_offline':
        return `Проверить считыватель на ${tapLabel}`;
      case 'display_offline':
        return `Проверить экран на ${tapLabel}`;
      case 'controller_offline':
        return `Проверить контроллер на ${tapLabel}`;
      case 'no_keg':
        return `Назначить кегу для ${tapLabel}`;
      default:
        return `Проверить ${tapLabel}`;
    }
  }


  function actionLabelForTarget(target) {
    switch (target) {
      case 'tap':
        return 'Открыть кран';
      case 'session':
        return 'Открыть сессию';
      case 'system':
        return 'Открыть систему';
      case 'incident':
        return 'Закрыть / эскалировать';
      default:
        return 'Открыть контекст';
    }
  }

  function buildActionItem(item) {
    const target = item.target || 'system';
    return {
      ...item,
      target,
      actionLabel: actionLabelForTarget(target),
    };
  }

  function describeSyncProblems() {
    return ($tapStore.summary?.unsyncedFlowCount || 0)
      + ($tapStore.summary?.readerOfflineCount || 0)
      + ($tapStore.summary?.displayOfflineCount || 0)
      + ($tapStore.summary?.controllerOfflineCount || 0)
      + ($systemStore.health.sections?.accumulatedIssues?.deviceCount || 0)
      + (['warning', 'critical', 'error', 'offline', 'unknown', 'degraded'].includes($systemStore.health.sync?.state) ? 1 : 0);
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
  $: criticalIncidents = activeIncidents
    .filter((item) => ['critical', 'high'].includes(item.priority))
    .sort((left, right) => (incidentPriorityWeight[left.priority] ?? 9) - (incidentPriorityWeight[right.priority] ?? 9));
  $: visibleFeedItems = ($pourStore.feedItems || []).filter((item) => !dismissedEventIds.has(item.item_id)).slice(0, 12);
  $: poursToday = ($pourStore.pours || []).filter((item) => {
    if (!item.poured_at) return false;
    const date = new Date(item.poured_at);
    return date.getFullYear() === now.getFullYear() && date.getMonth() === now.getMonth() && date.getDate() === now.getDate();
  });
  $: sessionsToday = new Set(poursToday.map((item) => item.visit_id).filter(Boolean)).size;
  $: volumeTodayMl = poursToday.reduce((sum, item) => sum + Number(item.volume_ml || 0), 0);
  $: revenueToday = poursToday.reduce((sum, item) => sum + Number(item.amount_charged || 0), 0);
  $: syncProblemCount = describeSyncProblems();
  $: needsHelpCount = ($tapStore.taps || []).filter((tap) => tap.operations?.productState === 'needs_help').length;
  $: hasCriticalTapAttention = attentionItems?.some((item) => item.target === 'tap' && item.severity === 'critical') || false;
  $: hasCriticalIncident = criticalIncidents.length > 0;
  $: deEmphasizeSecondaryStats = hasCriticalIncident || hasCriticalTapAttention;
  $: heroStats = [
    { label: 'Льют сейчас', value: $tapStore.summary?.pouringCount || 0, tone: 'neutral', emphasis: 'primary' },
    { label: 'Требуют помощи', value: needsHelpCount, tone: needsHelpCount ? 'warning' : 'neutral', emphasis: 'primary' },
    { label: 'Открытые инциденты', value: activeIncidents.length, tone: activeIncidents.length ? 'warning' : 'neutral', emphasis: 'primary' },
    { label: 'Sync / offline', value: syncProblemCount, tone: syncProblemCount ? 'warning' : 'neutral', emphasis: 'primary' },
    { label: 'Сессии сегодня', value: sessionsToday, tone: 'neutral', emphasis: 'secondary' },
    { label: 'Объём / выручка', value: `${formatVolumeRu(volumeTodayMl)} · ${revenueToday.toFixed(2)} ₽`, tone: 'neutral', emphasis: 'secondary' },
  ];
  $: healthItems = $systemStore.health.primaryPills || [];
  $: systemAttentionItems = healthItems
    .filter((item) => ['warning', 'critical', 'error', 'offline', 'unknown', 'degraded'].includes(item.state))
    .map((item) => ({
      key: `system-${item.key}`,
      kind: `${item.key}_offline`,
      severity: item.state === 'critical' || item.state === 'error' ? 'critical' : 'warning',
      title: item.label,
      description: item.detail,
      href: '/system',
      target: 'system',
      systemSource: item.label,
      actionLabel: actionLabelForTarget('system'),
      category: 'система',
    }));
  $: attentionItems = [
    ...(($tapStore.summary?.attentionItems || []).map((item) => buildActionItem({
      ...item,
      target: item.href === '#/sessions' ? 'session' : 'tap',
      tapId: item.tapId || item.tap_id || Number.parseInt(String(item.key).split('-').at(-1), 10) || null,
      visitId: item.visitId || item.visit_id || null,
      category: attentionCategory(item),
      actionTitle: actionTitleForAttention(item),
      href: item.href?.replace('#', '') || '/taps',
    }))),
    ...systemAttentionItems.map((item) => buildActionItem(item)),
  ]
    .filter((item) => !dismissedAttentionKeys.has(item.key))
    .sort((left, right) => (severityWeight[left.severity] ?? 9) - (severityWeight[right.severity] ?? 9));

  $: operatorActionItems = [
    ...criticalIncidents.slice(0, 3).map((incident) => buildActionItem({
      key: `incident-${incident.incident_id}`,
      severity: incident.priority === 'critical' ? 'critical' : 'warning',
      title: `Разобрать ${incident.priority === 'critical' ? 'критичный' : 'срочный'} инцидент #${incident.incident_id}`,
      description: incident.tap ? `Проверьте ${incident.tap} и зафиксируйте действие по инциденту.` : 'Откройте инцидент, назначьте ответственного и выберите решение.',
      target: 'incident',
      tapId: incident.tap || null,
      systemSource: `Инцидент #${incident.incident_id}`,
      href: '/incidents',
    })),
    ...attentionItems.slice(0, 4).map((item) => buildActionItem({
      key: `next-${item.key}`,
      severity: item.severity,
      title: item.actionTitle || `Проверить ${item.title}`,
      description: item.description,
      target: item.target,
      tapId: item.tapId || null,
      visitId: item.visitId || null,
      systemSource: item.systemSource || item.title,
      href: item.href,
    })),
  ]
    .sort((left, right) => (severityWeight[left.severity] ?? 9) - (severityWeight[right.severity] ?? 9))
    .filter((item, index, items) => items.findIndex((candidate) => candidate.key === item.key) === index)
    .slice(0, 5);
  $: primaryActionItem = operatorActionItems[0] || null;
  $: secondaryActionItems = operatorActionItems.slice(1, 5);

  $: priorityCta = primaryActionItem
    ? {
        label: primaryActionItem.actionLabel,
        target: primaryActionItem.target,
        tapId: primaryActionItem.tapId || null,
        visitId: primaryActionItem.visitId || null,
        systemSource: primaryActionItem.systemSource || primaryActionItem.title,
        href: primaryActionItem.href,
      }
    : { label: 'Открыть систему', target: 'system', systemSource: 'Today overview', href: '/system' };
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
      <span class="eyebrow">Сегодня</span>
      <h1>Главное за текущую смену</h1>
      <p>Сначала — живое операционное состояние, затем дневные итоги по продажам и наливам.</p>
    </div>
    <div class="hero-actions">
      <button class="cta-button" on:click={() => openActionTarget(priorityCta)}>{priorityCta.label}</button>
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
  .today-page{display:grid;gap:1rem}.ui-card{padding:1rem}.eyebrow{font-size:.8rem;color:var(--text-secondary);text-transform:uppercase}.top-strip{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1rem}.top-strip article{display:flex;flex-direction:column;gap:.35rem}.health-pills{display:flex;flex-wrap:wrap;gap:.5rem}.health-pill{padding:.3rem .55rem;border-radius:999px;background:#eef2ff;font-size:.8rem}.health-pill.ok{background:#e8f7ee;color:#166534}.health-pill.warning,.health-pill.unknown,.health-pill.degraded{background:#fff7e6;color:#9a6700}.health-pill.critical,.health-pill.error,.health-pill.offline{background:#fdecec;color:#b42318}.hero{display:grid;grid-template-columns:1.4fr auto;gap:1rem;align-items:start}.hero h1{margin:.25rem 0}.hero-copy p{margin:.25rem 0 0}.hero-actions{display:flex;gap:.75rem;justify-content:flex-end}.cta-button{display:inline-flex;align-items:center;justify-content:center;padding:.7rem 1rem;border-radius:.8rem;background:var(--accent-color,#1d4ed8);color:#fff;text-decoration:none;font-weight:600;border:0}.cta-button.secondary{background:#eef2ff;color:#1e3a8a}.stats{grid-column:1 / -1;display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:.85rem}.stats article{padding:.85rem;border-radius:.8rem;background:var(--surface-secondary,#f8fafc);transition:opacity .2s ease,transform .2s ease}.stats article[data-tone='warning']{background:#fff7e6}.stats[data-muted='true'] article[data-emphasis='secondary']{opacity:.62;transform:scale(.98)}.stats article span{display:block;color:var(--text-secondary);margin-bottom:.2rem}.stats article strong{display:block}.content-grid{display:grid;grid-template-columns:minmax(360px,.95fr) minmax(0,1.45fr);gap:1rem;align-items:start}.section-head{display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;margin-bottom:1rem}.section-head h2,.section-head p{margin:0}.section-head p{margin-top:.25rem;color:var(--text-secondary)}.feed-panel{min-height:540px}.priority-panel{position:sticky;top:1rem}.attention-panel .count,.next-actions-head span{padding:.35rem .65rem;border-radius:999px;background:#eef2ff;font-weight:700}.next-actions,.secondary-actions{display:grid;gap:.75rem;margin-bottom:1rem;padding:.9rem;border-radius:.9rem;background:#f8fafc}.next-actions{border:1px solid #dbe4ff}.next-actions-head{display:flex;justify-content:space-between;gap:1rem;align-items:center}.next-actions-head.compact h3{font-size:1rem}.next-actions-head h3{margin:0}.next-action,.secondary-action{display:grid;gap:.35rem;text-align:left;padding:.8rem .9rem;border-radius:.8rem;border:1px solid #dbe4ff;background:#fff;cursor:pointer}.next-action.primary{gap:.4rem;padding:1rem}.next-action.primary strong,.secondary-action strong{font-size:.85rem;color:#1d4ed8}.next-action[data-severity='critical'],.secondary-action[data-severity='critical']{border-color:#fda29b;background:#fff5f5}.next-action[data-severity='warning'],.secondary-action[data-severity='warning']{border-color:#facc15;background:#fffdf2}.next-action span,.secondary-action span{font-weight:700}.next-action small,.secondary-action small{color:var(--text-secondary)}.secondary-actions-list{display:grid;gap:.5rem}.secondary-action{grid-template-columns:minmax(0,1fr) auto;align-items:center}.attention-list{display:grid;gap:.75rem}.attention-item{display:grid;gap:.75rem;padding:.9rem;border:1px solid #e5e7eb;border-radius:.9rem}.attention-item[data-severity='critical']{border-color:#fda29b;background:#fff5f5}.attention-item[data-severity='warning']{border-color:#facc15;background:#fffdf2}.attention-category{display:block;font-size:.75rem;text-transform:uppercase;color:var(--text-secondary);margin-bottom:.25rem}.attention-actions{display:flex;gap:.5rem;flex-wrap:wrap}.attention-actions button{border:1px solid #d1d5db;background:#fff;border-radius:999px;padding:.45rem .8rem;cursor:pointer}.attention-actions .subtle{color:var(--text-secondary)}.error{color:#b42318}@media (max-width: 960px){.top-strip,.hero,.content-grid,.secondary-action{grid-template-columns:1fr}.hero-actions{justify-content:flex-start}.priority-panel{position:static}}
</style>
