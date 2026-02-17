<!-- src/routes/Login.svelte -->

<script>
  import { sessionStore } from '../stores/sessionStore.js';
  import { invoke } from '@tauri-apps/api/core';
  import { API_BASE_URL } from '../lib/config.js';

  let username = 'admin';
  let password = 'fake_password'; // Используйте ваш реальный пароль для теста
  let error = '';
  let isLoading = false;

  async function loginViaHttp() {
    const response = await fetch(`${API_BASE_URL}/api/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ username, password })
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || 'Ошибка входа. Проверьте учетные данные.');
    }

    const data = await response.json();
    if (!data?.access_token) {
      throw new Error('Ошибка входа: пустой токен от сервера.');
    }
    return data.access_token;
  }

  async function handleLogin() {
    error = '';
    isLoading = true;

    try {
      // Сначала пробуем нативный Tauri-путь
      let token;
      try {
        token = await invoke('login', { username, password });
      } catch (tauriError) {
        // Fallback для web-demo режима (без Tauri runtime)
        token = await loginViaHttp();
      }

      if (!token) {
        error = 'Ошибка входа: неверный ответ сервера.';
        return;
      }

      sessionStore.setToken(token);
    } catch (e) {
      error = e?.message || 'Ошибка входа. Проверьте учетные данные.';
    } finally {
      isLoading = false;
    }
  }
</script>

<div class="login-container">
  <h2>Вход</h2>
  <form on:submit|preventDefault={handleLogin}>
    <div class="form-group">
      <label for="username">Имя пользователя</label>
      <input type="text" id="username" bind:value={username} disabled={isLoading} autocomplete="username" required />
    </div>
    <div class="form-group">
      <label for="password">Пароль</label>
      <input type="password" id="password" bind:value={password} disabled={isLoading} autocomplete="current-password" required />
    </div>
    <button type="submit" disabled={isLoading || !username || !password}>
      {#if isLoading}Вход...{:else}Войти{/if}
    </button>
    {#if error}
      <p class="error">{error}</p>
    {/if}
  </form>
</div>

<style>
  .login-container { max-width: 400px; margin: 5rem auto; padding: 2rem; border: 1px solid #ddd; border-radius: 5px; }
  .form-group { margin-bottom: 1rem; }
  label { display: block; margin-bottom: 0.5rem; }
  input { width: 100%; padding: 0.5rem; }
  button { width: 100%; padding: 0.7rem; background-color: #007bff; color: white; border: none; cursor: pointer; }
  .error { color: red; margin-top: 1rem; }
</style>
