<script>
  import { demoModeStore } from '../../stores/demoModeStore.js';
</script>

<button
  class="toggle"
  class:active={$demoModeStore}
  on:click={() => demoModeStore.toggle()}
  aria-pressed={$demoModeStore}
>
  Demo mode: {$demoModeStore ? 'ON' : 'OFF'}
</button>

<style>
  .toggle {
    background: #eef3ff;
    color: #1f4f8f;
    border-color: #cad8f4;
  }
  .toggle.active {
    background: #dfeaff;
    color: #173f75;
  }
</style>
