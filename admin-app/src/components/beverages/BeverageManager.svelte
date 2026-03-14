<script>
  import { beverageStore } from "../../stores/beverageStore.js";

  let formData = {
    name: "",
    style: "IPA",
    brewery: "",
    abv: "5.0",
    sell_price_per_liter: "450.00",
    display_brand_name: "",
    description_short: "",
    accent_color: "#C79A3B",
    text_theme: "dark",
    price_display_mode_default: "per_100ml",
  };

  let formError = "";

  function resetForm() {
    formData = {
      name: "",
      style: "IPA",
      brewery: "",
      abv: "5.0",
      sell_price_per_liter: "450.00",
      display_brand_name: "",
      description_short: "",
      accent_color: "#C79A3B",
      text_theme: "dark",
      price_display_mode_default: "per_100ml",
    };
  }

  async function handleSubmit() {
    formError = "";
    try {
      const payload = {
        ...formData,
        abv: formData.abv ? String(formData.abv) : null,
        display_brand_name: formData.display_brand_name || null,
        description_short: formData.description_short || null,
        accent_color: formData.accent_color || null,
        text_theme: formData.text_theme || null,
        price_display_mode_default: formData.price_display_mode_default || null,
      };

      await beverageStore.createBeverage(payload);
      resetForm();
    } catch (error) {
      formError =
        typeof error === "string"
          ? error
          : error instanceof Error
            ? error.message
            : "Неизвестная ошибка";
    }
  }
</script>

<div class="beverage-manager">
  <div class="beverage-list">
    {#if $beverageStore.loading && $beverageStore.beverages.length === 0}
      <p class="placeholder-text">Загрузка напитков...</p>
    {:else if $beverageStore.beverages.length === 0}
      <p class="placeholder-text">Напитки не найдены. Добавьте один ниже.</p>
    {:else}
      <ul>
        {#each $beverageStore.beverages as beverage (beverage.beverage_id)}
          <li>
            <div class="beverage-copy">
              <span class="name">{beverage.name}</span>
              <span class="subtitle">
                {[beverage.display_brand_name || beverage.brewery, beverage.style].filter(Boolean).join(" · ")}
              </span>
            </div>
            <div class="beverage-meta">
              <span class="type">{beverage.price_display_mode_default || "per_100ml"}</span>
              <span class="price">{beverage.sell_price_per_liter} ₽/л</span>
            </div>
          </li>
        {/each}
      </ul>
    {/if}
  </div>

  <form class="beverage-form" on:submit|preventDefault={handleSubmit}>
    <h4>Добавить напиток</h4>

    <div class="form-grid">
      <label>
        <span>Название</span>
        <input type="text" placeholder="Название напитка" bind:value={formData.name} required disabled={$beverageStore.loading} />
      </label>

      <label>
        <span>Бренд на экране</span>
        <input type="text" placeholder="Бренд / производитель" bind:value={formData.display_brand_name} disabled={$beverageStore.loading} />
      </label>

      <label>
        <span>Пивоварня</span>
        <input type="text" placeholder="Пивоварня" bind:value={formData.brewery} required disabled={$beverageStore.loading} />
      </label>

      <label>
        <span>Стиль</span>
        <select bind:value={formData.style} disabled={$beverageStore.loading}>
          <option value="IPA">IPA</option>
          <option value="Stout">Стаут</option>
          <option value="Lager">Лагер</option>
          <option value="Cider">Сидр</option>
          <option value="Other">Другое</option>
        </select>
      </label>

      <label>
        <span>Крепость ABV</span>
        <input
          type="text"
          placeholder="5.0"
          bind:value={formData.abv}
          pattern="^\d*\.?\d*$"
          title="Например 5.0 или 4.5"
          disabled={$beverageStore.loading}
        />
      </label>

      <label>
        <span>Цена за литр</span>
        <input
          type="text"
          placeholder="450.00"
          bind:value={formData.sell_price_per_liter}
          required
          pattern="^\d*\.?\d*$"
          title="Например 450.00 или 500"
          disabled={$beverageStore.loading}
        />
      </label>

      <label>
        <span>Акцентный цвет</span>
        <div class="color-row">
          <input class="color-picker" type="color" bind:value={formData.accent_color} disabled={$beverageStore.loading} />
          <input type="text" placeholder="#C79A3B" bind:value={formData.accent_color} disabled={$beverageStore.loading} />
        </div>
      </label>

      <label>
        <span>Цена на экране</span>
        <select bind:value={formData.price_display_mode_default} disabled={$beverageStore.loading}>
          <option value="per_100ml">₽ / 100 мл</option>
          <option value="per_liter">₽ / л</option>
          <option value="auto">Авто</option>
        </select>
      </label>

      <label>
        <span>Тема текста</span>
        <select bind:value={formData.text_theme} disabled={$beverageStore.loading}>
          <option value="dark">Dark overlay</option>
          <option value="light">Light overlay</option>
          <option value="auto">Auto</option>
        </select>
      </label>

      <label class="wide">
        <span>Короткое описание для idle screen</span>
        <textarea
          rows="3"
          maxlength="160"
          placeholder="Короткое описание напитка для экрана у крана"
          bind:value={formData.description_short}
          disabled={$beverageStore.loading}
        ></textarea>
      </label>
    </div>

    <button type="submit" disabled={$beverageStore.loading}>
      {$beverageStore.loading ? "Добавление..." : "+ Добавить напиток"}
    </button>

    {#if formError}<p class="error">{formError}</p>{/if}
  </form>
</div>

<style>
  .beverage-manager {
    border: 1px solid #eee;
    border-radius: 8px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    height: 100%;
  }

  .beverage-list {
    flex-grow: 1;
    overflow-y: auto;
    padding: 0.5rem;
  }

  .beverage-list ul {
    list-style-type: none;
    padding: 0;
    margin: 0;
  }

  .beverage-list li {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    padding: 0.75rem;
    border-bottom: 1px solid #f0f0f0;
  }

  .beverage-list li:last-child {
    border-bottom: none;
  }

  .beverage-copy,
  .beverage-meta {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
  }

  .beverage-meta {
    align-items: flex-end;
  }

  .name {
    font-weight: 600;
  }

  .subtitle,
  .type {
    font-size: 0.85rem;
    color: #666;
  }

  .price {
    font-size: 0.85rem;
    font-weight: 600;
  }

  .placeholder-text {
    padding: 1rem;
    text-align: center;
    color: #888;
  }

  .beverage-form {
    padding: 1rem;
    background-color: #f9f9f9;
    border-top: 1px solid #eee;
  }

  .beverage-form h4 {
    margin: 0 0 1rem 0;
  }

  .form-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.75rem;
  }

  label {
    display: grid;
    gap: 0.35rem;
    font-size: 0.85rem;
    color: #444;
  }

  label span {
    font-weight: 600;
  }

  .wide {
    grid-column: 1 / -1;
  }

  input,
  select,
  textarea {
    width: 100%;
    padding: 0.55rem 0.65rem;
    box-sizing: border-box;
    border: 1px solid #d8d8d8;
    border-radius: 6px;
    font: inherit;
  }

  textarea {
    resize: vertical;
  }

  .color-row {
    display: grid;
    grid-template-columns: 52px 1fr;
    gap: 0.5rem;
  }

  .color-picker {
    padding: 0.2rem;
  }

  button {
    width: 100%;
    padding: 0.65rem;
    margin-top: 1rem;
  }

  .error {
    color: red;
    font-size: 0.8rem;
    margin-top: 0.5rem;
    text-align: center;
  }

  @media (max-width: 900px) {
    .form-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
