<script>
  // @ts-nocheck
  import { get } from 'svelte/store';
  import { onMount } from 'svelte';
  import { roleStore } from '../stores/roleStore.js';
  import { incidentStore } from '../stores/incidentStore.js';
  import { sessionStore } from '../stores/sessionStore.js';
  import { systemStore } from '../stores/systemStore.js';
  import { tapStore } from '../stores/tapStore.js';
  import { uiStore } from '../stores/uiStore.js';
  import { visitStore } from '../stores/visitStore.js';
  import IncidentList from '../components/incidents/IncidentList.svelte';

  const DEFAULT_FILTERS = {
    priority: 'all',
    status: 'all',
    type: 'all',
    tap: 'all',
    time: 'all',
    query: '',
  };

  const SECTION_ORDER = ['new', 'in_progress', 'closed'];
  const SECTION_LABELS = {
    new: 'Новые',
    in_progress: 'В работе',
    closed: 'Закрытые',
  };

  const PRIORITY_LABELS = {
    low: 'Низкий',
    medium: 'Средний',
    high: 'Высокий',
    critical: 'Критический',
  };

  const STATUS_LABELS = {
    new: 'Новый',
    in_progress: 'В работе',
    closed: 'Закрыт',
  };

  let hasLoadedContext = false;
  let filters = { ...DEFAULT_FILTERS };
  let selectedIncidentId = null;
  let localOverrides = {};

  onMount(() => {
    const token = get(sessionStore).token;
    if (token && !hasLoadedContext) {
      incidentStore.fetchIncidents();
      tapStore.fetchTaps();
      visitStore.fetchActiveVisits().catch(() => {});
      systemStore.fetchSystemStatus().catch(() => {});
      hasLoadedContext = true;
    }
  });

  function titleCase(value) {
    if (!value) return '—';
    const text = String(value).replaceAll('_', ' ');
    return text.charAt(0).toUpperCase() + text.slice(1);
  }

  function initials(name) {
    return (name || '—')
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() || '')
      .join('');
  }

  function timeMatches(createdAt, range) {
    if (range === 'all') return true;
    const created = new Date(createdAt);
    if (Number.isNaN(created.getTime())) return false;
    const now = Date.now();
    const diff = now - created.getTime();
    if (range === '24h') return diff <= 24 * 60 * 60 * 1000;
    if (range === '7d') return diff <= 7 * 24 * 60 * 60 * 1000;
    if (range === '30d') return diff <= 30 * 24 * 60 * 60 * 1000;
    return true;
  }

  function buildNarrative(incident, tapMatch, sessionMatch) {
    const happened = incident.status === 'closed'
      ? 'уже закрыт и сохранён в журнале.'
      : incident.status === 'in_progress'
        ? 'взят в работу оператором.'
        : 'ещё ждёт разбора оператором.';

    return [
      `${titleCase(incident.type)} на ${tapMatch?.display_name || incident.tap || 'непривязанном кране'} ${happened}`,
      tapMatch?.operations?.productStateLabel
        ? `Сейчас кран в состоянии «${tapMatch.operations.productStateLabel}», ${tapMatch.operations.liveStatus?.toLowerCase?.() || 'без live-описания'}.`
        : 'По крану нет расширенной telemеtry, поэтому narrative собран из incident/tap/session данных клиента.',
      sessionMatch
        ? `Связанная сессия #${sessionMatch.visit_id} ${sessionMatch.guest_full_name ? `для гостя ${sessionMatch.guest_full_name}` : 'без имени гостя'} ${sessionMatch.operator_status ? `со статусом ${sessionMatch.operator_status}` : ''}.`
        : 'Активная связанная сессия не найдена — стоит проверить журнал сессий и системные события.',
    ];
  }

  function deriveImpact(incident, tapMatch, sessionMatch) {
    const impact = [];
    if (incident.priority === 'critical') impact.push('риск остановки продаж или несанкционированного пролива');
    if (incident.priority === 'high') impact.push('требует быстрого вмешательства смены');
    if (tapMatch?.operations?.currentPour?.isActive) impact.push('по крану прямо сейчас фиксируется поток');
    if (tapMatch?.operations?.heartbeat?.isStale) impact.push('heartbeat устарел');
    if (sessionMatch?.has_incident || sessionMatch?.incident_count) impact.push(`в истории сессии уже есть incident (${sessionMatch.incident_count || 1})`);
    if (impact.length === 0) impact.push('локальное влияние ограничено одним краном и требует подтверждения оператором');
    return impact;
  }

  function deriveRelatedEvents(incident, tapMatch, sessionMatch) {
    const events = [];
    for (const item of tapMatch?.operations?.operatorHistory || []) {
      events.push({
        id: `tap-${item.id}`,
        time: item.happenedAt,
        title: item.title,
        description: item.description,
        href: item.sessionAction?.href || '#/taps',
        label: item.sessionAction?.label || 'Открыть кран',
      });
    }

    if (sessionMatch) {
      events.push({
        id: `session-${sessionMatch.visit_id}`,
        time: sessionMatch.last_event_at || sessionMatch.opened_at,
        title: `Сессия #${sessionMatch.visit_id}`,
        description: `${sessionMatch.operator_status || 'Статус неизвестен'} · taps: ${sessionMatch.taps?.join(', ') || '—'}`,
        href: '#/sessions/history',
        label: 'Открыть историю сессии',
      });
    }

    if (!events.length) {
      events.push({
        id: `incident-${incident.incident_id}`,
        time: incident.created_at,
        title: 'Incident зарегистрирован',
        description: 'Пока доступны только агрегированные данные incident API.',
        href: '#/system',
        label: 'Открыть системный контекст',
      });
    }

    return events.slice(0, 6);
  }

  function deriveActionsTaken(incident, override, tapMatch, sessionMatch) {
    const actions = [];
    if (incident.operator) {
      actions.push({
        kind: 'owner',
        title: `Назначен оператор ${incident.operator}`,
        detail: incident.note_action || 'Явное действие ещё не записано.',
      });
    }
    if (override?.note) {
      actions.push({
        kind: 'note',
        title: 'Добавлена заметка',
        detail: override.note,
      });
    }
    if (override?.escalatedAt) {
      actions.push({
        kind: 'escalation',
        title: 'Инцидент эскалирован',
        detail: `Передан в engineering/system context ${override.escalatedAt}.`,
      });
    }
    if (override?.status === 'closed') {
      actions.push({
        kind: 'closed',
        title: 'Инцидент закрыт локально',
        detail: 'До появления backend-команды статус удерживается как client-side override.',
      });
    }
    if (tapMatch?.operations?.heartbeat?.isStale) {
      actions.push({
        kind: 'signal',
        title: 'Автоматический сигнал',
        detail: `Последний heartbeat ${tapMatch.operations.heartbeat.minutesAgo} мин назад.`,
      });
    }
    if (sessionMatch?.incident_count) {
      actions.push({
        kind: 'history',
        title: 'Есть след в истории сессий',
        detail: `В связанной сессии отмечено incident: ${sessionMatch.incident_count}.`,
      });
    }
    return actions;
  }

  function matchSession(incident, tapMatch) {
    return ($visitStore.activeVisits || []).find((visit) => {
      const tapIds = visit.taps || [];
      const incidentTapId = tapMatch?.tap_id;
      return (incidentTapId && (visit.active_tap_id === incidentTapId || tapIds.includes(String(incidentTapId)) || tapIds.includes(incidentTapId)))
        || (incident.tap && tapIds.includes(incident.tap));
    }) || null;
  }

  $: enrichedItems = ($incidentStore.items || []).map((incident) => {
    const override = localOverrides[incident.incident_id] || {};
    const tapMatch = ($tapStore.taps || []).find((tap) => String(tap.tap_id) === String(incident.tap) || tap.display_name === incident.tap) || null;
    const sessionMatch = matchSession(incident, tapMatch);
    const status = override.status || incident.status;
    const operator = override.operator || incident.operator;
    const noteAction = override.note || incident.note_action;
    const tapLabel = tapMatch?.display_name || incident.tap || '—';

    return {
      ...incident,
      status,
      operator,
      note_action: noteAction,
      tapLabel,
      tapId: tapMatch?.tap_id || null,
      tapHref: tapMatch ? '#/taps' : null,
      sessionMatch,
      sessionHref: sessionMatch ? '#/sessions/history' : '#/sessions',
      systemHref: '#/system',
      sourceLabel: incident.source || tapMatch?.operations?.controllerStatus?.label || 'incident-api',
      typeLabel: titleCase(incident.type),
      priorityLabel: PRIORITY_LABELS[incident.priority] || titleCase(incident.priority),
      statusLabel: STATUS_LABELS[status] || titleCase(status),
      operatorInitials: initials(operator),
      summary: buildNarrative({ ...incident, status }, tapMatch, sessionMatch)[0],
      narrative: buildNarrative({ ...incident, status }, tapMatch, sessionMatch),
      impact: deriveImpact({ ...incident, status }, tapMatch, sessionMatch),
      relatedEvents: deriveRelatedEvents({ ...incident, status }, tapMatch, sessionMatch),
      actionsTaken: deriveActionsTaken({ ...incident, status, operator, note_action: noteAction }, override, tapMatch, sessionMatch),
      tapContext: tapMatch,
      systemState: $systemStore.overallState,
      openIncidentCount: $systemStore.openIncidentCount,
    };
  });

  $: filterOptions = {
    priorities: Array.from(new Set(enrichedItems.map((item) => item.priority))).filter(Boolean),
    statuses: Array.from(new Set(enrichedItems.map((item) => item.status))).filter(Boolean),
    types: Array.from(new Set(enrichedItems.map((item) => item.type))).filter(Boolean),
    taps: Array.from(new Set(enrichedItems.map((item) => item.tapLabel))).filter(Boolean),
  };

  $: filteredItems = enrichedItems.filter((item) => {
    const query = filters.query.trim().toLowerCase();
    return (filters.priority === 'all' || item.priority === filters.priority)
      && (filters.status === 'all' || item.status === filters.status)
      && (filters.type === 'all' || item.type === filters.type)
      && (filters.tap === 'all' || item.tapLabel === filters.tap)
      && timeMatches(item.created_at, filters.time)
      && (!query || [item.incident_id, item.typeLabel, item.tapLabel, item.operator || '', item.summary].join(' ').toLowerCase().includes(query));
  });

  $: groupedItems = SECTION_ORDER.map((status) => ({
    key: status,
    label: SECTION_LABELS[status],
    items: filteredItems.filter((item) => item.status === status),
  }));

  $: if (filteredItems.length > 0 && !filteredItems.some((item) => item.incident_id === selectedIncidentId)) {
    selectedIncidentId = filteredItems[0].incident_id;
  }

  $: selectedIncident = filteredItems.find((item) => item.incident_id === selectedIncidentId) || null;

  function resetFilters() {
    filters = { ...DEFAULT_FILTERS };
  }

  function selectIncident(event) {
    selectedIncidentId = event.detail.incidentId;
  }

  function openTap(event) {
    const item = event.detail.item;
    if (item.tapId) {
      sessionStorage.setItem('incidents.focusTapId', String(item.tapId));
    }
    window.location.hash = '/taps';
  }

  function openSession(event) {
    const item = event.detail.item;
    if (item.sessionMatch?.visit_id) {
      sessionStorage.setItem('visits.lookupVisitId', item.sessionMatch.visit_id);
      window.location.hash = '/sessions';
      return;
    }
    if (item.tapId) {
      sessionStorage.setItem('sessions.history.tapId', String(item.tapId));
      window.location.hash = '/sessions/history';
      return;
    }
    window.location.hash = '/sessions/history';
  }

  function openSystem(event) {
    const item = event.detail.item;
    sessionStorage.setItem('system.focusSource', item.sourceLabel || item.source || 'incident');
    window.location.hash = '/system';
  }

  async function closeIncident(event) {
    const item = event.detail.item;
    const approved = await uiStore.confirm({
      title: `Закрыть инцидент #${item.incident_id}`,
      message: 'Backend-команды закрытия пока нет, поэтому статус будет зафиксирован локально в клиенте до следующего обновления данных.',
      confirmText: 'Закрыть локально',
      cancelText: 'Отмена',
    });
    if (!approved) return;
    localOverrides = {
      ...localOverrides,
      [item.incident_id]: { ...(localOverrides[item.incident_id] || {}), status: 'closed' },
    };
    uiStore.notifySuccess(`Инцидент #${item.incident_id} помечен как закрытый в текущей сессии.`);
  }

  function escalateIncident(event) {
    const item = event.detail.item;
    localOverrides = {
      ...localOverrides,
      [item.incident_id]: { ...(localOverrides[item.incident_id] || {}), escalatedAt: new Date().toLocaleString('ru-RU') },
    };
    uiStore.notifyWarning(`Инцидент #${item.incident_id} эскалирован. Откройте «Система» для дальнейшей проверки.`);
    openSystem(event);
  }

  function addNote(event) {
    const item = event.detail.item;
    const note = typeof window !== 'undefined'
      ? window.prompt(`Заметка для инцидента #${item.incident_id}`, item.note_action || '')
      : '';
    if (!note?.trim()) return;
    localOverrides = {
      ...localOverrides,
      [item.incident_id]: { ...(localOverrides[item.incident_id] || {}), note: note.trim(), status: item.status === 'new' ? 'in_progress' : item.status },
    };
    uiStore.notifySuccess('Заметка сохранена локально в narrative инцидента.');
  }
