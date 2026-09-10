import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  ScrollView,
  RefreshControl,
  TouchableOpacity,
  Linking,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { BASE_URL } from "../../config";
import * as FileSystem from "expo-file-system/legacy";
import * as Sharing from "expo-sharing";
import { Alert } from "react-native";

const handleExport = async (deviceUid) => {
  try {
    const url = `${BASE_URL}/events/export/${deviceUid}`;

    const fileUri = FileSystem.documentDirectory + "events.csv";

    const download = await FileSystem.downloadAsync(url, fileUri);

    if (await Sharing.isAvailableAsync()) {
      await Sharing.shareAsync(download.uri);
    } else {
      Alert.alert("Exported", "File saved to device");
    }

  } catch (err) {
    console.log("❌ export error:", err);
    Alert.alert("Error", "Export failed");
  }
};

/* =========================================================
🧠 ICON MAPPER
========================================================= */
const getEventIcon = (type) => {
  switch (type) {
    case "EMERGENCY":
      return { name: "alert-circle", color: "#ef4444" };
    case "GRACEFUL":
      return { name: "checkmark-circle", color: "#22c55e" };
    case "DISABLED":
      return { name: "close-circle", color: "#f59e0b" };
    default:
      return { name: "help-circle", color: "#64748b" };
  }
};

const formatEventTime = (value) => {
  if (!value) return "—";
  try {
    if (typeof value === "number") {
      return new Date(value * 1000).toLocaleString();
    }
    return new Date(value).toLocaleString();
  } catch {
    return "—";
  }
};

const formatSize = (bytes) => {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024)
    return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

