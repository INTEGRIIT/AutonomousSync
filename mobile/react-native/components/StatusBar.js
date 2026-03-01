import React from "react";
import { View, Text, Pressable } from "react-native";
import { Ionicons } from "@expo/vector-icons";

export default function StatusBar({
  deviceName,
  deviceUid,
  connected,
  registered,
  pps,
  onSettingsPress,
}) {
  const shortUid = deviceUid ? deviceUid.slice(0, 6) : "—";
  const connectionColor = connected ? "#22c55e" : "#ef4444";

  return (
    <View
      style={{
        paddingVertical: 14,
        paddingHorizontal: 16,
        backgroundColor: "#0f172a",
        borderRadius: 18,
        marginBottom: 16,
      }}
    >
      {/* Top Row */}
      <View
        style={{
          flexDirection: "row",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <View>
          <Text
            style={{
              color: "white",
              fontWeight: "700",
              fontSize: 16,
            }}
          >
            {deviceName || "Unnamed Device"}
          </Text>

          <Text
            style={{
              color: "#64748b",
              fontSize: 12,
              marginTop: 2,
            }}
          >
            ID · {shortUid}
          </Text>
        </View>

        {/* Modern Press Animation */}
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
        }}
      >
        <Text
          style={{
            color: connectionColor,
            fontWeight: "600",
            fontSize: 12,
          }}
        >
          {connected ? "Connected" : "Disconnected"}
        </Text>

        <Text
          style={{
            color: "#94a3b8",
            fontSize: 12,
          }}
        >
          {registered ? "Push Active" : "Push Inactive"}
        </Text>

        <Text
          style={{
            color: "#94a3b8",
            fontSize: 12,
          }}
        >
          {pps} msg/s
        </Text>
      </View>
    </View>
  );
}