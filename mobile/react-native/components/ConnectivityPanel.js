import React from "react";
import { View, Text } from "react-native";

export default function ConnectivityPanel({
  connected,
  registered,
  pps,
  reconnecting,
}) {
  const wsColor = connected ? "#22c55e" : "#ef4444";
  const pushColor = registered ? "#22c55e" : "#f59e0b";

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
      <Text style={{ fontWeight: "900" }}>Connectivity</Text>

      <Text style={{ color: wsColor, marginTop: 6 }}>
        WebSocket: {connected ? "Connected" : "Disconnected"}
      </Text>

      <Text style={{ color: pushColor }}>
        Push: {registered ? "Registered" : "Not Registered"}
      </Text>

      <Text>Recv Rate: {pps} msg/sec</Text>

      <Text>
        Reconnect State: {reconnecting ? "Reconnecting…" : "Stable"}
      </Text>
    </View>
  );
}