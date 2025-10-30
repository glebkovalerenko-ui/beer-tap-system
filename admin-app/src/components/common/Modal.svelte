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

<svelte:window on:keydown={handleKeydown}/>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
<div class="modal-backdrop" on:click={() => dispatch('close')} role="document">
  
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <div
    class="modal-content"
    on:click|stopPropagation
    role="dialog"
    aria-modal="true"
    tabindex="-1"
    use:focusOnMount
  >
    <!-- Секция для заголовка -->
    <header class="modal-header">
      <slot name="header">
        <!-- Сюда попадет контент с атрибутом slot="header" -->
        <!-- Можно добавить дефолтный заголовок, если нужно -->
        <!-- <h2>Default Title</h2> -->
      </slot>
    </header>

    <!-- Секция для основного контента (дефолтный слот) -->
    <main class="modal-body">
      <slot />
    </main>

    <!-- Секция для кнопок (футер) -->
    <footer class="modal-footer">
      <slot name="footer">
        <!-- Сюда попадет контент с атрибутом slot="footer" -->
      </slot>
    </footer>
  </div>
</div>

<style>
  .modal-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.5);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 100;
  }
  .modal-content {
    background-color: white;
    padding: 0; /* Убираем главный padding, чтобы секции могли управлять своими */
    border-radius: 8px;
    min-width: 450px;
    max-width: 90%;
    box-shadow: 0 5px 15px rgba(0,0,0,0.3);
    display: flex;
    flex-direction: column;
  }
  .modal-content:focus {
    outline: none;
  }

  .modal-header {
    padding: 1.5rem;
    border-bottom: 1px solid #eee;
  }
  /* Убираем дефолтный margin у h2 внутри слота */
  .modal-header :global(h2) {
      margin: 0;
  }

  .modal-body {
    padding: 1.5rem;
    max-height: 60vh; /* Ограничиваем высоту, если контента много */
    overflow-y: auto;
  }

  .modal-footer {
    padding: 1rem 1.5rem;
    border-top: 1px solid #eee;
    display: flex;
    justify-content: flex-end; /* Кнопки по умолчанию справа */
  }
</style>