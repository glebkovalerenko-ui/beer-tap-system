<script>
  import SessionHistoryView from '../components/sessions/SessionHistoryView.svelte';
</script>

<section class="session-shell">
  <header class="session-header">
    <div>
      <h1>Сессии</h1>
      <p>Единый экран для активных визитов, истории, фильтров и detail panel без переключения между режимами.</p>
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
