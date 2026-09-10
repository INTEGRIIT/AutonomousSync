import React from "react";
import { View, Text, Pressable } from "react-native";

export default function ControlPanel({
  configured,
  connected,
  onConnectToggle,
  touchActive,
  setTouchActive,
}) {
  return (
    <View>
      <Pressable
        disabled={!configured}
        onPress={onConnectToggle}
        style={{
          padding: 12,
          borderRadius: 10,
          backgroundColor: !configured
            ? "#374151"
            : connected
            ? "#b91c1c"
            : "#065f46",
          marginBottom: 12,
          opacity: configured ? 1 : 0.6,
        }}
      >
        <Text style={{ color: "white", textAlign: "center", fontWeight: "800" }}>
          {connected ? "Disconnect" : "Connect"}
        </Text>
      </Pressable>

      <Pressable
        onPressIn={() => setTouchActive(true)}
        onPressOut={() => setTouchActive(false)}
        style={{
          padding: 18,
          borderRadius: 12,
          backgroundColor: touchActive ? "#2563eb" : "#111827",
          marginBottom: 14,
        }}
      >
        <Text style={{ color: "white", textAlign: "center" }}>
          Hold = Touch Sensor Active
        </Text>
      </Pressable>
    </View>
  );
}