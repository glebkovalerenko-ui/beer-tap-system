<!-- src/components/guests/GuestListItem.svelte -->
<script>
  import { createEventDispatcher } from 'svelte';
  export let guest;
  export let isSelected = false;

  const dispatch = createEventDispatcher();

  function selectGuest() {
    dispatch('select', { guestId: guest.guest_id });
  }
</script>

<li class:selected={isSelected}>
  <button type="button" on:click={selectGuest} class="guest-card">
    <div class="guest-main">
      <!-- Индикатор статуса: Зеленая точка если активен -->
      <div class="status-dot" class:active={guest.is_active} title={guest.is_active ? 'Активен' : 'Неактивен'}></div>
      
      <div class="info-block">
        <span class="guest-name">{guest.last_name} {guest.first_name}</span>
        {#if guest.phone_number}
          <span class="guest-meta">{guest.phone_number}</span>
        {/if}
      </div>
    </div>

    <div class="guest-balance">
      <span class="currency">₽</span>
      <span class="amount">{(Number(guest.balance) || 0).toFixed(2)}</span>
    </div>
  </button>
</li>

<style>
  li {
    list-style: none;
    margin-bottom: 0.75rem;
  }

  .guest-card {
    width: 100%;
    background: white;
    border: 1px solid #f0f0f0;
    border-radius: 12px;
    padding: 1rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    cursor: pointer;
    text-align: left;
    transition: all 0.2s ease;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  }

  .guest-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.08);
    border-color: #e0e0e0;
  }

  li.selected .guest-card {
    border-color: #1a73e8;
    background-color: #f8fbff;
    box-shadow: 0 0 0 2px rgba(26, 115, 232, 0.1);
  }

  .guest-main {
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .status-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background-color: #dadce0; /* Серый по умолчанию */
    flex-shrink: 0;
  }
  .status-dot.active {
    background-color: #34a853; /* Зеленый активный */
    box-shadow: 0 0 0 2px rgba(52, 168, 83, 0.1);
  }

  .info-block {
    display: flex;
    flex-direction: column;
  }

  .guest-name {
    font-weight: 600;
    font-size: 1rem;
    color: #202124;
  }

  .guest-meta {
    font-size: 0.8rem;
    color: #80868b;
    margin-top: 2px;
  }

  .guest-balance {
    text-align: right;
    font-feature-settings: "tnum";
    font-variant-numeric: tabular-nums;
  }

  .currency {
    font-size: 0.9rem;
    color: #9aa0a6;
    margin-right: 2px;
  }

  .amount {
    font-weight: 700;
    font-size: 1.1rem;
    color: #1a73e8;
  }
  
  /* Убираем дефолтные стили кнопки */
  button {
    background: none;
    border: none;
    font: inherit;
    outline: none;
  }
  button:focus-visible {
    outline: 2px solid #1a73e8;
    border-radius: 12px;
  }
</style>