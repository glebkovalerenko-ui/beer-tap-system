<script>
  import SessionHistoryView from '../components/sessions/SessionHistoryView.svelte';
  import { ROUTE_COPY } from '../lib/operator/routeCopy.js';
</script>

<section class="session-shell">
  <header class="session-header">
    <div>
      <h1>{ROUTE_COPY.visits.title}</h1>
      <p>{ROUTE_COPY.visits.description}</p>
    </div>
  </header>

  <SessionHistoryView />
</section>

<style>
  .session-shell { display: grid; gap: 1rem; }
  .session-header { display: flex; justify-content: space-between; gap: 1rem; align-items: end; flex-wrap: wrap; }
  h1, p { margin: 0; }
  p { color: var(--text-secondary, #64748b); }
</style>
