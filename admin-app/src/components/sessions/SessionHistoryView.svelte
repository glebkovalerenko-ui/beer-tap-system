<script>
  // @ts-nocheck
  import { onMount } from 'svelte';
  import { get } from 'svelte/store';
  import { visitStore } from '../../stores/visitStore.js';
  import { shiftStore } from '../../stores/shiftStore.js';
  import { formatDateTimeRu } from '../../lib/formatters.js';
  import { SESSION_COPY } from '../../lib/operatorLabels.js';

  const DEFAULT_FILTERS = {
    periodPreset: 'today',
    dateFrom: '',
    dateTo: '',
    tapId: '',
    status: '',
    cardUid: '',
    completionSource: '',
    incidentOnly: false,
    unsyncedOnly: false,
    zeroVolumeAbortOnly: false,
    activeOnly: false,
  };

  let filters = { ...DEFAULT_FILTERS };
  let focusVisitId = '';
  let focusTapId = '';
  let focusResolved = false;
  let selectedVisitId = '';

  const syncLabels = {
    pending_sync: 'Ожидает синхронизации',
    rejected: 'Синхронизация отклонена',
    reconciled: 'Сверено вручную',
    synced: 'Синхронизировано',
    not_started: 'Наливов не было',
  };

  const completionSourceLabels = {
    normal: 'Обычное завершение',
    card_removed: 'Карта извлечена',
    timeout: 'Таймаут / автоостановка',
    blocked: 'Заблокировано',
    denied: 'Отказано',
    no_sale_flow: 'Служебный налив без продажи',
    guest_checkout: 'Обычное завершение: расчёт гостя',
    checkout: 'Обычное завершение: расчёт',
    demo_checkout: 'Обычное завершение: демонстрационный расчёт',
    operator_close: 'Обычное завершение: оператор закрыл сессию',
    manual_close: 'Обычное завершение: ручное закрытие',
    card_removed_close: 'Завершена после извлечения карты',
    controller_timeout: 'Таймаут контроллера',
    sync_timeout: 'Таймаут синхронизации',
    timeout_close: 'Завершена по таймауту',
    blocked_lost_card: 'Заблокировано: карта помечена как потерянная',
    blocked_insufficient_funds: 'Заблокировано: недостаточно средств',
    blocked_card_in_use: 'Заблокировано: карта уже занята на другом кране',
    denied_insufficient_funds: 'Отказано: недостаточно средств',
    sync_pending: 'Ожидает синхронизации',
    system: 'Системное завершение',
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

  $: activeItems = ($visitStore.activeVisits || []).map((item) => normalizeVisit(item, 'active'));
  $: historyItems = ($visitStore.sessionHistory || []).map((item) => normalizeVisit(item, 'history'));
  $: mergedItems = mergeVisits(activeItems, historyItems);
  $: filteredItems = mergedItems.filter(matchesFilters);
  $: pinnedActiveItems = filteredItems.filter((item) => item.isActive);
  $: journalItems = filters.activeOnly ? pinnedActiveItems : filteredItems.filter((item) => !item.isActive);
  $: detail = $visitStore.sessionHistoryDetail;
  $: focusContextText = focusVisitId
    ? `Открываем сессию ${focusVisitId} в общем журнале.`
    : focusTapId
      ? `Журнал сфокусирован на кране ${focusTapId}.`
      : '';
  $: detailNarrativeGroups = detail ? groupedNarrative(detail) : { timeline: [], operatorObservations: [], lifecycleCards: [] };
  $: detailOperatorActions = detail ? normalizedOperatorActions(detail.summary) : [];
  $: if (focusVisitId && !focusResolved && !$visitStore.historyLoading && (!$visitStore.loading || activeItems.length > 0 || historyItems.length > 0)) {
    resolveFocusVisit();
  }

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

  function normalizeVisit(item, source) {
    const lifecycle = item.lifecycle || {};
    const isActive = source === 'active' || item.status === 'active' || item.visit_status === 'active' || item.operator_status === 'Активна';
    return {
      ...item,
      source,
      isActive,
      lifecycle,
      opened_at: item.opened_at || lifecycle.opened_at || null,
      last_event_at: item.last_event_at || lifecycle.last_event_at || lifecycle.last_pour_ended_at || item.updated_at || null,
      guest_full_name: item.guest_full_name || 'Гость без имени',
      operator_status: item.operator_status || (isActive ? 'Активна' : item.status || 'Неизвестно'),
      visit_status: item.visit_status || item.status || (isActive ? 'active' : null),
      taps: item.taps || (item.active_tap_id ? [String(item.active_tap_id)] : []),
      sync_state: item.sync_state || (isActive ? 'pending_sync' : 'not_started'),
      completion_source: item.completion_source ?? (isActive ? null : null),
      contains_tail_pour: Boolean(item.contains_tail_pour),
      contains_non_sale_flow: Boolean(item.contains_non_sale_flow),
      has_incident: Boolean(item.has_incident),
      has_unsynced: Boolean(item.has_unsynced),
      incident_count: item.incident_count || 0,
      card_uid: item.card_uid || '',
    };
  }

  function mergeVisits(active = [], history = []) {
    const map = new Map();
    for (const item of history) map.set(String(item.visit_id), item);
    for (const item of active) map.set(String(item.visit_id), { ...map.get(String(item.visit_id)), ...item, isActive: true, source: 'active' });
    return Array.from(map.values()).sort((a, b) => {
      if (a.isActive !== b.isActive) return a.isActive ? -1 : 1;
      return new Date(b.last_event_at || b.opened_at || 0).getTime() - new Date(a.last_event_at || a.opened_at || 0).getTime();
    });
  }

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

  function formatMaybeDate(value) {
    return value ? formatDateTimeRu(value) : '—';
  }

  function normalizeCompletionSource(item) {
    const raw = String(item?.completion_source || '').trim().toLowerCase();
    const actions = (item?.operator_actions || []).map((action) => String(action.action || '').toLowerCase());

    if (item?.contains_non_sale_flow) return 'no_sale_flow';
    if (raw === 'card_removed' || raw === 'card_removed_close' || raw.includes('card_removed')) return 'card_removed';
    if (raw === 'timeout' || raw === 'timeout_close' || raw.endsWith('_timeout') || raw.includes('timeout')) return 'timeout';
    if (
      raw.startsWith('blocked_')
      || actions.some((action) => ['lost_card_blocked', 'insufficient_funds_blocked', 'card_in_use_on_other_tap'].includes(action))
    ) return 'blocked';
    if (
      raw.startsWith('denied_')
      || actions.some((action) => ['insufficient_funds_denied'].includes(action))
    ) return 'denied';
    if (raw === 'sync_pending' && item?.has_unsynced) return 'timeout';
    if (raw) return 'normal';
    if (item?.operator_status === 'Прервана') return 'blocked';
    return item?.isActive ? '' : 'normal';
  }

  function describeCompletionSource(value) {
    if (!value) return 'Не указан';
    return completionSourceLabels[value] || value.replaceAll('_', ' ');
  }

  function describeCompletionSourceDetails(item) {
    const normalized = normalizeCompletionSource(item);
    const raw = String(item?.completion_source || '').trim();
    if (!normalized && !raw) return 'Не указан';
    if (raw && raw !== normalized) return `${describeCompletionSource(normalized)} · ${describeCompletionSource(raw.toLowerCase())}`;
    return describeCompletionSource(raw || normalized);
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

  function matchesText(item, query) {
    const normalized = String(query || '').trim().toLowerCase();
    if (!normalized) return true;
    return [item.card_uid, item.visit_id, item.guest_full_name]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(normalized));
  }

  function matchesStatus(item) {
    if (!filters.status) return true;
    if (filters.status === 'active') return item.isActive;
    if (filters.status === 'closed') return !item.isActive && item.operator_status !== 'Прервана';
    if (filters.status === 'aborted') return item.operator_status === 'Прервана';
    return true;
  }

  function matchesFilters(item) {
    if (filters.tapId) {
      const tapNeedle = String(filters.tapId).trim();
      const taps = (item.taps || []).map((tap) => String(tap));
      if (!taps.includes(tapNeedle)) return false;
    }
    if (!matchesStatus(item)) return false;
    if (!matchesText(item, filters.cardUid)) return false;
    if (filters.completionSource && normalizeCompletionSource(item) !== filters.completionSource) return false;
    if (filters.incidentOnly && !item.has_incident) return false;
    if (filters.unsyncedOnly && !item.has_unsynced) return false;
    if (filters.zeroVolumeAbortOnly && !isZeroVolumeAbort(item)) return false;
    if (filters.activeOnly && !item.isActive) return false;
    return true;
  }

  async function applyFilters() {
    focusResolved = false;
    if (filters.periodPreset !== 'range') {
      filters = { ...filters, ...getPeriodBounds(filters.periodPreset) };
    }
    await Promise.all([
      visitStore.fetchActiveVisits().catch(() => {}),
      visitStore.fetchSessionHistory(filters).catch(() => {}),
    ]);
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
    const target = mergedItems.find((item) => String(item.visit_id) === String(focusVisitId));
    if (target) {
      focusResolved = true;
      await openDetail(target);
      return;
    }
    focusResolved = true;
    selectedVisitId = String(focusVisitId);
    await visitStore.fetchSessionHistoryDetail(focusVisitId).catch(() => {});
  }

  async function openDetail(item) {
    focusVisitId = String(item.visit_id);
    selectedVisitId = String(item.visit_id);
    focusResolved = true;
    await visitStore.fetchSessionHistoryDetail(item.visit_id).catch(() => {});
  }

  function closeDetail() {
    selectedVisitId = '';
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
      description: event.description || 'Подробности по событию система не передала.',
    }));
    const operatorObservations = [];
    if (detailPayload.summary.has_incident) operatorObservations.push({ title: 'В сессии были инциденты', description: `Количество инцидентов: ${detailPayload.summary.incident_count || 1}.` });
    if (detailPayload.summary.contains_tail_pour) operatorObservations.push({ title: 'Есть долив хвоста', description: 'Сессия включает хвостовой долив и требует внимательной проверки итогов.' });
    if (detailPayload.summary.contains_non_sale_flow) operatorObservations.push({ title: 'Есть служебный налив', description: 'Часть действий прошла как служебный налив и не должна трактоваться как обычная продажа.' });
    if (detailPayload.summary.has_unsynced) operatorObservations.push({ title: 'Есть риск несинхронизированных данных', description: syncLabels[detailPayload.summary.sync_state] || detailPayload.summary.sync_state });

    const lifecycle = detailPayload.summary.lifecycle || {};
    const lifecycleCards = [
      { label: 'Старт сессии', value: formatMaybeDate(lifecycle.opened_at), note: 'Источник: открытие визита / старт workflow' },
      { label: 'Источник завершения', value: describeCompletionSource(detailPayload.summary.completion_source), note: 'Окончание сессии или причина прерывания' },
      { label: 'Синхронизация', value: syncLabels[detailPayload.summary.sync_state] || detailPayload.summary.sync_state, note: formatMaybeDate(lifecycle.last_sync_at) },
      { label: 'Хвостовой долив', value: detailPayload.summary.contains_tail_pour ? 'Да' : 'Нет', note: detailPayload.summary.contains_tail_pour ? 'Нужна проверка хвостового долива' : 'Хвостовой долив не найден' },
      { label: 'Служебный налив', value: detailPayload.summary.contains_non_sale_flow ? 'Да' : 'Нет', note: detailPayload.summary.contains_non_sale_flow ? 'Был служебный налив без продажи' : 'Служебных наливов нет' },
      { label: 'Финиш сессии', value: formatMaybeDate(lifecycle.closed_at), note: `Последний налив: ${formatMaybeDate(lifecycle.last_pour_ended_at)}` },
    ];

    return { timeline, operatorObservations, lifecycleCards };
  }

  function normalizedOperatorActions(summary) {
    if (summary.operator_actions?.length) {
      return summary.operator_actions.map((action) => ({
        ...action,
        label: action.label || actionLabels[action.action] || action.action?.replaceAll('_', ' ') || 'Действие оператора',
        details: action.details || 'Система не передала дополнительный комментарий.',
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
    <div class="filters-title">
      <div>
        <h2>Общий журнал сессий</h2>
        <p>Активные визиты закреплены сверху, а история и поиск работают в одном операторском экране.</p>
      </div>
      <button on:click={applyFilters} disabled={$visitStore.historyLoading || $visitStore.loading}>Обновить</button>
    </div>

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
      <label><span>{SESSION_COPY.cardUidVisitId}</span><input bind:value={filters.cardUid} placeholder={SESSION_COPY.cardUidVisitPlaceholder} /></label>
      <label>
        <span>{SESSION_COPY.completionReason}</span>
        <select bind:value={filters.completionSource}>
          <option value="">Все</option>
          <option value="normal">{completionSourceLabels.normal}</option>
          <option value="card_removed">{completionSourceLabels.card_removed}</option>
          <option value="timeout">{completionSourceLabels.timeout}</option>
          <option value="blocked">{completionSourceLabels.blocked}</option>
          <option value="denied">{completionSourceLabels.denied}</option>
          <option value="no_sale_flow">{completionSourceLabels.no_sale_flow}</option>
        </select>
      </label>
      <label class="checkbox"><input type="checkbox" bind:checked={filters.incidentOnly} /> Только с инцидентами</label>
      <label class="checkbox"><input type="checkbox" bind:checked={filters.unsyncedOnly} /> Только с несинхронизированными данными</label>
      <label class="checkbox"><input type="checkbox" bind:checked={filters.zeroVolumeAbortOnly} /> {SESSION_COPY.zeroVolumeAbortOnly}</label>
      <label class="checkbox"><input type="checkbox" bind:checked={filters.activeOnly} /> Только активные</label>
    </div>
    <div class="actions"><button on:click={applyFilters}>Применить</button><button class="secondary" on:click={resetFilters}>Сбросить</button></div>
  </section>

  {#if focusContextText}
    <div class="focus-banner">{focusContextText}</div>
  {/if}

  <div class="content-grid">
    <section class="list-stack">
      <section class="ui-card list-panel pinned-panel">
        <div class="list-head">
          <div>
            <h3>Активные сейчас</h3>
            <p>Закреплённый блок помогает сразу видеть, что ещё не завершено.</p>
          </div>
          <span class="counter">{pinnedActiveItems.length}</span>
        </div>

        {#if pinnedActiveItems.length === 0}
          <p class="muted">{SESSION_COPY.emptyActive}</p>
        {:else}
          <div class="session-list compact-list">
            {#each pinnedActiveItems as item}
              <button class:selected={String(item.visit_id) === String(selectedVisitId)} class="session-item pinned" on:click={() => openDetail(item)}>
                <div class="row top"><strong>{item.guest_full_name}</strong><span class="state active">Активна</span></div>
                <div class="row"><span>Карта: {item.card_uid || '—'}</span><span>Кран: {item.taps?.length ? item.taps.join(', ') : '—'}</span></div>
                <div class="row"><span>Открыта: {formatMaybeDate(item.opened_at)}</span><span>Последнее событие: {formatMaybeDate(item.last_event_at)}</span></div>
                <div class="chips">
                  <span>{syncLabels[item.sync_state] || item.sync_state}</span>
                  {#if item.has_unsynced}<span>Есть несинхронизированные данные</span>{/if}
                  {#if item.has_incident}<span>Инциденты: {item.incident_count}</span>{/if}
                </div>
              </button>
            {/each}
          </div>
        {/if}
      </section>

      <section class="ui-card list-panel">
        <div class="list-head">
          <div>
            <h3>{filters.activeOnly ? 'Отфильтрованные активные сессии' : 'История и завершённые сессии'}</h3>
            <p>{SESSION_COPY.openDetailsHint}</p>
          </div>
          <span class="counter">{journalItems.length}</span>
        </div>

        {#if journalItems.length === 0}
          <p class="muted">{SESSION_COPY.emptyList}</p>
        {:else}
          <div class="session-list">
            {#each journalItems as item}
              <button class:selected={String(item.visit_id) === String(selectedVisitId)} class="session-item" on:click={() => openDetail(item)}>
                <div class="row top">
                  <strong>{item.guest_full_name}</strong>
                  <span class:active={item.isActive} class="state">{item.operator_status}</span>
                </div>
                <div class="row meta-grid"><span>Карта: {item.card_uid || '—'}</span><span>Кран: {item.taps?.length ? item.taps.join(', ') : '—'}</span><span class="completion-pill">Источник: {describeCompletionSourceDetails(item)}</span></div>
                <div class="row"><span>Открыта: {formatMaybeDate(item.opened_at)}</span><span>Последнее событие: {formatMaybeDate(item.last_event_at)}</span></div>
                <div class="chips">
                  <span>{syncLabels[item.sync_state] || item.sync_state}</span>
                  {#if item.completion_source}<span>Код причины: {item.completion_source}</span>{/if}
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
    </section>

    <aside class="ui-card drawer" class:drawer-open={detail}>
      {#if detail}
        <div class="drawer-head">
          <div>
            <div class="eyebrow">{SESSION_COPY.detailsPanel}</div>
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
          {#each detailNarrativeGroups.lifecycleCards as card}
            <article>
              <span>{card.label}</span>
              <strong>{card.value}</strong>
              <small>{card.note}</small>
            </article>
          {/each}
        </section>

        <section class="timeline-section">
          <h3>{SESSION_COPY.lifecycleSummary}</h3>
          <dl>
            <div><dt>Открытие</dt><dd>{formatMaybeDate(detail.summary.lifecycle.opened_at)}</dd></div>
            <div><dt>Авторизация</dt><dd>{formatMaybeDate(detail.summary.lifecycle.first_authorized_at)}</dd></div>
            <div><dt>Старт налива</dt><dd>{formatMaybeDate(detail.summary.lifecycle.first_pour_started_at)}</dd></div>
            <div><dt>Последний налив завершён</dt><dd>{formatMaybeDate(detail.summary.lifecycle.last_pour_ended_at)}</dd></div>
            <div><dt>Последняя синхронизация</dt><dd>{formatMaybeDate(detail.summary.lifecycle.last_sync_at)}</dd></div>
            <div><dt>Закрытие / прерывание</dt><dd>{formatMaybeDate(detail.summary.lifecycle.closed_at)}</dd></div>
          </dl>
        </section>

        <section class="timeline-section">
          <h3>Ход сессии</h3>
          <ul class="timeline">
            {#each detailNarrativeGroups.timeline as event}
              <li>
                <div class="time">{formatMaybeDate(event.timestamp)}</div>
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
          <h3>{SESSION_COPY.operatorContext}</h3>
          {#if detailNarrativeGroups.operatorObservations.length}
            <ul class="timeline compact">
              {#each detailNarrativeGroups.operatorObservations as observation}
                <li><div class="time">Контекст</div><div><strong>{observation.title}</strong><p>{observation.description}</p></div></li>
              {/each}
            </ul>
          {:else}
            <p class="muted">Дополнительных операторских наблюдений система не передала.</p>
          {/if}
        </section>

        <section class="timeline-section">
          <h3>{SESSION_COPY.operatorActions}</h3>
          {#if detailOperatorActions.length}
            <ul class="timeline compact">
              {#each detailOperatorActions as action}
                <li><div class="time">{formatMaybeDate(action.timestamp)}</div><div><strong>{action.label}</strong><p>{action.details || 'Без дополнительного комментария'}</p></div></li>
              {/each}
            </ul>
          {:else}
            <p class="muted">Явных вмешательств оператора не было.</p>
          {/if}
        </section>
      {:else}
        <div class="empty-drawer">
          <div class="eyebrow">{SESSION_COPY.detailsPanel}</div>
          <h2>Выберите сессию</h2>
          <p>{SESSION_COPY.emptyDetailsText}</p>
        </div>
      {/if}
    </aside>
  </div>
</div>

<style>
  .history-layout, .filters-panel, .list-panel, .drawer, .timeline-section, .summary-section, .list-stack { display: grid; gap: 1rem; }
  .filters-title, .actions, .list-head, .drawer-head, .row, .timeline li, dl div, .stats-grid { display: flex; gap: 0.75rem; }
  .filters-title, .actions, .list-head, .drawer-head, .row, .timeline li, dl div { justify-content: space-between; }
  .content-grid { display: grid; grid-template-columns: minmax(320px, 1.2fr) minmax(380px, 0.9fr); gap: 1rem; align-items: start; }
  .filters-grid { display: grid; grid-template-columns: repeat(4, minmax(120px, 1fr)); gap: 0.75rem; }
  .period-grid { align-items: end; }
  label { display: grid; gap: 0.35rem; font-size: 0.92rem; }
  input, select, button { font: inherit; }
  input, select { border: 1px solid #cbd5e1; border-radius: 10px; padding: 0.65rem 0.8rem; }
  .checkbox { align-self: end; display: flex; gap: 0.5rem; align-items: center; }
  .session-list, .timeline { display: grid; gap: 0.75rem; }
  .session-item, .actions button, .drawer-head button, .filters-title button { border: 1px solid #cbd5e1; border-radius: 14px; background: #fff; padding: 0.9rem; text-align: left; }
  .session-item { transition: border-color 0.15s ease, box-shadow 0.15s ease; }
  .session-item:hover, .session-item.selected { border-color: #2563eb; box-shadow: 0 0 0 1px #bfdbfe; }
  .session-item.pinned { background: linear-gradient(180deg, #f8fbff 0%, #eff6ff 100%); }
  .focus-banner { border: 1px solid #bfdbfe; border-radius: 12px; padding: 0.85rem 1rem; color: #1d4ed8; background: #eff6ff; }
  .chips { display: flex; gap: 0.4rem; flex-wrap: wrap; margin-top: 0.5rem; }
  .chips span, .eyebrow, .muted, small, dt { color: var(--text-secondary, #64748b); }
  .chips span { background: #f1f5f9; border-radius: 999px; padding: 0.2rem 0.55rem; }
  .meta-grid { flex-wrap: wrap; }
  .completion-pill { font-weight: 600; color: #0f172a; }
  .drawer { position: sticky; top: 0; min-height: 320px; max-height: 85vh; overflow: auto; }
  .drawer-open { border-color: #bfdbfe; }
  .stats-grid { flex-wrap: wrap; }
  .stats-grid article, .summary-section, .empty-drawer { border: 1px solid #e2e8f0; border-radius: 12px; padding: 0.85rem; }
  .stats-grid article { flex: 1 1 180px; display: grid; gap: 0.35rem; }
  .timeline { list-style: none; padding: 0; margin: 0; }
  .timeline li { align-items: flex-start; border: 1px solid #e2e8f0; border-radius: 12px; padding: 0.75rem; }
  .timeline p, .drawer-head h2, .drawer-head p, .list-head h3, .list-head p, .summary-section p, .filters-title h2, .filters-title p, .empty-drawer h2, .empty-drawer p { margin: 0; }
  .time { min-width: 132px; color: var(--text-secondary, #64748b); font-size: 0.85rem; }
  .counter, .state { border-radius: 999px; padding: 0.2rem 0.65rem; background: #f1f5f9; color: #475569; }
  .state.active { background: #dcfce7; color: #166534; }
  dl { display: grid; gap: 0.5rem; margin: 0; }
  .compact-list { gap: 0.5rem; }
  @media (max-width: 1100px) {
    .content-grid { grid-template-columns: 1fr; }
    .filters-grid { grid-template-columns: repeat(2, minmax(120px, 1fr)); }
    .drawer { position: static; max-height: none; }
  }
</style>
