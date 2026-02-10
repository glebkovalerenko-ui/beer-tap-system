<!-- src/components/guests/GuestListItem.svelte -->

<script>
  import { createEventDispatcher } from 'svelte';

  // Получаем одного гостя как prop
  export let guest;

  // +++ ИЗМЕНЕНИЕ: Добавляем пропс для отслеживания выбранного элемента +++
  // Это нужно, чтобы правильно применять стили, когда кнопка внутри li
  export let isSelected = false;

  // Создаем диспетчер для отправки событий родителю
  const dispatch = createEventDispatcher();

  function selectGuest() {
    // Отправляем событие 'select' с ID гостя в payload
    dispatch('select', { guestId: guest.guest_id });
  }
</script>

<!-- 
  Элемент <li> теперь отвечает только за структуру списка. 
  Мы убрали с него обработчик on:click.
-->
<li class:selected={isSelected}>
  <!-- 
    +++ НАЧАЛО ИЗМЕНЕНИЙ: Вся интерактивность перенесена на <button> +++
    Это решает все проблемы доступности (a11y).
    Кнопка является "фокусируемым" элементом по умолчанию.
  -->
  <button type="button" on:click={selectGuest} class="guest-item-button">
    <div class="guest-info">
      <span class="status-indicator" class:active={guest.is_active} title={guest.is_active ? 'Активен' : 'Неактивен'}></span>
      <strong>{`${guest.last_name} ${guest.first_name}`}</strong>
    </div>
    <span>Баланс: {(Number(guest.balance) || 0).toFixed(2)}</span>
  </button>
  <!-- +++ КОНЕЦ ИЗМЕНЕНИЙ +++ -->
</li>

<style>
  li {
    /* Убираем все стили с li, он теперь просто контейнер */
    list-style-type: none;
    margin: 0;
    padding: 0;
  }

  /* +++ НАЧАЛО ИЗМЕНЕНИЙ: Новые стили для кнопки +++ */
  .guest-item-button {
    /* Сбрасываем стандартные стили кнопки, чтобы она не выглядела как кнопка */
    background: none;
    color: inherit;
    border: none;
    padding: 0;
    font: inherit;
    cursor: pointer;
    text-align: left;
    outline: inherit;
    
    /* Применяем стили, которые раньше были у .guest-item */
    width: 100%;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem;
    border-bottom: 1px solid #eee;
    transition: background-color 0.2s;
  }

  .guest-item-button:hover {
    background-color: #f0f8ff;
  }

  /* Для выбранного элемента подсвечиваем фон через родительский li */
  li.selected .guest-item-button {
    background-color: #e6f3ff;
  }
  
  /* Добавляем видимый контур фокуса для пользователей клавиатуры */
  .guest-item-button:focus-visible {
    outline: 2px solid #007bff;
    outline-offset: -2px;
    border-radius: 2px;
  }
  /* +++ КОНЕЦ ИЗМЕНЕНИЙ +++ */

  .guest-info {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }
  .status-indicator {
    display: block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background-color: #e76f51; /* Цвет для неактивного статуса по умолчанию */
  }
  .status-indicator.active {
    background-color: #2a9d8f; /* Цвет для активного статуса */
  }
</style>