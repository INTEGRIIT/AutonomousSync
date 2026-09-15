// src/screens/SessionModeScreen.js
//
// Duration recording for benign activity and energy measurement.
//
// WHY THIS EXISTS
// Battery and network already stream in every packet, but nothing
// marks which packets belong to which activity. Without that, the
// false-positive rate depends on someone writing a start time in a
// spreadsheet and the packets being matched to it afterwards. That is
// the same provenance problem trial_id solved for drops, and it
// applies to the benign hours just as much: they are where the
// false-positive rate comes from, and that is one of the measurements
// the reviewers asked for by name.
//
// Unlike Trial Mode there is no blinding here. Nothing is being
// labelled by judgement, so seeing live state is harmless and useful
// for confirming the stream is alive over a long recording.

import React, { useState, useEffect, useRef } from "react";
import {
  View, Text, TextInput, TouchableOpacity, ScrollView,
  StyleSheet, Alert, ActivityIndicator,
} from "react-native";
import { BASE_URL } from "../../config";

const TYPES = [
  { id: "walking_hand",    label: "Walking, in hand" },
  { id: "walking_pocket",  label: "Walking, pocket" },
  { id: "walking_bag",     label: "Walking, bag" },
  { id: "running",         label: "Running" },
  { id: "stairs",          label: "Stairs" },
  { id: "cycling",         label: "Cycling" },
  { id: "driving_loose",   label: "Driving, loose" },
  { id: "driving_mounted", label: "Driving, mounted" },
  { id: "desk",            label: "Desk work" },
  { id: "stationary",      label: "Stationary" },
  { id: "streaming_idle",  label: "Energy: streaming idle" },
  { id: "streaming_events",label: "Energy: streaming + events" },
];