export default function EventsScreen({ route }) {
  const { deviceUid } = route.params;

  const [events, setEvents] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [expanded, setExpanded] = useState({});

  const loadEvents = async () => {
    try {
      const res = await fetch(`${BASE_URL}/events/${deviceUid}`);
      const json = await res.json();

      if (json.ok) {
        setEvents(json.events || []);
      }
    } catch (e) {
      console.log("❌ events fetch error:", e);
    }
  };

  useEffect(() => {
    loadEvents();
  }, [deviceUid]);

  const onRefresh = async () => {
    setRefreshing(true);
    await loadEvents();
    setRefreshing(false);
  };

  return (
    <ScrollView
      style={{ padding: 16, backgroundColor: "#020617" }}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }
    >

      {/* ✅ ADD THIS BLOCK HERE */}
      <TouchableOpacity
        onPress={() => handleExport(deviceUid)}
        style={{
          backgroundColor: "#38bdf8",
          padding: 10,
          borderRadius: 10,
          marginBottom: 12,
          alignItems: "center",
        }}
      >
        <Text style={{ color: "#020617", fontWeight: "700" }}>
          Export Incident Report
        </Text>
      </TouchableOpacity>



      {events.map((e, i) => {
        const eventType = e.event_type || e.type || "UNKNOWN";
        const reason = e.reason || "unknown";
        const pushSuccess =
          typeof e.push_success === "boolean"
            ? e.push_success
            : !!e.push_sent;
        const syncTriggered =
          typeof e.sync_triggered === "boolean"
            ? e.sync_triggered
            : false;
        const eventTime = e.timestamp || e.ts || null;

        const icon = getEventIcon(eventType);
        const isEmergency = eventType === "EMERGENCY";

        return (
          <View
            key={e.event_id || e.snapshot_id || i}
            style={{
              backgroundColor: "#0f172a",
              padding: 14,
              borderRadius: 14,
              marginBottom: 12,
              borderWidth: 1,
              borderColor: isEmergency ? "#ef4444" : "#22c55e",
            }}
          >
            {/* HEADER */}
            <View style={{ flexDirection: "row", alignItems: "center", flexWrap: "wrap" }}>
              <Ionicons
                name={icon.name}
                size={18}
                color={icon.color}
                style={{ marginRight: 8 }}
              />

              <Text
                style={{
                  color: "#fff",
                  fontWeight: "700",
                  fontSize: 14,
                }}
              >
                {eventType} — {reason}
              </Text>


              {e.run_number && (
                <Text
                  style={{
                    color: "#38bdf8",
                    marginLeft: 8,
                    fontSize: 12,
                    fontWeight: "700",
                  }}
                >
                  • Run #{e.run_number}
                </Text>
              )}
            </View>

            {/* TIME */}
            <Text style={{ color: "#94a3b8", fontSize: 11, marginTop: 4 }}>
              {formatEventTime(eventTime)}
            </Text>

            {/* STATUS */}
            <Text style={{ color: "#cbd5f5", marginTop: 6 }}>
              State: {e.state || "—"}
            </Text>

            <Text style={{ color: "#94a3b8" }}>
              Sync: {syncTriggered ? "Yes" : "No"} | Push:{" "}
              {pushSuccess ? "Success" : "Fail"}
            </Text>

            {/* SNAPSHOT HEADER */}
            {e.snapshot_id && (
              <TouchableOpacity
                onPress={() =>
                  setExpanded((prev) => ({
                    ...prev,
                    [i]: !prev[i],
                  }))
                }
                style={{
                  marginTop: 6,
                  flexDirection: "row",
                  alignItems: "center",
                }}
              >
                <Ionicons
                  name="folder-open-outline"
                  size={14}
                  color="#22c55e"
                  style={{ marginRight: 4 }}
                />
                <Text style={{ color: "#22c55e" }}>
                  Snapshot: {e.snapshot_id.slice(0, 8)}...
                </Text>

                {e.file_count > 0 && (
                  <Text style={{ color: "#38bdf8", marginLeft: 8 }}>
                    ({e.file_count} files)
                  </Text>
                )}
              </TouchableOpacity>
            )}

            {/* FILES (FIXED + CLEAN) */}
            {expanded[i] && e.files?.length > 0 && (
              <View style={{ marginTop: 8 }}>

                {/* TOTAL SIZE */}
                <Text style={{ color: "#22c55e", fontSize: 12, marginBottom: 6 }}>
                  Total Size:{" "}
                  {formatSize(
                    e.files.reduce((sum, f) => sum + (f.size || 0), 0)
                  )}
                </Text>

                {e.files.map((f, idx) => (
                  <TouchableOpacity
                    key={idx}
                    onPress={() => Linking.openURL(f.url)}
                    style={{
                      padding: 10,
                      backgroundColor: "#020617",
                      borderRadius: 10,
                      marginBottom: 6,
                      borderWidth: 1,
                      borderColor: "#1e293b",
                    }}
                  >
                    <Text style={{ color: "#38bdf8", fontWeight: "600" }}>
                      📄 {f.filename}
                    </Text>

                    <Text style={{ color: "#94a3b8", fontSize: 11 }}>
                      Size: {formatSize(f.size)}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>
            )}

            {/* FEATURES */}
            <View style={{ marginTop: 8 }}>

              {/* 🧠 MOTION */}
              <Text style={{ color: "#38bdf8", fontSize: 12 }}>
                acc: {e.features?.acc_norm?.toFixed(2) || "—"} | 
                gyro: {e.features?.gyr_norm?.toFixed(2) || "—"} | 
                jerk: {e.features?.jerk?.toFixed(2) || "—"}
              </Text>

              {/* 📐 ORIENTATION */}
              <Text style={{ color: "#a78bfa", fontSize: 12, marginTop: 2 }}>
                roll: {e.features?.roll?.toFixed(2) || "—"} | 
                pitch: {e.features?.pitch?.toFixed(2) || "—"}
              </Text>

              {/* 🧩 STABILITY */}
              <Text style={{ color: "#22c55e", fontSize: 12, marginTop: 2 }}>
                stability: {e.features?.stability?.toFixed(2) || "—"} | 
                stable: {e.temporal?.stable_duration_ms || 0} ms
              </Text>

            </View>

            {/* FLAGS */}
            <View style={{ flexDirection: "row", marginTop: 6 }}>
              <Text style={{ color: "#fbbf24", fontSize: 11 }}>
                impact: {e.temporal?.impact ? "✔" : "✖"} | free_fall:{" "}
                {e.temporal?.free_fall ? "✔" : "✖"} | water:{" "}
                {e.temporal?.water_emergency ? "✔" : "✖"}
              </Text>
            </View>

            <Text style={{ color: "#64748b", fontSize: 11, marginTop: 4 }}>
              stable: {e.temporal?.stable_duration_ms || 0} ms
            </Text>
          </View>
        );
      })}

      {events.length === 0 && (
        <Text style={{ color: "#64748b", textAlign: "center", marginTop: 40 }}>
          No events yet
        </Text>
      )}
    </ScrollView>
  );
}