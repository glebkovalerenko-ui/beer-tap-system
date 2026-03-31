import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const repoRoot = resolve(import.meta.dirname, '..');

const appPath = resolve(repoRoot, 'src/App.svelte');
const actionRoutingPath = resolve(repoRoot, 'src/lib/actionRouting.js');
const routeCopyPath = resolve(repoRoot, 'src/lib/operator/routeCopy.js');

const routeFiles = {
  'Смена': 'src/routes/Today.svelte',
  'Визиты': 'src/routes/Visits.svelte',
  'Гости': 'src/routes/Guests.svelte',
  'Краны': 'src/routes/TapsWorkspace.svelte',
  'Потерянные карты': 'src/routes/LostCards.svelte',
  'Наливы': 'src/routes/Pours.svelte',
  'Кеги и напитки': 'src/routes/KegsBeverages.svelte',
  'Инциденты': 'src/routes/Incidents.svelte',
  'Система': 'src/routes/System.svelte',
  'Настройки': 'src/routes/Settings.svelte',
  'Справка': 'src/routes/Help.svelte',
};

const [appSource, actionRoutingSource, routeCopySource, ...routeSources] = await Promise.all([
  readFile(appPath, 'utf8'),
  readFile(actionRoutingPath, 'utf8'),
  readFile(routeCopyPath, 'utf8'),
  ...Object.values(routeFiles).map((file) => readFile(resolve(repoRoot, file), 'utf8')),
]);

const routeSourceByLabel = Object.fromEntries(Object.keys(routeFiles).map((label, index) => [label, routeSources[index]]));

const checks = [
  {
    name: 'routeCopy содержит финальные IA-лейблы primary nav',
    ok: [
      "label: 'Визиты'",
      "label: 'Гости'",
      "label: 'Краны'",
      "label: 'Потерянные карты'",
      "label: 'Наливы'",
      "label: 'Кеги и напитки'",
      "label: 'Инциденты'",
      "label: 'Система'",
    ].every((token) => routeCopySource.includes(token)),
  },
  {
    name: 'routeCopy содержит support nav лейблы',
    ok: ["label: 'Настройки'", "label: 'Справка'"].every((token) => routeCopySource.includes(token)),
  },
  {
    name: 'App использует routeCopy для primary и support nav',
    ok: [
      'ROUTE_COPY.visits.label',
      'ROUTE_COPY.guests.label',
      'ROUTE_COPY.taps.label',
      'ROUTE_COPY.lostCards.label',
      'ROUTE_COPY.pours.label',
      'ROUTE_COPY.kegsBeverages.label',
      'ROUTE_COPY.incidents.label',
      'ROUTE_COPY.system.label',
      'ROUTE_COPY.settings.label',
      'ROUTE_COPY.help.label',
    ].every((token) => appSource.includes(token)),
  },
  {
    name: 'home и legacy alias ведут в экран Смена',
    ok: [
      "'/': Today",
      "'/shift': Today",
      "'/today': Today",
      "'*': Today",
    ].every((token) => appSource.includes(token)),
  },
  {
    name: 'legacy alias визитов и гостей ведут в канонические operator screens',
    ok: [
      "'/visits': Visits",
      "'/sessions': Sessions",
      "'/sessions/history': Sessions",
      "'/guests': Guests",
      "'/cards-guests': Guests",
      "'/tap-screens': KegsBeverages",
    ].every((token) => appSource.includes(token)),
  },
  {
    name: 'action routing ведёт в canonical маршруты оператора',
    ok: [
      "window.location.hash = '/taps';",
      "window.location.hash = '/visits';",
      "window.location.hash = '/guests';",
      "window.location.hash = '/pours';",
      "window.location.hash = '/incidents';",
      "window.location.hash = '/system';",
      "window.location.hash = '/shift';",
    ].every((token) => actionRoutingSource.includes(token)),
  },
  {
    name: 'action-routing CTA остаются операторскими',
    ok: [
      "tap: 'Открыть кран'",
      "visit: 'Открыть визит'",
      "guest: 'Открыть гостя'",
      "pour: 'Открыть налив'",
      "incident: 'Открыть инцидент'",
      "system: 'Открыть систему'",
    ].every((token) => actionRoutingSource.includes(token)),
  },
  ...Object.entries(routeSourceByLabel).map(([label, source]) => ({
    name: `h1 страницы совпадает с меню: ${label}`,
    ok: source.includes(`<h1>${label}</h1>`) || source.includes('.title}</h1>'),
  })),
];

const failed = checks.filter((check) => !check.ok);
for (const check of checks) {
  console.log(`[SMOKE] ${check.ok ? 'OK' : 'FAIL'}: ${check.name}`);
}

if (failed.length > 0) {
  throw new Error(`navigation IA smoke failed: ${failed.map((check) => check.name).join('; ')}`);
}
