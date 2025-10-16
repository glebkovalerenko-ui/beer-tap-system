<!-- src/components/guests/GuestListItem.svelte -->

<script>
  import { createEventDispatcher } from 'svelte';

  // Получаем одного гостя как prop
  export let guest;

  // Создаем диспетчер для отправки событий родителю
  const dispatch = createEventDispatcher();

  function selectGuest() {
    // Отправляем событие 'select' с ID гостя в payload
    dispatch('select', { guestId: guest.guest_id });
  }
</script>

<li class="guest-item" on:click={selectGuest}>
  <div class="guest-info">
    <!-- ИЗМЕНЕНИЕ: Добавляем индикатор статуса -->
    <span class="status-indicator" class:active={guest.is_active} title={guest.is_active ? 'Active' : 'Inactive'}></span>
    <strong>{`${guest.last_name} ${guest.first_name}`}</strong>
  </div>
  <span>Balance: {(Number(guest.balance) || 0).toFixed(2)}</span>
</li>

<style>
  .guest-item {
    display: flex;
    justify-content: space-between;
    align-items: center; /* Добавлено для выравнивания по центру */
    padding: 0.75rem;
    border-bottom: 1px solid #eee;
    cursor: pointer;
    transition: background-color 0.2s;
  }
  .guest-item:hover {
    background-color: #f0f8ff;
  }
  /* ИЗМЕНЕНИЕ: Стили для индикатора и информации о госте */
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