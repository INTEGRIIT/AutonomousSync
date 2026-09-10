import * as Notifications from "expo-notifications";
import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";
import * as Device from "expo-device";
import { BASE_URL } from "../../config";

// CONFIG
const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 1200;

// STORAGE KEYS
const TOKEN_KEY = "push_token";
const ENV_KEY = "push_env";
const UID_KEY = "push_uid";

// UTIL
const sleep = (ms) => new Promise((res) => setTimeout(res, ms));

// =====================================================
// 🌍 ENV DETECTION
// =====================================================
function getEnvironment() {
  return __DEV__ ? "sandbox" : "production";
}

// =====================================================
// 🔐 PERMISSIONS
// =====================================================
async function requestPermissions() {
  const { status } = await Notifications.getPermissionsAsync();

  if (status !== "granted") {
    const req = await Notifications.requestPermissionsAsync();
    return req.status === "granted";
  }

  return true;
}

// =====================================================
// 📲 GET TOKEN (iOS + Android)
// =====================================================
async function getPushToken() {
  try {
    if (!Device.isDevice) {
      console.log("❌ Must use real device");
      return null;
    }

    // Native device token on both platforms:
    // iOS -> APNs hex token, Android -> FCM registration token.
    // getExpoPushTokenAsync returns an Expo relay token that
    // firebase_admin cannot send to.
    const tokenData = await Notifications.getDevicePushTokenAsync();
    const token = tokenData?.data;

    if (!token) {
      console.log("❌ No token returned");
      return null;
    }

    console.log("📲 TOKEN:", token.slice(0, 20) + "...");
    console.log("📱 PLATFORM:", Platform.OS);

    return token;

  } catch (err) {
    console.log("❌ token error:", err);
    return null;
  }
}

// =====================================================
// 🚀 REGISTER DEVICE (FIXED)
// =====================================================
export async function registerForPush(deviceUid, deviceName) {
  if (!deviceUid || !deviceName) {
    console.log("❌ missing device info");
    return null;
  }

  try {
    const currentEnv = getEnvironment();
    console.log("🌍 ENV:", currentEnv);

    // =====================================================
    // 🔥 DO NOT SKIP REGISTRATION (CRITICAL FIX)
    // =====================================================
    const storedToken = await SecureStore.getItemAsync(TOKEN_KEY);

    if (storedToken) {
      console.log("🔁 token exists → re-registering with backend");
    } else {
      console.log("🆕 no token → fresh registration");
    }

    // =====================================================
    // PERMISSIONS
    // =====================================================
    const granted = await requestPermissions();
    if (!granted) {
      console.log("❌ permission denied");
      return null;
    }

    // =====================================================
    // GET TOKEN
    // =====================================================
    const token = await getPushToken();
    if (!token) return null;

    console.log("🆕 TOKEN READY");

    // =====================================================
    // REGISTER WITH BACKEND (ALWAYS)
    // =====================================================
    let success = false;

    for (let i = 1; i <= MAX_RETRIES; i++) {
      try {
        console.log("🔁 register attempt", i);

        const res = await fetch(`${BASE_URL}/push/register`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            device_uid: deviceUid,
            device_name: deviceName,
            push_token: token,
            platform: Platform.OS,   // 🔥 REQUIRED
            env: currentEnv,         // 🔥 REQUIRED
          }),
        });

        const text = await res.text();

        console.log("📡 response:", res.status, text);

        if (res.ok) {
          console.log("✅ backend registration success");
          success = true;
          break;
        }

      } catch (err) {
        console.log("❌ register error:", err);
      }

      await sleep(RETRY_DELAY_MS);
    }

    if (!success) {
      console.log("❌ registration failed");
      return null;
    }

    // =====================================================
    // STORE LOCALLY (CACHE ONLY — NOT SOURCE OF TRUTH)
    // =====================================================
    await SecureStore.setItemAsync(TOKEN_KEY, token);
    await SecureStore.setItemAsync(ENV_KEY, currentEnv);
    await SecureStore.setItemAsync(UID_KEY, deviceUid);

    console.log("💾 stored push state");

    return token;

  } catch (err) {
    console.log("❌ push fatal error:", err);
    return null;
  }
}