<script>
  import { createEventDispatcher } from 'svelte';
  export let guest;
  export let recentActivity = [];

  const dispatch = createEventDispatcher();

  function formatDateTime(isoString) {
    if (!isoString) return 'N/A';
    return new Date(isoString).toLocaleString();
  }

  $: transactions = Array.isArray(guest?.transactions) ? guest.transactions.slice(0, 8) : [];
  $: activity = Array.isArray(recentActivity) ? recentActivity : [];
</script>

<div class="detail-container">
  <div class="detail-header">
    <div>
      <h3>{`${guest.last_name} ${guest.first_name} ${guest.patronymic || ''}`}</h3>
      <p>{guest.phone_number}</p>
    </div>
    <div class="header-actions">
      <button class="btn-edit" on:click={() => dispatch('edit')} title="Редактировать гостя">Редактировать</button>
      <button class="close-btn" on:click={() => dispatch('close')} title="Закрыть">×</button>
    </div>
  </div>

  <div class="summary ui-card">
    <div>
      <span class="label">Баланс</span>
      <span class="balance">{(Number(guest.balance) || 0).toFixed(2)}</span>
    </div>
    <div>
      <span class="label">Статус</span>
      <span class="status" class:active={guest.is_active} class:inactive={!guest.is_active}>
        {guest.is_active ? 'Активен' : 'Заблокирован'}
      </span>
    </div>
    <button class="top-up-btn" on:click={() => dispatch('top-up')}>Пополнить</button>
  </div>

  <div class="info-block">
    <div class="cards-header">
      <h4>Карты гостя</h4>
      <button class="btn-action" on:click={() => dispatch('bind-card')}>Привязать карту</button>
    </div>
    {#if guest.cards.length > 0}
      <ul class="card-list">
        {#each guest.cards as card (card.card_uid)}
          <li class:active={card.status === 'active'} class:inactive={card.status !== 'active'}>
            <span class="card-uid">{card.card_uid}</span>
            <span class="card-status">{card.status}</span>
          </li>
        {/each}
      </ul>
    {:else}
      <p class="hint">Карты не привязаны. Привяжите карту, чтобы проводить операции.</p>
    {/if}
  </div>

  <div class="info-block">
    <h4>Последние операции</h4>

    {#if transactions.length > 0}
      <ul class="tx-list">
        {#each transactions as tx (tx.transaction_id)}
          <li>
            <div>
              <strong>{tx.type || 'Операция'}</strong>
              <small>{formatDateTime(tx.created_at)}</small>
            </div>
            <span>{Number(tx.amount || 0).toFixed(2)}</span>
          </li>
        {/each}
      </ul>
    {:else if activity.length > 0}
      <ul class="tx-list">
        {#each activity as item (item.pour_id)}
          <li>
            <div>
              <strong>Списание за налив</strong>
              <small>{formatDateTime(item.poured_at)} · {item.beverage?.name || 'Напиток'}</small>
            </div>
            <span>-{Number(item.amount_charged || 0).toFixed(2)}</span>
          </li>
        {/each}
      </ul>
    {:else}
      <p class="hint">История операций недоступна или пока пуста. Можно продолжить работу и обновить данные позже.</p>
    {/if}
  </div>

  <div class="info-block system-info">
    <h4>Системная информация</h4>
    <p><span class="label">Registered:</span> {formatDateTime(guest.created_at)}</p>
    <p><span class="label">Last Update:</span> {formatDateTime(guest.updated_at)}</p>
    <p><span class="label">Guest ID:</span> <span class="uuid">{guest.guest_id}</span></p>
  </div>
</div>

<style>
  .detail-container { padding: 0.5rem; font-size: 0.95rem; display: grid; gap: 1rem; }
  .detail-header { display: flex; justify-content: space-between; align-items: start; border-bottom: 1px solid #eee; padding-bottom: 0.5rem; }
  .detail-header h3 { margin: 0; }
  .detail-header p { margin: 0.2rem 0 0; color: var(--text-secondary); }
  h4 { margin: 0; }

  .header-actions { display: flex; align-items: center; gap: 0.5rem; }
  .btn-edit { background-color: #edf2fb; color: #23416b; }
  .close-btn { background: none; border: none; font-size: 1.5rem; cursor: pointer; color: #888; }

  .summary {
    display: grid;
    grid-template-columns: 1fr 1fr auto;
    gap: 1rem;
    align-items: center;
    padding: 1rem;
  }
  .label { font-weight: 600; color: #555; display: block; margin-bottom: 0.25rem; font-size: 0.85rem; }
  .balance { font-size: 1.8rem; font-weight: bold; color: #155e4a; }
  .status { font-weight: bold; }
  .status.active { color: #2a9d8f; }
  .status.inactive { color: #e76f51; }
  .top-up-btn { min-height: 48px; }

  .info-block { border: 1px solid #edf0f4; border-radius: 10px; padding: 0.9rem; }
  .cards-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.6rem; }

  .card-list, .tx-list { list-style-type: none; padding-left: 0; margin: 0; display: grid; gap: 0.45rem; }
  .card-list li, .tx-list li {
    background: #fafcff;
    padding: 0.6rem 0.7rem;
    border-radius: 7px;
    border: 1px solid #edf0f4;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .card-list li.active { border-left: 4px solid #2a9d8f; }
  .card-list li.inactive { border-left: 4px solid #e76f51; }
  .card-uid { font-family: monospace; font-weight: 700; }
  .card-status { font-size: 0.85rem; color: #555; }

  .tx-list li strong { display: block; }
  .tx-list li small { color: var(--text-secondary); }

  .hint { margin: 0; color: var(--text-secondary); }
  .system-info { font-size: 0.85rem; color: #61718a; }
  .uuid { font-family: monospace; }
</style>
