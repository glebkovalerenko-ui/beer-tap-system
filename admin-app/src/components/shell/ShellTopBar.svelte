<script>
  import { roleStore } from '../../stores/roleStore.js';
  import { sessionStore } from '../../stores/sessionStore.js';
  import { guestContextStore } from '../../stores/guestContextStore.js';
  import ShellStatusPills from './ShellStatusPills.svelte';
  import ShellGuestContextChip from './ShellGuestContextChip.svelte';
  import DemoModeToggle from '../system/DemoModeToggle.svelte';

  export let title = 'POS Workspace';

  function changeRole(event) {
    roleStore.setRole(event.target.value);
  }
</script>

<header class="topbar ui-card">
  <div class="left">
    <h1>{title}</h1>
    <ShellGuestContextChip
      guestName={$guestContextStore.guestName}
      cardUid={$guestContextStore.cardUid}
      isActive={$guestContextStore.isActive}
    />
  </div>

  <div class="right">
    <ShellStatusPills />
    <DemoModeToggle />
    <select on:change={changeRole} value={$roleStore.key} aria-label="Role">
      {#each Object.entries(roleStore.roles) as [key, role]}
        <option value={key}>{role.label}</option>
      {/each}
    </select>
    <button class="ghost" on:click={() => sessionStore.logout()}>Выход</button>
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
  h1 { font-size: 1.1rem; margin: 0; min-width: 150px; }
  .right { display: flex; align-items: center; gap: 10px; }
  select { min-width: 150px; }
  .ghost { background: #edf2fb; color: #23416b; }
</style>