</script>

{#if !$roleStore.permissions.incidents_manage}
  <section class="ui-card restricted"><h1>Инциденты</h1><p>Раздел инцидентов скрыт для текущей роли.</p></section>
{:else}
  <section class="page">
    <div class="page-header">
      <div>
        <h1>Инциденты</h1>
        <p>Операторская очередь с фильтрами, явными действиями и связями в кран, сессию и системный контекст.</p>
      </div>
      <div class="header-stats">
        <article><span>Всего</span><strong>{enrichedItems.length}</strong></article>
        <article><span>Открытые</span><strong>{enrichedItems.filter((item) => item.status !== 'closed').length}</strong></article>
        <article><span>System state</span><strong>{$systemStore.overallState}</strong></article>
      </div>
    </div>

    <section class="ui-card filters-panel">
      <div class="filters-grid">
        <label><span>Поиск</span><input bind:value={filters.query} placeholder="ID, тип, кран, оператор" /></label>
        <label>
          <span>Приоритет</span>
          <select bind:value={filters.priority}>
            <option value="all">Все</option>
            {#each filterOptions.priorities as priority}<option value={priority}>{PRIORITY_LABELS[priority] || titleCase(priority)}</option>{/each}
          </select>
        </label>
        <label>
          <span>Статус</span>
          <select bind:value={filters.status}>
            <option value="all">Все</option>
            {#each filterOptions.statuses as status}<option value={status}>{STATUS_LABELS[status] || titleCase(status)}</option>{/each}
          </select>
        </label>
        <label>
          <span>Тип</span>
          <select bind:value={filters.type}>
            <option value="all">Все</option>
            {#each filterOptions.types as type}<option value={type}>{titleCase(type)}</option>{/each}
          </select>
        </label>
        <label>
          <span>Кран</span>
          <select bind:value={filters.tap}>
            <option value="all">Все</option>
            {#each filterOptions.taps as tap}<option value={tap}>{tap}</option>{/each}
          </select>
        </label>
        <label>
          <span>Время</span>
          <select bind:value={filters.time}>
            <option value="all">За всё время</option>
            <option value="24h">Последние 24 часа</option>
            <option value="7d">Последние 7 дней</option>
            <option value="30d">Последние 30 дней</option>
          </select>
        </label>
      </div>
      <div class="filters-actions">
        <button class="secondary" on:click={resetFilters}>Сбросить</button>
        <button on:click={() => incidentStore.fetchIncidents()} disabled={$incidentStore.loading}>Обновить incidents</button>
      </div>
    </section>

    <div class="content-grid">
      <div class="ui-card panel">
        {#if $incidentStore.loading && $incidentStore.items.length === 0}<p>Загрузка инцидентов...</p>
        {:else if $incidentStore.error}<p>{$incidentStore.error}</p>
        {:else}
          <IncidentList
            groupedItems={groupedItems}
            selectedIncidentId={selectedIncidentId}
            on:select={selectIncident}
            on:openTap={openTap}
            on:openSession={openSession}
            on:openSystem={openSystem}
            on:closeIncident={closeIncident}
            on:escalateIncident={escalateIncident}
            on:addNote={addNote}
          />
        {/if}
      </div>

      <aside class="ui-card detail-panel">
        {#if selectedIncident}
          <div class="detail-head">
            <div>
              <div class="eyebrow">Incident detail</div>
              <h2>#{selectedIncident.incident_id}</h2>
              <p>{selectedIncident.typeLabel} · {selectedIncident.priorityLabel} · {selectedIncident.statusLabel}</p>
            </div>
            <div class={`priority-badge ${selectedIncident.priority}`}>{selectedIncident.priorityLabel}</div>
          </div>

          <section class="detail-section narrative-section">
            <h3>Что случилось</h3>
            <p>{selectedIncident.summary}</p>
            <ul>
              {#each selectedIncident.narrative as line}<li>{line}</li>{/each}
            </ul>
          </section>

          <section class="detail-section meta-grid">
            <article><span>Кран</span><strong>{selectedIncident.tapLabel}</strong></article>
            <article><span>Оператор</span><strong>{selectedIncident.operator || 'Не назначен'}</strong></article>
            <article><span>Источник</span><strong>{selectedIncident.sourceLabel}</strong></article>
            <article><span>Связанная сессия</span><strong>{selectedIncident.sessionMatch ? `#${selectedIncident.sessionMatch.visit_id}` : 'Не найдена'}</strong></article>
          </section>

          <section class="detail-section">
            <div class="section-head"><h3>Impact</h3><button class="link" on:click={() => openSystem({ detail: { item: selectedIncident } })}>Открыть System</button></div>
            <ul class="chip-list">
              {#each selectedIncident.impact as item}<li>{item}</li>{/each}
            </ul>
          </section>

          <section class="detail-section">
            <div class="section-head"><h3>Связанные события</h3><button class="link" on:click={() => openSession({ detail: { item: selectedIncident } })}>Открыть Session</button></div>
            <ul class="timeline">
              {#each selectedIncident.relatedEvents as event}
                <li>
                  <div>
                    <strong>{event.title}</strong>
                    <p>{event.description}</p>
                  </div>
                  <div class="timeline-meta">
                    <span>{event.time || 'Время не указано'}</span>
                    <a href={event.href}>{event.label}</a>
                  </div>
                </li>
              {/each}
            </ul>
          </section>

          <section class="detail-section">
            <div class="section-head"><h3>Что уже предпринималось</h3><button class="link" on:click={() => addNote({ detail: { item: selectedIncident } })}>Добавить заметку</button></div>
            {#if selectedIncident.actionsTaken.length}
              <ul class="timeline compact">
                {#each selectedIncident.actionsTaken as action}
                  <li>
                    <div>
                      <strong>{action.title}</strong>
                      <p>{action.detail}</p>
                    </div>
                  </li>
                {/each}
              </ul>
            {:else}
              <p class="muted">Явных действий пока нет. Можно оставить note или эскалировать кейс.</p>
            {/if}
          </section>
        {:else}
          <p class="muted">По текущим фильтрам инциденты не найдены.</p>
        {/if}
      </aside>
    </div>
  </section>
{/if}

<style>
  .page, .filters-panel, .panel, .detail-panel, .detail-section { display: grid; gap: 1rem; }
  .page-header, .filters-actions, .detail-head, .section-head, .timeline li { display: flex; gap: 1rem; justify-content: space-between; }
  .page-header { align-items: flex-start; flex-wrap: wrap; }
  .page-header h1, .page-header p, .detail-head h2, .detail-head p, .detail-section h3, .timeline p { margin: 0; }
  .header-stats { display: flex; gap: 0.75rem; flex-wrap: wrap; }
  .header-stats article, .meta-grid article { border: 1px solid #e2e8f0; border-radius: 14px; padding: 0.85rem 1rem; background: #fff; min-width: 120px; display: grid; gap: 0.3rem; }
  .filters-grid, .meta-grid { display: grid; gap: 0.75rem; }
  .filters-grid { grid-template-columns: repeat(6, minmax(120px, 1fr)); }
  .meta-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  label { display: grid; gap: 0.35rem; }
  input, select, button { font: inherit; }
  input, select, button { border: 1px solid #cbd5e1; border-radius: 12px; padding: 0.7rem 0.85rem; background: #fff; }
  button { font-weight: 700; }
  .secondary, .link { background: #fff; color: #0f172a; }
  .link { padding: 0; border: none; color: #1d4ed8; }
  .content-grid { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(360px, 0.9fr); gap: 1rem; align-items: start; }
  .detail-panel { position: sticky; top: 0; }
  .eyebrow, .muted, .detail-section p, label span, .timeline-meta { color: var(--text-secondary, #64748b); }
  .priority-badge { align-self: flex-start; padding: 0.35rem 0.7rem; border-radius: 999px; font-weight: 700; }
  .priority-badge.low { background: #e2e8f0; }
  .priority-badge.medium { background: #dbeafe; color: #1d4ed8; }
  .priority-badge.high { background: #fef3c7; color: #92400e; }
  .priority-badge.critical { background: #fee2e2; color: #b91c1c; }
  .detail-section { border: 1px solid #e2e8f0; border-radius: 18px; padding: 1rem; background: rgba(248,250,252,0.8); }
  .narrative-section ul, .chip-list, .timeline { margin: 0; padding-left: 1rem; }
  .chip-list { display: flex; flex-wrap: wrap; gap: 0.5rem; list-style: none; padding-left: 0; }
  .chip-list li { background: #eff6ff; color: #1e3a8a; border-radius: 999px; padding: 0.35rem 0.7rem; }
  .timeline { list-style: none; padding-left: 0; display: grid; gap: 0.75rem; }
  .timeline li { align-items: flex-start; border: 1px solid #e2e8f0; border-radius: 14px; background: #fff; padding: 0.85rem; }
  .timeline-meta { min-width: 160px; display: grid; gap: 0.5rem; text-align: right; }
  .timeline a { color: #1d4ed8; text-decoration: none; font-weight: 600; }
  .restricted { padding: 1rem; }
  @media (max-width: 1200px) { .content-grid { grid-template-columns: 1fr; } .detail-panel { position: static; } .filters-grid { grid-template-columns: repeat(3, minmax(120px, 1fr)); } }
  @media (max-width: 720px) { .filters-grid, .meta-grid { grid-template-columns: 1fr; } }
</style>
