import React from "react";
import { View, Text } from "react-native";

export default function EmergencyPanel({ latest }) {
  return (
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
  );
}