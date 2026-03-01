import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  TextInput,
  Pressable,
  Modal,
  KeyboardAvoidingView,
  Platform,
} from "react-native";

export default function SettingsModal({
  visible,
  onClose,
  deviceName,
  setDeviceName,
}) {
  const [localName, setLocalName] = useState(deviceName || "");

  // 🔄 Always hydrate input when modal opens
  useEffect(() => {
    if (visible) {
      setLocalName(deviceName || "");
    }
  }, [visible, deviceName]);

  const trimmed = (localName || "").trim();
  const original = (deviceName || "").trim();

  const canSave =
    trimmed.length > 0 &&
    trimmed !== original;

  const handleSave = () => {
    if (!canSave) return;

    // ✅ Only update state
    // App.js handles persistence + re-register logic
    setDeviceName(trimmed);

    onClose();
  };

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent
      onRequestClose={onClose}
    >
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
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
            padding: 24,
            borderRadius: 22,
          }}
        >
          <Text
            style={{
              fontSize: 18,
              fontWeight: "800",
              color: "white",
              marginBottom: 18,
            }}
          >
            Device Settings
          </Text>

          <Text
            style={{
              color: "#94a3b8",
              marginBottom: 6,
              fontWeight: "600",
            }}
          >
            Device Name
          </Text>

          <TextInput
            value={localName}
            onChangeText={setLocalName}
            autoCapitalize="words"
            autoCorrect={false}
            autoFocus
            returnKeyType="done"
            onSubmitEditing={handleSave}
            placeholder="e.g., Darryl’s iPhone"
            placeholderTextColor="#64748b"
            style={{
              borderWidth: 1,
              borderColor: "#334155",
              padding: 14,
              borderRadius: 16,
              marginBottom: 20,
              color: "white",
              backgroundColor: "#1e293b",
              fontSize: 15,
            }}
          />

          <Pressable
            onPress={handleSave}
            disabled={!canSave}
            style={({ pressed }) => ({
              padding: 16,
              borderRadius: 16,
              backgroundColor: !canSave
                ? "#064e3b"
                : pressed
                ? "#15803d"
                : "#16a34a",
              opacity: !canSave ? 0.6 : 1,
              marginBottom: 12,
              transform: pressed ? [{ scale: 0.98 }] : [{ scale: 1 }],
            })}
          >
            <Text
              style={{
                color: "white",
                textAlign: "center",
                fontWeight: "800",
              }}
            >
              Save Changes
            </Text>
          </Pressable>

          <Pressable
            onPress={onClose}
            style={({ pressed }) => ({
              padding: 16,
              borderRadius: 16,
              backgroundColor: pressed ? "#7f1d1d" : "#991b1b",
              transform: pressed ? [{ scale: 0.98 }] : [{ scale: 1 }],
            })}
          >
            <Text
              style={{
                color: "white",
                textAlign: "center",
                fontWeight: "800",
              }}
            >
              Cancel
            </Text>
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}