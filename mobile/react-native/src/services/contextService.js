// src/services/contextService.js
//
// Collects battery, network, and device context into refs so the
// telemetry send loop can read current values without stale-closure
// capture. The previous implementation read `batteryLevel` from React
// state inside setInterval, which captured the value at loop-creation
// time (null) and never updated.
//
// Requires:
//   npx expo install expo-battery expo-device expo-application expo-network

import * as Battery from "expo-battery";
import * as Device from "expo-device";
import * as Application from "expo-application";
import * as Network from "expo-network";
import { Platform } from "react-native";
import { BASE_URL } from "../../config";

// Battery level is quantised (often 1%, sometimes 5%), so a drain rate
// computed from two samples 15 s apart is mostly noise. Track a rolling
// window and derive the rate by least squares over it instead.
const DRAIN_WINDOW_MS = 5 * 60 * 1000;
const BATTERY_POLL_MS = 15000;
const NETWORK_POLL_MS = 10000;

function batteryStateName(s) {
  switch (s) {
    case Battery.BatteryState.CHARGING: return "charging";
    case Battery.BatteryState.FULL: return "full";
    case Battery.BatteryState.UNPLUGGED: return "unplugged";
    default: return "unknown";
  }
}

// Least-squares slope of level (%) against time (minutes).
// Positive result = discharging at that many percent per minute.
function drainRateFromHistory(hist) {
  if (hist.length < 3) return null;
  const t0 = hist[0].ts;
  const xs = hist.map((h) => (h.ts - t0) / 60000);
  const ys = hist.map((h) => h.level * 100);
  const n = xs.length;
  const mx = xs.reduce((a, b) => a + b, 0) / n;
  const my = ys.reduce((a, b) => a + b, 0) / n;
  let num = 0, den = 0;
  for (let i = 0; i < n; i++) {
    num += (xs[i] - mx) * (ys[i] - my);
    den += (xs[i] - mx) ** 2;
  }
  if (den === 0) return null;
  return -(num / den); // negate: falling level = positive drain
}

/**
 * Start context collection.
 *
 * @param {object} batteryRef  ref updated with BatteryState
 * @param {object} networkRef  ref updated with NetworkState
 * @param {object} deviceRef   ref updated once with DeviceContext
 * @returns {function} cleanup
 */
export function startContext(batteryRef, networkRef, deviceRef,
                             deviceUidRef, sessionRef, trialRef) {
  // ---- device context: static, resolve once ----
  deviceRef.current = {
    platform: Platform.OS,
    model: Device.modelName ?? null,
    os_version: Device.osVersion ?? null,
    app_version: Application.nativeApplicationVersion ?? null,
  };

  // ---- battery ----
  const history = [];

  const pollBattery = async () => {
    try {
      const [level, state, lowPower] = await Promise.all([
        Battery.getBatteryLevelAsync(),
        Battery.getBatteryStateAsync(),
        Battery.isLowPowerModeEnabledAsync(),
      ]);
      const now = Date.now();

      history.push({ ts: now, level });
      while (history.length && now - history[0].ts > DRAIN_WINDOW_MS) {
        history.shift();
      }

      const charging = state === Battery.BatteryState.CHARGING ||
                       state === Battery.BatteryState.FULL;

      batteryRef.current = {
        level,                                   // 0.0 - 1.0
        state: batteryStateName(state),
        drain_rate: charging ? null : drainRateFromHistory(history),
        low_power_mode: lowPower,
      };
    } catch (err) {
      console.log("battery poll error:", err?.message || err);
    }
  };

  // ---- network ----
  const pollNetwork = async () => {
    try {
      const st = await Network.getNetworkStateAsync();
      let type = "unknown";
      if (st.type === Network.NetworkStateType.WIFI) type = "wifi";
      else if (st.type === Network.NetworkStateType.CELLULAR) type = "cellular";
      else if (st.type === Network.NetworkStateType.ETHERNET) type = "ethernet";
      else if (st.type === Network.NetworkStateType.NONE) type = "none";

      const prev = networkRef.current;
      networkRef.current = {
        type,
        is_connected: !!st.isConnected,
        strength: null, // not exposed cross-platform by expo-network
      };

      // A handoff is not a disconnection. The socket can move from
      // WiFi to cellular without ever reporting a loss, so the
      // fault-injection cases that induce an outage do not cover it.
      // Record the transition so it is visible in analysis rather
      // than depending on someone noticing they walked out of range.
      if (prev && prev.type && prev.type !== type) {
        try {
          fetch(`${BASE_URL}/network/transition`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              device_uid: deviceUidRef?.current ?? null,
              session_id: sessionRef?.current?.session_id ?? null,
              trial_id: trialRef?.current?.trial_id ?? null,
              from_type: prev.type,
              to_type: type,
              was_connected: prev.is_connected,
              is_connected: !!st.isConnected,
              ts: Date.now(),
            }),
          }).catch(() => {});
        } catch { /* transition logging is best effort */ }
      }
    } catch (err) {
      console.log("network poll error:", err?.message || err);
    }
  };

  pollBattery();
  pollNetwork();
  const bi = setInterval(pollBattery, BATTERY_POLL_MS);
  const ni = setInterval(pollNetwork, NETWORK_POLL_MS);

  // React to battery events between polls so charge-state changes
  // are captured immediately rather than up to 15 s late.
  const levelSub = Battery.addBatteryLevelListener(pollBattery);
  const stateSub = Battery.addBatteryStateListener(pollBattery);
  const lpSub = Battery.addLowPowerModeListener(pollBattery);

  return () => {
    clearInterval(bi);
    clearInterval(ni);
    levelSub?.remove?.();
    stateSub?.remove?.();
    lpSub?.remove?.();
  };
}
