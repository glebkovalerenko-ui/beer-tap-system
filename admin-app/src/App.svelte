<!-- src/App.svelte -->

<script>
  import Router from 'svelte-spa-router';
  // <-- ИЗМЕНЕНО: Импортируем Svelte Stores вместо api.js
  import { sessionStore } from './stores/sessionStore.js';
  import { guestStore } from './stores/guestStore.js';

  // Импортируем наши страницы
  import Dashboard from './routes/Dashboard.svelte';
  import Guests from './routes/Guests.svelte';
  import Taps from './routes/Taps.svelte';
  import Login from './routes/Login.svelte';

  const routes = {
    '/': Dashboard,
    '/guests': Guests,
    '/taps': Taps,
    '*': Dashboard
  };

  // <-- ДОБАВЛЕНО: Реактивный блок для автоматической загрузки данных
  // Этот код выполнится, когда $sessionStore.token изменится (например, после логина),
  // но только если гости еще не были загружены.
  /*$: if ($sessionStore.token && $guestStore.guests.length === 0 && !$guestStore.loading) {
    guestStore.fetchGuests();
  }*/

</script>

<!-- Реактивно показываем либо страницу входа, либо основное приложение -->
<!-- <-- ИЗМЕНЕНО: Проверяем токен из sessionStore -->
{#if $sessionStore.token}
  <!-- Если пользователь залогинен -->
  <div class="app-layout">
    <nav class="sidebar">
      <h1>Admin App</h1>
      <ul>
        <li><a href="#/">Dashboard</a></li>
        <li><a href="#/guests">Guests</a></li>
        <li><a href="#/taps">Taps & Kegs</a></li>
      </ul>
      <!-- <-- ИЗМЕНЕНО: Вызываем logout из sessionStore -->
      <button on:click={() => sessionStore.logout()} class="logout-button">Log Out</button>
    </nav>

    <main class="main-content">
      <!-- <-- ДОБАВЛЕНО: Временный блок для проверки загрузки данных -->
      <!-- !!Этот блок можно будет удалить после того, как вы убедитесь, что все работает -->
      <!-- !! <div style="background: #eee; padding: 10px; margin-bottom: 15px; border-radius: 5px;">
        <h3>Debug Info (Step 1.1)</h3>
        {#if $guestStore.loading}
          <p>Загрузка гостей...</p>
        {:else if $guestStore.error}
          <p style="color: red;">Ошибка: {$guestStore.error}</p>
        {:else}
          <p>Загружено <b>{$guestStore.guests.length}</b> гостей.</p>
          <!-- Раскомментируйте, чтобы увидеть имена:
          <ul>
            {#each $guestStore.guests as guest}
              <li>{guest.name}</li>
            {/each}
          </ul>
          -->
        <!-- !!{/if}
      </div> !! -->
      <!-- Конец временного блока -->

      <Router {routes} />
    </main>
  </div>
{:else}
  <!-- Если пользователь НЕ залогинен -->
  <Login />
{/if}

<style>
  .app-layout { display: flex; height: 100vh; }
  .sidebar { width: 200px; background-color: #f4f4f4; padding: 1rem; border-right: 1px solid #ddd; position: relative; }
  .sidebar h1 { font-size: 1.5rem; margin-top: 0; }
  .sidebar ul { list-style-type: none; padding: 0; }
  .sidebar ul li a { display: block; padding: 0.5rem 0; text-decoration: none; color: #333; }
  .sidebar ul li a:hover { color: #007bff; }
  .main-content { flex-grow: 1; padding: 1rem; }
  .logout-button { position: absolute; bottom: 1rem; left: 1rem; right: 1rem; width: calc(100% - 2rem); }
</style>