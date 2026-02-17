<script>
  import { auditTrailStore } from '../../stores/auditTrailStore.js';

  function fmt(ts) {
    return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
</script>

<section class="trail ui-card">
  <h3>Журнал действий интерфейса</h3>
  {#if $auditTrailStore.length === 0}
    <p class="ui-muted">Пока событий нет.</p>
  {:else}
    <ul>
      {#each $auditTrailStore as item (item.id)}
        <li>
          <span>{fmt(item.timestamp)}</span>
          <div>
            <strong>{item.event}</strong>
            {#if item.details}<small>{item.details}</small>{/if}
          </div>
        </li>
      {/each}
    </ul>
  {/if}
</section>

<style>
  .trail { margin-top: var(--space-3); padding: var(--space-3); }
  .trail h3 { margin: 0 0 0.5rem; font-size: 0.95rem; }
  .trail ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.5rem; }
  .trail li { display: grid; grid-template-columns: 50px 1fr; gap: 0.5rem; font-size: 0.82rem; }
  .trail li span { color: var(--text-secondary); }
  .trail small { display: block; color: var(--text-secondary); }
</style>
