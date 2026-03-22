<script>
  // @ts-nocheck
  import { onMount } from 'svelte';
  import { visitStore } from '../../stores/visitStore.js';
  import { formatDateTimeRu, formatRubAmount, formatVolumeRu } from '../../lib/formatters.js';

  let filters = {
    dateFrom: '',
    dateTo: '',
    tapId: '',
    status: '',
    cardUid: '',
    incidentOnly: false,
    unsyncedOnly: false,
  };

  $: items = $visitStore.sessionHistory || [];
  $: detail = $visitStore.sessionHistoryDetail;

  onMount(() => {
    const presetCardUid = sessionStorage.getItem('sessions.history.cardUid');
    if (presetCardUid) {
      sessionStorage.removeItem('sessions.history.cardUid');
      filters = { ...filters, cardUid: presetCardUid };
    }
    const presetTapId = sessionStorage.getItem('sessions.history.tapId');
    if (presetTapId) {
      sessionStorage.removeItem('sessions.history.tapId');
      filters = { ...filters, tapId: presetTapId };
    }
    visitStore.fetchSessionHistory(filters).catch(() => {});
  });

  const syncLabels = {
    pending_sync: 'Ожидает sync',
    rejected: 'Sync отклонён',
    reconciled: 'Сверено вручную',
    synced: 'Синхронизировано',
    not_started: 'Без наливов',
  };

  function applyFilters() {
    visitStore.fetchSessionHistory(filters).catch(() => {});
  }

  function resetFilters() {
    filters = { dateFrom: '', dateTo: '', tapId: '', status: '', cardUid: '', incidentOnly: false, unsyncedOnly: false };
    applyFilters();
  }

  function openDetail(item) {
    visitStore.fetchSessionHistoryDetail(item.visit_id).catch(() => {});
  }

  function closeDetail() {
    visitStore.clearSessionHistoryDetail();
  }
</script>

