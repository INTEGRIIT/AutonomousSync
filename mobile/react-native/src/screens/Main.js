import "react-native-get-random-values";
import React, { useEffect, useRef, useState } from "react";
import { ScrollView, Text, TouchableOpacity } from "react-native";
import {
  SafeAreaView,
  SafeAreaProvider,
  useSafeAreaInsets,
} from "react-native-safe-area-context";

import { Accelerometer, Gyroscope, Magnetometer } from "expo-sensors";
import * as Notifications from "expo-notifications";
import * as SecureStore from "expo-secure-store";
import { v4 as uuidv4 } from "uuid";
import * as Battery from "expo-battery";

import StatusBar from "../components/StatusBar";
import SettingsModal from "../components/SettingsModal";
import ControlPanel from "../components/ControlPanel";
import StatePanel from "../components/StatePanel";
import TelemetryPanel from "../components/TelemetryPanel";
import EmergencyPanel from "../components/EmergencyPanel";
import BatteryPanel from "../components/BatteryPanel";
import { startContext } from "../services/contextService";
import ResearchUnlock from "../components/ResearchUnlock";
import { startAutoFlush } from "../services/uploadQueue";
import { uploadSelectedFilesTracked } from "../services/fileService";
import { BASE_URL } from "../../config";
import ConnectivityPanel from "../components/ConnectivityPanel";

import { registerForPush } from "../services/pushService";
import { uploadSelectedFiles } from "../services/fileService";

// ✅ FIXED (PRODUCTION SAFE)
const WS_URL = "wss://api.autonomous-sync.com/ws/stream";

const SEND_INTERVAL_MS = 60;
const DEVICE_UID_KEY = "device_uid";

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});

export default function MainScreenWrapper(props) {  
  return (
    <SafeAreaProvider>
      <MainScreen {...props} />
    </SafeAreaProvider>
  );
}

