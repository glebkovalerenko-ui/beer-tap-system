<!-- admin-app/src/App.svelte -->

<script>
  import { onMount, onDestroy } from 'svelte'; // <-- ИЗМЕНЕНО: Добавлены хуки жизненного цикла
  import Router from 'svelte-spa-router';
  
  import { sessionStore } from './stores/sessionStore.js';
  import { guestStore } from './stores/guestStore.js';
  import { systemStore } from './stores/systemStore.js'; 

  import Dashboard from './routes/Dashboard.svelte';
  import Guests from './routes/Guests.svelte';
  import TapsKegs from './routes/TapsKegs.svelte'; 
  import Login from './routes/Login.svelte';

  const routes = {
    '/': Dashboard,
    '/guests': Guests,
    '/taps-kgs': TapsKegs,
    '*': Dashboard
  };
  
  // --- ИЗМЕНЕНО: Явно управляем жизненным циклом фоновых процессов ---
  onMount(() => {
    console.log('[App.svelte] Компонент смонтирован, запускаем фоновые процессы.');
    // Запускаем опрос статуса системы
    systemStore.startPolling();

    // Здесь же можно инициализировать и другие сторы, которым нужно загрузить данные
    // Это более надежно, чем реактивный блок.
    if ($guestStore.guests.length === 0 && !$guestStore.loading) {
      guestStore.fetchGuests();
    }
  });

  onDestroy(() => {
    console.log('[App.svelte] Компонент уничтожен, останавливаем фоновые процессы.');
    // Останавливаем опрос статуса системы, чтобы избежать утечек памяти
    systemStore.stopPolling();
  });

  /* <-- ИЗМЕНЕНО: Старый реактивный блок закомментирован в пользу onMount
  $: if ($sessionStore.token && $guestStore.guests.length === 0 && !$guestStore.loading) {
    guestStore.fetchGuests();
  }
  */

</script>

<!-- Реактивно показываем либо страницу входа, либо основное приложение -->
{#if $sessionStore.token}
  <!-- Если пользователь залогинен -->
  <div class="app-layout" class:emergency-active={$systemStore.emergencyStop}>
    {#if $systemStore.emergencyStop}
    <div class-="emergency-banner">
      WARNING: SYSTEM IS IN EMERGENCY STOP MODE. ALL TAPS ARE LOCKED.
    </div>
    {/if}
    <nav class="sidebar">
      <h1>Admin App</h1>
      <ul>
        <li><a href="#/">Dashboard</a></li>
        <li><a href="#/guests">Guests</a></li>
        <li><a href="#/taps-kegs">Taps & Kegs</a></li>
      </ul>
      <button on:click={() => sessionStore.logout()} class="logout-button">Log Out</button>
    </nav>

    <main class="main-content">
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
  .emergency-banner {
    background-color: #d9534f;
    color: white;
    text-align: center;
    padding: 0.5rem;
    font-weight: bold;
    width: 100%;
    position: fixed;
    top: 0;
    left: 0;
    z-index: 1000;
  }
  .app-layout { 
    display: flex; 
    height: 100vh;
    padding-top: 0;
  }
  .app-layout.emergency-active {
    padding-top: 2.5rem;
  }
</style>