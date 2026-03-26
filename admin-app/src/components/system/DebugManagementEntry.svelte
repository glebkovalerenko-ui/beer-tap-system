<script>
  import { ROLE_SWITCH_ENABLED } from '../../lib/config.js';
  import { roleStore } from '../../stores/roleStore.js';
  import DemoModeToggle from './DemoModeToggle.svelte';
  import ServerSettingsModal from './ServerSettingsModal.svelte';

  let isOpen = false;

  function changeRole(event) {
    roleStore.setRole(event.target.value);
  }

  $: canAccessDebugTools = $roleStore.permissions.debug_tools;
  $: canAccessRoleSwitch = ROLE_SWITCH_ENABLED || $roleStore.permissions.role_switch;
  $: canRenderEntry = canAccessDebugTools || canAccessRoleSwitch;
</script>

{#if canRenderEntry}
  <section class="debug-entry ui-card" aria-label="Скрытая сервисная точка входа">
    <button
      class="debug-toggle"
      type="button"
      aria-expanded={isOpen}
      on:click={() => (isOpen = !isOpen)}
    >
      {isOpen ? 'Скрыть сервисный вход' : 'Показать сервисный вход'}
    </button>

    {#if isOpen}
      <div class="debug-panel">
        <p class="debug-copy">
          {#if canAccessDebugTools}
            Сервисные и демонстрационные инструменты вынесены из верхней панели оператора и открываются только по отдельному скрытому доступу.
          {:else}
            В этой сборке переключение роли оставлено отдельно от настроек подключения, чтобы не потерять инженерный доступ.
          {/if}
        </p>

        {#if canAccessDebugTools}
          <div class="debug-actions">
            <DemoModeToggle />
            <ServerSettingsModal buttonLabel="Подключение" variant="ghost" />
          </div>
        {/if}

        {#if canAccessRoleSwitch}
          <label class="role-picker">
            <span>Рабочая роль</span>
            <select on:change={changeRole} value={$roleStore.key} aria-label="Выбор рабочей роли">
              {#each Object.entries(roleStore.roles) as [key, role]}
                <option value={key}>{role.label}</option>
              {/each}
            </select>
          </label>
        {/if}
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
