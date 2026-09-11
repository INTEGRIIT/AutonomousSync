// src/screens/TrialModeScreen.js
//
// Labelled trial capture for the MobiQuitous 2027 collection run.
//
// DESIGN CONSTRAINT — OPERATOR BLINDING
// While a trial is armed this screen shows only the trial id, an
// elapsed timer and a packet count. It deliberately hides motion
// state, features and any detection result. If the operator can see
// "IMPACT DETECTED" after a drop, their judgement about whether the
// trial was clean is contaminated, and the labels stop being
// independent of the system's output. That circularity is what the
// 2026 reviewers rejected.
//
// The label is chosen BEFORE arming and is never edited afterwards.

import React, { useState, useEffect, useRef } from "react";
import {
  View, Text, TextInput, TouchableOpacity, ScrollView,
  StyleSheet, Alert, ActivityIndicator,
} from "react-native";
import { BASE_URL } from "../../config";

// The core grid every member runs, so results are comparable across
// devices. Anything outside it is still allowed but is tagged
// exploratory, and analysis reports the two separately.
const CORE_SURFACES = ["wood", "tile", "carpet", "mattress"];
const EXTRA_SURFACES = ["concrete", "sidewalk", "asphalt", "grass",
                        "gravel", "dirt"];
const CORE_HEIGHTS = [1, 2, 3, 4, 5];
const ORIENTATIONS = ["flat", "edge", "tumbling"];
const CLASSES = ["drop", "toss", "benign_handle", "stationary"];