export default function SessionModeScreen({ route, navigation }) {
  const { deviceUid, deviceName, platform, deviceModel,
          sessionRef, packetCountRef, batteryRef, networkRef,
          member: assignedMember } = route.params || {};

  const [type, setType] = useState("walking_hand");
  const [notes, setNotes] = useState("");
  const [running, setRunning] = useState(false);
  const [busy, setBusy] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [packets, setPackets] = useState(0);
  const [seq, setSeq] = useState(1);
  const [batteryNow, setBatteryNow] = useState(null);

  const startPacketsRef = useRef(0);
  const startTsRef = useRef(0);
  const startBattRef = useRef(null);

  const member = assignedMember || "M1";
  const sessionId = `${member}-S${String(seq).padStart(3, "0")}`;

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(
          `${BASE_URL}/sessions/next?member=${encodeURIComponent(member)}`);
        const j = await res.json();
        if (!cancelled && j?.ok && j.next) setSeq(j.next);
      } catch { /* offline: operator can set it by hand */ }
    })();
    return () => { cancelled = true; };
  }, [member]);

  useEffect(() => {
    const i = setInterval(() => {
      const b = batteryRef?.current;
      if (b) setBatteryNow(b.level);
      if (!running) return;
      setElapsed(Math.floor((Date.now() - startTsRef.current) / 1000));
      const n = (packetCountRef?.current ?? 0) - startPacketsRef.current;
      setPackets(n > 0 ? n : 0);
    }, 1000);
    return () => clearInterval(i);
  }, [running]);

  const start = async () => {
    if (!deviceUid) {
      Alert.alert("No device", "Connect on the main screen first.");
      return;
    }
    setBusy(true);
    const batt = batteryRef?.current?.level ?? null;
    const net = networkRef?.current?.type ?? null;
    try {
      const res = await fetch(`${BASE_URL}/sessions/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          device_uid: deviceUid,
          member,
          session_type: type,
          platform,
          device_model: deviceModel,
          battery_start: batt,
          network_type: net,
        }),
      });
      const j = await res.json();
      if (!j?.ok) {
        Alert.alert("Could not start", j?.error || "unknown error");
        setBusy(false);
        return;
      }
    } catch (err) {
      Alert.alert("Network error", String(err?.message || err));
      setBusy(false);
      return;
    }

    if (sessionRef) {
      sessionRef.current = { session_id: sessionId, session_type: type,
                             member };
    }
    startPacketsRef.current = packetCountRef?.current ?? 0;
    startBattRef.current = batt;
    startTsRef.current = Date.now();
    setElapsed(0);
    setPackets(0);
    setRunning(true);
    setBusy(false);
  };

  const stop = async () => {
    setBusy(true);
    const captured = (packetCountRef?.current ?? 0) - startPacketsRef.current;
    const battEnd = batteryRef?.current?.level ?? null;
    if (sessionRef) sessionRef.current = null;
    try {
      await fetch(`${BASE_URL}/sessions/end`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          device_uid: deviceUid,
          packets: captured > 0 ? captured : 0,
          battery_end: battEnd,
          notes: notes || null,
        }),
      });
    } catch { /* the record exists server-side and can be closed later */ }
    setRunning(false);
    setBusy(false);
    setNotes("");
    setSeq((s) => s + 1);
  };

  const hh = String(Math.floor(elapsed / 3600)).padStart(2, "0");
  const mm = String(Math.floor((elapsed % 3600) / 60)).padStart(2, "0");
  const ss = String(elapsed % 60).padStart(2, "0");
  const label = TYPES.find((t) => t.id === type)?.label || type;

  if (running) {
    const drop = (startBattRef.current != null && batteryNow != null)
      ? ((startBattRef.current - batteryNow) * 100).toFixed(1)
      : null;
    return (
      <View style={s.runWrap}>
        <Text style={s.runLabel}>RECORDING</Text>
        <Text style={s.runId}>{sessionId}</Text>
        <Text style={s.runType}>{label}</Text>
        <Text style={s.runTimer}>{hh}:{mm}:{ss}</Text>
        <Text style={s.runMeta}>{packets} packets</Text>
        {batteryNow != null && (
          <Text style={s.runMeta}>
            battery {(batteryNow * 100).toFixed(0)}%
            {drop != null ? `  (−${drop}%)` : ""}
          </Text>
        )}
        <Text style={s.runNote}>
          Keep the screen on and the app in the foreground. Android
          stops delivering sensor data to a backgrounded app.
        </Text>
        <TouchableOpacity style={s.stopBtn} onPress={stop} disabled={busy}>
          {busy ? <ActivityIndicator color="#fff" />
                : <Text style={s.stopTxt}>STOP</Text>}
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <ScrollView style={s.wrap} contentContainerStyle={{ paddingBottom: 40 }}>
      <Text style={s.h1}>Session Mode</Text>
      <Text style={s.sub}>
        For benign activity and energy runs. Records which packets belong
        to which activity, so false-positive rates and battery drain come
        from the data rather than from a stopwatch.
      </Text>

      <View style={s.card}>
        <Text style={s.cardTitle}>Session</Text>
        <Text style={s.sid}>{sessionId}</Text>
        <Text style={s.meta}>
          {member} · {deviceName || "unnamed"} · {platform || "?"}
          {batteryNow != null ? ` · battery ${(batteryNow*100).toFixed(0)}%` : ""}
        </Text>

        <Text style={s.lbl}>Activity</Text>
        <View style={s.row}>
          {TYPES.map((t) => (
            <TouchableOpacity key={t.id}
              style={[s.chip, type === t.id && s.chipOn]}
              onPress={() => setType(t.id)}>
              <Text style={[s.chipTxt, type === t.id && s.chipTxtOn]}>
                {t.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        <Text style={s.lbl}>Notes (optional)</Text>
        <TextInput style={s.input} value={notes} onChangeText={setNotes}
                   placeholder="route, conditions, anything unusual"
                   placeholderTextColor="#667" />
      </View>

      <TouchableOpacity style={s.startBtn} onPress={start} disabled={busy}>
        {busy ? <ActivityIndicator color="#fff" />
              : <Text style={s.startTxt}>START {sessionId}</Text>}
      </TouchableOpacity>

      <TouchableOpacity style={s.linkBtn}
                        onPress={() => navigation?.goBack?.()}>
        <Text style={s.linkTxt}>Back</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: "#0b1220", padding: 16 },
  h1: { color: "#fff", fontSize: 24, fontWeight: "700", marginTop: 8 },
  sub: { color: "#8aa", fontSize: 12, marginTop: 6, marginBottom: 16,
         lineHeight: 17 },
  card: { backgroundColor: "#111c31", borderRadius: 12, padding: 14,
          marginBottom: 14 },
  cardTitle: { color: "#9fb", fontSize: 12, fontWeight: "700",
               letterSpacing: 1, marginBottom: 10 },
  sid: { color: "#4ade80", fontSize: 26, fontWeight: "700" },
  meta: { color: "#667", fontSize: 11, marginTop: 6 },
  lbl: { color: "#8aa", fontSize: 12, marginTop: 14, marginBottom: 6 },
  row: { flexDirection: "row", flexWrap: "wrap" },
  chip: { paddingHorizontal: 12, paddingVertical: 8, borderRadius: 8,
          backgroundColor: "#1b2942", marginRight: 8, marginBottom: 8 },
  chipOn: { backgroundColor: "#2563eb" },
  chipTxt: { color: "#9ab", fontSize: 12 },
  chipTxtOn: { color: "#fff", fontWeight: "700" },
  input: { backgroundColor: "#1b2942", color: "#fff", borderRadius: 8,
           paddingHorizontal: 12, paddingVertical: 10, fontSize: 14 },
  startBtn: { backgroundColor: "#2563eb", borderRadius: 12,
              paddingVertical: 18, alignItems: "center" },
  startTxt: { color: "#fff", fontSize: 17, fontWeight: "700" },
  linkBtn: { marginTop: 18, alignItems: "center" },
  linkTxt: { color: "#6af", fontSize: 14 },

  runWrap: { flex: 1, backgroundColor: "#0b2a3a", alignItems: "center",
             justifyContent: "center", padding: 24 },
  runLabel: { color: "#7dd3fc", fontSize: 13, letterSpacing: 3,
              fontWeight: "700" },
  runId: { color: "#fff", fontSize: 38, fontWeight: "800", marginTop: 8 },
  runType: { color: "#7dd3fc", fontSize: 16, marginTop: 4 },
  runTimer: { color: "#fff", fontSize: 44, marginTop: 18,
              fontVariant: ["tabular-nums"] },
  runMeta: { color: "#9cd", fontSize: 14, marginTop: 6 },
  runNote: { color: "#7dd3fc", fontSize: 11, textAlign: "center",
             marginTop: 26, paddingHorizontal: 24, lineHeight: 16 },
  stopBtn: { marginTop: 32, backgroundColor: "#111", borderRadius: 12,
             paddingVertical: 18, paddingHorizontal: 60 },
  stopTxt: { color: "#fff", fontSize: 18, fontWeight: "700" },
});
