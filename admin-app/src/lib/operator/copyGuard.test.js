import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const currentDir = path.dirname(fileURLToPath(import.meta.url));

const ACTIVE_OPERATOR_FILES = [
  '../../routes/System.svelte',
  '../../routes/Help.svelte',
  '../../routes/Today.svelte',
  '../../routes/Pours.svelte',
  '../../routes/Incidents.svelte',
  '../../routes/TapsWorkspace.svelte',
  '../../components/common/DataFreshnessChip.svelte',
  '../../components/shell/ShellStatusPills.svelte',
  '../../components/system/SystemFallbackBanner.svelte',
  '../../components/system/SystemHealthSummary.svelte',
  '../../components/system/DebugManagementEntry.svelte',
  '../../components/taps/TapDrawer.svelte',
  '../../components/sessions/sessionNarrative.js',
];

const BANNED_PATTERNS = [
  { label: 'Read-only mode', pattern: /Read-only mode/g },
  { label: 'Sale mode', pattern: /Sale mode/g },
  { label: 'Lifecycle', pattern: /Lifecycle/g },
  { label: 'Display context', pattern: /Display context/g },
  { label: 'Display state / availability', pattern: /Display state \/ availability/g },
  { label: 'Guest-facing title', pattern: /Guest-facing title/g },
  { label: 'Guest-facing subtitle', pattern: /Guest-facing subtitle/g },
  { label: 'Support / dev', pattern: /Support \/ dev/g },
  { label: 'Operational health', pattern: /Operational health/g },
  { label: 'Read-only overview', pattern: /Read-only overview/g },
  { label: 'Advanced access', pattern: /Advanced access/g },
  { label: 'permission gate', pattern: /permission gate/g },
  { label: 'operator playbooks', pattern: /operator playbooks/g },
  { label: 'operator workflow', pattern: /operator workflow/g },
  { label: 'Activity trail', pattern: /Activity trail/g },
  { label: 'Debug / management', pattern: /Debug \/ management/g },
  { label: 'SOP', pattern: /\bSOP\b/g },
  { label: 'Playbooks', pattern: /\bPlaybooks\b/g },
  { label: 'DemoGuide', pattern: /\bDemoGuide\b/g },
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
