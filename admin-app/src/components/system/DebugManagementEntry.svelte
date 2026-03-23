<script>
  import { roleStore } from '../../stores/roleStore.js';
  import DemoModeToggle from './DemoModeToggle.svelte';
  import ServerSettingsModal from './ServerSettingsModal.svelte';

  let isOpen = false;

  function changeRole(event) {
    roleStore.setRole(event.target.value);
  }
</script>

{#if $roleStore.permissions.debug_tools}
  <section class="debug-entry ui-card" aria-label="Скрытая debug / management точка входа">
    <button
      class="debug-toggle"
      type="button"
      aria-expanded={isOpen}
      on:click={() => (isOpen = !isOpen)}
    >
      {isOpen ? 'Скрыть management' : 'Debug / management'}
    </button>

    {#if isOpen}
      <div class="debug-panel">
        <p class="debug-copy">Сервисные и demo-инструменты вынесены из operator top bar и открываются только по скрытому debug flag.</p>
        <div class="debug-actions">
          <DemoModeToggle />
          <ServerSettingsModal buttonLabel="Подключение" variant="ghost" />
        </div>
        <label class="role-picker">
          <span>Рабочая роль</span>
          <select on:change={changeRole} value={$roleStore.key} aria-label="Выбор рабочей роли">
            {#each Object.entries(roleStore.roles) as [key, role]}
              <option value={key}>{role.label}</option>
            {/each}
          </select>
        </label>
      </div>
    {/if}
  </section>
{/if}

<style>
  .debug-entry {
    display: grid;
    gap: 10px;
    padding: 0;
    background: transparent;
    border: 0;
    box-shadow: none;
  }
  .debug-toggle {
    align-self: start;
    background: transparent;
    color: var(--text-secondary);
    border: 1px dashed var(--border-soft);
    padding: 8px 10px;
  }
  .debug-panel {
    display: grid;
    gap: 12px;
    padding: 12px;
    border-radius: 12px;
    background: var(--bg-surface-muted);
    border: 1px solid var(--border-soft);
  }
  .debug-copy {
    margin: 0;
    color: var(--text-secondary);
    font-size: 0.85rem;
  }
  .debug-actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }
  .role-picker {
    display: grid;
    gap: 6px;
    font-size: 0.85rem;
  }
</style>
