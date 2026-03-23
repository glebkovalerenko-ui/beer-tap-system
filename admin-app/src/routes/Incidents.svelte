<script>
  // @ts-nocheck
  import { get } from 'svelte/store';
  import { onMount } from 'svelte';
  import Modal from '../components/common/Modal.svelte';
  import IncidentList from '../components/incidents/IncidentList.svelte';
  import { formatDateTimeRu } from '../lib/formatters.js';
  import { INCIDENT_COPY } from '../lib/operatorLabels.js';
  import { roleStore } from '../stores/roleStore.js';
  import { incidentStore } from '../stores/incidentStore.js';
  import { sessionStore } from '../stores/sessionStore.js';
  import { systemStore } from '../stores/systemStore.js';
  import { tapStore } from '../stores/tapStore.js';
  import { uiStore } from '../stores/uiStore.js';
  import { visitStore } from '../stores/visitStore.js';

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
  let isActionModalOpen = false;
  let actionForm = {
    incidentId: null,
    action: 'note',
    owner: '',
    note: '',
    escalationReason: '',
    resolutionSummary: '',
  };

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

  function buildNarrative(incident, tapMatch, sessionMatch, accountability) {
    const happened = incident.status === 'closed'
      ? 'закрыт и подтверждён системой.'
      : incident.status === 'in_progress'
        ? 'в работе и требует подтверждённого результата.'
        : 'ещё ждёт назначения ответственного оператора.';

    return [
      `${titleCase(incident.type)} на ${tapMatch?.display_name || incident.tap || 'непривязанном кране'} ${happened}`,
      accountability.owner
        ? `Ответственный оператор: ${accountability.owner}. Последний зафиксированный шаг: ${accountability.lastActionLabel}.`
        : 'Ответственный оператор не назначен — это нужно исправить следующим действием в системе.',
      tapMatch?.operations?.productStateLabel
        ? `Сейчас кран в состоянии «${tapMatch.operations.productStateLabel}», ${tapMatch.operations.liveStatus?.toLowerCase?.() || 'без уточнения от системы'}.`
        : 'По крану не хватает сигналов системы, поэтому описание собрано из данных по инциденту, крану и сессии.',
      sessionMatch
        ? `Связанная сессия #${sessionMatch.visit_id} ${sessionMatch.guest_full_name ? `для гостя ${sessionMatch.guest_full_name}` : 'без имени гостя'} ${sessionMatch.operator_status ? `со статусом ${sessionMatch.operator_status}` : ''}.`
        : 'Связанная сессия не найдена — стоит проверить журнал сессий и сигналы системы.',
    ];
  }

  function deriveImpact(incident, tapMatch, sessionMatch) {
    const impact = [];
    if (incident.priority === 'critical') impact.push('риск остановки продаж или несанкционированного пролива');
    if (incident.priority === 'high') impact.push('требует быстрого вмешательства смены');
    if (tapMatch?.operations?.currentPour?.isActive) impact.push('по крану прямо сейчас фиксируется поток');
    if (tapMatch?.operations?.heartbeat?.isStale) impact.push('heartbeat устарел');
    if (sessionMatch?.has_incident || sessionMatch?.incident_count) impact.push(`в истории сессии уже есть инцидент (${sessionMatch.incident_count || 1})`);
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
        label: item.sessionAction?.label || INCIDENT_COPY.openTap,
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
        title: 'Инцидент зарегистрирован',
        description: 'Пока доступны только сводные данные системы по инциденту.',
        href: '#/system',
        label: INCIDENT_COPY.openSystem,
      });
    }

    return events.slice(0, 6);
  }

  function deriveAccountability(incident, sessionMatch) {
    const owner = incident.owner || incident.operator || sessionMatch?.operator_name || null;
    const lastEscalatedAt = incident.escalated_at || (incident.source === 'system_state' ? incident.created_at : null);
    const lastActionLabel = incident.last_action || incident.note_action || (incident.status === 'closed' ? 'Закрытие подтверждено источником' : 'Действие не зафиксировано');
    const nextStep = incident.status === 'new'
      ? 'Назначить ответственного и перевести инцидент в работу.'
      : incident.status === 'in_progress'
        ? 'Зафиксировать действие, при необходимости передать на разбор и закрыть только после подтверждения системы.'
        : 'Проверить, что closure note и таймлайн содержат итог разбора.';

    return {
      owner,
      ownerLabel: owner || 'Не назначен',
      ownerBadge: owner ? `Ответственный: ${owner}` : 'Ответственный не назначен',
      ownerState: owner ? 'assigned' : 'unassigned',
      acknowledgedAt: incident.last_action_at || (incident.status !== 'new' ? incident.created_at : null),
      lastEscalatedAt,
      closedAt: incident.closed_at || (incident.status === 'closed' ? incident.created_at : null),
      lastActionLabel,
      nextStep,
      stateFlow: [
        {
          key: 'new',
          label: 'Новый',
          description: 'Инцидент поступил из системы и ждёт первичной обработки.',
          active: incident.status === 'new',
          done: incident.status !== 'new',
        },
        {
          key: 'in_progress',
          label: 'В работе',
          description: owner
            ? `Ответственный ${owner} ведёт разбор.`
            : 'Нужно назначить ответственного, чтобы зафиксировать работу по инциденту.',
          active: incident.status === 'in_progress',
          done: incident.status === 'closed',
        },
        {
          key: 'closed',
          label: 'Закрыт',
          description: incident.status === 'closed'
            ? 'Система уже подтвердила закрытие — статус считается итоговым.'
            : 'Закрытие допустимо только после подтверждения системы.',
          active: incident.status === 'closed',
          done: incident.status === 'closed',
        },
      ],
    };
  }

  function deriveActionsTaken(incident, tapMatch, sessionMatch, accountability) {
    const actions = [];
    if (accountability.owner) {
      actions.push({
        kind: 'owner',
        title: `Ответственный: ${accountability.owner}`,
        detail: accountability.lastActionLabel,
        time: accountability.acknowledgedAt,
      });
    }
    if (accountability.lastEscalatedAt) {
      actions.push({
        kind: 'escalation',
        title: 'Эскалация в system context',
        detail: 'Передача на разбор видна как сигнал системы; без подтверждённого действия её нельзя считать завершённой.',
        time: accountability.lastEscalatedAt,
      });
    }
    if (incident.note_action || incident.last_action) {
      actions.push({
        kind: 'note',
        title: 'Последнее подтверждённое действие',
        detail: incident.note_action || incident.last_action,
        time: incident.last_action_at || incident.created_at,
      });
    }
    if (tapMatch?.operations?.heartbeat?.isStale) {
      actions.push({
        kind: 'signal',
        title: 'Автоматический сигнал',
        detail: `Последний heartbeat ${tapMatch.operations.heartbeat.minutesAgo} мин назад.`,
        time: tapMatch.operations.heartbeat.at,
      });
    }
    if (sessionMatch?.incident_count) {
      actions.push({
        kind: 'history',
        title: 'Есть след в истории сессий',
        detail: `В связанной сессии отмечен инцидент: ${sessionMatch.incident_count}.`,
        time: sessionMatch.last_event_at || sessionMatch.opened_at,
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
    const tapMatch = ($tapStore.taps || []).find((tap) => String(tap.tap_id) === String(incident.tap) || tap.display_name === incident.tap) || null;
    const sessionMatch = matchSession(incident, tapMatch);
    const accountability = deriveAccountability(incident, sessionMatch);
    const tapLabel = tapMatch?.display_name || incident.tap || '—';

    return {
      ...incident,
      tapLabel,
      tapId: tapMatch?.tap_id || null,
      tapHref: tapMatch ? '#/taps' : null,
      sessionMatch,
      sessionHref: sessionMatch ? '#/sessions/history' : '#/sessions',
      systemHref: '#/system',
      sourceLabel: incident.source || tapMatch?.operations?.controllerStatus?.label || 'система инцидентов',
      typeLabel: titleCase(incident.type),
      priorityLabel: PRIORITY_LABELS[incident.priority] || titleCase(incident.priority),
      statusLabel: STATUS_LABELS[incident.status] || titleCase(incident.status),
      operatorInitials: initials(accountability.owner),
      accountability,
      summary: buildNarrative(incident, tapMatch, sessionMatch, accountability)[0],
      narrative: buildNarrative(incident, tapMatch, sessionMatch, accountability),
      impact: deriveImpact(incident, tapMatch, sessionMatch),
      relatedEvents: deriveRelatedEvents(incident, tapMatch, sessionMatch),
      actionsTaken: deriveActionsTaken(incident, tapMatch, sessionMatch, accountability),
      tapContext: tapMatch,
      systemState: $systemStore.overallState,
      openIncidentCount: $systemStore.openIncidentCount,
      backendStatusIsAuthoritative: true,
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
      && (!query || [item.incident_id, item.typeLabel, item.tapLabel, item.accountability.ownerLabel, item.summary].join(' ').toLowerCase().includes(query));
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
  $: actionModalIncident = enrichedItems.find((item) => item.incident_id === actionForm.incidentId) || selectedIncident;

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

  function openActionForm(event, suggestedAction = 'note') {
    const item = event.detail?.item || event;
    actionForm = {
      incidentId: item.incident_id,
      action: suggestedAction,
      owner: item.accountability?.owner || item.operator || '',
      note: item.note_action || '',
      escalationReason: '',
      resolutionSummary: '',
    };
    incidentStore.clearActionError();
    isActionModalOpen = true;
  }

  function closeActionForm() {
    isActionModalOpen = false;
    incidentStore.clearActionError();
  }

  async function submitActionForm() {
    const item = actionModalIncident;
    if (!item) return;

    try {
      if (actionForm.action === 'claim') {
        await incidentStore.claimIncident({ incidentId: item.incident_id, owner: actionForm.owner.trim(), note: actionForm.note.trim() || null });
      } else if (actionForm.action === 'escalate') {
        await incidentStore.escalateIncident({ incidentId: item.incident_id, reason: actionForm.escalationReason.trim(), note: actionForm.note.trim() || null });
      } else if (actionForm.action === 'close') {
        await incidentStore.closeIncident({ incidentId: item.incident_id, resolutionSummary: actionForm.resolutionSummary.trim(), note: actionForm.note.trim() || null });
      } else {
        await incidentStore.addIncidentNote({ incidentId: item.incident_id, note: actionForm.note.trim() });
      }

      uiStore.notifySuccess('Действие по инциденту зафиксировано.');
      if (selectedIncidentId !== item.incident_id) {
        selectedIncidentId = item.incident_id;
      }
      closeActionForm();
    } catch (error) {
      uiStore.notifyWarning(error.message || 'Фиксация действия по инциденту сейчас недоступна.');
    }
  }
</script>

{#if !$roleStore.permissions.incidents_manage}
  <section class="ui-card restricted"><h1>Инциденты</h1><p>Раздел инцидентов скрыт для текущей роли.</p></section>
{:else}
  <section class="page">
    <div class="page-header">
      <div>
        <h1>Инциденты</h1>
        <p>Оператор видит подтверждённый статус инцидента, ответственного и разницу между доступными действиями и только информацией для просмотра.</p>
      </div>
      <div class="header-stats">
        <article><span>Всего</span><strong>{enrichedItems.length}</strong></article>
        <article><span>Открытые</span><strong>{enrichedItems.filter((item) => item.status !== 'closed').length}</strong></article>
        <article><span>{INCIDENT_COPY.systemLabel}</span><strong>{$systemStore.overallState}</strong></article>
      </div>
    </div>

    <section class="ui-card banner-panel" data-tone={$incidentStore.readOnly ? 'warning' : 'ok'}>
      <div>
        <div class="eyebrow">{INCIDENT_COPY.actionLayer}</div>
        <strong>{$incidentStore.readOnly ? INCIDENT_COPY.readOnlyMode : INCIDENT_COPY.backendActionsActive}</strong>
        <p>{$incidentStore.readOnly ? $incidentStore.readOnlyReason : 'Все действия оператора записываются в систему и сразу обновляют очередь инцидентов.'}</p>
      </div>
      {#if $incidentStore.actionError}
        <p class="banner-error">{$incidentStore.actionError}</p>
      {/if}
    </section>

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
        <button on:click={() => incidentStore.fetchIncidents()} disabled={$incidentStore.loading}>{INCIDENT_COPY.refreshQueue}</button>
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
            actionCapabilities={$incidentStore.capabilities}
            readOnly={$incidentStore.readOnly}
            on:select={selectIncident}
            on:openTap={openTap}
            on:openSession={openSession}
            on:openSystem={openSystem}
            on:claimIncident={(event) => openActionForm(event, 'claim')}
            on:escalateIncident={(event) => openActionForm(event, 'escalate')}
            on:openActionForm={(event) => openActionForm(event, 'note')}
          />
        {/if}
      </div>

      <aside class="ui-card detail-panel">
        {#if selectedIncident}
          <div class="detail-head">
            <div>
              <div class="eyebrow">{INCIDENT_COPY.detailsPanel}</div>
              <h2>#{selectedIncident.incident_id}</h2>
              <p>{selectedIncident.typeLabel} · {selectedIncident.priorityLabel} · {selectedIncident.statusLabel}</p>
            </div>
            <div class={`priority-badge ${selectedIncident.priority}`}>{selectedIncident.priorityLabel}</div>
          </div>

          <section class="detail-section accountability-strip">
            <article>
              <span>{INCIDENT_COPY.owner}</span>
              <strong>{selectedIncident.accountability.ownerLabel}</strong>
              <small>{selectedIncident.accountability.nextStep}</small>
            </article>
            <article>
              <span>Последнее действие</span>
              <strong>{selectedIncident.accountability.lastActionLabel}</strong>
              <small>{selectedIncident.backendStatusIsAuthoritative ? 'Источник: лента инцидентов системы' : 'Источник: временная локальная запись'}</small>
            </article>
            <article>
              <span>Закрыт в</span>
              <strong>{selectedIncident.accountability.closedAt ? formatDateTimeRu(selectedIncident.accountability.closedAt) : 'Ещё открыт'}</strong>
              <small>{selectedIncident.closed_at ? 'Время закрытия подтверждено системой.' : 'Ожидает подтверждения закрытия от системы.'}</small>
            </article>
          </section>

          <section class="detail-section">
            <div class="section-head">
              <h3>{INCIDENT_COPY.stateFlow}</h3>
              <button class="link" on:click={() => openActionForm(selectedIncident, selectedIncident.status === 'new' ? 'claim' : 'note')}>{INCIDENT_COPY.actionForm}</button>
            </div>
            <ol class="state-flow">
              {#each selectedIncident.accountability.stateFlow as step}
                <li class:done={step.done} class:active={step.active}>
                  <strong>{step.label}</strong>
                  <p>{step.description}</p>
                </li>
              {/each}
            </ol>
          </section>

          <section class="detail-section narrative-section">
            <h3>Что случилось</h3>
            <p>{selectedIncident.summary}</p>
            <ul>
              {#each selectedIncident.narrative as line}<li>{line}</li>{/each}
            </ul>
          </section>

          <section class="detail-section meta-grid">
            <article><span>Кран</span><strong>{selectedIncident.tapLabel}</strong></article>
            <article><span>{INCIDENT_COPY.ownerServer}</span><strong>{selectedIncident.owner || selectedIncident.accountability.ownerLabel}</strong></article>
            <article><span>Источник</span><strong>{selectedIncident.sourceLabel}</strong></article>
            <article><span>Связанная сессия</span><strong>{selectedIncident.sessionMatch ? `#${selectedIncident.sessionMatch.visit_id}` : 'Не найдена'}</strong></article>
          </section>

          <section class="detail-section">
            <div class="section-head"><h3>{INCIDENT_COPY.impact}</h3><button class="link" on:click={() => openSystem({ detail: { item: selectedIncident } })}>{INCIDENT_COPY.openSystem}</button></div>
            <ul class="chip-list">
              {#each selectedIncident.impact as item}<li>{item}</li>{/each}
            </ul>
          </section>

          <section class="detail-section">
            <div class="section-head"><h3>{INCIDENT_COPY.relatedEvents}</h3><button class="link" on:click={() => openSession({ detail: { item: selectedIncident } })}>{INCIDENT_COPY.openSession}</button></div>
            <ul class="timeline">
              {#each selectedIncident.relatedEvents as event}
                <li>
                  <div>
                    <strong>{event.title}</strong>
                    <p>{event.description}</p>
                  </div>
                  <div class="timeline-meta">
                    <span>{event.time ? formatDateTimeRu(event.time) : 'Время не указано'}</span>
                    <a href={event.href}>{event.label}</a>
                  </div>
                </li>
              {/each}
            </ul>
          </section>

          <section class="detail-section">
            <div class="section-head"><h3>{INCIDENT_COPY.actionsTaken}</h3><button class="link" on:click={() => openActionForm(selectedIncident, 'note')}>{INCIDENT_COPY.actionForm}</button></div>
            {#if selectedIncident.actionsTaken.length}
              <ul class="timeline compact">
                {#each selectedIncident.actionsTaken as action}
                  <li>
                    <div>
                      <strong>{action.title}</strong>
                      <p>{action.detail}</p>
                    </div>
                    <div class="timeline-meta compact">{action.time ? formatDateTimeRu(action.time) : '—'}</div>
                  </li>
                {/each}
              </ul>
            {:else}
              <p class="muted">{INCIDENT_COPY.noActionsYet}</p>
            {/if}
          </section>
        {:else}
          <p class="muted">{INCIDENT_COPY.noIncidentsFiltered}</p>
        {/if}
      </aside>
    </div>
  </section>

  {#if isActionModalOpen && actionModalIncident}
    <Modal on:close={closeActionForm}>
      <div slot="header">
        <h2>{INCIDENT_COPY.actionFormTitle} · #{actionModalIncident.incident_id}</h2>
        <p class="modal-subtitle">Форма записывает реальное действие по инциденту в систему и ждёт подтверждения перед обновлением карточки.</p>
      </div>

      <div class="incident-action-form">
        <section class="detail-section compact-panel">
          <div class="form-grid two-columns">
            <label>
              <span>Действие</span>
              <select bind:value={actionForm.action} disabled={$incidentStore.readOnly}>
                <option value="claim">Взять в работу</option>
                <option value="note">Добавить заметку</option>
                <option value="escalate">Эскалировать</option>
                <option value="close">Закрыть</option>
              </select>
            </label>
            <label>
              <span>Ответственный</span>
              <input bind:value={actionForm.owner} placeholder="Имя оператора" disabled={$incidentStore.readOnly} />
            </label>
          </div>
          <p class="muted">Текущий статус в системе: <strong>{actionModalIncident.statusLabel}</strong>. После сохранения карточка обновится подтверждёнными данными без сброса выбранного инцидента.</p>
        </section>

        <section class="detail-section compact-panel">
          <h3>{INCIDENT_COPY.operatorNote}</h3>
          <textarea bind:value={actionForm.note} rows="5" placeholder="Что сделал оператор, что проверил, какие данные увидел" disabled={$incidentStore.readOnly}></textarea>
        </section>

        {#if actionForm.action === 'escalate'}
          <section class="detail-section compact-panel">
            <h3>{INCIDENT_COPY.escalationHandoff}</h3>
            <textarea bind:value={actionForm.escalationReason} rows="4" placeholder="Кому передаёте инцидент, почему нужен дополнительный разбор и какой сигнал это подтвердил" disabled={$incidentStore.readOnly}></textarea>
          </section>
        {/if}

        {#if actionForm.action === 'close'}
          <section class="detail-section compact-panel">
            <h3>{INCIDENT_COPY.closureSummary}</h3>
            <textarea bind:value={actionForm.resolutionSummary} rows="4" placeholder="Как устранено, чем подтверждено, когда можно считать кейс закрытым" disabled={$incidentStore.readOnly}></textarea>
          </section>
        {/if}

        <section class="detail-section compact-panel">
          <h3>Прозрачность статуса</h3>
          <ul class="modal-checklist">
            <li>Новый → в работе → закрыт отображаются только по данным системы.</li>
            <li>Ответственный, передача на разбор и закрытие сохраняются в журнале системы.</li>
            <li>Экран показывает ответственного, последнее действие и время закрытия только из подтверждённых полей.</li>
          </ul>
        </section>
      </div>

      <div slot="footer" class="modal-actions">
        <button class="secondary" type="button" on:click={closeActionForm}>Закрыть</button>
        <button type="button" on:click={submitActionForm} disabled={$incidentStore.readOnly || $incidentStore.actionLoading}>
          {$incidentStore.readOnly ? INCIDENT_COPY.readOnlyCta : INCIDENT_COPY.saveAction}
        </button>
      </div>
    </Modal>
  {/if}
{/if}

<style>
  .page, .filters-panel, .panel, .detail-panel, .detail-section, .banner-panel, .incident-action-form { display: grid; gap: 1rem; }
  .page-header, .filters-actions, .detail-head, .section-head, .timeline li { display: flex; gap: 1rem; justify-content: space-between; }
  .page-header { align-items: flex-start; flex-wrap: wrap; }
  .page-header h1, .page-header p, .detail-head h2, .detail-head p, .detail-section h3, .timeline p { margin: 0; }
  .header-stats { display: flex; gap: 0.75rem; flex-wrap: wrap; }
  .header-stats article, .meta-grid article, .accountability-strip article { border: 1px solid #e2e8f0; border-radius: 14px; padding: 0.85rem 1rem; background: #fff; min-width: 120px; display: grid; gap: 0.3rem; }
  .filters-grid, .meta-grid, .form-grid { display: grid; gap: 0.75rem; }
  .filters-grid { grid-template-columns: repeat(6, minmax(120px, 1fr)); }
  .meta-grid, .accountability-strip, .two-columns { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .accountability-strip { display: grid; gap: 0.75rem; }
  .banner-panel[data-tone='warning'] { border: 1px solid #fdba74; background: #fff7ed; }
  .banner-panel[data-tone='ok'] { border: 1px solid #86efac; background: #f0fdf4; }
  .banner-error { color: #9a3412; margin: 0; }
  label { display: grid; gap: 0.35rem; }
  input, select, button, textarea { font: inherit; }
  input, select, button, textarea { border: 1px solid #cbd5e1; border-radius: 12px; padding: 0.7rem 0.85rem; background: #fff; }
  textarea { resize: vertical; min-height: 120px; }
  button { font-weight: 700; }
  .secondary, .link { background: #fff; color: #0f172a; }
  .link { padding: 0; border: none; color: #1d4ed8; }
  .content-grid { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(360px, 0.9fr); gap: 1rem; align-items: start; }
  .detail-panel { position: sticky; top: 0; }
  .eyebrow, .muted, .detail-section p, label span, .timeline-meta, .modal-subtitle, .accountability-strip small { color: var(--text-secondary, #64748b); }
  .priority-badge { align-self: flex-start; padding: 0.35rem 0.7rem; border-radius: 999px; font-weight: 700; }
  .priority-badge.low { background: #e2e8f0; }
  .priority-badge.medium { background: #dbeafe; color: #1d4ed8; }
  .priority-badge.high { background: #fef3c7; color: #92400e; }
  .priority-badge.critical { background: #fee2e2; color: #b91c1c; }
  .detail-section { border: 1px solid #e2e8f0; border-radius: 18px; padding: 1rem; background: rgba(248,250,252,0.8); }
  .compact-panel { background: #fff; }
  .narrative-section ul, .chip-list, .timeline, .state-flow, .modal-checklist { margin: 0; padding-left: 1rem; }
  .chip-list { display: flex; flex-wrap: wrap; gap: 0.5rem; list-style: none; padding-left: 0; }
  .chip-list li { background: #eff6ff; color: #1e3a8a; border-radius: 999px; padding: 0.35rem 0.7rem; }
  .timeline { list-style: none; padding-left: 0; display: grid; gap: 0.75rem; }
  .timeline li { align-items: flex-start; border: 1px solid #e2e8f0; border-radius: 14px; background: #fff; padding: 0.85rem; }
  .timeline-meta { min-width: 160px; display: grid; gap: 0.5rem; text-align: right; }
  .timeline-meta.compact { min-width: auto; }
  .timeline a { color: #1d4ed8; text-decoration: none; font-weight: 600; }
  .state-flow { display: grid; gap: 0.75rem; list-style: none; padding-left: 0; counter-reset: flow; }
  .state-flow li { border: 1px solid #e2e8f0; border-radius: 14px; padding: 0.9rem 1rem; background: #fff; }
  .state-flow li.active { border-color: #2563eb; background: #eff6ff; }
  .state-flow li.done { border-color: #86efac; background: #f0fdf4; }
  .state-flow p { margin-top: 0.25rem; }
  .modal-actions { display: flex; justify-content: flex-end; gap: 0.75rem; }
  .restricted { padding: 1rem; }
  @media (max-width: 1200px) { .content-grid { grid-template-columns: 1fr; } .detail-panel { position: static; } .filters-grid { grid-template-columns: repeat(3, minmax(120px, 1fr)); } }
  @media (max-width: 720px) { .filters-grid, .meta-grid, .accountability-strip, .two-columns { grid-template-columns: 1fr; } }
</style>
