<script>
  import { onMount } from "svelte";
  import { get, writable } from "svelte/store";
  import { getSnapshotCopy, isFastRuntimePhase, resolveDisplayState } from "./display-state.js";

  const FAST_RUNTIME_POLL_MS = 250;
  const SLOW_RUNTIME_POLL_MS = 250;
  const BOOTSTRAP_POLL_MS = 5000;
  const AUTHORIZING_UI_GRACE_MS = 700;

  const deniedCopy = {
    lost_card: {
      headline: "Карта утеряна",
      nextStep: "Обратитесь к оператору",
    },
    insufficient_funds: {
      headline: "Недостаточно средств",
      nextStep: "Пополните баланс",
    },
    no_active_visit: {
      headline: "Нет активного визита",
      nextStep: "Обратитесь к оператору",
    },
    card_in_use_on_other_tap: {
      headline: "Карта занята",
      nextStep: "Обратитесь к оператору",
    },
    backend_unreachable: {
      headline: "Нет связи с системой",
      nextStep: "Кран временно недоступен",
    },
    authorize_rejected: {
      headline: "Налив недоступен",
      nextStep: "Заберите карту",
    },
  };

  const serviceCopy = {
    no_connection: {
      headline: "Нет связи с системой",
      nextStep: "Кран временно недоступен",
      code: "backend_unreachable",
      tone: "warning",
    },
    maintenance: {
      headline: "Кран временно недоступен",
      nextStep: "Обратитесь к оператору",
      code: "maintenance",
      tone: "info",
    },
    no_keg: {
      headline: "Напиток не назначен",
      nextStep: "Обратитесь к оператору",
      code: "no_keg",
      tone: "neutral",
    },
    processing_sync: {
      headline: "Подождите",
      nextStep: "Кран завершает синхронизацию",
      code: "processing_sync",
      tone: "info",
    },
    emergency_stop: {
      headline: "Кран недоступен",
      nextStep: "Обратитесь к оператору",
      code: "emergency_stop",
      tone: "danger",
    },
    authorize_invalid_contract: {
      headline: "Кран недоступен",
      nextStep: "Обратитесь к оператору",
      code: "authorize_invalid_contract",
      tone: "danger",
    },
    controller_runtime_stale: {
      headline: "Нет связи с контроллером",
      nextStep: "Обратитесь к оператору",
      code: "controller_runtime_stale",
      tone: "warning",
    },
    flow_timeout: {
      headline: "Налив остановлен",
      nextStep: "Заберите карту",
      code: "flow_timeout",
      tone: "warning",
    },
    card_removed: {
      headline: "Заберите карту",
      nextStep: "Уберите карту со считывателя",
      code: "card_removed",
      tone: "neutral",
    },
  };

  const bootstrap = writable(null);
  const runtimePayload = writable(null);
  const bootstrapError = writable(null);
  const runtimeError = writable(null);
  let authorizingStartedAtMs = null;
  let runtimeTimer;
  let bootstrapTimer;

  function formatMoneyFromCents(value) {
    if (value === null || value === undefined) return "—";
    return `${(Number(value) / 100).toLocaleString("ru-RU", {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    })} ₽`;
  }

  function formatMl(value) {
    return `${Math.max(Number(value) || 0, 0).toLocaleString("ru-RU")} мл`;
  }

  function formatAbv(value) {
    if (value === null || value === undefined || value === "") return "";
    return `${String(value).replace(".", ",")}%`;
  }

  async function refreshBootstrap() {
    try {
      const response = await fetch("/local/display/bootstrap");
      if (!response.ok) throw new Error(`bootstrap_http_${response.status}`);
      bootstrap.set(await response.json());
      bootstrapError.set(null);
    } catch (error) {
      bootstrapError.set(error.message);
    }
  }

  async function refreshRuntime() {
    try {
      const response = await fetch("/local/display/runtime");
      if (!response.ok) throw new Error(`runtime_http_${response.status}`);
      runtimePayload.set(await response.json());
      runtimeError.set(null);
    } catch (error) {
      runtimeError.set(error.message);
    } finally {
      const phase = get(runtimePayload)?.runtime?.phase ?? "idle";
      const nextDelay = isFastRuntimePhase(phase) ? FAST_RUNTIME_POLL_MS : SLOW_RUNTIME_POLL_MS;
      clearTimeout(runtimeTimer);
      runtimeTimer = window.setTimeout(refreshRuntime, nextDelay);
    }
  }

  function resolveServiceUi(state, { copy, theme }) {
    if (state.code === "booting") {
      return {
        kind: "service",
        tone: "neutral",
        headline: "Загрузка экрана",
        secondary: "Подождите",
        tertiary: null,
        code: "booting",
        accentColor: "#475569",
      };
    }

    if (state.code === "no_connection") {
      const message = serviceCopy.no_connection;
      return {
        kind: "service",
        tone: message.tone,
        headline: message.headline,
        secondary: message.nextStep,
        tertiary: null,
        code: message.code,
        accentColor: "#9A6B28",
      };
    }

    if (state.code === "no_keg" || state.code === "empty") {
      const message = serviceCopy.no_keg;
      return {
        kind: "service",
        tone: message.tone,
        headline: copy.fallback_title || message.headline,
        secondary: copy.fallback_subtitle || message.nextStep,
        tertiary: null,
        code: state.code,
        accentColor: "#475569",
      };
    }

    if (state.code === "maintenance" || state.code === "cleaning" || state.code === "locked") {
      const message = serviceCopy.maintenance;
      return {
        kind: "service",
        tone: message.tone,
        headline: copy.maintenance_title || message.headline,
        secondary: copy.maintenance_subtitle || message.nextStep,
        tertiary: null,
        code: state.code,
        accentColor: state.code === "cleaning" ? "#2563EB" : "#334155",
      };
    }

    const message = serviceCopy[state.code] ?? serviceCopy.maintenance;
    const accentColorByCode = {
      controller_runtime_stale: "#9A6B28",
      emergency_stop: "#B91C1C",
    };

    return {
      kind: "service",
      tone: message.tone,
      headline: message.headline,
      secondary: message.nextStep,
      tertiary: null,
      code: message.code,
      accentColor: accentColorByCode[state.code] ?? "#334155",
      backgroundUrl: theme.background_asset?.content_url ?? null,
    };
  }

  function buildIdleUi({ presentation, pricing, copy, theme }) {
    return {
      kind: "idle",
      tone: "brand",
      headline: presentation.name,
      secondary: pricing.display_text,
      tertiary: [presentation.style, formatAbv(presentation.abv)].filter(Boolean).join(" / "),
      description: presentation.description_short,
      brand: presentation.brand_name || presentation.brewery,
      instruction: copy.idle_instruction || "Приложите карту",
      accentColor: theme.accent_color ?? "#C79A3B",
      backgroundUrl: theme.background_asset?.content_url ?? null,
      logoUrl: theme.logo_asset?.content_url ?? null,
    };
  }

  function resolveUiState({ bootstrap, runtimePayload, bootstrapError, runtimeError }) {
    const state = resolveDisplayState({ bootstrap, runtimePayload, bootstrapError, runtimeError });
    const snapshot = state.snapshot;
    const runtime = state.runtime;
    const copy = getSnapshotCopy(snapshot);
    const presentation = snapshot?.presentation ?? {};
    const pricing = snapshot?.pricing ?? {};
    const theme = snapshot?.theme ?? {};
    const warning = state.warning ? "Нет связи с системой" : null;

    if (state.kind === "denied") {
      const message = deniedCopy[runtime.reason_code] ?? deniedCopy.authorize_rejected;
      return {
        kind: "denied",
        tone: "warning",
        headline: message.headline,
        secondary: message.nextStep,
        tertiary: "Заберите карту",
        code: runtime.reason_code,
        accentColor: "#D97706",
      };
    }

    if (state.kind === "service") {
      return resolveServiceUi(state, { copy, theme });
    }

    if (state.kind === "authorized" && state.code === "authorizing") {
      if (
        snapshot &&
        authorizingStartedAtMs !== null &&
        Date.now() - authorizingStartedAtMs < AUTHORIZING_UI_GRACE_MS
      ) {
        return buildIdleUi({ presentation, pricing, copy, theme });
      }

      return {
        kind: "authorized",
        tone: "brand",
        headline: "Подождите",
        secondary: "Проверяем карту",
        tertiary: null,
        accentColor: theme.accent_color ?? "#C79A3B",
        backgroundUrl: theme.background_asset?.content_url ?? null,
      };
    }

    if (state.kind === "authorized") {
      return {
        kind: "authorized",
        tone: "brand",
        headline: "Откройте кран",
        secondary: runtime.guest_first_name
          ? `${runtime.guest_first_name}, можно наливать`
          : "Можно наливать",
        tertiary: formatMoneyFromCents(runtime.balance_cents_at_authorize),
        accentColor: theme.accent_color ?? "#C79A3B",
        backgroundUrl: theme.background_asset?.content_url ?? null,
        logoUrl: theme.logo_asset?.content_url ?? null,
        warning,
        priceChip: pricing.display_text,
      };
    }

    if (state.kind === "pouring") {
      return {
        kind: "pouring",
        tone: "brand",
        headline: formatMl(runtime.current_volume_ml),
        secondary: formatMoneyFromCents(runtime.current_cost_cents),
        tertiary: formatMoneyFromCents(runtime.projected_remaining_balance_cents),
        metaLabel: runtime.guest_first_name || presentation.name || "",
        accentColor: theme.accent_color ?? "#C79A3B",
        backgroundUrl: theme.background_asset?.content_url ?? null,
        progress: state.progress,
        warning,
      };
    }

    if (state.kind === "finished") {
      return {
        kind: "finished",
        tone: "brand",
        headline: formatMl(runtime.current_volume_ml),
        secondary: formatMoneyFromCents(runtime.current_cost_cents),
        tertiary: formatMoneyFromCents(runtime.projected_remaining_balance_cents),
        accentColor: theme.accent_color ?? "#C79A3B",
        backgroundUrl: theme.background_asset?.content_url ?? null,
        logoUrl: theme.logo_asset?.content_url ?? null,
        warning: state.warning ? "Ожидается синхронизация" : null,
      };
    }

    return buildIdleUi({ presentation, pricing, copy, theme });
  }

  let ui = resolveUiState({
    bootstrap: null,
    runtimePayload: null,
    bootstrapError: null,
    runtimeError: null,
  });

  $: {
    const phase = $runtimePayload?.runtime?.phase ?? "idle";
    if (phase === "authorizing") {
      authorizingStartedAtMs ??= Date.now();
    } else {
      authorizingStartedAtMs = null;
    }
  }

  $: ui = resolveUiState({
    bootstrap: $bootstrap,
    runtimePayload: $runtimePayload,
    bootstrapError: $bootstrapError,
    runtimeError: $runtimeError,
  });
  $: uiStyle = `--accent:${ui?.accentColor ?? "#C79A3B"}`;

  onMount(() => {
    refreshBootstrap();
    refreshRuntime();
    bootstrapTimer = window.setInterval(refreshBootstrap, BOOTSTRAP_POLL_MS);
    return () => {
      clearInterval(bootstrapTimer);
      clearTimeout(runtimeTimer);
    };
  });
