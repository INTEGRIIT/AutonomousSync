import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  TextInput,
  Pressable,
  Modal,
  KeyboardAvoidingView,
  Platform,
  Switch,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
} from "react-native";
import * as SecureStore from "expo-secure-store";
import { Feather } from "@expo/vector-icons";

const DEFAULT_PREFS = {
  auto_backup: true,
  alert_sensitivity: "high",
  include_telemetry: true,
  include_battery: true,
};

export default function SettingsModal({
  visible,
  onClose,
  deviceName,
  setDeviceName,
  navigation,
}) {
  const [localName, setLocalName] = useState(deviceName || "");
  const [prefs, setPrefs] = useState(DEFAULT_PREFS);
  const [uploading, setUploading] = useState(false);

  // 🔄 Hydrate name
  useEffect(() => {
    if (visible) {
      setLocalName(deviceName || "");
    }
  }, [visible, deviceName]);

  // 🔄 Load preferences
  useEffect(() => {
    if (!visible) return;

    const loadPrefs = async () => {
      try {
        const raw = await SecureStore.getItemAsync("user_preferences");
        if (raw) {
          setPrefs({ ...DEFAULT_PREFS, ...JSON.parse(raw) });
        } else {
          setPrefs(DEFAULT_PREFS);
        }
      } catch (e) {
        console.log("PREF LOAD ERROR:", e);
      }
    };

    loadPrefs();
  }, [visible]);

  const updatePref = (key, value) => {
    setPrefs((prev) => ({ ...prev, [key]: value }));
  };

  const trimmed = (localName || "").trim();
  const original = (deviceName || "").trim();
  const canSave = trimmed.length > 0;

  const handleSave = async () => {
    if (!canSave) return;

    try {
      if (trimmed !== original) {
        await SecureStore.setItemAsync("device_name", trimmed);
        setDeviceName(trimmed);
      }

      await SecureStore.setItemAsync(
        "user_preferences",
        JSON.stringify(prefs)
      );

      console.log("💾 Saved prefs + device name:", trimmed);

      onClose();
    } catch (e) {
      console.log("SAVE ERROR:", e);
    }
  };

  return (
    <Modal visible={visible} animationType="slide" transparent>
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
          <Text style={{ fontSize: 18, fontWeight: "800", color: "white", marginBottom: 18 }}>
            Device Settings
          </Text>

          {/* DEVICE NAME */}
          <Text style={{ color: "#94a3b8", marginBottom: 6 }}>Device Name</Text>
          <TextInput
            value={localName}
            onChangeText={setLocalName}
            autoCapitalize="words"
            autoCorrect={false}
            placeholder="Enter device name"
            placeholderTextColor="#64748b"
            style={{
              borderWidth: 1,
              borderColor: "#334155",
              padding: 14,
              borderRadius: 16,
              marginBottom: 20,
              color: "white",
              backgroundColor: "#1e293b",
            }}
          />

          {/* SWITCHES */}
          <Row label="Auto Backup">
            <Switch
              value={prefs.auto_backup}
              onValueChange={(v) => updatePref("auto_backup", v)}
            />
          </Row>

          <Row label="Include Telemetry">
            <Switch
              value={prefs.include_telemetry}
              onValueChange={(v) => updatePref("include_telemetry", v)}
            />
          </Row>

          <Row label="Include Battery">
            <Switch
              value={prefs.include_battery}
              onValueChange={(v) => updatePref("include_battery", v)}
            />
          </Row>

          {/* VIEW FILES */}
          <TouchableOpacity
            onPress={() => {
              onClose();
              navigation.navigate("FileManager");
            }}
          >
            <Text style={{ color: "#38bdf8", marginTop: 12 }}>
              View Uploaded Files
            </Text>
          </TouchableOpacity>

          {/* SENSITIVITY */}
          <Text style={{ color: "#94a3b8", marginTop: 16 }}>
            Alert Sensitivity
          </Text>

          <View style={{ flexDirection: "row", marginTop: 8 }}>
            {["low", "medium", "high"].map((level) => (
              <Pressable
                key={level}
                onPress={() => updatePref("alert_sensitivity", level)}
                style={{
                  flex: 1,
                  padding: 10,
                  marginRight: 6,
                  borderRadius: 10,
                  backgroundColor:
                    prefs.alert_sensitivity === level ? "#2563eb" : "#1e293b",
                }}
              >
                <Text style={{ color: "white", textAlign: "center" }}>
                  {level.toUpperCase()}
                </Text>
              </Pressable>
            ))}
          </View>

          {/* SAVE */}
          <Pressable
            onPress={handleSave}
            disabled={!canSave}
            style={{
              marginTop: 20,
              padding: 16,
              borderRadius: 16,
              backgroundColor: "#16a34a",
            }}
          >
            <Text style={{ color: "white", textAlign: "center", fontWeight: "800" }}>
              Save Changes
            </Text>
          </Pressable>

          {/* CANCEL */}
          <Pressable
            onPress={onClose}
            style={{
              marginTop: 10,
              padding: 16,
              borderRadius: 16,
              backgroundColor: "#991b1b",
            }}
          >
            <Text style={{ color: "white", textAlign: "center", fontWeight: "800" }}>
              Cancel
            </Text>
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

/* ---------------------------------------- */
/* HELPER */
/* ---------------------------------------- */

const Row = ({ label, children }) => (
  <View
    style={{
      flexDirection: "row",
      justifyContent: "space-between",
      alignItems: "center",
      marginBottom: 12,
    }}
  >
    <Text style={{ color: "white" }}>{label}</Text>
    {children}
  </View>
);