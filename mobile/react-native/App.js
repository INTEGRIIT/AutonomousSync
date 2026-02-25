import React, { useEffect, useMemo, useRef, useState } from "react";
import { View, Text, TextInput, Pressable, ScrollView } from "react-native";
import { Accelerometer, Gyroscope, Magnetometer } from "expo-sensors";
import * as Notifications from "expo-notifications";
import * as Device from "expo-device";

async function registerForAPNsAsync() {
  const { status } = await Notifications.getPermissionsAsync();
  if (status !== "granted") {
    const req = await Notifications.requestPermissionsAsync();
    if (req.status !== "granted") return null;
  }

  // 🔑 THIS is the real APNs token
  const nativeToken = await Notifications.getDevicePushTokenAsync();
  return nativeToken.data; // hex string
}

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});

const WS_PORT = 8012;
const SEND_INTERVAL_MS = 60;
const SENSOR_ACCEL_MS = 50;
const SENSOR_GYRO_MS = 50;
const SENSOR_MAG_MS = 100;

// 🔔 Notification tuning (diamond-tier: prevent spam + OS throttling)
const NOTIFY_COOLDOWN_MS = 4000;

export default function App() {
  const wsRef = useRef(null);
  const sendTimerRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const lastSendTsRef = useRef(0);

  // 🔔 Last notification time (rate limiting)
  const lastNotifyRef = useRef(0);

  // ✅ De-dupe key so “same event frame” doesn’t spam
  const lastNotifyKeyRef = useRef(null);

  // ✅ Push registration guard (prevents re-register spam when editing IP / deviceId)
  const hasRegisteredRef = useRef(false);

  const [ip, setIp] = useState("3.80.27.210"); // e.g. 192.168.50.187

  // ✅ Diamond-tier default: unique deviceId per phone (teammates won’t overwrite each other)
  // Still editable in the UI if you want a specific ID for demos.
  const [deviceId, setDeviceId] = useState(
    `${Device.modelName || "ios"}-${Math.random().toString(36).slice(2, 8)}`
  );

  const [connected, setConnected] = useState(false);
  const [touchActive, setTouchActive] = useState(false);
  // ❤️ Heartbeat (JS thread liveness)
  const [heartbeat, setHeartbeat] = useState(0);

  const [latest, setLatest] = useState({
    state: "—",
    decision: { sync: false, reason: "—" },
  });

  const [pps, setPps] = useState(0);
  const recvCountRef = useRef(0);

  const accRef = useRef({ x: 0, y: 0, z: 0 });
  const gyrRef = useRef({ x: 0, y: 0, z: 0 });
  const magRef = useRef({ x: 0, y: 0, z: 0 });

  const wsUrl = useMemo(() => `ws://${ip}:${WS_PORT}/ws/stream`, [ip]);

  // ❤️ Heartbeat ticker (1Hz)
  useEffect(() => {
    console.log("🟢 Heartbeat effect mounted");

    const t = setInterval(() => {
      setHeartbeat((h) => h + 1);
    }, 1000);

    return () => clearInterval(t);
  }, []);

  // 🔔 PUSH DELIVERY PROOF (ADD THIS BLOCK)
  useEffect(() => {
    const subRecv = Notifications.addNotificationReceivedListener((n) => {
      console.log("📬 PUSH RECEIVED (foreground):", JSON.stringify(n, null, 2));
    });

    const subResp = Notifications.addNotificationResponseReceivedListener((r) => {
      console.log("👉 PUSH TAPPED:", JSON.stringify(r, null, 2));
    });

    return () => {
      subRecv.remove();
      subResp.remove();
    };
  }, []);

  useEffect(() => {
    // ✅ Prevent re-registering push every time IP/deviceId changes (still can be done manually by reloading app)
    if (hasRegisteredRef.current) return;
    hasRegisteredRef.current = true;

    (async () => {
      const apnsToken = await registerForAPNsAsync();

      if (!apnsToken) {
        console.warn("❌ APNs token unavailable");
        return;
      }

      console.log("✅ APNs token:", apnsToken);

      try {
        const res = await fetch(`http://${ip}:8012/push/register`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            device_id: deviceId,
            push_token: apnsToken, // 🔑 REAL APNs TOKEN
            platform: "ios",
          }),
        });

        console.log("📡 Push register status:", res.status);
      } catch (err) {
        console.log("❌ Push register failed:", err);
      }
    })();
  }, [ip, deviceId]);

  /* ---------------- Sensors ---------------- */

  useEffect(() => {
    Accelerometer.setUpdateInterval(SENSOR_ACCEL_MS);
    Gyroscope.setUpdateInterval(SENSOR_GYRO_MS);
    Magnetometer.setUpdateInterval(SENSOR_MAG_MS);

    const a = Accelerometer.addListener((d) => (accRef.current = d));
    const g = Gyroscope.addListener((d) => (gyrRef.current = d));
    const m = Magnetometer.addListener((d) => (magRef.current = d));

    return () => {
      a.remove();
      g.remove();
      m.remove();
    };
  }, []);

  /* ---------------- Receive rate meter ---------------- */

  useEffect(() => {
    const t = setInterval(() => {
      setPps(recvCountRef.current);
      recvCountRef.current = 0;
    }, 1000);
    return () => clearInterval(t);
  }, []);

  /* ---------------- Helpers ---------------- */

  const cleanupTimers = () => {
    if (sendTimerRef.current) clearInterval(sendTimerRef.current);
    sendTimerRef.current = null;
    if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
    reconnectTimerRef.current = null;
  };

  const disconnect = () => {
    cleanupTimers();
    try {
      wsRef.current?.close();
    } catch {}
    wsRef.current = null;
    setConnected(false);
  };

  const startSendLoop = () => {
    if (sendTimerRef.current) return;

    sendTimerRef.current = setInterval(() => {
      const ws = wsRef.current;
      if (!ws || ws.readyState !== 1) return;

      const now = Date.now();
      if (now - lastSendTsRef.current < SEND_INTERVAL_MS - 5) return;
      lastSendTsRef.current = now;

      ws.send(
        JSON.stringify({
          ts: now,
          device_id: deviceId,
          accel: accRef.current,
          gyro: gyrRef.current,
          mag: magRef.current,
          touch: { active: touchActive },
          moisture: { value: null, source: "placeholder" },
          meta: { client: "apns", send_interval_ms: SEND_INTERVAL_MS },
        })
      );
    }, SEND_INTERVAL_MS);
  };

  const scheduleReconnect = () => {
    if (reconnectTimerRef.current) return;
    reconnectTimerRef.current = setTimeout(() => {
      reconnectTimerRef.current = null;
      connect(true);
    }, 900);
  };

  const connect = (isReconnect = false) => {
    console.log("🔗 Attempting WS URL:", wsUrl);
    if (wsRef.current && [0, 1].includes(wsRef.current.readyState)) return;

    cleanupTimers();
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log("🟢 WS OPEN");
      setConnected(true);
      startSendLoop();
    };

    ws.onclose = (e) => {
      console.log("🔴 WS CLOSED", e.code, e.reason);
      setConnected(false);
      cleanupTimers();
      wsRef.current = null;
      scheduleReconnect();
    };

    ws.onerror = (e) => {
      console.log("❌ WS ERROR", e.message || e);
      setConnected(false);
      cleanupTimers();
      try {
        ws.close();
      } catch {}
      wsRef.current = null;
      scheduleReconnect();
    };

    ws.onmessage = (evt) => {
      console.log("📨 WS MESSAGE");
      try {
        const data = JSON.parse(evt.data);
        if (data?.state) {
          setLatest(data);
          recvCountRef.current += 1;
        }
      } catch (err) {
        console.log("⚠️ PARSE ERROR", err);
      }
    };

    wsRef.current = ws;
  };

  useEffect(() => {
    return () => disconnect();
  }, []);

  /* ---------------- Display helpers ---------------- */

  const f = (x) => (typeof x === "number" ? x.toFixed(2) : "—");

  const transitionText = latest?.transition
    ? `${latest.transition.from} → ${latest.transition.to}`
    : "—";

  const actionText = latest?.action?.action ?? "—";

  const waterText = latest?.water
    ? `${String(latest.water.is_water)} (conf ${f(latest.water.confidence)})`
    : "—";

  /* ---------------- UI ---------------- */

  return (
    <ScrollView
      style={{ backgroundColor: "#ffffff" }}
      contentContainerStyle={{
        flexGrow: 1,
        padding: 18,
        justifyContent: "center",
      }}
    >
      <Text style={{ fontSize: 22, fontWeight: "800", marginBottom: 12 }}>
        Autonomous Sync
      </Text>

      <Text>Backend IP (LAN):</Text>
      <TextInput
        value={ip}
        onChangeText={setIp}
        style={{
          borderWidth: 1,
          borderColor: "#444",
          padding: 10,
          borderRadius: 10,
          marginBottom: 10,
        }}
        autoCapitalize="none"
        autoCorrect={false}
      />

      <Text>Device ID:</Text>
      <TextInput
        value={deviceId}
        onChangeText={setDeviceId}
        style={{
          borderWidth: 1,
          borderColor: "#444",
          padding: 10,
          borderRadius: 10,
          marginBottom: 10,
        }}
        autoCapitalize="none"
        autoCorrect={false}
      />

      <Pressable
        onPress={() => {
          console.log("🔌 CONNECT PRESSED");
          connected ? disconnect() : connect(false);
        }}
        style={{
          padding: 12,
          borderRadius: 10,
          backgroundColor: connected ? "#b91c1c" : "#065f46",
          marginBottom: 12,
        }}
      >
        <Text style={{ color: "white", textAlign: "center", fontWeight: "800" }}>
          {connected ? "Disconnect" : "Connect"} ({ip}:{WS_PORT})
        </Text>
      </Pressable>

      <Pressable
        onPressIn={() => setTouchActive(true)}
        onPressOut={() => setTouchActive(false)}
        style={{
          padding: 18,
          borderRadius: 12,
          backgroundColor: touchActive ? "#2563eb" : "#111827",
          marginBottom: 14,
        }}
      >
        <Text style={{ color: "white", textAlign: "center" }}>
          Hold = Touch Sensor Active
        </Text>
      </Pressable>

      <Text style={{ fontSize: 18, fontWeight: "900" }}>State: {latest.state}</Text>
      <Text>Transition: {transitionText}</Text>
      <Text>Action: {actionText}</Text>
      <Text style={{ marginTop: 6 }}>
        Sync: {String(latest.decision?.sync)} ({latest.decision?.reason ?? "—"})
      </Text>

      <View
        style={{
          marginTop: 14,
          padding: 12,
          borderWidth: 1,
          borderColor: "#333",
          borderRadius: 12,
        }}
      >
        <Text style={{ fontWeight: "900" }}>Live Telemetry</Text>
        <Text>Recv Rate: {pps} msg/sec</Text>
        <Text>Water: {waterText}</Text>
        <Text>Stable(ms): {latest?.temporal?.stable_duration_ms ?? "—"}</Text>
        <Text>
          acc_norm: {f(latest?.features?.acc_norm)} | gyr_norm:{" "}
          {f(latest?.features?.gyr_norm)}
        </Text>
        <Text>
          jerk: {f(latest?.features?.jerk)} | stability:{" "}
          {f(latest?.features?.stability)}
        </Text>
      </View>

      <View
        style={{
          marginTop: 12,
          padding: 12,
          borderWidth: 1,
          borderColor: "#333",
          borderRadius: 12,
        }}
      >
        <Text style={{ fontWeight: "900" }}>Emergency</Text>
        <Text>
          Snapshot:{" "}
          {latest?.emergency?.type
            ? `${latest.emergency.type} (${latest.emergency.state})`
            : "—"}
        </Text>
      </View>

      <Text style={{ marginTop: 16, color: "#666" }}>
        Tip: Backend must be running on port 8012. Phone + Mac on same Wi-Fi.
      </Text>
    </ScrollView>
  );
}