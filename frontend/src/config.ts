export const APP_ENV = import.meta.env.MODE ?? "development";
export const IS_PRODUCTION = import.meta.env.PROD || APP_ENV === "production";

const rawApiBaseUrl = String(import.meta.env.VITE_API_BASE_URL ?? "")
  .trim()
  .replace(/\/+$/, "");

export const API_BASE_URL = rawApiBaseUrl || (IS_PRODUCTION ? "" : "http://localhost:8000");
export const API_BASE_URL_CONFIGURED = Boolean(rawApiBaseUrl);
export const API_CONFIG_ERROR =
  IS_PRODUCTION && !rawApiBaseUrl ? "VITE_API_BASE_URL precisa ser configurado em producao." : "";

const rawDemoFallback = import.meta.env.VITE_ENABLE_DEMO_FALLBACK;

export const ENABLE_DEMO_FALLBACK =
  rawDemoFallback === undefined ? !IS_PRODUCTION : String(rawDemoFallback).toLowerCase() === "true";

export const diagnosticsConfig = {
  apiBaseUrl: API_BASE_URL || "nao configurado",
  apiBaseUrlConfigured: API_BASE_URL_CONFIGURED,
  appEnv: APP_ENV,
  demoFallbackEnabled: ENABLE_DEMO_FALLBACK,
  isProduction: IS_PRODUCTION,
};

export function apiUrl(path: string) {
  if (API_CONFIG_ERROR) {
    throw new Error(API_CONFIG_ERROR);
  }
  if (!API_BASE_URL) {
    throw new Error("API base URL nao configurada.");
  }
  return `${API_BASE_URL}${path}`;
}
