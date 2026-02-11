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
    '/taps-kegs': TapsKegs,
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
      <div class="emergency-banner">
        ВНИМАНИЕ: СИСТЕМА В РЕЖИМЕ ЭКСТРЕННОЙ ОСТАНОВКИ. ВСЕ КРАНЫ ЗАБЛОКИРОВАНЫ.
      </div>
    {/if}

    <nav class="sidebar" aria-label="Главная навигация">
      <h1>Админ-панель</h1>
      <ul>
        <li><a href="#/">Дашборд</a></li>
        <li><a href="#/guests">Гости</a></li>
        <li><a href="#/taps-kegs">Краны и Кеги</a></li>
      </ul>
      <button on:click={() => sessionStore.logout()} class="logout-button">Выход</button>
    </nav>

    <main class="main-content">
      <!-- Внутри main оставляем шапку/панель и добавляем специально скроллящийся контейнер для страниц -->
      <div class="page-scroll">
        <Router {routes} />
      </div>
    </main>
  </div>
{:else}
  <!-- Если пользователь НЕ залогинен -->
  <Login />
{/if}

<style>
  /* Global layout reset required by the UX spec */
  :global(html, body) {
    margin: 0;
    padding: 0;
    height: 100vh;
    overflow: hidden; /* prevent body scrolling, app will control scroll inside */
    font-size: 16px; /* base font size */
  }

  .app-layout { display: flex; height: 100vh; }
  .sidebar {
    width: 240px;
    flex: 0 0 240px; /* fixed width sidebar */
    background-color: #f4f4f4;
    padding: 1rem;
    border-right: 1px solid #ddd;
    display: flex;
    flex-direction: column;
    box-sizing: border-box;
  }
  .sidebar h1 { font-size: 1.5rem; margin-top: 0; }
  .sidebar ul { list-style-type: none; padding: 0; }
  .sidebar ul li a { display: block; padding: 0.5rem 0; text-decoration: none; color: #333; }
  .sidebar ul li a:hover { color: #007bff; }
  .main-content {
    flex-grow: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden; /* main itself never scrolls; inner container scrolls */
  }

  /* Scrolling container for page content per requirements */
  .page-scroll {
    overflow-y: auto;
    padding: 2rem;
    flex: 1 1 auto;
    -webkit-overflow-scrolling: touch;
    box-sizing: border-box;
  }

  .logout-button { margin-top: auto; /* sticks to bottom of sidebar */ width: 100%; }
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

  /* Global interactive styles (buttons / inputs) */
  :global(button) {
    font-size: 1rem;
    padding: 0.6rem 1rem;
    border-radius: 6px;
    border: 1px solid rgba(0,0,0,0.08);
    background: #007bff;
    color: white;
    cursor: pointer;
    transition: transform 0.06s ease, filter 0.06s ease, box-shadow 0.06s ease;
    box-shadow: 0 1px 0 rgba(0,0,0,0.02);
  }
  :global(button:hover:not(:disabled)) {
    filter: brightness(0.95);
  }
  :global(button:active:not(:disabled)) {
    transform: scale(0.98);
  }
  :global(button:disabled) {
    opacity: 0.6;
    cursor: not-allowed;
    filter: none;
  }

  :global(input, textarea, select) {
    font-size: 1rem;
    padding: 0.5rem 0.75rem;
    border-radius: 6px;
    border: 1px solid #dcdcdc;
    box-sizing: border-box;
  }
</style>