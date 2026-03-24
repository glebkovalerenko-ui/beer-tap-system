import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const repoRoot = resolve(import.meta.dirname, '..');

const appPath = resolve(repoRoot, 'src/App.svelte');
const actionRoutingPath = resolve(repoRoot, 'src/lib/actionRouting.js');

const routeFiles = {
  'Сегодня': 'src/routes/Today.svelte',
  'Краны': 'src/routes/TapsWorkspace.svelte',
  'Сессии': 'src/routes/Sessions.svelte',
  'Карты и гости': 'src/routes/CardsGuests.svelte',
  'Кеги и напитки': 'src/routes/KegsBeverages.svelte',
  'Инциденты': 'src/routes/Incidents.svelte',
  'Экраны кранов': 'src/routes/TapScreens.svelte',
  'Система': 'src/routes/System.svelte',
  'Настройки': 'src/routes/Settings.svelte',
  'Справка / регламенты': 'src/routes/Help.svelte',
};

const [appSource, actionRoutingSource, ...routeSources] = await Promise.all([
  readFile(appPath, 'utf8'),
  readFile(actionRoutingPath, 'utf8'),
  ...Object.values(routeFiles).map((file) => readFile(resolve(repoRoot, file), 'utf8')),
]);

const routeSourceByLabel = Object.fromEntries(Object.keys(routeFiles).map((label, index) => [label, routeSources[index]]));

const checks = [
  {
    name: 'primaryNav содержит финальные IA-лейблы',
    ok: [
      "label: 'Сегодня'",
      "label: 'Краны'",
      "label: 'Сессии'",
      "label: 'Карты и гости'",
      "label: 'Кеги и напитки'",
      "label: 'Инциденты'",
      "label: 'Экраны кранов'",
      "label: 'Система'",
    ].every((token) => appSource.includes(token)),
  },
  {
    name: 'supportNav содержит Настройки и Справка / регламенты',
    ok: ["label: 'Настройки'", "label: 'Справка / регламенты'"].every((token) => appSource.includes(token)),
  },
  {
    name: 'route alias / и /today направляют на Today',
    ok: /'\/':\s*Today,\s*'\/today':\s*Today/s.test(appSource),
  },
  {
    name: 'route alias /sessions/history направляет на Sessions',
    ok: /'\/sessions':\s*Sessions,\s*'\/sessions\/history':\s*Sessions/s.test(appSource),
  },
  {
    name: 'action routing ведёт в canonical маршруты оператора',
    ok: [
      "window.location.hash = '/taps';",
      "window.location.hash = '/sessions';",
      "window.location.hash = '/incidents';",
      "window.location.hash = '/system';",
      "window.location.hash = href || '/today';",
    ].every((token) => actionRoutingSource.includes(token)),
  },
  {
    name: 'action-routing CTA остаются операторскими',
    ok: [
      "tap: 'Открыть кран'",
      "session: 'Открыть сессию'",
      "incident: 'Открыть инцидент'",
      "system: 'Открыть систему'",
    ].every((token) => actionRoutingSource.includes(token)),
  },
  ...Object.entries(routeSourceByLabel).map(([label, source]) => ({
    name: `h1 страницы совпадает с меню: ${label}`,
    ok: source.includes(`<h1>${label}</h1>`),
  })),
];

const failed = checks.filter((check) => !check.ok);
for (const check of checks) {
  console.log(`[SMOKE] ${check.ok ? 'OK' : 'FAIL'}: ${check.name}`);
}

if (failed.length > 0) {
  throw new Error(`navigation IA smoke failed: ${failed.map((check) => check.name).join('; ')}`);
}
