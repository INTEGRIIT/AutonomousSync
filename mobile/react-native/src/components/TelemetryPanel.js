import React from "react";
import { View, Text } from "react-native";

export default function TelemetryPanel({ pps, latest, waterText, f }) {
  return (
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
  );
}