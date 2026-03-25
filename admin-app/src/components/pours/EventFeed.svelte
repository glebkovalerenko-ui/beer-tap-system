<script>
  import {
    formatDurationRu,
    formatRubAmount,
    formatTimeRu,
    formatVolumeRu,
  } from '../../lib/formatters.js';

  export let items = [];
  export let title = 'Живая лента событий';
  export let emptyMessage = 'Нет недавних событий для отображения.';
  export let onOpenTap = () => {};
  export let onOpenSession = () => {};
  export let onDismiss = () => {};

  function eventKey(item, index) {
    return item?.item_id || item?.id || `${item?.item_type || 'event'}-${item?.eventAt || item?.timestamp || item?.poured_at || index}`;
  }

  function tapLabel(item) {
    return item?.tap_name || `Кран #${item?.tap_id ?? '—'}`;
  }

  function titleFor(item) {
    if (item?.headline) return item.headline;

    if (item?.item_type === 'pour') {
      if (item?.guest) {
        return `${item.guest.first_name} ${item.guest.last_name}`;
      }
      return tapLabel(item);
    }

    if (item?.session_state === 'authorized_session') {
      return `${tapLabel(item)} · активный налив`;
    }
    if (item?.card_present) {
      return `${tapLabel(item)} · пролив при закрытом клапане`;
    }
    return `${tapLabel(item)} · пролив без карты`;
  }

  function statusFor(item) {
    if (item?.badgeLabel) return item.badgeLabel;
    if (item?.item_type === 'pour') {
      return item?.status === 'rejected' ? 'отклонён' : 'завершён';
    }
    if (item?.event_status === 'stopped') {
      return 'остановлен';
    }
    return 'идёт';
  }

  function detailFor(item) {
    if (item?.detail) return item.detail;

    if (item?.item_type === 'pour') {
      const beverage = item?.beverage_name || 'напиток';
      return `налито ${formatVolumeRu(item?.volume_ml)} ${beverage}${item?.duration_ms != null ? `, длительность ${formatDurationRu(item.duration_ms)}` : ''}`;
    }

    const parts = [`${statusFor(item)} ${formatVolumeRu(item?.volume_ml)}`];
    if (item?.duration_ms != null) {
      parts.push(`длительность ${formatDurationRu(item.duration_ms)}`);
    }
    if (item?.reason === 'flow_detected_when_valve_closed_without_active_session') {
      parts.push('клапан закрыт, активного визита нет');
    } else if (item?.reason === 'authorized_pour_in_progress') {
      parts.push('контроллер подтверждает активный налив');
    }
    return parts.join(', ');
  }

  function metricFor(item) {
    if (item?.metric) return item.metric;
    if (item?.item_type === 'pour' && item?.amount_charged != null) {
      return `-${formatRubAmount(item.amount_charged)}`;
    }
    return null;
  }

  function severityFor(item) {
    return item?.severity || (item?.item_type === 'flow_event' && item?.event_status !== 'stopped' ? 'info' : 'neutral');
  }

  function visitLabel(item) {
    return item?.visit_id ? `Визит #${item.visit_id}` : 'Открыть визит';
  }

  function timeFor(item) {
    return formatTimeRu(item?.eventAt || item?.ended_at || item?.timestamp || item?.poured_at);
  }
</script>