export default function TrialModeScreen({ route, navigation }) {
  // trialRef is the same ref the send loop reads, so the trial id and
  // metadata ride inside every telemetry packet.
  const { deviceUid, deviceName, platform, deviceModel, trialRef,
          packetCountRef } = route.params || {};

  const [member, setMember] = useState("M1");
  const [caseType, setCaseType] = useState("none");
  const [seq, setSeq] = useState(1);

  const [height, setHeight] = useState(2);
  const [customHeight, setCustomHeight] = useState("");
  const [useCustomHeight, setUseCustomHeight] = useState(false);
  const [surface, setSurface] = useState("wood");
  const [customSurface, setCustomSurface] = useState("");
  const [useCustomSurface, setUseCustomSurface] = useState(false);
  const [orientation, setOrientation] = useState("flat");
  const [intendedClass, setIntendedClass] = useState("drop");
  const [notes, setNotes] = useState("");

  const [armed, setArmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [packets, setPackets] = useState(0);
  const [completed, setCompleted] = useState(0);

  const startPacketsRef = useRef(0);
  const startTsRef = useRef(0);

  const trialId = `${member}-${String(seq).padStart(3, "0")}`;

  const resolvedHeight = useCustomHeight
    ? (parseFloat(customHeight) || null)
    : height;
  const resolvedSurface = useCustomSurface
    ? (customSurface.trim().toLowerCase() || null)
    : surface;

  // A trial counts toward the balanced design only if it sits inside
  // the grid every member is running.
  const isCoreGrid =
    intendedClass === "drop" &&
    orientation === "flat" &&
    CORE_HEIGHTS.includes(resolvedHeight) &&
    CORE_SURFACES.includes(resolvedSurface);

  // Ask the backend where this member left off, so a reinstall or a
  // second session does not restart numbering at 001.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(
          `${BASE_URL}/trials/next?member=${encodeURIComponent(member)}` +
          `&device_uid=${encodeURIComponent(deviceUid)}`
        );
        const j = await res.json();
        if (!cancelled && j?.ok && j.next) setSeq(j.next);
      } catch {
        // offline is fine; operator can set the number by hand
      }
    })();
    return () => { cancelled = true; };
  }, [member, deviceUid]);

  useEffect(() => {
    if (!armed) return;
    const i = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTsRef.current) / 1000));
      const n = (packetCountRef?.current ?? 0) - startPacketsRef.current;
      setPackets(n > 0 ? n : 0);
    }, 500);
    return () => clearInterval(i);
  }, [armed]);

  const isBenign = intendedClass === "benign_handle" ||
                   intendedClass === "stationary";

  const arm = async () => {
    if (!deviceUid) {
      Alert.alert("No device", "Connect on the main screen first.");
      return;
    }
    if (!isBenign && (resolvedHeight === null || resolvedHeight <= 0)) {
      Alert.alert("Height missing", "Enter a height in feet before arming.");
      return;
    }
    if (!isBenign && !resolvedSurface) {
      Alert.alert("Surface missing", "Name the surface before arming.");
      return;
    }
    setBusy(true);
    const meta = {
      trial_id: trialId,
      device_uid: deviceUid,
      member,
      height_ft: intendedClass === "benign_handle" ? null : resolvedHeight,
      surface: intendedClass === "benign_handle" ? null : resolvedSurface,
      orientation: intendedClass === "benign_handle" ? null : orientation,
      intended_class: intendedClass,
      case_type: caseType,
      design: isCoreGrid ? "core_grid" : "exploratory",
      platform,
      device_model: deviceModel,
    };
    try {
      const res = await fetch(`${BASE_URL}/trials/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(meta),
      });
      const j = await res.json();
      if (!j?.ok) {
        Alert.alert("Could not start trial", j?.error || "unknown error");
        setBusy(false);
        return;
      }
    } catch (err) {
      Alert.alert("Network error", String(err?.message || err));
      setBusy(false);
      return;
    }

    // Stamp the packet stream. Everything from here carries trial_id.
    if (trialRef) {
      trialRef.current = {
        trial_id: trialId,
        member,
        intended_class: intendedClass,
        height_ft: meta.height_ft,
        surface: meta.surface,
        orientation: meta.orientation,
        case_type: caseType,
        design: meta.design,
      };
    }
    startPacketsRef.current = packetCountRef?.current ?? 0;
    startTsRef.current = Date.now();
    setElapsed(0);
    setPackets(0);
    setArmed(true);
    setBusy(false);
  };

  const stop = async () => {
    setBusy(true);
    const captured = (packetCountRef?.current ?? 0) - startPacketsRef.current;
    if (trialRef) trialRef.current = null;
    try {
      await fetch(`${BASE_URL}/trials/end`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          trial_id: trialId,
          device_uid: deviceUid,
          packets: captured > 0 ? captured : 0,
          notes: notes || null,
        }),
      });
    } catch {
      // the record exists server-side; it can be closed later
    }
    setArmed(false);
    setBusy(false);
    setNotes("");
    setCompleted((c) => c + 1);
    setSeq((s) => s + 1);
  };

  // ---------------- ARMED VIEW (blinded) ----------------
  if (armed) {
    const mm = String(Math.floor(elapsed / 60)).padStart(2, "0");
    const ss = String(elapsed % 60).padStart(2, "0");
    return (
      <View style={s.armedWrap}>
        <Text style={s.armedLabel}>RECORDING</Text>
        <Text style={s.armedId}>{trialId}</Text>
        <Text style={s.armedTimer}>{mm}:{ss}</Text>
        <Text style={s.armedPackets}>{packets} packets</Text>
        <Text style={s.armedCond}>
          {isBenign
            ? intendedClass
            : `${resolvedHeight} ft · ${resolvedSurface} · ${orientation}`}
        </Text>

        <View style={s.blindNote}>
          <Text style={s.blindText}>
            Detection output is hidden during a trial so the label stays
            independent of what the system decided.
          </Text>
        </View>

        <TouchableOpacity style={s.stopBtn} onPress={stop} disabled={busy}>
          {busy ? <ActivityIndicator color="#fff" />
                : <Text style={s.stopTxt}>STOP TRIAL</Text>}
        </TouchableOpacity>
      </View>
    );
  }

  // ---------------- SETUP VIEW ----------------
  const Chip = ({ label, active, onPress }) => (
    <TouchableOpacity
      style={[s.chip, active && s.chipActive]}
      onPress={onPress}
    >
      <Text style={[s.chipTxt, active && s.chipTxtActive]}>{label}</Text>
    </TouchableOpacity>
  );

  return (
    <ScrollView style={s.wrap} contentContainerStyle={{ paddingBottom: 40 }}>
      <Text style={s.h1}>Trial Mode</Text>
      <Text style={s.sub}>
        Set the label before the drop. Never change it afterwards.
      </Text>

      <View style={s.card}>
        <Text style={s.cardTitle}>Session</Text>
        <Text style={s.lbl}>Member</Text>
        <View style={s.row}>
          {["M1", "M2", "M3", "TEST"].map((m) => (
            <Chip key={m} label={m} active={member === m}
                  onPress={() => setMember(m)} />
          ))}
        </View>
        <Text style={s.lbl}>Case / protection</Text>
        <TextInput style={s.input} value={caseType} onChangeText={setCaseType}
                   placeholder="none / rugged / folio"
                   placeholderTextColor="#667" />
        <Text style={s.meta}>
          {deviceName || "unnamed"} · {platform || "?"} · {deviceModel || "?"}
        </Text>
      </View>

      <View style={s.card}>
        <Text style={s.cardTitle}>Next trial</Text>
        <Text style={s.trialId}>{trialId}</Text>

        <Text style={s.lbl}>Intended class</Text>
        <View style={s.row}>
          {CLASSES.map((c) => (
            <Chip key={c} label={c} active={intendedClass === c}
                  onPress={() => setIntendedClass(c)} />
          ))}
        </View>

        {!isBenign && (
          <>
            <Text style={s.lbl}>Height (ft)</Text>
            <View style={s.row}>
              {CORE_HEIGHTS.map((h) => (
                <Chip key={h} label={String(h)}
                      active={!useCustomHeight && height === h}
                      onPress={() => { setUseCustomHeight(false); setHeight(h); }} />
              ))}
              <Chip label="custom" active={useCustomHeight}
                    onPress={() => setUseCustomHeight(true)} />
            </View>
            {useCustomHeight && (
              <TextInput
                style={s.input}
                value={customHeight}
                onChangeText={setCustomHeight}
                keyboardType="decimal-pad"
                placeholder="height in feet, e.g. 10 or 7.5"
                placeholderTextColor="#667"
              />
            )}

            <Text style={s.lbl}>Surface</Text>
            <View style={s.row}>
              {CORE_SURFACES.map((x) => (
                <Chip key={x} label={x}
                      active={!useCustomSurface && surface === x}
                      onPress={() => { setUseCustomSurface(false); setSurface(x); }} />
              ))}
            </View>
            <Text style={s.lblSmall}>Outdoor / other</Text>
            <View style={s.row}>
              {EXTRA_SURFACES.map((x) => (
                <Chip key={x} label={x}
                      active={!useCustomSurface && surface === x}
                      onPress={() => { setUseCustomSurface(false); setSurface(x); }} />
              ))}
              <Chip label="other…" active={useCustomSurface}
                    onPress={() => setUseCustomSurface(true)} />
            </View>
            {useCustomSurface && (
              <TextInput
                style={s.input}
                value={customSurface}
                onChangeText={setCustomSurface}
                autoCapitalize="none"
                placeholder="name the surface, e.g. rubber_mat"
                placeholderTextColor="#667"
              />
            )}

            <View style={isCoreGrid ? s.gridOk : s.gridExtra}>
              <Text style={isCoreGrid ? s.gridOkTxt : s.gridExtraTxt}>
                {isCoreGrid
                  ? "CORE GRID — counts toward the balanced design"
                  : "EXPLORATORY — logged separately, not part of the grid"}
              </Text>
            </View>

            <Text style={s.lbl}>Orientation</Text>
            <View style={s.row}>
              {ORIENTATIONS.map((o) => (
                <Chip key={o} label={o} active={orientation === o}
                      onPress={() => setOrientation(o)} />
              ))}
            </View>
          </>
        )}

        <Text style={s.lbl}>Notes (optional)</Text>
        <TextInput style={s.input} value={notes} onChangeText={setNotes}
                   placeholder="anything unusual about this trial"
                   placeholderTextColor="#667" />
      </View>

      <TouchableOpacity style={s.armBtn} onPress={arm} disabled={busy}>
        {busy ? <ActivityIndicator color="#fff" />
              : <Text style={s.armTxt}>ARM TRIAL {trialId}</Text>}
      </TouchableOpacity>

      <Text style={s.footer}>Completed this session: {completed}</Text>

      <TouchableOpacity
        style={s.linkBtn}
        onPress={() => navigation?.goBack?.()}
      >
        <Text style={s.linkTxt}>Back</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: "#0b1220", padding: 16 },
  h1: { color: "#fff", fontSize: 24, fontWeight: "700", marginTop: 8 },
  sub: { color: "#f0a", fontSize: 13, marginBottom: 16, marginTop: 4 },
  card: { backgroundColor: "#111c31", borderRadius: 12, padding: 14,
          marginBottom: 14 },
  cardTitle: { color: "#9fb", fontSize: 12, fontWeight: "700",
               letterSpacing: 1, marginBottom: 10 },
  lbl: { color: "#8aa", fontSize: 12, marginTop: 10, marginBottom: 6 },
  lblSmall: { color: "#667", fontSize: 11, marginTop: 4, marginBottom: 6 },
  gridOk: { backgroundColor: "#14321f", borderRadius: 8, padding: 8,
            marginTop: 12 },
  gridOkTxt: { color: "#4ade80", fontSize: 11, textAlign: "center",
               fontWeight: "700" },
  gridExtra: { backgroundColor: "#3a2a10", borderRadius: 8, padding: 8,
               marginTop: 12 },
  gridExtraTxt: { color: "#fbbf24", fontSize: 11, textAlign: "center",
                  fontWeight: "700" },
  armedCond: { color: "#fecaca", fontSize: 14, marginTop: 14 },
  meta: { color: "#667", fontSize: 11, marginTop: 12 },
  trialId: { color: "#4ade80", fontSize: 28, fontWeight: "700",
             marginBottom: 6 },
  row: { flexDirection: "row", flexWrap: "wrap" },
  chip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 8,
          backgroundColor: "#1b2942", marginRight: 8, marginBottom: 8 },
  chipActive: { backgroundColor: "#2563eb" },
  chipTxt: { color: "#9ab", fontSize: 13 },
  chipTxtActive: { color: "#fff", fontWeight: "700" },
  input: { backgroundColor: "#1b2942", color: "#fff", borderRadius: 8,
           paddingHorizontal: 12, paddingVertical: 10, fontSize: 14 },
  armBtn: { backgroundColor: "#16a34a", borderRadius: 12, paddingVertical: 18,
            alignItems: "center" },
  armTxt: { color: "#fff", fontSize: 17, fontWeight: "700" },
  footer: { color: "#667", textAlign: "center", marginTop: 16, fontSize: 12 },
  linkBtn: { marginTop: 18, alignItems: "center" },
  linkTxt: { color: "#6af", fontSize: 14 },

  armedWrap: { flex: 1, backgroundColor: "#7f1d1d", alignItems: "center",
               justifyContent: "center", padding: 24 },
  armedLabel: { color: "#fecaca", fontSize: 14, letterSpacing: 3,
                fontWeight: "700" },
  armedId: { color: "#fff", fontSize: 46, fontWeight: "800", marginTop: 8 },
  armedTimer: { color: "#fecaca", fontSize: 30, marginTop: 12,
                fontVariant: ["tabular-nums"] },
  armedPackets: { color: "#fca5a5", fontSize: 15, marginTop: 6 },
  blindNote: { marginTop: 28, paddingHorizontal: 20 },
  blindText: { color: "#fecaca", fontSize: 12, textAlign: "center",
               lineHeight: 18 },
  stopBtn: { marginTop: 36, backgroundColor: "#111", borderRadius: 12,
             paddingVertical: 18, paddingHorizontal: 60 },
  stopTxt: { color: "#fff", fontSize: 18, fontWeight: "700" },
});
