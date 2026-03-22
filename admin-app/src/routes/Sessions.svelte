<script>
  import { onMount } from 'svelte';
  import Visits from './Visits.svelte';
  import SessionHistoryView from '../components/sessions/SessionHistoryView.svelte';

  const getHash = () => (typeof window === 'undefined' ? '#/sessions' : window.location.hash || '#/sessions');
  let hash = getHash();
  let stopListening = null;

  $: activeSubview = hash.startsWith('#/sessions/history') ? 'history' : 'active';

  onMount(() => {
    const onHashChange = () => {
      hash = getHash();
    };
    window.addEventListener('hashchange', onHashChange);
    stopListening = () => window.removeEventListener('hashchange', onHashChange);
    return stopListening;
  });

  function openSubview(next) {
    window.location.hash = next === 'history' ? '/sessions/history' : '/sessions';
  }
</script>

<section class="session-shell">
  <header class="session-header">
    <div>
      <h1>Sessions</h1>
      <p>Активные визиты остаются в текущем workflow, а история вынесена в отдельный операторский журнал.</p>
    </div>
    <div class="subnav">
      <button class:active={activeSubview === 'active'} on:click={() => openSubview('active')}>Активные визиты</button>
      <button class:active={activeSubview === 'history'} on:click={() => openSubview('history')}>Журнал сессий</button>
    </div>
  </header>

  {#if activeSubview === 'history'}
    <SessionHistoryView />
  {:else}
    <Visits />
  {/if}
</section>

<style>
  .session-shell { display: grid; gap: 1rem; }
  .session-header { display: flex; justify-content: space-between; gap: 1rem; align-items: end; flex-wrap: wrap; }
  h1, p { margin: 0; }
  p { color: var(--text-secondary, #64748b); }
  .subnav { display: flex; gap: 0.5rem; }
  .subnav button { border: 1px solid #cbd5e1; background: #fff; border-radius: 999px; padding: 0.7rem 1rem; font-weight: 700; }
  .subnav button.active { background: #0f172a; color: #fff; border-color: #0f172a; }
</style>
