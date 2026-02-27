<!-- src/components/pours/PourFeed.svelte -->
<script>
  /** @type {import('../../../../src-tauri/src/api_client').PourResponse[]} */
  export let pours = [];

  function formatTime(isoString) {
    if (!isoString) return '';
    return new Date(isoString).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  function formatDuration(durationMs) {
    if (durationMs == null) return '';
    const seconds = Math.max(0, Math.round(durationMs / 1000));
    return `${seconds}s`;
  }
</script>

<div class="pour-feed">
  <div class="header">
    <h4>Живая лента</h4>
  </div>
  <div class="feed-body">
    {#if pours.length > 0}
      <ul>
        {#each pours as pour (pour.pour_id)}
          <li>
            <div class="time">{formatTime(pour.ended_at || pour.poured_at)}</div>
            <div class="info">
              <span class="guest-name">{pour.guest.first_name} {pour.guest.last_name}</span>
              <span class="details">
                налил {pour.volume_ml}мл из {pour.beverage.name}
                {#if pour.duration_ms != null}
                  , длительность {formatDuration(pour.duration_ms)}
                {/if}
              </span>
            </div>
            <div class="amount">-${pour.amount_charged}</div>
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
  .no-pours-message {
    text-align: center;
    color: #888;
    padding: 2rem;
  }
</style>
