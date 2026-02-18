<script>
  import Modal from '../common/Modal.svelte';
  import { uiStore } from '../../stores/uiStore.js';
</script>

{#if $uiStore.confirm}
  <Modal on:close={() => uiStore.resolveConfirm(false)}>
    <h2 slot="header">{$uiStore.confirm.title}</h2>
    <p>{$uiStore.confirm.message}</p>

    <div slot="footer" class="actions">
      <button class="cancel" on:click={() => uiStore.resolveConfirm(false)}>{$uiStore.confirm.cancelText}</button>
      <button class:danger={$uiStore.confirm.danger} on:click={() => uiStore.resolveConfirm(true)}>{$uiStore.confirm.confirmText}</button>
    </div>
  </Modal>
{/if}

<style>
  .actions { display: flex; gap: 0.75rem; justify-content: flex-end; }
  .cancel { background: #f0f0f0; color: #333; }
  .danger { background: #d9534f; color: #fff; }
</style>
