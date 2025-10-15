<script>
  import Router from 'svelte-spa-router';
  import { isAuthenticated, logout } from './lib/api.js';

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
</script>

<!-- Реактивно показываем либо страницу входа, либо основное приложение -->
{#if $isAuthenticated}
  <!-- Если пользователь залогинен -->
  <div class="app-layout">
    <nav class="sidebar">
      <h1>Admin App</h1>
      <ul>
        <li><a href="#/">Dashboard</a></li>
        <li><a href="#/guests">Guests</a></li>
        <li><a href="#/taps">Taps & Kegs</a></li>
      </ul>
      <button on:click={logout} class="logout-button">Log Out</button>
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
</style>