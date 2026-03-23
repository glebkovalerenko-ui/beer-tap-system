<script>
  // @ts-nocheck
  import { onMount } from 'svelte';
  import { get } from 'svelte/store';
  import { visitStore } from '../../stores/visitStore.js';
  import { shiftStore } from '../../stores/shiftStore.js';
  import { formatDateTimeRu } from '../../lib/formatters.js';

  const DEFAULT_FILTERS = {
    periodPreset: 'today',
    dateFrom: '',
    dateTo: '',
    tapId: '',
    status: '',
    cardUid: '',
    incidentOnly: false,
    unsyncedOnly: false,
    zeroVolumeAbortOnly: false,
  };

  let filters = { ...DEFAULT_FILTERS };
  let focusVisitId = '';
  let focusTapId = '';
  let focusResolved = false;

  $: items = $visitStore.sessionHistory || [];
  $: detail = $visitStore.sessionHistoryDetail;
  $: filteredItems = items.filter(matchesClientFilters);
  $: focusContextText = focusVisitId
    ? `Журнал сфокусирован на сессии ${focusVisitId}.`
    : focusTapId
      ? `Журнал сфокусирован на контексте крана ${focusTapId}.`
      : '';
  $: detailNarrativeGroups = detail ? groupedNarrative(detail) : { timeline: [], operatorObservations: [] };
  $: detailOperatorActions = detail ? normalizedOperatorActions(detail.summary) : [];
  $: if (focusVisitId && !focusResolved && !$visitStore.historyLoading && (filteredItems.length > 0 || items.length > 0)) {
    resolveFocusVisit();
  }

  const syncLabels = {
    pending_sync: 'Ожидает синхронизации',
    rejected: 'Синхронизация отклонена',
    reconciled: 'Сверено вручную',
    synced: 'Синхронизировано',
    not_started: 'Наливов не было',
  };

  const completionSourceLabels = {
    operator: 'Завершена оператором',
    auto_close: 'Закрылась автоматически',
    abort: 'Прервана оператором',
    incident: 'Остановлена из-за инцидента',
    system: 'Завершена системой',
    timeout: 'Завершена по таймауту',
  };

  const narrativeKindLabels = {
    open: 'Сессия открыта',
    authorize: 'Карта подтверждена',
    pour_start: 'Налив начался',
    pour_end: 'Налив завершён',
    sync: 'Статус синхронизации обновлён',
    close: 'Сессия закрыта',
    abort: 'Сессия прервана',
    incident: 'Зафиксирован инцидент',
    action: 'Действие оператора',
  };

  const actionLabels = {
    force_unlock: 'Оператор принудительно разблокировал сессию',
    reconcile_pour: 'Оператор скорректировал налив',
    report_lost_card: 'Оператор отметил карту как потерянную',
    close_visit: 'Оператор завершил сессию',
    assign_card: 'Оператор привязал карту',
  };

  onMount(async () => {
    filters = { ...filters, ...getPeriodBounds(filters.periodPreset) };

    const presetCardUid = sessionStorage.getItem('sessions.history.cardUid');
    if (presetCardUid) {
      sessionStorage.removeItem('sessions.history.cardUid');
      filters = { ...filters, cardUid: presetCardUid };
    }

    const presetTapId = sessionStorage.getItem('sessions.history.tapId');
    if (presetTapId) {
      sessionStorage.removeItem('sessions.history.tapId');
      focusTapId = presetTapId;
      filters = { ...filters, tapId: presetTapId };
    }

    const presetVisitId = sessionStorage.getItem('visits.lookupVisitId') || sessionStorage.getItem('sessions.history.visitId');
    if (presetVisitId) {
      sessionStorage.removeItem('visits.lookupVisitId');
      sessionStorage.removeItem('sessions.history.visitId');
      focusVisitId = presetVisitId;
    }

    await applyFilters();
  });

  function isoDateLocal(value) {
    const local = new Date(value.getTime() - value.getTimezoneOffset() * 60000);
    return local.toISOString().slice(0, 10);
  }

  function getPeriodBounds(periodPreset) {
    const now = new Date();
    if (periodPreset === 'range') {
      return { dateFrom: filters.dateFrom, dateTo: filters.dateTo };
    }
    if (periodPreset === 'shift') {
      const shift = get(shiftStore).shift;
      if (shift?.opened_at) {
        const openedAt = new Date(shift.opened_at);
        return {
          dateFrom: isoDateLocal(openedAt),
          dateTo: shift.closed_at ? isoDateLocal(new Date(shift.closed_at)) : isoDateLocal(now),
        };
      }
    }
    const today = isoDateLocal(now);
    return { dateFrom: today, dateTo: today };
  }

  function describeCompletionSource(value) {
    if (!value) return 'Не указан';
    return completionSourceLabels[value] || value.replaceAll('_', ' ');
  }

  function describeFlags(item) {
    const flags = [];
    if (item.contains_tail_pour) flags.push('Есть долив хвоста');
    if (item.contains_non_sale_flow) flags.push('Есть служебный налив без продажи');
    if (item.has_incident) flags.push(`Есть инциденты (${item.incident_count || 1})`);
    if (item.has_unsynced) flags.push('Есть несинхронизированные данные');
    return flags.length ? flags.join(' · ') : 'Особых флагов нет';
  }

  function isZeroVolumeAbort(item) {
    return item.operator_status === 'Прервана' && !item.lifecycle?.first_pour_started_at && !item.lifecycle?.last_pour_ended_at;
  }

  function matchesClientFilters(item) {
    if (filters.zeroVolumeAbortOnly && !isZeroVolumeAbort(item)) return false;
    return true;
  }

  async function applyFilters() {
    focusResolved = false;
    if (filters.periodPreset !== 'range') {
      filters = { ...filters, ...getPeriodBounds(filters.periodPreset) };
    }
    await visitStore.fetchSessionHistory(filters).catch(() => {});
  }

  function resetFilters() {
    filters = { ...DEFAULT_FILTERS, ...getPeriodBounds(DEFAULT_FILTERS.periodPreset) };
    focusTapId = '';
    focusVisitId = '';
    focusResolved = false;
    closeDetail();
    applyFilters();
  }

  async function resolveFocusVisit() {
    const target = items.find((item) => String(item.visit_id) === String(focusVisitId));
    if (target) {
      focusResolved = true;
      await openDetail(target);
      return;
    }
    focusResolved = true;
    await visitStore.fetchSessionHistoryDetail(focusVisitId).catch(() => {});
  }

  async function openDetail(item) {
    focusVisitId = String(item.visit_id);
    focusResolved = true;
    await visitStore.fetchSessionHistoryDetail(item.visit_id).catch(() => {});
  }

  function closeDetail() {
    visitStore.clearSessionHistoryDetail();
  }

  function updatePeriodPreset(periodPreset) {
    filters = { ...filters, periodPreset, ...getPeriodBounds(periodPreset) };
  }

  function buildWhatHappened(summary) {
    const lifecycle = [];
    lifecycle.push(`Сессия ${summary.operator_status?.toLowerCase() || 'обработана'}${summary.card_uid ? ` по карте ${summary.card_uid}` : ' без привязанной карты'}`);
    if (summary.taps?.length) {
      lifecycle.push(`через кран ${summary.taps.join(', ')}`);
    }
    const state = [];
    state.push(syncLabels[summary.sync_state] || summary.sync_state);
    if (summary.contains_tail_pour) state.push('зафиксирован долив хвоста');
    if (summary.contains_non_sale_flow) state.push('был служебный налив без продажи');
    if (summary.has_unsynced) state.push('остались несинхронизированные данные');
    return [
      `${lifecycle.join(' ')}.`,
      `Источник завершения: ${describeCompletionSource(summary.completion_source)}. ${state.join(', ')}.`,
    ];
  }

  function fallbackNarrative(summary) {
    const lifecycle = summary.lifecycle || {};
    return [
      lifecycle.opened_at && {
        timestamp: lifecycle.opened_at,
        title: 'Сессия открыта',
        description: 'Оператор открыл сессию и журнал начал отслеживание событий.',
        kind: 'open',
        status: summary.visit_status,
      },
      lifecycle.first_authorized_at && {
        timestamp: lifecycle.first_authorized_at,
        title: 'Карта подтверждена',
        description: summary.card_uid ? `Карта ${summary.card_uid} была подтверждена для доступа к наливу.` : 'Система подтвердила доступ к наливу.',
        kind: 'authorize',
        status: summary.visit_status,
      },
      lifecycle.first_pour_started_at && {
        timestamp: lifecycle.first_pour_started_at,
        title: 'Налив начался',
        description: 'Гость начал налив по этой сессии.',
        kind: 'pour_start',
        status: summary.visit_status,
      },
      lifecycle.last_pour_ended_at && {
        timestamp: lifecycle.last_pour_ended_at,
        title: 'Последний налив завершён',
        description: 'Последний зафиксированный налив по сессии завершился.',
        kind: 'pour_end',
        status: summary.visit_status,
      },
      lifecycle.closed_at && {
        timestamp: lifecycle.closed_at,
        title: summary.operator_status === 'Прервана' ? 'Сессия прервана' : 'Сессия завершена',
        description: `Завершение отмечено как: ${describeCompletionSource(summary.completion_source)}.`,
        kind: summary.operator_status === 'Прервана' ? 'abort' : 'close',
        status: summary.visit_status,
      },
    ].filter(Boolean);
  }

  function groupedNarrative(detailPayload) {
    const source = detailPayload?.narrative?.length ? detailPayload.narrative : fallbackNarrative(detailPayload.summary);
    const timeline = source.map((event) => ({
      ...event,
      title: event.title || narrativeKindLabels[event.kind] || 'Событие сессии',
      description: event.description || 'Подробности по событию не переданы backend.',
    }));
    const operatorObservations = [];
    if (detailPayload.summary.has_incident) operatorObservations.push({ title: 'В сессии были инциденты', description: `Количество инцидентов: ${detailPayload.summary.incident_count || 1}.` });
    if (detailPayload.summary.contains_tail_pour) operatorObservations.push({ title: 'Есть долив хвоста', description: 'Сессия включает хвостовой долив и требует внимательной проверки итогов.' });
    if (detailPayload.summary.contains_non_sale_flow) operatorObservations.push({ title: 'Есть служебный налив', description: 'Часть действий прошла как non-sale и не должна трактоваться как обычная продажа.' });
    if (detailPayload.summary.has_unsynced) operatorObservations.push({ title: 'Есть риск несинхронизированных данных', description: syncLabels[detailPayload.summary.sync_state] || detailPayload.summary.sync_state });
    return { timeline, operatorObservations };
  }

  function normalizedOperatorActions(summary) {
    if (summary.operator_actions?.length) {
      return summary.operator_actions.map((action) => ({
        ...action,
        label: action.label || actionLabels[action.action] || action.action?.replaceAll('_', ' ') || 'Действие оператора',
        details: action.details || 'Backend не передал дополнительный комментарий.',
      }));
    }
    if (summary.completion_source || summary.contains_tail_pour || summary.contains_non_sale_flow) {
      return [{
        timestamp: summary.closed_at || summary.last_event_at || summary.opened_at,
        label: 'Клиент собрал краткое резюме действий',
        details: `Источник завершения: ${describeCompletionSource(summary.completion_source)}. ${describeFlags(summary)}.`,
      }];
    }
    return [];
  }
