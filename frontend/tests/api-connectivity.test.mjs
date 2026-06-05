import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

const root = process.cwd();

function read(path) {
  return readFileSync(join(root, path), "utf8");
}

test("frontend centralizes API configuration and healthcheck", () => {
  const config = read("src/config.ts");
  const api = read("src/api.ts");

  assert.match(config, /VITE_API_BASE_URL/);
  assert.match(config, /VITE_ENABLE_DEMO_FALLBACK/);
  assert.match(config, /http:\/\/localhost:8000/);
  assert.match(api, /checkApiHealth/);
  assert.match(api, /\/health/);
  assert.match(api, /fallbackUsed/);
});

test("widget makes offline and demo states explicit", () => {
  const widget = read("src/components/ChatWidget.tsx");

  assert.match(widget, /Modo demonstracao/);
  assert.match(widget, /Tentar reconectar/);
  assert.match(widget, /apiStatus === "checking"/);
  assert.match(widget, /apiStatus !== "online"/);
  assert.match(widget, /Para enviar conta de energia/);
  assert.match(widget, /offlineMessage/);
  assert.match(widget, /!ENABLE_DEMO_FALLBACK/);
  assert.doesNotMatch(widget, /suba o backend/i);
});

test("admin dashboard exposes local diagnostic panel", () => {
  const dashboard = read("src/components/AdminDashboard.tsx");

  assert.match(dashboard, /DiagnosticsView/);
  assert.match(dashboard, /Diagnostico local/);
  assert.match(dashboard, /checkApiHealth/);
  assert.match(dashboard, /API base URL/);
});
