<script>
  import { login } from '../lib/api.js';

  let username = 'admin';
  let password = 'fake_password';
  let error = '';

  async function handleLogin() {
    error = '';
    try {
      await login(username, password);
      // Успешный вход обработает App.svelte
    } catch (e) {
      error = 'Failed to log in. Please check your credentials.';
    }
  }
</script>

<div class="login-container">
  <h2>Login</h2>
  <form on:submit|preventDefault={handleLogin}>
    <div class="form-group">
      <label for="username">Username</label>
      <input type="text" id="username" bind:value={username} />
    </div>
    <div class="form-group">
      <label for="password">Password</label>
      <input type="password" id="password" bind:value={password} />
    </div>
    <button type="submit">Log In</button>
    {#if error}
      <p class="error">{error}</p>
    {/if}
  </form>
</div>

<style>
  /* Стили для формы входа */
  .login-container { max-width: 400px; margin: 5rem auto; padding: 2rem; border: 1px solid #ddd; border-radius: 5px; }
  .form-group { margin-bottom: 1rem; }
  label { display: block; margin-bottom: 0.5rem; }
  input { width: 100%; padding: 0.5rem; }
  button { width: 100%; padding: 0.7rem; background-color: #007bff; color: white; border: none; cursor: pointer; }
  .error { color: red; margin-top: 1rem; }
</style>