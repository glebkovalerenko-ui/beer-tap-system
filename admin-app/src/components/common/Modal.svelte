<!-- admin-app/src/components/common/Modal.svelte -->
<!-- --- ДЛЯ ПОЛНОЙ ЗАМЕНЫ --- -->

<script>
  import { createEventDispatcher } from 'svelte';
  const dispatch = createEventDispatcher();

  function handleKeydown(event) {
    if (event.key === 'Escape') {
      dispatch('close');
    }
  }
  
  function focusOnMount(node) {
    node.focus();
  }
</script>

<svelte:window on:keydown={handleKeydown} />

<!-- Overlay/backdrop -->
<!-- click on backdrop closes modal; content click stops propagation -->
<div class="modal-backdrop" on:click={() => dispatch('close')} role="presentation">
  <div
    class="modal-content"
    on:click|stopPropagation
    role="dialog"
    aria-modal="true"
    tabindex="-1"
    use:focusOnMount
  >
    <!-- Секция для заголовка (фиксирована) -->
    <header class="modal-header">
      <slot name="header" />
    </header>

    <!-- Основное тело должно быть скроллируемым внутри окна -->
    <div class="modal-body">
      <main>
        <slot />
      </main>
    </div>

    <!-- Футер (фиксирован внутри модального окна) -->
    <footer class="modal-footer">
      <slot name="footer" />
    </footer>
  </div>
</div>

<style>
  .modal-backdrop {
    position: fixed;
    inset: 0;
    background-color: rgba(0, 0, 0, 0.5);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000; /* per requirement */
    padding: 1.5rem; /* small gap on mobile */
    box-sizing: border-box;
  }

  .modal-content {
    background-color: white;
    padding: 0;
    border-radius: 10px;
    width: min(95%, 720px);
    max-width: 100%;
    max-height: 85vh; /* per requirement */
    box-shadow: 0 10px 30px rgba(0,0,0,0.35);
    display: flex;
    flex-direction: column;
    overflow: hidden; /* ensure internal regions control scroll */
  }
  .modal-content:focus { outline: none; }

  .modal-header {
    padding: 1rem 1.25rem;
    border-bottom: 1px solid #eee;
    flex: 0 0 auto; /* fixed area */
    background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(255,255,255,0.95));
  }
  .modal-header :global(h2) { margin: 0; }

  .modal-body {
    padding: 1rem 1.25rem;
    overflow-y: auto; /* body scrolls if content is long */
    flex: 1 1 auto; /* takes available space */
  }

  .modal-body main { min-width: 0; }

  .modal-footer {
    padding: 0.75rem 1.25rem;
    border-top: 1px solid #eee;
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
    flex: 0 0 auto; /* fixed footer -> always visible */
    background: linear-gradient(0deg, rgba(255,255,255,0.98), rgba(255,255,255,0.95));
  }

  /* Ensure action buttons in footer are visible and responsive */
  .modal-footer :global(button) {
    min-width: 88px;
    padding: 0.6rem 0.9rem;
  }
</style>