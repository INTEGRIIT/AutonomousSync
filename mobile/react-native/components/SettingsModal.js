import React, { useState } from "react";
import { View, Text, TextInput, Pressable, Modal } from "react-native";
import * as SecureStore from "expo-secure-store";

export default function SettingsModal({
  visible,
  onClose,
  deviceName,
  setDeviceName,
  onReRegister,
}) {
  const [localName, setLocalName] = useState(deviceName);

  const handleSave = async () => {
    const trimmed = localName.trim();
    if (!trimmed) return;

    await SecureStore.setItemAsync("device_name", trimmed);
    setDeviceName(trimmed);

    if (onReRegister) {
      await onReRegister(trimmed);
    }

    onClose();
  };

  return (
    <Modal visible={visible} animationType="slide" transparent>
      <View
        style={{
          flex: 1,
          justifyContent: "center",
          backgroundColor: "rgba(0,0,0,0.6)",
          padding: 20,
        }}
      >
        <View
          style={{
            backgroundColor: "#0f172a",
            padding: 22,
            borderRadius: 20,
          }}
        >
          <Text
            style={{
              fontSize: 18,
              fontWeight: "700",
              color: "white",
              marginBottom: 18,
            }}
          >
            Device Settings
          </Text>

          <Text style={{ color: "#94a3b8", marginBottom: 6 }}>
            Device Name
          </Text>

          <TextInput
            value={localName}
            onChangeText={setLocalName}
            style={{
              borderWidth: 1,
              borderColor: "#334155",
              padding: 12,
              borderRadius: 14,
              marginBottom: 18,
              color: "white",
              backgroundColor: "#1e293b",
            }}
          />

          <Pressable
            onPress={handleSave}
            style={({ pressed }) => ({
              padding: 14,
              borderRadius: 14,
              backgroundColor: pressed ? "#15803d" : "#16a34a",
              marginBottom: 12,
            })}
          >
            <Text
              style={{
                color: "white",
                textAlign: "center",
                fontWeight: "700",
              }}
            >
              Save Changes
            </Text>
          </Pressable>

          <Pressable
            onPress={onClose}
            style={({ pressed }) => ({
              padding: 14,
              borderRadius: 14,
              backgroundColor: pressed ? "#7f1d1d" : "#991b1b",
            })}
          >
            <Text
              style={{
                color: "white",
                textAlign: "center",
                fontWeight: "700",
              }}
            >
              Cancel
            </Text>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}