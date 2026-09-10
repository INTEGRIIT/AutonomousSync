import React, { useMemo, useState } from "react";
import { View, Text, Pressable, ActivityIndicator } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import * as Clipboard from "expo-clipboard";

export default function StatusBar({
  deviceName,
  deviceUid,
  connected,
  registered, // true | false | null | "idle"
  pps,
  onSettingsPress,
  onEventsPress,
}) {
  // =========================================================
  // 🧠 FORMAT DEVICE UID
  // =========================================================
  const shortUid = useMemo(() => {
    if (!deviceUid) return "—";
    return deviceUid.length > 10
      ? `${deviceUid.slice(0, 6)}…${deviceUid.slice(-4)}`
      : deviceUid;
  }, [deviceUid]);

  const isConfigured = deviceName?.trim().length > 0;

  const [copied, setCopied] = useState(false);

  const copyUid = async () => {
    if (!deviceUid) return;
    try {
      await Clipboard.setStringAsync(deviceUid);
      setCopied(true);
      setTimeout(() => setCopied(false), 900);
    } catch (e) {
      console.log("Clipboard error:", e);
    }
  };

  // =========================================================
  // 🔥 STATUS LOGIC (UPGRADED)
  // =========================================================

  let pushColor = "#64748b";
  let pushLabel = "Checking Push...";

  if (registered === true) {
    pushColor = "#22c55e";
    pushLabel = "Push Registered";
  } else if (registered === false) {
    pushColor = "#ef4444";
    pushLabel = "Push Failed";
  } else if (registered === "idle") {
    pushColor = "#64748b";
    pushLabel = "Push Not Initialized";
  }

  const connectionColor = connected ? "#22c55e" : "#ef4444";

  // =========================================================
  // 🧠 UI
  // =========================================================

  return (
    <View
      style={{
        paddingVertical: 14,
        paddingHorizontal: 16,
        backgroundColor: "#0f172a",
        borderRadius: 18,
        marginBottom: 16,
        borderWidth: 1,
        borderColor: "#1e293b",
      }}
    >
      {/* ===================================================== */}
      {/* 🔝 TOP ROW */}
      {/* ===================================================== */}
      <View
        style={{
          flexDirection: "row",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <View style={{ flex: 1 }}>
          <Text
            numberOfLines={1}
            style={{
              color: isConfigured ? "#ffffff" : "#f59e0b",
              fontWeight: "700",
              fontSize: 16,
            }}
          >
            {isConfigured ? deviceName : "Setup Required"}
          </Text>

          <Pressable
            onPress={copyUid}
            disabled={!deviceUid}
            style={({ pressed }) => ({
              marginTop: 4,
              opacity: !deviceUid ? 0.6 : pressed ? 0.7 : 1,
            })}
          >
            <Text
              style={{
                color: copied ? "#22c55e" : "#64748b",
                fontSize: 12,
              }}
            >
              {copied ? "Copied UID" : `ID · ${shortUid}`}
            </Text>
          </Pressable>
        </View>

        {/* 🔥 ACTION BUTTONS */}
        <View style={{ flexDirection: "row" }}>
          
          {/* 📊 EVENTS */}
          <Pressable
            onPress={onEventsPress}
            style={({ pressed }) => ({
              padding: 10,
              borderRadius: 12,
              backgroundColor: pressed ? "#334155" : "#1e293b",
              marginRight: 8,
            })}
          >
            <Ionicons name="bar-chart-outline" size={18} color="#22c55e" />
          </Pressable>

          {/* ⚙️ SETTINGS */}
          <Pressable
            onPress={onSettingsPress}
            style={({ pressed }) => ({
              padding: 10,
              borderRadius: 12,
              backgroundColor: pressed ? "#334155" : "#1e293b",
            })}
          >
            <Ionicons name="settings-outline" size={18} color="#e2e8f0" />
          </Pressable>

        </View>
      </View>

      {/* ===================================================== */}
      {/* 🔻 BOTTOM ROW */}
      {/* ===================================================== */}
      <View
        style={{
          flexDirection: "row",
          justifyContent: "space-between",
          marginTop: 14,
          alignItems: "center",
        }}
      >
        {/* CONNECTION */}
        <View style={{ flexDirection: "row", alignItems: "center" }}>
          <View
            style={{
              width: 8,
              height: 8,
              borderRadius: 99,
              backgroundColor: connectionColor,
              marginRight: 6,
            }}
          />
          <Text
            style={{
              color: connectionColor,
              fontWeight: "600",
              fontSize: 12,
            }}
          >
            {connected ? "Connected" : "Disconnected"}
          </Text>
        </View>

        {/* PUSH STATUS */}
        <View style={{ flexDirection: "row", alignItems: "center" }}>
          {registered === null ? (
            <ActivityIndicator size="small" color="#64748b" />
          ) : (
            <View
              style={{
                width: 8,
                height: 8,
                borderRadius: 99,
                backgroundColor: pushColor,
                marginRight: 6,
              }}
            />
          )}

          <Text style={{ color: "#94a3b8", fontSize: 12 }}>
            {pushLabel}
          </Text>
        </View>

        {/* PPS */}
        <View style={{ flexDirection: "row", alignItems: "center" }}>
          <Ionicons
            name="speedometer-outline"
            size={14}
            color="#94a3b8"
            style={{ marginRight: 4 }}
          />
          <Text style={{ color: "#94a3b8", fontSize: 12 }}>
            {pps || 0}
          </Text>
        </View>
      </View>
    </View>
  );
}