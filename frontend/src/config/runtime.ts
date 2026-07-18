/**
 * Runtime URLs are centralized so the static build works locally and behind
 * any HTTPS host (CloudFront today, a custom domain later) without rebuilding.
 */
function configuredValue(value: string | undefined): string | undefined {
  return value?.trim().replace(/\/$/, "") || undefined;
}

export function getApiBaseUrl(): string {
  return configuredValue(import.meta.env.VITE_API_BASE_URL) ?? window.location.origin;
}

export function getWebSocketUrl(): string {
  const configured = configuredValue(import.meta.env.VITE_WS_URL);
  if (configured) return configured;
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/ws/live`;
}
