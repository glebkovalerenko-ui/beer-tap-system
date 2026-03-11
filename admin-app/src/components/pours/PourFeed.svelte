<!-- src/components/pours/PourFeed.svelte -->
<script>
  import {
    formatDurationRu,
    formatRubAmount,
    formatTimeRu,
    formatVolumeRu,
  } from '../../lib/formatters.js';

  export let items = [];

  function tapLabel(item) {
    return item.tap_name || `Кран #${item.tap_id}`;
  }

  function titleFor(item) {
    if (item.item_type === 'pour') {
      if (item.guest) {
        return `${item.guest.first_name} ${item.guest.last_name}`;
      }
      return tapLabel(item);
    }

    if (item.session_state === 'authorized_session') {
      return `${tapLabel(item)} • активный налив`;
    }
    if (item.card_present) {
      return `${tapLabel(item)} • flow при закрытом клапане`;
    }
    return `${tapLabel(item)} • flow без карты`;
  }

  function statusFor(item) {
    if (item.item_type === 'pour') {
      return item.status === 'rejected' ? 'отклонён' : 'завершён';
    }
    if (item.event_status === 'stopped') {
      return 'остановлен';
    }
    return 'идёт';
  }

  function detailsFor(item) {
    if (item.item_type === 'pour') {
      const beverage = item.beverage_name || 'напиток';
      return `налил ${formatVolumeRu(item.volume_ml)} ${beverage}${item.duration_ms != null ? `, длительность ${formatDurationRu(item.duration_ms)}` : ''}`;
    }

    const parts = [`${statusFor(item)} ${formatVolumeRu(item.volume_ml)}`];
    if (item.duration_ms != null) {
      parts.push(`длительность ${formatDurationRu(item.duration_ms)}`);
    }
    if (item.reason === 'flow_detected_when_valve_closed_without_active_session') {
      parts.push('клапан закрыт, активной сессии нет');
    } else if (item.reason === 'authorized_pour_in_progress') {
      parts.push('данные идут с контроллера');
    }
    return parts.join(', ');
  }
</script>

<div class="pour-feed">
  <div class="header">
    <h4>Живая лента</h4>
  </div>
  <div class="feed-body">
    {#if items.length > 0}
      <ul>
        {#each items as item (item.item_id)}
          <li class:live={item.item_type === 'flow_event' && item.event_status !== 'stopped'}>
            <div class="time">{formatTimeRu(item.ended_at || item.timestamp)}</div>
            <div class="info">
              <span class="guest-name">{titleFor(item)}</span>
              <span class="details">{detailsFor(item)}</span>
            </div>
            {#if item.item_type === 'pour' && item.amount_charged != null}
              <div class="amount">-{formatRubAmount(item.amount_charged)}</div>
            {:else}
              <div class="badge">{statusFor(item)}</div>
            {/if}
          </li>
        {/each}
      </ul>
    {:else}
      <p class="no-pours-message">Нет недавних наливов для отображения.</p>
    {/if}
  </div>
</div>

<style>
  .pour-feed {
    border: 1px solid #eee;
    border-radius: 8px;
    background-color: #fff;
    height: 100%;
    display: flex;
    flex-direction: column;
  }
  .header {
    padding: 0.75rem 1rem;
    border-bottom: 1px solid #eee;
  }
  .header h4 {
    margin: 0;
    font-size: 1.1rem;
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
  li {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.75rem 0.5rem;
    border-bottom: 1px solid #f5f5f5;
  }
  li.live {
    background: rgba(198, 31, 53, 0.06);
  }
  li:last-child {
    border-bottom: none;
  }
  .time {
    font-weight: 500;
    color: #333;
    font-size: 0.9rem;
    width: 60px;
  }
  .info {
    display: flex;
    flex-direction: column;
    flex-grow: 1;
  }
  .guest-name {
    font-weight: 500;
  }
  .details {
    font-size: 0.85rem;
    color: #666;
  }
  .amount {
    font-weight: bold;
    color: #dc3545;
    font-size: 1rem;
  }
  .badge {
    font-size: 0.8rem;
    font-weight: 700;
    text-transform: uppercase;
    color: #9a1c2f;
  }
  .no-pours-message {
    text-align: center;
    color: #888;
    padding: 2rem;
  }
</style>
