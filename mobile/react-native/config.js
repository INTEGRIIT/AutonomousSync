// ==========================================
// ENVIRONMENT SWITCH
// ==========================================
const ENV = "cloud";

// ==========================================
// LOCAL CONFIG (dev only)
// ==========================================
const LOCAL_CONFIG = {
  API_HOST: "localhost",
  API_PORT: 8012,
  WS_PROTOCOL: "ws",
};

// ==========================================
// CLOUD CONFIG (PRODUCTION)
// ==========================================
const CLOUD_CONFIG = {
  API_HOST: "api.autonomous-sync.com",
  WS_PROTOCOL: "wss",
};

// ==========================================
// SELECT ACTIVE CONFIG
// ==========================================
const ACTIVE = ENV === "local" ? LOCAL_CONFIG : CLOUD_CONFIG;

// ==========================================
// EXPORTS
// ==========================================
export const API_HOST = ACTIVE.API_HOST;

// HTTP vs HTTPS
export const BASE_URL =
  ENV === "local"
    ? `http://${API_HOST}:${LOCAL_CONFIG.API_PORT}`
    : `https://${API_HOST}`;

// WS vs WSS
export const WS_URL =
  ENV === "local"
    ? `ws://${API_HOST}:${LOCAL_CONFIG.API_PORT}/ws/stream`
    : `wss://${API_HOST}/ws/stream`;