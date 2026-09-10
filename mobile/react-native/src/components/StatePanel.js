import React from "react";
import { View, Text } from "react-native";

export default function StatePanel({ latest, transitionText, actionText }) {
  return (
    <View style={{ marginBottom: 12 }}>
      <Text style={{ fontSize: 18, fontWeight: "900" }}>
        State: {latest.state}
      </Text>
      <Text>Transition: {transitionText}</Text>
      <Text>Action: {actionText}</Text>
      <Text style={{ marginTop: 6 }}>
        Sync: {String(latest.decision?.sync)} ({latest.decision?.reason ?? "—"})
      </Text>
    </View>
  );
}