<!-- src/components/common/Modal.svelte -->
<script>
  import { createEventDispatcher, onMount } from 'svelte';
  const dispatch = createEventDispatcher();

  function handleKeydown(event) {
    if (event.key === 'Escape') {
      dispatch('close');
    }
  }

  // +++ НАЧАЛО ИЗМЕНЕНИЙ: Svelte Action для управления фокусом +++
  /**
   * Эта "action" автоматически устанавливает фокус на элемент,
   * как только он появляется в DOM.
   * @param {HTMLElement} node - Элемент, к которому применяется action.
   */
  function focusOnMount(node) {
    // Устанавливаем фокус на узел
    node.focus();
  }
  // +++ КОНЕЦ ИЗМЕНЕНИЙ +++

</script>

<svelte:window on:keydown={handleKeydown}/>

<!--
  +++ НАЧАЛО ИЗМЕНЕНИЙ: Добавляем svelte-ignore +++
  Мы осознанно отключаем это правило для фона.
  Причина: у нас есть полноценный и более удобный способ закрыть окно
  с клавиатуры - клавиша Escape. Делать фон интерактивным для клавиатуры
  (добавляя tabindex) - плохая практика, т.к. это сбивает пользователя с толку.
-->
<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
<div class="modal-backdrop" on:click={() => dispatch('close')} role="document">
  <!--
    +++ НАЧАЛО ИЗМЕНЕНИЙ: Добавляем tabindex и используем action для фокуса +++
    - `tabindex="-1"` делает этот div программно фокусируемым, но не через Tab.
    - `use:focusOnMount` - наша новая action, которая переместит фокус сюда при открытии.
    - `on:click|stopPropagation` по-прежнему нужен, чтобы клик внутри окна не закрывал его.
      Мы также игнорируем предупреждение для этого, т.к. фокус теперь управляется корректно.
  -->
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <div
    class="modal-content"
    on:click|stopPropagation
    role="dialog"
    aria-modal="true"
    tabindex="-1"
    use:focusOnMount
  >
    <slot />
  </div>
</div>
<!-- +++ КОНЕЦ ИЗМЕНЕНИЙ +++ -->


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
    padding: 2rem;
    border-radius: 5px;
    min-width: 400px;
    max-width: 90%;
    box-shadow: 0 5px 15px rgba(0,0,0,0.3);
  }
  /* Добавляем стиль для контура фокуса на самом модальном окне */
  .modal-content:focus {
    outline: none;
  }
</style>