<div class="history-layout">
  <section class="ui-card filters-panel">
    <div class="filters-grid">
      <label><span>Дата от</span><input type="date" bind:value={filters.dateFrom} /></label>
      <label><span>Дата до</span><input type="date" bind:value={filters.dateTo} /></label>
      <label><span>Tap</span><input type="number" min="1" bind:value={filters.tapId} placeholder="1" /></label>
      <label>
        <span>Статус</span>
        <select bind:value={filters.status}>
          <option value="">Все</option>
          <option value="active">active</option>
          <option value="closed">closed</option>
          <option value="aborted">aborted</option>
        </select>
      </label>
      <label><span>Card UID</span><input bind:value={filters.cardUid} placeholder="UID карты" /></label>
      <label class="checkbox"><input type="checkbox" bind:checked={filters.incidentOnly} /> Только incident</label>
      <label class="checkbox"><input type="checkbox" bind:checked={filters.unsyncedOnly} /> Только unsynced</label>
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
      {#if items.length === 0}
        <p class="muted">Нет сессий по выбранным фильтрам.</p>
      {:else}
        <div class="session-list">
          {#each items as item}
            <button class="session-item" on:click={() => openDetail(item)}>
              <div class="row top"><strong>{item.guest_full_name}</strong><span>{item.operator_status}</span></div>
              <div class="row"><span>Карта: {item.card_uid || '—'}</span><span>Tap: {item.taps?.length ? item.taps.join(', ') : '—'}</span></div>
              <div class="row"><span>Открыта: {formatDateTimeRu(item.opened_at)}</span><span>Последнее событие: {formatDateTimeRu(item.last_event_at)}</span></div>
              <div class="chips">
                <span>{syncLabels[item.sync_state] || item.sync_state}</span>
                {#if item.completion_source}<span>completion: {item.completion_source}</span>{/if}
                {#if item.contains_tail_pour}<span>tail</span>{/if}
                {#if item.contains_non_sale_flow}<span>non-sale</span>{/if}
                {#if item.has_incident}<span>{item.incident_count} incident</span>{/if}
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
            <div class="eyebrow">Session detail</div>
            <h2>{detail.summary.guest_full_name}</h2>
            <p>{detail.summary.card_uid || 'Без карты'} · {detail.summary.operator_status}</p>
          </div>
          <button on:click={closeDetail}>✕</button>
        </div>

        <section class="stats-grid">
          <article><span>Completion source</span><strong>{detail.summary.completion_source || '—'}</strong></article>
          <article><span>Sync state</span><strong>{syncLabels[detail.summary.sync_state] || detail.summary.sync_state}</strong></article>
          <article><span>Flags</span><strong>{detail.summary.contains_tail_pour ? 'tail ' : ''}{detail.summary.contains_non_sale_flow ? 'non-sale' : '—'}</strong></article>
        </section>

        <section class="timeline-section">
          <h3>Lifecycle timestamps</h3>
          <dl>
            <div><dt>Open</dt><dd>{formatDateTimeRu(detail.summary.lifecycle.opened_at)}</dd></div>
            <div><dt>Authorize</dt><dd>{formatDateTimeRu(detail.summary.lifecycle.first_authorized_at)}</dd></div>
            <div><dt>Pour start</dt><dd>{formatDateTimeRu(detail.summary.lifecycle.first_pour_started_at)}</dd></div>
            <div><dt>Last pour end</dt><dd>{formatDateTimeRu(detail.summary.lifecycle.last_pour_ended_at)}</dd></div>
            <div><dt>Sync result</dt><dd>{formatDateTimeRu(detail.summary.lifecycle.last_sync_at)}</dd></div>
            <div><dt>Close / abort</dt><dd>{formatDateTimeRu(detail.summary.lifecycle.closed_at)}</dd></div>
          </dl>
        </section>

        <section class="timeline-section">
          <h3>Operator narrative</h3>
          <ul class="timeline">
            {#each detail.narrative as event}
              <li>
                <div class="time">{formatDateTimeRu(event.timestamp)}</div>
                <div>
                  <strong>{event.title}</strong>
                  <p>{event.description}</p>
                  {#if event.status}<small>{event.kind} · {event.status}</small>{/if}
                </div>
              </li>
            {/each}
          </ul>
        </section>

        <section class="timeline-section">
          <h3>Operator actions</h3>
          {#if detail.summary.operator_actions.length}
            <ul class="timeline compact">
              {#each detail.summary.operator_actions as action}
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
  .history-layout, .filters-panel, .list-panel, .drawer, .timeline-section { display: grid; gap: 1rem; }
  .content-grid { display: grid; grid-template-columns: minmax(360px, 520px) minmax(420px, 1fr); gap: 1rem; align-items: start; }
  .filters-grid { display: grid; grid-template-columns: repeat(4, minmax(120px, 1fr)); gap: 0.75rem; }
  label { display: grid; gap: 0.35rem; font-size: 0.92rem; }
  input, select, button { font: inherit; }
  input, select { border: 1px solid #cbd5e1; border-radius: 10px; padding: 0.65rem 0.8rem; }
  .checkbox { align-self: end; display: flex; gap: 0.5rem; align-items: center; }
  .actions, .list-head, .drawer-head, .row, .timeline li, dl div, .stats-grid { display: flex; gap: 0.75rem; }
  .actions, .list-head, .drawer-head, .row, .timeline li, dl div { justify-content: space-between; }
  .session-list, .timeline { display: grid; gap: 0.75rem; }
  .session-item, .actions button, .drawer-head button { border: 1px solid #cbd5e1; border-radius: 14px; background: #fff; padding: 0.9rem; text-align: left; }
  .session-item .top { align-items: center; }
  .chips { display: flex; gap: 0.4rem; flex-wrap: wrap; margin-top: 0.5rem; }
  .chips span, .eyebrow, .muted, small, dt { color: var(--text-secondary, #64748b); }
  .chips span { background: #f1f5f9; border-radius: 999px; padding: 0.2rem 0.55rem; }
  .drawer { position: sticky; top: 0; max-height: 85vh; overflow: auto; }
  .stats-grid { flex-wrap: wrap; }
  .stats-grid article { flex: 1 1 160px; border: 1px solid #e2e8f0; border-radius: 12px; padding: 0.75rem; display: grid; gap: 0.35rem; }
  .timeline { list-style: none; padding: 0; margin: 0; }
  .timeline li { align-items: flex-start; border: 1px solid #e2e8f0; border-radius: 12px; padding: 0.75rem; }
  .timeline p, .drawer-head h2, .drawer-head p, .list-head h2, .list-head p { margin: 0; }
  .time { min-width: 132px; color: var(--text-secondary, #64748b); font-size: 0.85rem; }
  dl { display: grid; gap: 0.5rem; margin: 0; }
  @media (max-width: 1100px) { .content-grid { grid-template-columns: 1fr; } .filters-grid { grid-template-columns: repeat(2, minmax(120px, 1fr)); } }
</style>
