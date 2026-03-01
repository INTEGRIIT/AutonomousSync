import React from "react";
import { View, Text } from "react-native";

export default function BatteryPanel({
  batteryLevel,
  batteryState,
  drainRate,
}) {
  const levelPercent =
    typeof batteryLevel === "number"
      ? Math.round(batteryLevel * 100)
      : null;

  const getColor = () => {
    if (levelPercent === null) return "#94a3b8";
    if (levelPercent > 50) return "#22c55e";
    if (levelPercent > 20) return "#f59e0b";
    return "#ef4444";
  };

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
      <Text style={{ fontWeight: "900" }}>Battery</Text>

      <Text style={{ color: getColor(), marginTop: 6 }}>
        Level: {levelPercent !== null ? `${levelPercent}%` : "—"}
      </Text>

      <Text>State: {batteryState ?? "—"}</Text>

      <Text>Drain Rate: {drainRate ?? "—"} %/min</Text>
    </View>
  );
}