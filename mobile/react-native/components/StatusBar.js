import React, { useMemo, useState } from "react";
import { View, Text, Pressable } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import * as Clipboard from "expo-clipboard";

export default function StatusBar({
  deviceName,
  deviceUid,
  connected,
  registered,
  pps,
  onSettingsPress,
}) {
  const shortUid = useMemo(() => {
    if (!deviceUid) return "—";
    return deviceUid.length > 10 ? `${deviceUid.slice(0, 6)}…${deviceUid.slice(-4)}` : deviceUid;
  }, [deviceUid]);

  const connectionColor = connected ? "#22c55e" : "#ef4444";
  const pushColor = registered ? "#22c55e" : "#f59e0b"; // amber for "not registered"
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
      {/* Top Row */}
      <View
        style={{
          flexDirection: "row",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 12,
        }}
      >
        <View style={{ flex: 1 }}>
          <Text
            numberOfLines={1}
            style={{
              color: isConfigured ? "white" : "#f59e0b", // amber if setup required
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
              marginTop: 2,
              alignSelf: "flex-start",
              opacity: !deviceUid ? 0.6 : pressed ? 0.75 : 1,
            })}
          >
            <Text
              style={{
                color: copied ? "#22c55e" : "#64748b",
                fontSize: 12,
              }}
            >
              {copied ? "Copied UID ✅" : `ID · ${shortUid}`}
            </Text>
          </Pressable>
        </View>

        {/* Settings Button */}
        <Pressable
          onPress={onSettingsPress}
          style={({ pressed }) => ({
            padding: 8,
            borderRadius: 12,
            backgroundColor: pressed ? "#334155" : "#1e293b",
            transform: [{ scale: pressed ? 0.96 : 1 }],
            opacity: pressed ? 0.85 : 1,
          })}
        >
          <Ionicons name="settings-outline" size={18} color="#e2e8f0" />
        </Pressable>
      </View>

      {/* Bottom Row */}
      <View
        style={{
          flexDirection: "row",
          justifyContent: "space-between",
          marginTop: 12,
          alignItems: "center",
        }}
      >
        <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
          <View
            style={{
              width: 8,
              height: 8,
              borderRadius: 99,
              backgroundColor: connectionColor,
            }}
          />
          <Text style={{ color: connectionColor, fontWeight: "600", fontSize: 12 }}>
            {connected ? "Connected" : "Disconnected"}
          </Text>
        </View>

        <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
          <View
            style={{
              width: 8,
              height: 8,
              borderRadius: 99,
              backgroundColor: pushColor,
            }}
          />
          <Text style={{ color: "#94a3b8", fontSize: 12 }}>
            {registered ? "Push Registered" : "Push Not Registered"}
          </Text>
        </View>

        <Text style={{ color: "#94a3b8", fontSize: 12 }}>{pps} msg/s</Text>
      </View>
    </View>
  );
}