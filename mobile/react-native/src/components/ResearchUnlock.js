// src/components/ResearchUnlock.js
//
// Hidden gate for research mode.
//
// TestFlight testers and research operators run the same build. This
// component keeps Trial Mode invisible to ordinary testers: seven taps
// on the version label reveal a code prompt, and only a device the
// server flags as a research device shows the Trial Mode button or
// stamps `research: true` on its packets.
//
// This is a convenience gate for a small team, not authentication.

import React, { useState } from "react";
import {
  View, Text, TextInput, TouchableOpacity, Modal,
  StyleSheet, ActivityIndicator, Alert,
} from "react-native";
import * as Application from "expo-application";
import { BASE_URL } from "../../config";

const TAPS_REQUIRED = 7;

export function ResearchUnlock({ deviceUid, researchMode, onChange,
                                 version = Application.nativeApplicationVersion || "1.0.0" }) {
  const [taps, setTaps] = useState(0);
  const [open, setOpen] = useState(false);
  const [code, setCode] = useState("");
  const [member, setMember] = useState("M1");
  const [busy, setBusy] = useState(false);

  const onTap = () => {
    const n = taps + 1;
    if (n >= TAPS_REQUIRED) {
      setTaps(0);
      setOpen(true);
    } else {
      setTaps(n);
    }
  };

  const submit = async (enable) => {
    if (!deviceUid) {
      Alert.alert("No device", "Set a device name first.");
      return;
    }
    setBusy(true);
    try {
      const res = await fetch(`${BASE_URL}/admin/research-device`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          device_uid: deviceUid,
          code,
          enabled: enable,
          member: enable ? member : null,
        }),
      });
      const j = await res.json();
      if (!j?.ok) {
        Alert.alert("Rejected", j?.error || "unknown error");
      } else {
        onChange?.(j.is_research_device, enable ? member : null);
        setOpen(false);
        setCode("");
      }
    } catch (err) {
      Alert.alert("Network error", String(err?.message || err));
    }
    setBusy(false);
  };

  return (
    <>
      <TouchableOpacity onPress={onTap} activeOpacity={1}>
        <Text style={s.version}>
          v{version}
          {researchMode ? "  ·  research" : ""}
          {taps > 2 && taps < TAPS_REQUIRED ? `  ${TAPS_REQUIRED - taps}` : ""}
        </Text>
      </TouchableOpacity>

      <Modal visible={open} transparent animationType="fade"
             onRequestClose={() => setOpen(false)}>
        <View style={s.backdrop}>
          <View style={s.card}>
            <Text style={s.title}>Research Mode</Text>
            <Text style={s.body}>
              Flags this device as part of the research collection. Its
              telemetry is tagged separately from ordinary use, and Trial
              Mode becomes available.
            </Text>

            <Text style={s.lbl}>Unlock code</Text>
            <TextInput
              style={s.input}
              value={code}
              onChangeText={setCode}
              secureTextEntry
              autoCapitalize="none"
              placeholder="code"
              placeholderTextColor="#667"
            />

            <Text style={s.lbl}>Member</Text>
            <View style={s.row}>
              {["M1", "M2", "M3"].map((m) => (
                <TouchableOpacity
                  key={m}
                  style={[s.chip, member === m && s.chipOn]}
                  onPress={() => setMember(m)}
                >
                  <Text style={[s.chipTxt, member === m && s.chipTxtOn]}>
                    {m}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            {busy ? (
              <ActivityIndicator color="#6af" style={{ marginTop: 20 }} />
            ) : (
              <>
                <TouchableOpacity style={s.primary} onPress={() => submit(true)}>
                  <Text style={s.primaryTxt}>Enable research mode</Text>
                </TouchableOpacity>
                {researchMode && (
                  <TouchableOpacity style={s.danger} onPress={() => submit(false)}>
                    <Text style={s.dangerTxt}>Disable</Text>
                  </TouchableOpacity>
                )}
              </>
            )}

            <TouchableOpacity onPress={() => { setOpen(false); setCode(""); }}>
              <Text style={s.cancel}>Cancel</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </>
  );
}

const s = StyleSheet.create({
  version: { color: "#445", fontSize: 11, textAlign: "center",
             paddingVertical: 14 },
  backdrop: { flex: 1, backgroundColor: "rgba(0,0,0,0.7)",
              justifyContent: "center", padding: 24 },
  card: { backgroundColor: "#111c31", borderRadius: 14, padding: 20 },
  title: { color: "#fff", fontSize: 19, fontWeight: "700" },
  body: { color: "#8aa", fontSize: 12, marginTop: 8, lineHeight: 18 },
  lbl: { color: "#8aa", fontSize: 12, marginTop: 16, marginBottom: 6 },
  input: { backgroundColor: "#1b2942", color: "#fff", borderRadius: 8,
           paddingHorizontal: 12, paddingVertical: 10, fontSize: 15 },
  row: { flexDirection: "row" },
  chip: { paddingHorizontal: 16, paddingVertical: 8, borderRadius: 8,
          backgroundColor: "#1b2942", marginRight: 8 },
  chipOn: { backgroundColor: "#2563eb" },
  chipTxt: { color: "#9ab", fontSize: 13 },
  chipTxtOn: { color: "#fff", fontWeight: "700" },
  primary: { backgroundColor: "#2563eb", borderRadius: 10, paddingVertical: 14,
             alignItems: "center", marginTop: 20 },
  primaryTxt: { color: "#fff", fontSize: 15, fontWeight: "700" },
  danger: { backgroundColor: "#7f1d1d", borderRadius: 10, paddingVertical: 12,
            alignItems: "center", marginTop: 10 },
  dangerTxt: { color: "#fecaca", fontSize: 14, fontWeight: "700" },
  cancel: { color: "#6af", fontSize: 14, textAlign: "center", marginTop: 16 },
});

export default ResearchUnlock;