<div class="event-feed">
  <div class="header">
    <h4>{title}</h4>
  </div>
  <div class="feed-body">
    {#if items.length > 0}
      <ul>
        {#each items as item, index (eventKey(item, index))}
          <li class={`feed-item severity-${severityFor(item)}`}>
            <div class="time">{timeFor(item)}</div>
            <div class="info">
              <div class="headline-row">
                <span class={`severity-chip severity-${severityFor(item)}`}>{item.severityLabel || statusFor(item)}</span>
                {#if item.category}
                  <span class="category-chip">{item.category}</span>
                {/if}
              </div>
              <span class="guest-name">{titleFor(item)}</span>
              <span class="details">{detailFor(item)}</span>
            </div>
            <div class="meta">
              {#if metricFor(item)}
                <div class={`metric severity-${severityFor(item)}`}>{metricFor(item)}</div>
              {:else}
                <div class={`badge severity-${severityFor(item)}`}>{statusFor(item)}</div>
              {/if}
              <div class="actions">
                <button class="ghost-action" on:click={() => onOpenTap(item)}>Открыть кран</button>
                <button class="ghost-action" on:click={() => onOpenSession(item)}>{visitLabel(item)}</button>
                <button class="ghost-action subtle" on:click={() => onDismiss(item)}>Скрыть</button>
              </div>
            </div>
          </li>
        {/each}
      </ul>
    {:else}
      <p class="no-pours-message">{emptyMessage}</p>
    {/if}
  </div>
</div>

<style>
  .event-feed {
    border: 1px solid var(--border-soft, #dfe6f2);
    border-radius: 14px;
    background-color: #fff;
    height: 100%;
    display: flex;
    flex-direction: column;
  }

  .header {
    padding: 0.85rem 1rem;
    border-bottom: 1px solid var(--border-soft, #dfe6f2);
  }

  .header h4 {
    margin: 0;
    font-size: 1.05rem;
  }

  .feed-body {
    padding: 0.5rem;
    overflow-y: auto;
    flex-grow: 1;
  }

  ul {
    list-style-type: none;
    padding: 0;
    margin: 0;
  }

  .feed-item {
    display: grid;
    grid-template-columns: 72px minmax(0, 1fr) auto;
    gap: 1rem;
    align-items: start;
    padding: 0.85rem 0.6rem;
    border-bottom: 1px solid #f1f5f9;
    border-radius: 12px;
  }

  .feed-item:last-child {
    border-bottom: none;
  }

  .feed-item.severity-critical {
    background: var(--state-critical-bg);
  }

  .feed-item.severity-warning {
    background: var(--state-warning-bg);
  }

  .feed-item.severity-info {
    background: rgba(239, 246, 255, 0.92);
  }

  .time {
    font-weight: 600;
    color: #334155;
    font-size: 0.9rem;
  }

  .info {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    min-width: 0;
  }

  .headline-row {
    display: flex;
    gap: 0.45rem;
    flex-wrap: wrap;
    align-items: center;
  }

  .severity-chip,
  .category-chip,
  .badge {
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    padding: 0.28rem 0.65rem;
    font-size: 0.78rem;
    font-weight: 700;
  }

  .severity-chip.severity-critical,
  .metric.severity-critical,
  .badge.severity-critical {
    background: rgba(190, 24, 93, 0.12);
    color: #9f1239;
  }

  .severity-chip.severity-warning,
  .metric.severity-warning,
  .badge.severity-warning {
    background: rgba(245, 158, 11, 0.14);
    color: #8a5a00;
  }

  .severity-chip.severity-info,
  .metric.severity-info,
  .badge.severity-info {
    background: rgba(29, 78, 216, 0.1);
    color: #1d4ed8;
  }

  .category-chip,
  .badge.severity-neutral {
    background: #eef2ff;
    color: #3447a3;
  }

  .guest-name {
    font-weight: 700;
  }

  .details,
  .no-pours-message {
    color: var(--text-secondary, #64748b);
  }

  .meta {
    display: grid;
    gap: 0.5rem;
    justify-items: end;
  }

  .metric {
    font-weight: 700;
  }

  .actions {
    display: flex;
    gap: 0.4rem;
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .ghost-action {
    border: 1px solid #d7e2f1;
    border-radius: 999px;
    background: #fff;
    color: #23416b;
    padding: 0.35rem 0.75rem;
  }

  .ghost-action.subtle {
    color: var(--text-secondary);
  }

  @media (max-width: 960px) {
    .feed-item {
      grid-template-columns: 1fr;
    }

    .meta,
    .actions {
      justify-items: start;
      justify-content: flex-start;
    }
  }
</style>