</script>

<div class="history-layout">
  <section class="ui-card filters-panel">
    <div class="filters-grid period-grid">
      <label>
        <span>Период</span>
        <select bind:value={filters.periodPreset} on:change={(event) => updatePeriodPreset(event.currentTarget.value)}>
          <option value="today">Сегодня</option>
          <option value="shift">Текущая смена</option>
          <option value="range">Произвольный диапазон</option>
        </select>
      </label>
      <label><span>Дата от</span><input type="date" bind:value={filters.dateFrom} disabled={filters.periodPreset !== 'range'} /></label>
      <label><span>Дата до</span><input type="date" bind:value={filters.dateTo} disabled={filters.periodPreset !== 'range'} /></label>
      <label><span>Кран</span><input type="number" min="1" bind:value={filters.tapId} placeholder="1" /></label>
      <label>
        <span>Статус</span>
        <select bind:value={filters.status}>
          <option value="">Все</option>
          <option value="active">Активна</option>
          <option value="closed">Завершена</option>
          <option value="aborted">Прервана</option>
        </select>
      </label>
      <label><span>Карта</span><input bind:value={filters.cardUid} placeholder="UID карты" /></label>
      <label class="checkbox"><input type="checkbox" bind:checked={filters.incidentOnly} /> Только с инцидентами</label>
      <label class="checkbox"><input type="checkbox" bind:checked={filters.unsyncedOnly} /> Только с несинхронизированными данными</label>
      <label class="checkbox"><input type="checkbox" bind:checked={filters.zeroVolumeAbortOnly} /> Только нулевые прерывания без налива</label>
    </div>
    <div class="actions"><button on:click={applyFilters}>Применить</button><button class="secondary" on:click={resetFilters}>Сбросить</button></div>
  </section>

  <div class="content-grid">
    <section class="ui-card list-panel">
      <div class="list-head">
        <div>
          <h2>Журнал сессий</h2>
          <p>Текущие и завершённые сессии в операторском представлении.</p>
        </div>
        <button on:click={applyFilters} disabled={$visitStore.historyLoading}>Обновить</button>
      </div>
      {#if focusContextText}
        <div class="focus-banner">{focusContextText}</div>
      {/if}
      {#if filteredItems.length === 0}
        <p class="muted">Нет сессий по выбранным фильтрам.</p>
      {:else}
        <div class="session-list">
          {#each filteredItems as item}
            <button class:selected={String(item.visit_id) === String(focusVisitId)} class="session-item" on:click={() => openDetail(item)}>
              <div class="row top"><strong>{item.guest_full_name}</strong><span>{item.operator_status}</span></div>
              <div class="row"><span>Карта: {item.card_uid || '—'}</span><span>Кран: {item.taps?.length ? item.taps.join(', ') : '—'}</span></div>
              <div class="row"><span>Открыта: {formatDateTimeRu(item.opened_at)}</span><span>Последнее событие: {formatDateTimeRu(item.last_event_at)}</span></div>
              <div class="chips">
                <span>{syncLabels[item.sync_state] || item.sync_state}</span>
                {#if item.completion_source}<span>Источник завершения: {describeCompletionSource(item.completion_source)}</span>{/if}
                {#if item.contains_tail_pour}<span>Есть долив хвоста</span>{/if}
                {#if item.contains_non_sale_flow}<span>Есть служебный налив</span>{/if}
                {#if item.has_incident}<span>Инциденты: {item.incident_count}</span>{/if}
                {#if isZeroVolumeAbort(item)}<span>Прервана без налива</span>{/if}
              </div>
            </button>
          {/each}
        </div>
      {/if}
    </section>

    {#if detail}
      <aside class="ui-card drawer">
        <div class="drawer-head">
          <div>
            <div class="eyebrow">Детали сессии</div>
            <h2>{detail.summary.guest_full_name}</h2>
            <p>{detail.summary.card_uid || 'Без карты'} · {detail.summary.operator_status}</p>
          </div>
          <button on:click={closeDetail}>✕</button>
        </div>

        <section class="summary-section">
          <h3>Что произошло</h3>
          {#each buildWhatHappened(detail.summary) as sentence}
            <p>{sentence}</p>
          {/each}
        </section>

        <section class="stats-grid">
          <article><span>Источник завершения</span><strong>{describeCompletionSource(detail.summary.completion_source)}</strong></article>
          <article><span>Синхронизация</span><strong>{syncLabels[detail.summary.sync_state] || detail.summary.sync_state}</strong></article>
          <article><span>Флаги</span><strong>{describeFlags(detail.summary)}</strong></article>
        </section>

        <section class="timeline-section">
          <h3>Lifecycle timestamps</h3>
          <dl>
            <div><dt>Открытие</dt><dd>{formatDateTimeRu(detail.summary.lifecycle.opened_at)}</dd></div>
            <div><dt>Авторизация</dt><dd>{formatDateTimeRu(detail.summary.lifecycle.first_authorized_at)}</dd></div>
            <div><dt>Старт налива</dt><dd>{formatDateTimeRu(detail.summary.lifecycle.first_pour_started_at)}</dd></div>
            <div><dt>Последний налив завершён</dt><dd>{formatDateTimeRu(detail.summary.lifecycle.last_pour_ended_at)}</dd></div>
            <div><dt>Последняя синхронизация</dt><dd>{formatDateTimeRu(detail.summary.lifecycle.last_sync_at)}</dd></div>
            <div><dt>Закрытие / прерывание</dt><dd>{formatDateTimeRu(detail.summary.lifecycle.closed_at)}</dd></div>
          </dl>
        </section>

        <section class="timeline-section">
          <h3>Ход сессии</h3>
          <ul class="timeline">
            {#each detailNarrativeGroups.timeline as event}
              <li>
                <div class="time">{formatDateTimeRu(event.timestamp)}</div>
                <div>
                  <strong>{event.title}</strong>
                  <p>{event.description}</p>
                  {#if event.status}<small>{narrativeKindLabels[event.kind] || event.kind} · {event.status}</small>{/if}
                </div>
              </li>
            {/each}
          </ul>
        </section>

        <section class="timeline-section">
          <h3>Что увидел оператор</h3>
          {#if detailNarrativeGroups.operatorObservations.length}
            <ul class="timeline compact">
              {#each detailNarrativeGroups.operatorObservations as observation}
                <li><div class="time">Контекст</div><div><strong>{observation.title}</strong><p>{observation.description}</p></div></li>
              {/each}
            </ul>
          {:else}
            <p class="muted">Дополнительных операторских наблюдений backend не передал.</p>
          {/if}
        </section>

        <section class="timeline-section">
          <h3>Какие действия были предприняты</h3>
          {#if detailOperatorActions.length}
            <ul class="timeline compact">
              {#each detailOperatorActions as action}
                <li><div class="time">{formatDateTimeRu(action.timestamp)}</div><div><strong>{action.label}</strong><p>{action.details || 'Без дополнительного комментария'}</p></div></li>
              {/each}
            </ul>
          {:else}
            <p class="muted">Явных вмешательств оператора не было.</p>
          {/if}
        </section>
      </aside>
    {/if}
  </div>
</div>

<style>
  .history-layout, .filters-panel, .list-panel, .drawer, .timeline-section, .summary-section { display: grid; gap: 1rem; }
  .content-grid { display: grid; grid-template-columns: minmax(360px, 520px) minmax(420px, 1fr); gap: 1rem; align-items: start; }
  .filters-grid { display: grid; grid-template-columns: repeat(4, minmax(120px, 1fr)); gap: 0.75rem; }
  .period-grid { align-items: end; }
  label { display: grid; gap: 0.35rem; font-size: 0.92rem; }
  input, select, button { font: inherit; }
  input, select { border: 1px solid #cbd5e1; border-radius: 10px; padding: 0.65rem 0.8rem; }
  .checkbox { align-self: end; display: flex; gap: 0.5rem; align-items: center; }
  .actions, .list-head, .drawer-head, .row, .timeline li, dl div, .stats-grid { display: flex; gap: 0.75rem; }
  .actions, .list-head, .drawer-head, .row, .timeline li, dl div { justify-content: space-between; }
  .session-list, .timeline { display: grid; gap: 0.75rem; }
  .session-item, .actions button, .drawer-head button { border: 1px solid #cbd5e1; border-radius: 14px; background: #fff; padding: 0.9rem; text-align: left; }
  .session-item.selected, .focus-banner { border-color: #2563eb; background: #eff6ff; }
  .focus-banner { border: 1px solid #bfdbfe; border-radius: 12px; padding: 0.85rem 1rem; color: #1d4ed8; }
  .session-item .top { align-items: center; }
  .chips { display: flex; gap: 0.4rem; flex-wrap: wrap; margin-top: 0.5rem; }
  .chips span, .eyebrow, .muted, small, dt { color: var(--text-secondary, #64748b); }
  .chips span { background: #f1f5f9; border-radius: 999px; padding: 0.2rem 0.55rem; }
  .drawer { position: sticky; top: 0; max-height: 85vh; overflow: auto; }
  .stats-grid { flex-wrap: wrap; }
  .stats-grid article, .summary-section { border: 1px solid #e2e8f0; border-radius: 12px; padding: 0.75rem; }
  .stats-grid article { flex: 1 1 160px; display: grid; gap: 0.35rem; }
  .timeline { list-style: none; padding: 0; margin: 0; }
  .timeline li { align-items: flex-start; border: 1px solid #e2e8f0; border-radius: 12px; padding: 0.75rem; }
  .timeline p, .drawer-head h2, .drawer-head p, .list-head h2, .list-head p, .summary-section p { margin: 0; }
  .time { min-width: 132px; color: var(--text-secondary, #64748b); font-size: 0.85rem; }
  dl { display: grid; gap: 0.5rem; margin: 0; }
  @media (max-width: 1100px) { .content-grid { grid-template-columns: 1fr; } .filters-grid { grid-template-columns: repeat(2, minmax(120px, 1fr)); } }
</style>
