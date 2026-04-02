import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const currentDir = path.dirname(fileURLToPath(import.meta.url));

test("tap display user-facing copy stays Russian in client and agent fallback", () => {
  const appSource = readFileSync(path.resolve(currentDir, "../src/App.svelte"), "utf8");
  const agentSource = readFileSync(path.resolve(currentDir, "../../tap-display-agent/main.py"), "utf8");

  assert.match(appSource, /<title>Экран крана<\/title>/);
  assert.doesNotMatch(appSource, /<title>Tap Display<\/title>/);

  assert.match(agentSource, /<title>Экран крана<\/title>/);
  assert.match(agentSource, /Сборка клиентского экрана не найдена/);
  assert.doesNotMatch(agentSource, /Display client build not found/);
});
