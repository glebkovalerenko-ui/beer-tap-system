<script>
  import { get } from 'svelte/store';
  import { onMount } from 'svelte';
  import Modal from '../components/common/Modal.svelte';
  import IncidentList from '../components/incidents/IncidentList.svelte';
  import { getActionPlan, navigateWithFocus } from '../lib/actionRouting.js';
  import { formatDateTimeRu } from '../lib/formatters.js';
  import { buildEnrichedIncidents, buildFilterOptions, filterIncidents, groupIncidentsByStatus } from '../lib/incidentsViewModel.js';
  import { buildIncidentCapabilities, resolveIncidentAction, resolveIncidentActionRequest } from '../lib/operator/incidentModel.js';
  import { INCIDENT_COPY } from '../lib/operatorLabels.js';
  import { ensureIncidentsData } from '../stores/operatorShellOrchestrator.js';
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
    slaRisk: 'all',
  };

  const SECTION_LABELS = {
    new: 'Новые',
    in_progress: 'В работе',
    closed: 'Закрытые',
  };

  /** @type {Record<string, string>} */
  const PRIORITY_LABELS = {
    low: 'Низкий',
    medium: 'Средний',
    high: 'Высокий',
    critical: 'Критический',
  };

  /** @type {Record<string, string>} */
  const STATUS_LABELS = {
    new: 'Новый',
    in_progress: 'В работе',
    closed: 'Закрыт',
  };

  let filters = { ...DEFAULT_FILTERS };
  /** @type {any} */
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
    if (token) {
      ensureIncidentsData({ reason: 'route-enter' });
    }

    const focusedIncidentId = sessionStorage.getItem('incidents.focusIncidentId');
    if (focusedIncidentId) {
      const parsed = Number.parseInt(focusedIncidentId, 10);
      selectedIncidentId = Number.isNaN(parsed) ? focusedIncidentId : parsed;
      sessionStorage.removeItem('incidents.focusIncidentId');
    }

    const focusedSource = sessionStorage.getItem('incidents.focusSource');
    if (focusedSource) {
      filters = { ...filters, query: focusedSource };
      sessionStorage.removeItem('incidents.focusSource');
    }
  });



  /** @param {string|number|null|undefined} value */
  function titleCase(value) {
    if (!value) return '—';
    const text = String(value).replaceAll('_', ' ');
    return text.charAt(0).toUpperCase() + text.slice(1);
  }


  /** @type {import('../lib/incidentsViewModel.js').IncidentViewModel[]} */
  let enrichedItems = [];

  /** @type {any} */
  let filterOptions = { priorities: [], statuses: [], types: [], taps: [] };

  /** @type {any} */
  let permissions = {};

  /** @type {import('../lib/incidentsViewModel.js').IncidentViewModel[]} */
  let filteredItems = [];

  /** @type {{key: string, label: string, items: import('../lib/incidentsViewModel.js').IncidentViewModel[]}[]} */
  let groupedItems = [];

  $: enrichedItems = buildEnrichedIncidents({
    incidents: $incidentStore.items,
    taps: $tapStore.taps,
    activeVisits: $visitStore.activeVisits,
    systemState: $systemStore.overallState,
    openIncidentCount: $systemStore.openIncidentCount,
    incidentCopy: INCIDENT_COPY,
    priorityLabels: PRIORITY_LABELS,
    statusLabels: STATUS_LABELS,
  });

  $: filterOptions = /** @type {any} */ (buildFilterOptions(enrichedItems));

  $: filteredItems = filterIncidents(enrichedItems, filters);

  $: groupedItems = groupIncidentsByStatus(filteredItems, SECTION_LABELS);

  $: if (filteredItems.length > 0 && !filteredItems.some((item) => item.incident_id === selectedIncidentId)) {
    selectedIncidentId = filteredItems[0].incident_id;
  }

  $: selectedIncident = filteredItems.find((item) => item.incident_id === selectedIncidentId) || null;
  $: actionModalIncident = enrichedItems.find((item) => item.incident_id === actionForm.incidentId) || selectedIncident;


  /** @typedef {CustomEvent<{ incidentId: string|number }>} SelectIncidentEvent */
  function resetFilters() {
    filters = { ...DEFAULT_FILTERS };
  }

  /** @param {SelectIncidentEvent} event */
  function selectIncident(event) {
    selectedIncidentId = event.detail.incidentId;
  }

  /** @param {any} event */
  function openTap(event) {
    const item = event.detail.item;
    navigateWithFocus(/** @type {any} */ ({ target: 'tap', tapId: item.tapId || undefined, source: item.tapLabel || item.sourceLabel || undefined }));
  }

  /** @param {any} event */
  function openSession(event) {
    const item = event.detail.item;
    if (item.sessionMatch?.visit_id) {
      navigateWithFocus(/** @type {any} */ ({ target: 'session', visitId: item.sessionMatch.visit_id || undefined, source: item.tapLabel || item.sourceLabel || undefined }));
      return;
    }
    if (item.tapId) {
      sessionStorage.setItem('sessions.history.tapId', String(item.tapId));
      window.location.hash = '/sessions/history';
      return;
    }
    window.location.hash = '/sessions/history';
  }

  /** @param {any} event */
  function openSystem(event) {
    const item = event.detail.item;
    navigateWithFocus(/** @type {any} */ ({ target: 'system', source: item.sourceLabel || item.source || 'incident', tapId: item.tapId, incidentId: item.incident_id }));
  }

  $: permissions = /** @type {any} */ ($roleStore.permissions || {});
  $: canViewIncidents = Boolean(permissions.incidents_view);
  $: incidentActionCapabilitiesRaw = $incidentStore.capabilities || {};
  $: incidentCapabilitiesModel = buildIncidentCapabilities(incidentActionCapabilitiesRaw);
  /** @type {Record<string, boolean>} */
  $: incidentActionCapabilities = incidentCapabilitiesModel.capabilities;
  /** @type {Record<string, string|null>} */
  $: incidentActionCapabilityReasons = incidentCapabilitiesModel.reasons;
  $: incidentActionReadOnly = $incidentStore.readOnly;
  $: incidentActionReadOnlyReason = $incidentStore.readOnlyReason || 'Фиксация действий временно недоступна.';
  $: incidentActionPlan = getActionPlan('incident');

  /** @param {any} event */
  function openActionForm(event, suggestedAction = 'note') {
    const item = event?.detail?.item || event;
    if (incidentActionReadOnly) return;
    const resolvedAction = resolveIncidentAction({ suggestedAction, capabilities: incidentActionCapabilities });

    actionForm = {
      incidentId: item.incident_id,
      action: resolvedAction,
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
    if (!incidentActionCapabilities[actionForm.action]) {
      uiStore.notifyWarning(incidentActionCapabilityReasons[actionForm.action] || 'Действие недоступно для текущей роли/окружения.');
      return;
    }

    try {
      const request = resolveIncidentActionRequest({ action: actionForm.action, item, form: actionForm });
      await incidentStore[request.method](request.payload);
      await ensureIncidentsData({ reason: 'incident-action', force: true });

      uiStore.notifySuccess('Действие по инциденту зафиксировано.');
      if (selectedIncidentId !== item.incident_id) {
        selectedIncidentId = item.incident_id;
      }
      closeActionForm();
    } catch (error) {
      const errorMessage = typeof error === 'string' ? error : error instanceof Error ? error.message : 'Фиксация действия по инциденту сейчас недоступна.';
      uiStore.notifyWarning(errorMessage);
    }
  }
</script>

{#if !canViewIncidents}
  <section class="ui-card restricted"><h1>Инциденты</h1><p>Раздел инцидентов скрыт для текущей роли.</p></section>
{:else}
  <section class="page">
    <div class="page-header">
      <div>
        <h1>Инциденты</h1>
        <p>{incidentActionReadOnly ? 'Оператор видит очередь инцидентов и причины недоступности mutation-действий в текущем окружении.' : 'Оператор видит подтверждённый статус инцидента, ответственного и может фиксировать действия прямо из очереди.'}</p>
      </div>
      <div class="header-stats">
        <article><span>Всего</span><strong>{enrichedItems.length}</strong></article>
        <article><span>Открытые</span><strong>{enrichedItems.filter((item) => item.status !== 'closed').length}</strong></article>
        <article><span>{INCIDENT_COPY.systemLabel}</span><strong>{$systemStore.overallState}</strong></article>
      </div>
    </div>

    <section class="ui-card banner-panel" data-tone={incidentActionReadOnly ? 'warning' : 'ok'}>
      <div>
        <div class="eyebrow">{INCIDENT_COPY.actionLayer}</div>
        <strong>{incidentActionReadOnly ? INCIDENT_COPY.readOnlyMode : INCIDENT_COPY.backendActionsActive}</strong>
        <p>{incidentActionReadOnly ? incidentActionReadOnlyReason : 'Все действия оператора записываются в систему и сразу обновляют очередь инцидентов.'}</p>
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
        <label>
          <span>SLA</span>
          <select bind:value={filters.slaRisk}>
            <option value="all">Все</option>
            <option value="at_risk">SLA at risk</option>
          </select>
        </label>
      </div>
      <div class="filters-actions">
        <button class="secondary" on:click={resetFilters}>Сбросить</button>
        <button on:click={() => ensureIncidentsData({ reason: 'manual-refresh', force: true })} disabled={$incidentStore.loading}>{INCIDENT_COPY.refreshQueue}</button>
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
            actionCapabilities={incidentActionCapabilities}
            actionCapabilityReasons={incidentActionCapabilityReasons}
            {permissions}
            readOnly={incidentActionReadOnly}
            on:select={selectIncident}
            on:openTap={openTap}
            on:openSession={openSession}
            on:openSystem={openSystem}
            on:claimIncident={(event) => openActionForm(event, 'claim')}
            on:openCloseForm={(event) => openActionForm(event, 'close')}
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

          <section class="detail-section next-step-panel">
            <div class="section-head">
              <h3>Следующий шаг</h3>
            </div>
            <p>
              {selectedIncident.accountability.nextStep}
              Рекомендация: <strong>{incidentActionPlan.recommendedOwnerState}</strong> · {incidentActionPlan.recommendedActionState}.
            </p>
            <div class="next-step-actions">
              <button on:click={() => navigateWithFocus(/** @type {any} */ ({
                target: incidentActionPlan.primaryTarget,
                incidentId: selectedIncident.incident_id || undefined,
                tapId: selectedIncident.tapId || undefined,
                source: selectedIncident.sourceLabel || undefined,
              }))}>{incidentActionPlan.primaryCta}</button>
              <button
                class="secondary"
                on:click={() => navigateWithFocus(/** @type {any} */ ({
                  target: incidentActionPlan.secondaryCta.target,
                  incidentId: selectedIncident.incident_id || undefined,
                  tapId: selectedIncident.tapId || undefined,
                  source: selectedIncident.sourceLabel || undefined,
                }))}
              >
                {incidentActionPlan.secondaryCta.label}
              </button>
            </div>
          </section>

          <section class="detail-section">
            <div class="section-head">
              <h3>{INCIDENT_COPY.stateFlow}</h3>
              {#if !incidentActionReadOnly}<button class="link" on:click={() => openActionForm(selectedIncident, selectedIncident.status === 'new' ? 'claim' : 'note')}>{INCIDENT_COPY.actionForm}</button>{/if}
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

          {#if incidentActionReadOnly}
            <section class="detail-section viewer-guidance">
              <div class="section-head"><h3>Что может сделать оператор</h3></div>
              <p>{incidentActionReadOnlyReason} Доступны просмотр очереди, фильтры и переходы в связанный контекст.</p>
            </section>
          {/if}

          <section class="detail-section">
            <div class="section-head"><h3>{INCIDENT_COPY.actionsTaken}</h3>{#if !incidentActionReadOnly}<button class="link" on:click={() => openActionForm(selectedIncident, 'note')}>{INCIDENT_COPY.actionForm}</button>{/if}</div>
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
              <select bind:value={actionForm.action} disabled={incidentActionReadOnly}>
                <option value="claim" disabled={!incidentActionCapabilities.claim}>Взять в работу</option>
                <option value="note" disabled={!incidentActionCapabilities.note}>Добавить заметку</option>
                <option value="escalate" disabled={!incidentActionCapabilities.escalate}>Эскалировать</option>
                <option value="close" disabled={!incidentActionCapabilities.close}>Закрыть</option>
              </select>
            </label>
            <label>
              <span>Ответственный</span>
              <input bind:value={actionForm.owner} placeholder="Имя оператора" disabled={incidentActionReadOnly} />
            </label>
          </div>
          <p class="muted">Текущий статус в системе: <strong>{actionModalIncident.statusLabel}</strong>. После сохранения карточка обновится подтверждёнными данными без сброса выбранного инцидента.</p>
          {#if incidentActionReadOnly}
            <p class="muted">{incidentActionReadOnlyReason}</p>
          {/if}
        </section>

        <section class="detail-section compact-panel">
          <h3>{INCIDENT_COPY.operatorNote}</h3>
          <textarea bind:value={actionForm.note} rows="5" placeholder="Что сделал оператор, что проверил, какие данные увидел" disabled={incidentActionReadOnly}></textarea>
        </section>

        {#if actionForm.action === 'escalate'}
          <section class="detail-section compact-panel">
            <h3>{INCIDENT_COPY.escalationHandoff}</h3>
            <textarea bind:value={actionForm.escalationReason} rows="4" placeholder="Кому передаёте инцидент, почему нужен дополнительный разбор и какой сигнал это подтвердил" disabled={incidentActionReadOnly}></textarea>
          </section>
        {/if}

        {#if actionForm.action === 'close'}
          <section class="detail-section compact-panel">
            <h3>{INCIDENT_COPY.closureSummary}</h3>
            <textarea bind:value={actionForm.resolutionSummary} rows="4" placeholder="Как устранено, чем подтверждено, когда можно считать кейс закрытым" disabled={incidentActionReadOnly}></textarea>
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
        <button type="button" on:click={submitActionForm} disabled={incidentActionReadOnly || $incidentStore.actionLoading}>
          {incidentActionReadOnly ? INCIDENT_COPY.readOnlyCta : INCIDENT_COPY.saveAction}
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
  .next-step-panel p { margin: 0; }
  .next-step-actions { display: flex; gap: 0.75rem; flex-wrap: wrap; }
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
