<script>
  import { invoke } from '@tauri-apps/api/core';

  import ServerSettingsModal from '../components/system/ServerSettingsModal.svelte';
  import { getApiBaseUrl, initializeBackendBaseUrl } from '../lib/config.js';
  import { normalizeErrorMessage } from '../lib/errorUtils';
  import { sessionStore } from '../stores/sessionStore.js';

  let username = '';
  let password = '';
  let error = '';
  let isLoading = false;
  /** @type {import('../components/system/ServerSettingsModal.svelte').default | undefined} */
  let serverSettingsModal;

  async function loginViaHttp() {
    const response = await fetch(`${getApiBaseUrl()}/api/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ username, password }),
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || 'Ошибка входа. Проверьте учётные данные и URL сервера.');
    }

    const data = await response.json();
    if (!data?.access_token) {
      throw new Error('Ошибка входа: сервер не вернул access token.');
    }

    return data.access_token;
  }

  async function onSubmit() {
    error = '';
    isLoading = true;

    try {
      await initializeBackendBaseUrl();

      let token;
      try {
        token = await invoke('login', { username, password });
      } catch {
        token = await loginViaHttp();
      }

      if (!token) {
        throw new Error('Ошибка входа: сервер вернул пустой токен.');
      }

      sessionStore.setToken(token);
    } catch (loginError) {
      error = normalizeErrorMessage(
        loginError,
        'Ошибка входа. Проверьте учётные данные и доступность сервера.'
      );
    } finally {
      isLoading = false;
    }
  }

  /** @param {MouseEvent} event */
  async function openServerSettings(event) {
    event?.preventDefault();
    await serverSettingsModal?.openModal();
  }
</script>

<div class="login-container">
  <h2>Вход</h2>
  <ServerSettingsModal bind:this={serverSettingsModal} showLauncher={false} />
  <form on:submit|preventDefault={onSubmit}>
    <div class="form-group">
      <label for="username">Имя пользователя</label>
      <input type="text" id="username" bind:value={username} disabled={isLoading} autocomplete="username" required />
    </div>
    <div class="form-group">
      <label for="password">Пароль</label>
      <input type="password" id="password" bind:value={password} disabled={isLoading} autocomplete="current-password" required />
    </div>

    <div class="actions">
      <button type="submit" disabled={isLoading || !username || !password}>
        {#if isLoading}Вход...{:else}Войти{/if}
      </button>
      <button type="button" class="secondary" on:click={openServerSettings}>
        Настройки сервера
      </button>
    </div>

    {#if error}
      <p class="error">{error}</p>
    {/if}
  </form>
</div>

<style>
  .login-container {
    max-width: 400px;
    margin: 5rem auto;
    padding: 2rem;
    border: 1px solid #ddd;
    border-radius: 5px;
    background: white;
  }

  .form-group {
    margin-bottom: 1rem;
  }

  label {
    display: block;
    margin-bottom: 0.5rem;
  }

  input {
    width: 100%;
    padding: 0.5rem;
  }

  .actions {
    display: grid;
    gap: 0.75rem;
  }

  button {
    width: 100%;
    padding: 0.7rem;
    background-color: #007bff;
    color: white;
    border: none;
    cursor: pointer;
  }

  .secondary {
    background: #edf2fb;
    color: #23416b;
  }

  .error {
    color: red;
    margin-top: 1rem;
  }
</style>
