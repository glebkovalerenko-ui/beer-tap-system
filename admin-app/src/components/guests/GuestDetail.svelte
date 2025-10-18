<!-- src/components/guests/GuestDetail.svelte -->

<script>
  import { createEventDispatcher } from 'svelte';
  export let guest;
  
  const dispatch = createEventDispatcher();

  // Вспомогательная функция для форматирования даты и времени
  function formatDateTime(isoString) {
    if (!isoString) return 'N/A';
    return new Date(isoString).toLocaleString();
  }
</script>

<div class="detail-container">
  <div class="detail-header">
    <h3>{`${guest.last_name} ${guest.first_name} ${guest.patronymic || ''}`}</h3>
    <div class="header-actions">
      <button class="btn-edit" on:click={() => dispatch('edit')} title="Edit Guest">
        Edit
      </button>
      <button class="close-btn" on:click={() => dispatch('close')} title="Close">×</button>
    </div>
  </div>

  <div class="detail-body">
    <!-- Основной блок с балансом и статусом -->
    <div class="info-block primary">
      <div class="balance-section">
        <span class="label">Balance</span>
        <span class="value balance">{(Number(guest.balance) || 0).toFixed(2)}</span>
        <!-- +++ НАЧАЛО ИЗМЕНЕНИЙ: Добавляем кнопку пополнения баланса +++ -->
        <button class="btn-action top-up-btn" on:click={() => dispatch('top-up')}>
          + Top Up
        </button>
        <!-- +++ КОНЕЦ ИЗМЕНЕНИЙ +++ -->
      </div>
      <div>
        <span class="label">Status</span>
        <span 
          class="value status" 
          class:active={guest.is_active} 
          class:inactive={!guest.is_active}
        >
          {guest.is_active ? 'Active' : 'Inactive'}
        </span>
      </div>
    </div>

    <!-- Блок с контактной информацией -->
    <div class="info-block">
      <h4>Contact & ID</h4>
      <p><span class="label">Phone:</span> {guest.phone_number}</p>
      <p><span class="label">ID Document:</span> {guest.id_document}</p>
      <p><span class="label">Date of Birth:</span> {guest.date_of_birth}</p>
    </div>

    <!-- Блок с привязанными картами -->
    <div class="info-block">
      <div class="cards-header">
        <h4>Assigned Cards ({guest.cards.length})</h4>
        {#if guest.cards.length === 0}
          <button class="btn-action" on:click={() => dispatch('bind-card')}>+ Bind Card</button>
        {/if}
      </div>
      {#if guest.cards.length > 0}
        <ul class="card-list">
          {#each guest.cards as card (card.card_uid)}
            <li class:active={card.status === 'active'} class:inactive={card.status !== 'active'}>
              <span class="card-icon">💳</span>
              <div class="card-details">
                <span class="card-uid">{card.card_uid}</span>
                <span class="card-status">{card.status}</span>
              </div>
            </li>
          {/each}
        </ul>
      {:else}
        <p>No cards assigned.</p>
      {/if}
    </div>

    <!-- Блок с системной информацией -->
    <div class="info-block system-info">
      <h4>System Information</h4>
      <p><span class="label">Registered:</span> {formatDateTime(guest.created_at)}</p>
      <p><span class="label">Last Update:</span> {formatDateTime(guest.updated_at)}</p>
      <p><span class="label">Guest ID:</span> <span class="uuid">{guest.guest_id}</span></p>
    </div>
    
  </div>
</div>

<style>
  .detail-container { padding: 0.5rem; font-size: 0.95rem; }
  .detail-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #eee; padding-bottom: 0.5rem; margin-bottom: 1rem;}
  h3 { margin: 0; }
  h4 { margin-top: 0; margin-bottom: 0.5rem; border-bottom: 1px solid #f0f0f0; padding-bottom: 0.25rem; }
  .header-actions { display: flex; align-items: center; gap: 0.5rem; }
  .btn-edit { background-color: #f0f0f0; border: 1px solid #ccc; padding: 0.25rem 0.75rem; border-radius: 4px; cursor: pointer; }
  .btn-edit:hover { background-color: #e0e0e0; }
  .close-btn { background: none; border: none; font-size: 1.5rem; cursor: pointer; color: #888; }
  .close-btn:hover { color: #333; }
  .info-block { margin-bottom: 1.5rem; }
  .info-block.primary { display: flex; justify-content: space-around; align-items: start; background: #f7f7f7; padding: 1rem; border-radius: 5px; text-align: center; }
  .info-block p { margin: 0.5rem 0; }
  .label { font-weight: bold; color: #555; display: block; margin-bottom: 0.25rem; }
  .balance { font-size: 1.5rem; font-weight: bold; color: #2a9d8f; }
  .status { font-weight: bold; }
  .status.active { color: #2a9d8f; }
  .status.inactive { color: #e76f51; }
  
  .cards-header { display: flex; justify-content: space-between; align-items: center; }
  .btn-action { background-color: #2a9d8f; color: white; border: none; padding: 0.25rem 0.75rem; border-radius: 4px; cursor: pointer; font-size: 0.8rem; }
  .btn-action:hover { background-color: #268a7e; }
  .card-list { list-style-type: none; padding-left: 0; margin: 0; }
  .card-list li { background: #fafafa; padding: 0.5rem; border-radius: 3px; margin-bottom: 0.25rem; display: flex; align-items: center; gap: 0.75rem; border-left: 4px solid #ccc; }
  .card-list li.active { border-left-color: #2a9d8f; }
  .card-list li.inactive { border-left-color: #e76f51; opacity: 0.7; }
  .card-icon { font-size: 1.5rem; }
  .card-details { display: flex; flex-direction: column; }
  .card-uid { font-family: monospace; font-weight: bold; }
  .card-status { font-size: 0.8rem; text-transform: capitalize; color: #555; }

  .system-info { font-size: 0.8rem; color: #888; }
  .uuid { font-family: monospace; }
  
  /* +++ НАЧАЛО ИЗМЕНЕНИЙ: Стили для секции баланса +++ */
  .balance-section { display: flex; flex-direction: column; align-items: center; gap: 0.5rem; }
  .top-up-btn { font-size: 0.9rem; padding: 0.4rem 1rem; }
  /* +++ КОНЕЦ ИЗМЕНЕНИЙ +++ */
</style>