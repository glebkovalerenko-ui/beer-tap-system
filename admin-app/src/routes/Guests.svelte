<script>
  import { onMount } from 'svelte';
  import { apiFetch } from '../lib/api.js';

  let guests = [];
  let error = '';
  let isLoading = true;

  async function fetchGuests() {
    isLoading = true;
    error = '';
    try {
      guests = await apiFetch('/api/guests/');
    } catch (e) {
      error = 'Failed to load guests. You might be logged out.';
    } finally {
      isLoading = false;
    }
  }

  onMount(fetchGuests);
</script>

<h2>Guests</h2>
<button on:click={fetchGuests} disabled={isLoading}>Refresh List</button>

{#if isLoading}
  <p>Loading guests...</p>
{:else if error}
  <p class="error">{error}</p>
{:else if guests.length === 0}
  <p>No guests found in the system.</p>
{:else}
  <ul>
    {#each guests as guest (guest.guest_id)}
      <li>
        <!-- ИСПОЛЬЗУЕМ ПРАВИЛЬНЫЕ ПОЛЯ ДЛЯ ОТОБРАЖЕНИЯ ИМЕНИ -->
        <strong>{`${guest.last_name} ${guest.first_name} ${guest.patronymic}`}</strong> 
        - Balance: {(Number(guest.balance) || 0).toFixed(2)}
      </li>
    {/each}
  </ul>
{/if}

<style>
  .error { color: red; }
  button { margin-bottom: 1rem; }
</style>