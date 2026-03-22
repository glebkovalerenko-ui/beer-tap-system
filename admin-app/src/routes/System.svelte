<script>
  import Dashboard from './Dashboard.svelte';
  import { roleStore } from '../stores/roleStore.js';
</script>

{#if !$roleStore.permissions.system}
  <section class="ui-card restricted">
    <h1>System</h1>
    <p>Раздел настроек и инженерных инструментов доступен только роли engineer_owner.</p>
  </section>
{:else}
  <Dashboard systemMode={true} />
{/if}

<style>
  .restricted { padding: 1rem; }
</style>
