import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const repoRoot = resolve(import.meta.dirname, '..');
const loginPath = resolve(repoRoot, 'src/routes/Login.svelte');
const modalPath = resolve(repoRoot, 'src/components/system/ServerSettingsModal.svelte');

const [loginSource, modalSource] = await Promise.all([
  readFile(loginPath, 'utf8'),
  readFile(modalPath, 'utf8'),
]);

const checks = [
  {
    name: 'login form submits only via onSubmit handler',
    ok: /<form on:submit\|preventDefault=\{onSubmit\}>/.test(loginSource),
  },
  {
    name: 'settings button is explicit type=button in Login.svelte',
    ok: /<button type="button" class="secondary" on:click=\{openServerSettings\}>/.test(loginSource),
  },
  {
    name: 'settings button opens bound modal instance',
    ok: /await serverSettingsModal\?\.openModal\(\);/.test(loginSource),
  },
  {
    name: 'login page mounts modal without internal launcher',
    ok: /<ServerSettingsModal bind:this=\{serverSettingsModal\} showLauncher=\{false\} \/>/.test(loginSource),
  },
  {
    name: 'modal launcher defaults to type=button',
    ok: /export let launcherType = 'button';/.test(modalSource),
  },
  {
    name: 'modal launcher click prevents default before opening',
    ok: /async function handleLauncherClick\(event\) \{\s*event\?\.preventDefault\(\);\s*await openModal\(\);/s.test(
      modalSource
    ),
  },
];

const failed = checks.filter((check) => !check.ok);

for (const check of checks) {
  console.log(`[SMOKE] ${check.ok ? 'OK' : 'FAIL'}: ${check.name}`);
}

if (failed.length > 0) {
  throw new Error(`login settings smoke failed: ${failed.map((check) => check.name).join('; ')}`);
}