function MainScreen({ navigation }) {
  const insets = useSafeAreaInsets();

  const wsRef = useRef(null);
  const sendLoopRef = useRef(null);
  const connectingRef = useRef(false);

  const accRef = useRef({ x: 0, y: 0, z: 0 });
  const gyrRef = useRef({ x: 0, y: 0, z: 0 });
  const magRef = useRef({ x: 0, y: 0, z: 0 });

  const recvCountRef = useRef(0);

  const [deviceUid, setDeviceUid] = useState(null);
  const [deviceName, setDeviceName] = useState("");
  const [connected, setConnected] = useState(false);
  const [registered, setRegistered] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [touchActive, setTouchActive] = useState(false);

  const [latest, setLatest] = useState({
    state: "—",
    decision: { sync: false, reason: "—" },
  });

  const [pps, setPps] = useState(0);
  const [batteryLevel, setBatteryLevel] = useState(null);
  const [batteryState, setBatteryState] = useState(null);
  const [drainRate, setDrainRate] = useState(null);

  const batteryRef = useRef(null);
  const networkRef = useRef(null);
  const deviceCtxRef = useRef(null);
  const trialRef = useRef(null);        // set by TrialModeScreen
  const sessionRef = useRef(null);      // set by SessionModeScreen
  // deviceUid is state; the network poll runs on an interval and would
  // capture whatever it held when the interval was created. Mirror it
  // into a ref so transition logging reports the current device.
  const deviceUidRef = useRef(null);
  const packetCountRef = useRef(0);

  // Research-device flag. TestFlight testers and research operators run
  // the same build; only flagged devices see Trial Mode and only their
  // telemetry is tagged as research data.
  const [researchMode, setResearchMode] = useState(false);
  const [researchMember, setResearchMember] = useState(null);
  const researchRef = useRef(false);
  const [preferences, setPreferences] = useState(null);

  const f = (x) => (typeof x === "number" ? x.toFixed(2) : "—");
  const lastUploadRef = useRef(null);

  /* ================= DEVICE INIT ================= */

  useEffect(() => {
    const initDevice = async () => {
      let uid = await SecureStore.getItemAsync(DEVICE_UID_KEY);

      if (!uid) {
        uid = uuidv4();
        await SecureStore.setItemAsync(DEVICE_UID_KEY, uid);
        console.log("🆕 NEW DEVICE UID:", uid);
      }

      setDeviceUid(uid);

      let storedName = await SecureStore.getItemAsync("device_name");

      // ✅ LOCAL NAME EXISTS → USE IT
      if (storedName?.trim()) {
        setDeviceName(storedName.trim());
      } else {
        // 🔥 TRY BACKEND RESTORE
        try {
          console.log("🌐 Fetching device from backend...");

          const res = await fetch(
            `https://api.autonomous-sync.com/device/${uid}`
          );

          const json = await res.json();

          if (json.ok && json.device_name) {
            console.log("🔄 Restored from backend:", json.device_name);

            setDeviceName(json.device_name);

            await SecureStore.setItemAsync(
              "device_name",
              json.device_name
            );
          } else {
            console.log("⚠️ No device name found → show settings");
            setShowSettings(true);
          }
        } catch (e) {
          console.log("❌ Device restore failed:", e);
          setShowSettings(true);
        }
      }

      const pushRegistered = await SecureStore.getItemAsync("push_registered");
      setRegistered(pushRegistered === "1");
    };

    initDevice();
  }, []);

  /* ================= AUTO PUSH REGISTRATION ================= */

  useEffect(() => {
    if (!deviceUid || !deviceName) return;

    console.log("🚀 AUTO REGISTER DEVICE START");

    const run = async () => {
      try {
        setRegistered(null); // ⏳ StatusBar shows "Checking..."

        const token = await registerForPush(deviceUid, deviceName);

        if (token) {
          console.log("✅ AUTO PUSH REGISTERED");
          setRegistered(true);
        } else {
          console.log("❌ AUTO PUSH FAILED");
          setRegistered(false);
        }
      } catch (e) {
        console.log("❌ AUTO REGISTER ERROR:", e);
        setRegistered(false);
      }
    };

    run();
  }, [deviceUid, deviceName]);


  /* ================= PUSH HANDLER ================= */

  useEffect(() => {
    const sub = Notifications.addNotificationReceivedListener(async (n) => {
      const data = n.request?.content?.data || {};
      const snapshotId = data.snapshot_id || data.snapshot?.id;

      console.log("📬 PUSH DATA:", data);

      if (data.action === "UPLOAD" && snapshotId) {
        // 🚫 Prevent duplicate uploads (only skip if SUCCESS already happened)
        if (lastUploadRef.current === snapshotId) return;

        if (!deviceUid || !deviceName) return;

        console.log("🚀 PUSH TRIGGER → AUTO FILE UPLOAD:", snapshotId);

        try {
          await uploadSelectedFiles(deviceUid, deviceName, snapshotId);

          // ✅ mark ONLY after success
          lastUploadRef.current = snapshotId;

        } catch (e) {
          console.log("❌ PUSH AUTO UPLOAD FAILED:", e);

          // 🔁 retry once
          setTimeout(async () => {
            try {
              await uploadSelectedFiles(deviceUid, deviceName, snapshotId);

              // ✅ mark after retry success
              lastUploadRef.current = snapshotId;

            } catch (err) {
              console.log("❌ RETRY FAILED:", err);
            }
          }, 3000);
        }
      }
    });

    return () => sub.remove();
  }, [deviceUid, deviceName]);

  /* ================= SENSORS ================= */

  useEffect(() => {
    Accelerometer.setUpdateInterval(50);
    Gyroscope.setUpdateInterval(50);
    Magnetometer.setUpdateInterval(100);

    const a = Accelerometer.addListener((d) => (accRef.current = d));
    const g = Gyroscope.addListener((d) => (gyrRef.current = d));
    const m = Magnetometer.addListener((d) => (magRef.current = d));

    return () => {
      a.remove();
      g.remove();
      m.remove();
    };
  }, []);

  /* ================= UPLOAD QUEUE ================= */

  // Drain anything left queued by a previous session. An upload that
  // failed during a hazard is retried here rather than lost.
  useEffect(() => {
    if (!deviceUid || !deviceName) return;
    return startAutoFlush(async (entry) => {
      const r = await uploadSelectedFilesTracked(
        entry.device_uid || deviceUid,
        entry.device_name || deviceName,
        entry.snapshot_id);
      return !!r?.ok;
    }, 30000);
  }, [deviceUid, deviceName]);

  /* ================= RESEARCH FLAG ================= */

  useEffect(() => {
    if (!deviceUid) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(
          `${BASE_URL}/admin/research-device?device_uid=${encodeURIComponent(deviceUid)}`
        );
        const j = await res.json();
        if (!cancelled && j?.ok) {
          setResearchMode(!!j.is_research_device);
          setResearchMember(j.member || null);
          researchRef.current = !!j.is_research_device;
        }
      } catch {
        // offline: stay in normal mode
      }
    })();
    return () => { cancelled = true; };
  }, [deviceUid]);

  /* ================= CONTEXT (battery / network / device) ================= */

  useEffect(() => { deviceUidRef.current = deviceUid; }, [deviceUid]);

  useEffect(() => {
    const stop = startContext(batteryRef, networkRef, deviceCtxRef,
                              deviceUidRef, sessionRef, trialRef);
    const ui = setInterval(() => {
      const b = batteryRef.current;
      if (b) {
        setBatteryLevel(b.level);
        setBatteryState(b.state);
        setDrainRate(b.drain_rate == null ? null : b.drain_rate.toFixed(2));
      }
    }, 2000);
    return () => { stop(); clearInterval(ui); };
  }, []);

  /* ================= SEND LOOP ================= */

  const startSendLoop = () => {
    if (sendLoopRef.current) return;

    console.log("🚀 START SEND LOOP");

    sendLoopRef.current = setInterval(() => {
      if (!wsRef.current || wsRef.current.readyState !== 1) return;

      const packet = {
        ts: Date.now(),
        device_uid: deviceUid,
        accel: accRef.current,
        gyro: gyrRef.current,
        mag: magRef.current,
        touch: { active: touchActive },
        battery: batteryRef.current,
        network: networkRef.current,
        device: deviceCtxRef.current,
        trial_id: trialRef.current?.trial_id ?? null,
        trial_meta: trialRef.current ?? null,
        session_id: sessionRef.current?.session_id ?? null,
        session_meta: sessionRef.current ?? null,
        research: researchRef.current || null,
        preferences: preferences || {},
        schema_version: "v3",
      };

      wsRef.current.send(JSON.stringify(packet));
      packetCountRef.current += 1;
    }, SEND_INTERVAL_MS);
  };

  const stopSendLoop = () => {
    console.log("🛑 STOP SEND LOOP");
    clearInterval(sendLoopRef.current);
    sendLoopRef.current = null;
  };

  /* ================= CONNECT ================= */

  const connect = async () => {
    if (connectingRef.current) return;
    if (!deviceUid || !deviceName) return;

    connectingRef.current = true;

    try {
      console.log("🚀 STEP 1: REGISTER DEVICE FIRST");

      // Push registration is best-effort. The downlink path is
      // WS_active OR Push_active, so a device that cannot register
      // for push must still stream telemetry and remain reachable
      // over the socket. Emulators (Device.isDevice === false) and
      // devices with notifications denied fall into this case.
      const token = await registerForPush(deviceUid, deviceName);

      if (!token) {
        console.log("⚠️ Push unavailable — continuing with WebSocket only");
        setRegistered(false);
      } else {
        console.log("✅ Push registered successfully");
        setRegistered(true);
      }

      console.log("🌐 STEP 2: CONNECTING WEBSOCKET");

      const ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        console.log("✅ WS CONNECTED");
        wsRef.current = ws;
        setConnected(true);
        startSendLoop();
        connectingRef.current = false;
      };

      ws.onmessage = async (evt) => {
        try {
          const data = JSON.parse(evt.data);
          recvCountRef.current += 1;

          setLatest(data);

          const snapshotId = data.snapshot_id || data.snapshot?.id;

          // 🔥 ONLY RUN IF VALID TRIGGER
          if (data.trigger_upload && snapshotId) {

            // 🚫 prevent duplicate uploads
            if (lastUploadRef.current === snapshotId) return;

            console.log("🚀 WS TRIGGER → AUTO FILE UPLOAD:", snapshotId);

            if (!deviceUid || !deviceName) return;

            try {
              await uploadSelectedFiles(deviceUid, deviceName, snapshotId);

              // ✅ mark ONLY after success
              lastUploadRef.current = snapshotId;

            } catch (e) {
              console.log("❌ AUTO UPLOAD FAILED:", e);

              // 🔁 retry once
              setTimeout(async () => {
                try {
                  await uploadSelectedFiles(deviceUid, deviceName, snapshotId);
                  lastUploadRef.current = snapshotId;
                } catch (err) {
                  console.log("❌ RETRY FAILED:", err);
                }
              }, 3000);
            }
          }

        } catch (err) {
          console.log("❌ WS PARSE ERROR:", err);
        }
      };

      ws.onerror = (e) => {
        console.log("🚨 WS ERROR:", e?.message || e);
      };

      ws.onclose = (e) => {
        console.log("❌ WS CLOSED:", e.code, e.reason);
        setConnected(false);
        stopSendLoop();
        connectingRef.current = false;
      };

    } catch (e) {
      console.log("❌ CONNECT ERROR:", e);
      setRegistered(false);
      connectingRef.current = false;
    }
  };

  const disconnect = () => {
    stopSendLoop();
    wsRef.current?.close();
    wsRef.current = null;
    setConnected(false);
  };

  /* ================= PPS ================= */

  useEffect(() => {
    const t = setInterval(() => {
      setPps(recvCountRef.current);
      recvCountRef.current = 0;
    }, 1000);
    return () => clearInterval(t);
  }, []);

  /* ================= UI ================= */

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: "#f8fafc" }}>
      <ScrollView
        contentContainerStyle={{
          paddingHorizontal: 16,
          paddingTop: insets.top + 8,
          paddingBottom: insets.bottom + 20,
          gap: 12,
        }}
      >
        <StatusBar
          deviceName={deviceName}
          deviceUid={deviceUid}
          connected={connected}
          registered={registered}
          pps={pps}
          onSettingsPress={() => setShowSettings(true)}
            onEventsPress={() => {
          console.log("📊 EVENTS PRESSED");
          navigation.navigate("Events", { deviceUid });
        }}
        />

        {researchMode && (
        <TouchableOpacity
          style={{
            backgroundColor: "#12263a",
            borderRadius: 10,
            paddingVertical: 14,
            alignItems: "center",
            marginHorizontal: 16,
            marginTop: 10,
            borderWidth: 1,
            borderColor: "#0ea5e9",
          }}
          onPress={() =>
            navigation.navigate("SessionMode", {
              deviceUid,
              deviceName,
              platform: deviceCtxRef.current?.platform,
              deviceModel: deviceCtxRef.current?.model,
              sessionRef,
              packetCountRef,
              batteryRef,
              networkRef,
              member: researchMember,
            })
          }
        >
          <Text style={{ color: "#7dd3fc", fontSize: 15, fontWeight: "700" }}>
            ⏱ Session Mode
          </Text>
        </TouchableOpacity>
        )}

        {researchMode && (
        <TouchableOpacity
          style={{
            backgroundColor: "#1b2942",
            borderRadius: 10,
            paddingVertical: 14,
            alignItems: "center",
            marginHorizontal: 16,
            marginTop: 10,
            borderWidth: 1,
            borderColor: "#2563eb",
          }}
          onPress={() =>
            navigation.navigate("TrialMode", {
              deviceUid,
              deviceName,
              platform: deviceCtxRef.current?.platform,
              deviceModel: deviceCtxRef.current?.model,
              trialRef,
              packetCountRef,
              member: researchMember,
            })
          }
        >
          <Text style={{ color: "#6af", fontSize: 15, fontWeight: "700" }}>
            🧪 Trial Mode{researchMember ? ` · ${researchMember}` : ""}
          </Text>
        </TouchableOpacity>
        )}

        <ControlPanel
          configured={!!deviceName}
          connected={connected}
          onConnectToggle={() => (connected ? disconnect() : connect())}
          touchActive={touchActive}
          setTouchActive={setTouchActive}
        />

        <StatePanel latest={latest} />
        <TelemetryPanel latest={latest} pps={pps} f={f} />

        <BatteryPanel
          batteryLevel={batteryLevel}
          batteryState={batteryState}
          drainRate={drainRate}
        />

        <ConnectivityPanel
          connected={connected}
          registered={registered}
          pps={pps}
        />

        <EmergencyPanel latest={latest} />

        <SettingsModal
          visible={showSettings}
          onClose={() => setShowSettings(false)}
          deviceName={deviceName}
          setDeviceName={setDeviceName}
          navigation={navigation}
        />
        <ResearchUnlock
          deviceUid={deviceUid}
          researchMode={researchMode}
          onChange={(on, mem) => {
            setResearchMode(on);
            setResearchMember(mem);
            researchRef.current = on;
          }}
        />

      </ScrollView>
    </SafeAreaView>
  );
}