</script>

<svelte:head>
  <title>Tap Display</title>
</svelte:head>

<main class={`screen ${ui?.kind ?? "service"} ${ui?.tone ?? "neutral"}`} style={uiStyle}>
  {#if ui?.backgroundUrl && ui.kind !== "service"}
    <div class="background" style={`background-image:url(${ui.backgroundUrl})`}></div>
  {/if}
  <div class="overlay"></div>

  {#if ui?.warning}
    <div class="warning-pill">{ui.warning}</div>
  {/if}

  <section class="content">
    {#if ui?.kind === "idle"}
      <div class="meta">
        {#if ui.brand}<span>{ui.brand}</span>{/if}
        {#if ui.logoUrl}<img class="logo" src={ui.logoUrl} alt="" />{/if}
      </div>
      <h1>{ui.headline}</h1>
      <div class="secondary-row">
        <div class="price-chip">{ui.secondary}</div>
        {#if ui.tertiary}<span class="meta-text">{ui.tertiary}</span>{/if}
      </div>
      {#if ui.description}<p class="description">{ui.description}</p>{/if}
      <div class="instruction">{ui.instruction}</div>
    {:else if ui?.kind === "authorized"}
      <div class="status-label">Готово к наливу</div>
      <h1>{ui.headline}</h1>
      <p class="lead">{ui.secondary}</p>
      <div class="stats-grid">
        <div>
          <span class="stat-label">Баланс</span>
          <strong>{ui.tertiary}</strong>
        </div>
        {#if ui.priceChip}
          <div>
            <span class="stat-label">Цена</span>
            <strong>{ui.priceChip}</strong>
          </div>
        {/if}
      </div>
    {:else if ui?.kind === "pouring"}
      <div class="pour-layout">
        <div class="ring-wrap">
          <svg viewBox="0 0 240 240" class="progress-ring" aria-hidden="true">
            <circle class="track" cx="120" cy="120" r="90"></circle>
            <circle
              class="progress"
              cx="120"
              cy="120"
              r="90"
              stroke-dasharray={565.48}
              stroke-dashoffset={565.48 * (1 - ui.progress)}
            ></circle>
          </svg>
          <div class="ring-center">
            <span class="meta-text">{ui.metaLabel}</span>
            <h1>{ui.headline}</h1>
          </div>
        </div>
        <div class="stats-grid">
          <div>
            <span class="stat-label">Сумма</span>
            <strong>{ui.secondary}</strong>
          </div>
          <div>
            <span class="stat-label">Остаток после списания</span>
            <strong>{ui.tertiary}</strong>
          </div>
        </div>
      </div>
    {:else if ui?.kind === "finished"}
      <div class="status-label">Налив завершён</div>
      <h1>{ui.headline}</h1>
      <div class="stats-grid">
        <div>
          <span class="stat-label">Сумма</span>
          <strong>{ui.secondary}</strong>
        </div>
        <div>
          <span class="stat-label">Остаток после списания</span>
          <strong>{ui.tertiary}</strong>
        </div>
      </div>
      <div class="instruction">Заберите карту</div>
    {:else if ui?.kind === "denied"}
      <div class="status-label">Налив недоступен</div>
      <h1>{ui.headline}</h1>
      <p class="lead">{ui.secondary}</p>
      <div class="instruction">{ui.tertiary}</div>
      {#if ui.code}<div class="operator-code">{ui.code}</div>{/if}
    {:else}
      <div class="status-label">Сервисное состояние</div>
      <h1>{ui?.headline}</h1>
      <p class="lead">{ui?.secondary}</p>
      {#if ui?.tertiary}<div class="instruction">{ui.tertiary}</div>{/if}
      {#if ui?.code}<div class="operator-code">{ui.code}</div>{/if}
    {/if}
  </section>
</main>

<style>
  :global(html, body, #app) {
    width: 100%;
    height: 100%;
    margin: 0;
  }

  :global(body) {
    font-family: "Onest", "Golos Text", "Segoe UI", sans-serif;
    background: #0f172a;
    color: #f8fafc;
    overflow: hidden;
  }

  .screen {
    --accent: #c79a3b;
    position: relative;
    min-height: 100%;
    padding: 28px;
    display: grid;
    place-items: stretch;
    background:
      radial-gradient(circle at 85% 20%, color-mix(in srgb, var(--accent) 38%, transparent), transparent 28%),
      linear-gradient(135deg, #0f172a, #111827 55%, #1f2937);
    isolation: isolate;
  }

  .background,
  .overlay {
    position: absolute;
    inset: 0;
  }

  .background {
    background-size: cover;
    background-position: center;
    filter: saturate(0.9);
    transform: scale(1.03);
  }

  .overlay {
    background:
      linear-gradient(180deg, rgba(15, 23, 42, 0.2), rgba(15, 23, 42, 0.72)),
      linear-gradient(135deg, rgba(7, 12, 24, 0.4), rgba(7, 12, 24, 0.78));
    z-index: 0;
  }

  .screen.service .overlay,
  .screen.denied .overlay {
    background: linear-gradient(135deg, rgba(15, 23, 42, 0.96), rgba(30, 41, 59, 0.98));
  }

  .screen.warning {
    background: linear-gradient(135deg, #3f2a0c, #1f2937);
  }

  .screen.danger {
    background: linear-gradient(135deg, #3a1010, #1f2937);
  }

  .content {
    position: relative;
    z-index: 1;
    display: grid;
    align-content: space-between;
    min-height: calc(100vh - 56px);
    max-width: 100%;
  }

  .meta,
  .secondary-row,
  .stats-grid,
  .pour-layout {
    display: flex;
    align-items: center;
  }

  .meta,
  .secondary-row {
    justify-content: space-between;
    gap: 18px;
  }

  .meta {
    font-size: 16px;
    color: rgba(241, 245, 249, 0.9);
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }

  .logo {
    max-height: 44px;
    max-width: 120px;
    object-fit: contain;
    filter: drop-shadow(0 12px 20px rgba(0, 0, 0, 0.25));
  }

  h1 {
    margin: 12px 0 0;
    font-size: clamp(44px, 8vw, 88px);
    line-height: 0.95;
    letter-spacing: -0.04em;
    max-width: 12ch;
  }

  .lead {
    margin: 12px 0 0;
    font-size: clamp(22px, 3.6vw, 34px);
    line-height: 1.15;
    max-width: 22ch;
    color: rgba(241, 245, 249, 0.94);
  }

  .description {
    margin: 16px 0 0;
    max-width: 34ch;
    font-size: 18px;
    line-height: 1.35;
    color: rgba(226, 232, 240, 0.88);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .instruction {
    margin-top: 22px;
    display: inline-flex;
    align-items: center;
    gap: 12px;
    align-self: end;
    padding: 14px 18px;
    border-radius: 999px;
    background: color-mix(in srgb, var(--accent) 26%, rgba(15, 23, 42, 0.65));
    border: 1px solid color-mix(in srgb, var(--accent) 50%, rgba(255, 255, 255, 0.08));
    font-size: clamp(24px, 3vw, 30px);
    font-weight: 700;
    max-width: fit-content;
  }

  .price-chip,
  .status-label,
  .warning-pill,
  .operator-code {
    display: inline-flex;
    align-items: center;
    max-width: fit-content;
    border-radius: 999px;
    font-weight: 700;
  }

  .price-chip,
  .status-label {
    padding: 10px 14px;
    font-size: 16px;
    background: rgba(15, 23, 42, 0.48);
    border: 1px solid rgba(255, 255, 255, 0.14);
  }

  .warning-pill {
    position: absolute;
    top: 18px;
    right: 18px;
    z-index: 2;
    padding: 10px 14px;
    background: rgba(180, 83, 9, 0.92);
    color: white;
    font-size: 14px;
    letter-spacing: 0.03em;
  }

  .meta-text {
    font-size: clamp(16px, 2vw, 20px);
    color: rgba(226, 232, 240, 0.82);
  }

  .stats-grid {
    gap: 16px;
    margin-top: 22px;
    flex-wrap: wrap;
  }

  .stats-grid > div {
    min-width: 220px;
    padding: 18px 20px;
    border-radius: 22px;
    background: rgba(15, 23, 42, 0.48);
    border: 1px solid rgba(255, 255, 255, 0.12);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
  }

  .stat-label {
    display: block;
    font-size: 14px;
    color: rgba(203, 213, 225, 0.78);
    margin-bottom: 8px;
  }

  .stats-grid strong {
    font-size: clamp(26px, 4vw, 36px);
    line-height: 1;
  }

  .pour-layout {
    justify-content: space-between;
    gap: 28px;
    flex-wrap: wrap;
  }

  .ring-wrap {
    position: relative;
    width: min(54vw, 420px);
    aspect-ratio: 1;
    display: grid;
    place-items: center;
  }

  .progress-ring {
    width: 100%;
    height: 100%;
    transform: rotate(-90deg);
  }

  .track,
  .progress {
    fill: none;
    stroke-width: 18;
  }

  .track {
    stroke: rgba(255, 255, 255, 0.12);
  }

  .progress {
    stroke: var(--accent);
    stroke-linecap: round;
    transition: stroke-dashoffset 180ms linear;
    filter: drop-shadow(0 0 18px color-mix(in srgb, var(--accent) 55%, transparent));
  }

  .ring-center {
    position: absolute;
    inset: 20%;
    display: grid;
    place-items: center;
    text-align: center;
  }

  .ring-center h1 {
    font-size: clamp(58px, 9vw, 88px);
    max-width: none;
    margin-top: 8px;
  }

  .operator-code {
    margin-top: 18px;
    padding: 8px 12px;
    font-size: 12px;
    letter-spacing: 0.08em;
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.12);
    color: rgba(203, 213, 225, 0.72);
    text-transform: uppercase;
  }

  @media (max-width: 900px) {
    .screen {
      padding: 20px;
    }

    .content {
      min-height: calc(100vh - 40px);
    }

    .stats-grid > div {
      min-width: 180px;
    }

    .ring-wrap {
      width: min(64vw, 340px);
    }
  }

  @media (max-width: 720px) {
    .screen {
      padding: 16px;
    }

    .warning-pill {
      top: 12px;
      right: 12px;
    }

    h1 {
      max-width: 100%;
    }

    .stats-grid {
      gap: 12px;
    }

    .stats-grid > div {
      width: 100%;
    }

    .instruction {
      width: 100%;
      justify-content: center;
    }
  }
</style>
