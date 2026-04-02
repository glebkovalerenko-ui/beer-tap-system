import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const currentDir = path.dirname(fileURLToPath(import.meta.url));

const ACTIVE_OPERATOR_FILES = [
  '../../routes/Visits.svelte',
  '../../routes/LostCards.svelte',
  '../../routes/Guests.svelte',
  '../../routes/KegsBeverages.svelte',
  '../../routes/System.svelte',
  '../../routes/Help.svelte',
  '../../routes/Today.svelte',
  '../../routes/Pours.svelte',
  '../../routes/Incidents.svelte',
  '../../routes/TapScreens.svelte',
  '../../routes/TapsWorkspace.svelte',
  '../../components/beverages/BeverageManager.svelte',
  '../../components/common/DataFreshnessChip.svelte',
  '../../components/guests/CardLookupPanel.svelte',
  '../../components/shell/ShellStatusPills.svelte',
  '../../components/sessions/SessionHistoryDetailDrawer.svelte',
  '../../components/system/SystemFallbackBanner.svelte',
  '../../components/system/SystemHealthSummary.svelte',
  '../../components/system/DebugManagementEntry.svelte',
  '../../components/taps/TapCard.svelte',
  '../../components/taps/TapDrawer.svelte',
  '../../components/taps/TapDisplaySettingsModal.svelte',
  '../../stores/tapStore.js',
  '../../stores/systemStore.js',
  '../../stores/incidentStore.js',
  '../../stores/visitStore.js',
  '../../stores/roleStore.js',
  '../../lib/actionRouting.js',
  '../../lib/criticalActionMatrix.js',
  '../../lib/formatters.js',
  '../../lib/incidentsViewModel.js',
  '../../lib/operatorLabels.js',
  '../../lib/operator/actionPolicyAdapter.js',
  '../../components/sessions/sessionNarrative.js',
];

const BANNED_PATTERNS = [
  { label: 'Read-only mode', pattern: /Read-only mode/g },
  { label: 'Read-only access', pattern: /Read-only доступ/g },
  { label: 'read-only mode', pattern: /read-only режим/gi },
  { label: 'Sale mode', pattern: /Sale mode/g },
  { label: 'Lifecycle', pattern: /Lifecycle/g },
  { label: 'Display context', pattern: /Display context/g },
  { label: 'Display state / availability', pattern: /Display state \/ availability/g },
  { label: 'Guest-facing title', pattern: /Guest-facing title/g },
  { label: 'Guest-facing subtitle', pattern: /Guest-facing subtitle/g },
  { label: 'guest-facing cards', pattern: /guest-facing карточек/g },
  { label: 'Support / dev', pattern: /Support \/ dev/g },
  { label: 'Operational health', pattern: /Operational health/g },
  { label: 'Read-only overview', pattern: /Read-only overview/g },
  { label: 'Advanced access', pattern: /Advanced access/g },
  { label: 'permission gate', pattern: /permission gate/g },
  { label: 'operator playbooks', pattern: /operator playbooks/g },
  { label: 'operator workflow', pattern: /operator workflow/g },
  { label: 'Activity trail', pattern: /Activity trail/g },
  { label: 'Debug / management', pattern: /Debug \/ management/g },
  { label: 'debug / management', pattern: /debug \/ management/g },
  { label: 'management actions', pattern: /management-(действий|инструменты)/g },
  { label: 'override content', pattern: /Override (контента|экрана крана)/g },
  { label: 'guest display', pattern: /guest display/g },
  { label: 'LostCard copy', pattern: /отметки?\s+LostCard/g },
  { label: 'lost copy', pattern: /(?:Снять|отмена|отметка)\s+lost\b/g },
  { label: 'recovery-flow', pattern: /recovery-flow/g },
  { label: 'blocked-lost message', pattern: /blocked-lost/g },
  { label: 'service-close', pattern: /service-close/gi },
  { label: 'normal flow', pattern: /normal flow/g },
  { label: 'NFC scan path', pattern: /NFC scan path/g },
  { label: 'operator lookup', pattern: /Единый lookup/g },
  { label: 'operator flow', pattern: /operator flow/g },
  { label: 'reuse', pattern: /\breuse\b/g },
  { label: 'inventory pool', pattern: /inventory pool/g },
  { label: 'SOP', pattern: /\bSOP\b/g },
  { label: 'Playbooks', pattern: /\bPlaybooks\b/g },
  { label: 'DemoGuide', pattern: /\bDemoGuide\b/g },
  { label: 'Tap Display copy', pattern: /Tap Display/g },
  { label: 'Fallback copy', pattern: /Fallback (для|:)/g },
  { label: 'fallback signature', pattern: /fallback-подпись/g },
  { label: 'override copy', pattern: /override гостевого экрана|override экрана|Сводка override|override недоступна/g },
  { label: 'backend user wording', pattern: /Ожидание backend|не подтверждены backend|от backend|с backend|с бэкендом/g },
  { label: 'sync wording', pattern: /Проверить sync/g },
  { label: 'permission key leak', pattern: /правом taps_control/g },
  { label: 'system blocked actions', pattern: /Emergency stop|Incident mutation|Session mutation|Tap control/g },
  { label: 'system next step english', pattern: /No blocked actions right now|continue regular shift workflow/g },
  { label: 'tap runtime english', pattern: /Controller heartbeat stale|display assigned|reader ready|Line is quiet and ready for the next operator action/g },
  { label: 'incident type english', pattern: /Visit force unlock|Closed valve flow|flow-closed-valve/g },
];

test('active operator surfaces avoid banned mixed-language copy', () => {
  const findings = [];

  for (const relativePath of ACTIVE_OPERATOR_FILES) {
    const absolutePath = path.resolve(currentDir, relativePath);
    const source = readFileSync(absolutePath, 'utf8');

    for (const { label, pattern } of BANNED_PATTERNS) {
      pattern.lastIndex = 0;
      if (pattern.test(source)) {
        findings.push(`${relativePath}: ${label}`);
      }
    }
  }

  assert.deepEqual(findings, []);
});
