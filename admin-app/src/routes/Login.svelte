<!-- src/routes/Login.svelte -->

<script>
  // Шаг 1: Импортируем нужные нам инструменты
  import { sessionStore } from '../stores/sessionStore.js';
  import { invoke } from '@tauri-apps/api/core';

  let username = 'admin';
  let password = 'fake_password'; // Используйте ваш реальный пароль для теста
  let error = '';
  let isLoading = false;

  async function handleLogin() {
    error = '';
    isLoading = true;
    try {
      // Шаг 2: Напрямую вызываем команду Rust, которую мы сейчас создадим
      const token = await invoke('login', {
        username: username,
        password: password,
      });
      
      // Шаг 3: Если команда выполнилась успешно и вернула токен...
      if (token) {
        // ...сохраняем его в наше глобальное хранилище.
        sessionStore.setToken(token);
        // App.svelte увидит это изменение и автоматически переключит интерфейс.
      } else {
        // На случай, если бэкенд по какой-то причине не вернул ошибку, но и токен пустой
        error = 'Ошибка входа: неверный ответ сервера.';
      }

    } catch (e) {
      // Шаг 4: Если invoke() вернул ошибку, отображаем ее.
      // Наш AppError в Rust как раз вернет сюда объект с полем `message`.
      error = e.message || 'Ошибка входа. Проверьте учетные данные.';
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
      <input type="text" id="username" bind:value={username} disabled={isLoading} />
    </div>
    <div class="form-group">
      <label for="password">Пароль</label>
      <input type="password" id="password" bind:value={password} disabled={isLoading} />
    </div>
    <!-- Добавляем disabled на кнопку во время загрузки -->
    <button type="submit" disabled={isLoading}>
      {#if isLoading}Вход...{:else}Войти{/if}
    </button>
    {#if error}
      <p class="error">{error}</p>
    {/if}
  </form>
</div>

<style>
  /* Ваши стили остаются без изменений */
  .login-container { max-width: 400px; margin: 5rem auto; padding: 2rem; border: 1px solid #ddd; border-radius: 5px; }
  .form-group { margin-bottom: 1rem; }
  label { display: block; margin-bottom: 0.5rem; }
  input { width: 100%; padding: 0.5rem; }
  button { width: 100%; padding: 0.7rem; background-color: #007bff; color: white; border: none; cursor: pointer; }
  .error { color: red; margin-top: 1rem; }
</style>