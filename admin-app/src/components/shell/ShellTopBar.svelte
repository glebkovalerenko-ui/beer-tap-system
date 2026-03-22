<script>
  import { roleStore } from '../../stores/roleStore.js';
  import { sessionStore } from '../../stores/sessionStore.js';
  import { guestContextStore } from '../../stores/guestContextStore.js';
  import { shiftStore } from '../../stores/shiftStore.js';
  import { uiStore } from '../../stores/uiStore.js';
  import ShellStatusPills from './ShellStatusPills.svelte';
  import ShellGuestContextChip from './ShellGuestContextChip.svelte';
  import DemoModeToggle from '../system/DemoModeToggle.svelte';
  import ServerSettingsModal from '../system/ServerSettingsModal.svelte';

  export let title = 'Operator workspace';

  function changeRole(event) {
    roleStore.setRole(event.target.value);
  }

  async function handleOpenShift() {
    try {
      await shiftStore.openShift();
      uiStore.notifySuccess('Смена открыта');
    } catch (error) {
      uiStore.notifyError(error?.message || error?.toString?.() || 'Не удалось открыть смену');
    }
  }

  async function handleCloseShift() {
    try {
      await shiftStore.closeShift();
      uiStore.notifySuccess('Смена закрыта');
    } catch (error) {
      uiStore.notifyError(error?.message || error?.toString?.() || 'Не удалось закрыть смену');
    }
  }
</script>

<header class="topbar ui-card">
  <div class="left">
    <div>
      <p class="eyebrow">Beer Tap System · operator workspace</p>
      <h1>{title}</h1>
    </div>
    <ShellGuestContextChip
      guestName={$guestContextStore.guestName}
      cardUid={$guestContextStore.cardUid}
      isActive={$guestContextStore.isActive}
    />
  </div>

  <div class="right">
    <ShellStatusPills />
    <ServerSettingsModal buttonLabel="Подключение" variant="ghost" />
    {#if $shiftStore.isOpen}
      <button on:click={handleCloseShift} disabled={$shiftStore.loading}>Закрыть смену</button>
    {:else}
      <button on:click={handleOpenShift} disabled={$shiftStore.loading}>Открыть смену</button>
    {/if}
    <DemoModeToggle />
    <select on:change={changeRole} value={$roleStore.key} aria-label="Рабочая роль">
      {#each Object.entries(roleStore.roles) as [key, role]}
        <option value={key}>{role.label}</option>
      {/each}
    </select>
    <button class="ghost" on:click={() => sessionStore.logout()}>Выйти из workspace</button>
  </div>
</header>

<style>
  .topbar {
    margin: 12px;
    padding: 12px 14px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
    border-radius: 14px;
  }
  .left { display: flex; gap: 14px; align-items: center; }
  .eyebrow {
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text-secondary);
    margin: 0 0 0.2rem;
  }
  h1 { font-size: 1.1rem; margin: 0; min-width: 150px; }
  .right { display: flex; align-items: center; gap: 10px; }
  select { min-width: 170px; }
  .ghost { background: #edf2fb; color: #23416b; }
</style>
