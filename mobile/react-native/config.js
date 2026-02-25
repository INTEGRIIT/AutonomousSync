// mobile/react-native/config.js

// ==========================================
// ENVIRONMENT SWITCH
// ==========================================
// Change this to "local" if you want to test against localhost
// Otherwise keep it "cloud"
const ENV = "cloud";

// ==========================================
// LOCAL CONFIG (for development only)
// ==========================================
const LOCAL_CONFIG = {
  API_HOST: "localhost",
  API_PORT: 8012,
  WS_PROTOCOL: "ws",
};

// ==========================================
// CLOUD CONFIG (EC2)
// ==========================================
const CLOUD_CONFIG = {
  API_HOST: "3.80.27.210",   // Your EC2 Public IP
  API_PORT: 8012,
  WS_PROTOCOL: "ws",
};

// ==========================================
// SELECT ACTIVE CONFIG
// ==========================================
const ACTIVE = ENV === "local" ? LOCAL_CONFIG : CLOUD_CONFIG;

// ==========================================
// EXPORTS
// ==========================================
export const API_HOST = ACTIVE.API_HOST;
export const API_PORT = ACTIVE.API_PORT;
export const WS_PROTOCOL = ACTIVE.WS_PROTOCOL;

export const BASE_URL = `http://${API_HOST}:${API_PORT}`;
export const WS_URL = `${WS_PROTOCOL}://${API_HOST}:${API_PORT}`;