import "react-native-get-random-values";
import React, { useEffect, useMemo, useRef, useState } from "react";
import { View, Text, TextInput, Pressable, ScrollView } from "react-native";
import { Accelerometer, Gyroscope, Magnetometer } from "expo-sensors";
import * as Notifications from "expo-notifications";
import * as SecureStore from "expo-secure-store";
import { v4 as uuidv4 } from "uuid";
import StatusBar from "./components/StatusBar";
import SettingsModal from "./components/SettingsModal";

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

  const didHydrateNameRef = useRef(false);
  const hydratedNameRef = useRef(""); // remembers the name we hydrated from storage

  const [configured, setConfigured] = useState(false);
  const [registered, setRegistered] = useState(false);
  const [deviceUid, setDeviceUid] = useState(null);
  const [deviceName, setDeviceName] = useState("My iPhone");
  const [connected, setConnected] = useState(false);
  const [touchActive, setTouchActive] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
    // ❤️ Heartbeat (JS thread liveness)
  const [heartbeat, setHeartbeat] = useState(0);

  // 🔐 Persist device name whenever it changes
  // 🔐 Persist device name whenever it changes
  useEffect(() => {
    const save = async () => {
      try {
        const name = (deviceName || "").trim();
        if (name.length === 0) return;

        await SecureStore.setItemAsync("device_name", name);

        // ✅ Only force re-register if the name actually changed AFTER hydration
        if (didHydrateNameRef.current) {
          const prev = (hydratedNameRef.current || "").trim();

          // if we have a previous hydrated name AND it differs, force re-register
          if (prev.length > 0 && prev !== name) {
            await SecureStore.deleteItemAsync("push_registered");
            setRegistered(false);

            // update baseline so we don't keep triggering
            hydratedNameRef.current = name;
          }
        }
      } catch (e) {
        console.log("SAVE NAME ERROR:", e);
      }
    };

    save();
  }, [deviceName]);

  useEffect(() => {
    setConfigured((deviceName || "").trim().length > 0);
  }, [deviceName]);

  useEffect(() => {
    const initDevice = async () => {
      try {
        console.log("INIT DEVICE START");

        // --- UID ---
        let storedUid = await SecureStore.getItemAsync("device_uid");
        if (!storedUid) {
          console.log("GENERATING UUID");
          storedUid = uuidv4();
          await SecureStore.setItemAsync("device_uid", storedUid);
        }
        setDeviceUid(storedUid);

        // --- Device Name ---
        let storedName = await SecureStore.getItemAsync("device_name");
        if (storedName) {
          setDeviceName(storedName);
        }

        // ✅ set baseline hydrated name (stored name if present, otherwise current default)
        hydratedNameRef.current = (storedName || "").trim();

        const reg = await SecureStore.getItemAsync("push_registered");
        setRegistered(reg === "1");
        didHydrateNameRef.current = true;

        console.log("DEVICE INIT COMPLETE");

      } catch (e) {
        console.log("INIT ERROR:", e);
      }
    };

    initDevice();
  }, []);

  const [latest, setLatest] = useState({
    state: "—",
    decision: { sync: false, reason: "—" },
  });

  const [pps, setPps] = useState(0);
  const recvCountRef = useRef(0);

  const accRef = useRef({ x: 0, y: 0, z: 0 });
  const gyrRef = useRef({ x: 0, y: 0, z: 0 });
  const magRef = useRef({ x: 0, y: 0, z: 0 });

  const wsUrl = useMemo(() => `wss://api.autonomous-sync.com/ws/stream`, []);

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
      if (!deviceUid) return;


      const now = Date.now();
      if (now - lastSendTsRef.current < SEND_INTERVAL_MS - 5) return;
      lastSendTsRef.current = now;

      ws.send(
        JSON.stringify({
          ts: now,
          device_uid: deviceUid,
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



  const connect = async (isReconnect = false) => {
    if (!deviceUid) {
      console.warn("Device UID not ready yet");
      return;
    }

    if (deviceName.trim().length === 0) {
      console.warn("Device name required");
      return;
    }

    // 1️⃣ Get APNs token
    const apnsToken = await registerForAPNsAsync();

    if (!apnsToken) {
      console.warn("❌ APNs token unavailable");
      return;
    }

    console.log("✅ APNs token:", apnsToken);

    // 2️⃣ Register with backend
    const res = await fetch(
      "https://api.autonomous-sync.com/push/register",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          device_uid: deviceUid,
          device_name: deviceName.trim(),
          push_token: apnsToken,
          platform: "ios",
        }),
      }
    );

    if (!res.ok) {
      console.warn("Push registration failed:", await res.text());
      return;
    }

    console.log("📡 Push registered successfully");
    setRegistered(true);
    await SecureStore.setItemAsync("push_registered", "1");
    hydratedNameRef.current = deviceName.trim();

    // 3️⃣ Open WebSocket
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
      console.log("🔴 WS CLOSED");
      console.log("WS CLOSED CODE:", e.code);
      console.log("WS CLOSED REASON:", e.reason);
      console.log("WAS CLEAN:", e.wasClean);

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
    <ScrollView style={{ backgroundColor: "#ffffff" }} contentContainerStyle={{ flexGrow: 1, padding: 18, justifyContent: "center" }}>
      <StatusBar
        deviceName={deviceName}
        deviceUid={deviceUid}
        connected={connected}
        registered={registered}
        pps={pps}
        onSettingsPress={() => setShowSettings(true)}
      />
      <Text style={{ fontSize: 22, fontWeight: "800", marginBottom: 12 }}>
        Autonomous Sync
      </Text>

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
          {connected ? "Disconnect" : "Connect"}
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

      <View style={{ marginTop: 14, padding: 12, borderWidth: 1, borderColor: "#333", borderRadius: 12 }}>
        <Text style={{ fontWeight: "900" }}>Live Telemetry</Text>
        <Text>Recv Rate: {pps} msg/sec</Text>
        <Text>Water: {waterText}</Text>
        <Text>Stable(ms): {latest?.temporal?.stable_duration_ms ?? "—"}</Text>
        <Text>
          acc_norm: {f(latest?.features?.acc_norm)} | gyr_norm: {f(latest?.features?.gyr_norm)}
        </Text>
        <Text>
          jerk: {f(latest?.features?.jerk)} | stability: {f(latest?.features?.stability)}
        </Text>
      </View>

      <View style={{ marginTop: 12, padding: 12, borderWidth: 1, borderColor: "#333", borderRadius: 12 }}>
        <Text style={{ fontWeight: "900" }}>Emergency</Text>
        <Text>
          Snapshot:{" "}
          {latest?.emergency?.type ? `${latest.emergency.type} (${latest.emergency.state})` : "—"}
        </Text>
      </View>

      <Text style={{ marginTop: 16, color: "#666" }}>
        Connected to secure AWS cloud infrastructure.
      </Text>
      <SettingsModal
        visible={showSettings}
        onClose={() => setShowSettings(false)}
        deviceName={deviceName}
        setDeviceName={setDeviceName}
        onReRegister={async () => {
          // Optional: call push/register again here
        }}
      />
    </ScrollView>
  );
}