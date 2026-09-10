import React, { useState, useCallback } from "react";
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  Linking,
} from "react-native";
import * as SecureStore from "expo-secure-store";
import { useFocusEffect } from "@react-navigation/native";
import { Feather } from "@expo/vector-icons";

import {
  pickFile,
  persistFile,
  saveFile,
  getStoredFiles,
  removeFile,
} from "../services/fileService";

const BASE_URL = "https://api.autonomous-sync.com";

// ✅ STABLE ID
const getId = (f) => f.name;

export default function FileManagerScreen() {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState({});

  // ================= HELPERS =================

  const formatDate = (date) => {
    if (!date) return "N/A";
    try {
      return new Date(date).toLocaleString();
    } catch {
      return "N/A";
    }
  };

  const formatSize = (bytes) => {
    if (!bytes) return "—";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024)
      return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // ================= SELECTION =================

  const toggleSelect = (item) => {
    const id = getId(item);

    setSelected((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  const selectedCount = Object.values(selected).filter(Boolean).length;

  // ================= SAVE =================

  const saveSelection = async () => {
    try {
      const selectedFiles = files
        .filter((f) => selected[getId(f)])
        .map((f) => ({
          id: f.name,
          key: f.key,
          name: f.name,
          uri: f.uri,
          source: f.source,
          size: f.size || 0,
          type: "application/octet-stream",
        }));

      if (!selectedFiles.length) {
        Alert.alert("No files selected");
        return;
      }

      await SecureStore.setItemAsync(
        "selected_files",
        JSON.stringify(selectedFiles)
      );

      Alert.alert("Saved", `${selectedFiles.length} files ready`);
    } catch (e) {
      console.log("❌ save error:", e);
    }
  };

  // ================= PICK =================

  const handlePickFile = async () => {
    try {
      const picked = await pickFile();
      if (!picked) return;

      const persisted = await persistFile(picked);

      if (!persisted) {
        Alert.alert("Error", "Persist failed");
        return;
      }

      await saveFile(persisted);
      await loadFiles();

      Alert.alert("Saved", "File stored locally");
    } catch (e) {
      console.log("❌ pick error:", e);
    }
  };

  // ================= LOAD =================

  const loadFiles = async () => {
    try {
      setLoading(true);

      const deviceUid = await SecureStore.getItemAsync("device_uid");

      let s3Files = [];
      let localFiles = [];

      // 🔹 CLOUD
      if (deviceUid) {
        const res = await fetch(`${BASE_URL}/files/${deviceUid}`);
        if (res.ok) {
          const json = await res.json();
          if (json.ok && Array.isArray(json.files)) {
            s3Files = json.files.map((f) => ({
              ...f,
              source: "s3",
            }));
          }
        }
      }

      // 🔹 LOCAL
      const stored = await getStoredFiles();

      localFiles = stored.map((f) => ({
        key: `local-${f.name}`,
        name: f.name,
        uri: f.uri,
        size: f.size || 0,
        uploaded_at: f.uploaded_at || Date.now(),
        last_synced: f.last_synced || null,
        source: "local",
      }));

      const merged = [...localFiles, ...s3Files];

      setFiles(merged);

      // 🔥 RESTORE + CLEAN
      await loadSelected(merged);

    } catch (err) {
      console.log("❌ loadFiles error:", err);
      setFiles([]);
    } finally {
      setLoading(false);
    }
  };

  // ================= RESTORE (FIXED) =================

  const loadSelected = async (fileList) => {
    try {
      const raw = await SecureStore.getItemAsync("selected_files");
      if (!raw) return;

      const parsed = JSON.parse(raw);

      const map = {};
      const validFiles = [];

      parsed.forEach((f) => {
        const exists = fileList.find(
          (item) => item.name === f.name
        );

        if (exists) {
          map[f.name] = true;
          validFiles.push(f);
        }
      });

      setSelected(map);

      // 🔥 CLEAN INVALID ENTRIES
      await SecureStore.setItemAsync(
        "selected_files",
        JSON.stringify(validFiles)
      );

      console.log("✅ CLEAN RESTORE:", map);
    } catch (err) {
      console.log("❌ loadSelected error:", err);
    }
  };

  useFocusEffect(
    useCallback(() => {
      loadFiles();
    }, [])
  );

  // ================= DOWNLOAD =================

  const handleDownload = async (key, source) => {
    try {
      if (source === "local") {
        Alert.alert("Local file already on device");
        return;
      }

      const deviceUid = await SecureStore.getItemAsync("device_uid");

      const res = await fetch(
        `${BASE_URL}/download?key=${encodeURIComponent(
          key
        )}&device_uid=${deviceUid}`
      );

      const json = await res.json();

      if (json.ok && json.url) {
        Linking.openURL(json.url);
      }
    } catch (err) {
      console.log("❌ download error:", err);
    }
  };

  // ================= DELETE =================

  const handleDelete = (item) => {
    Alert.alert("Delete File", "Are you sure?", [
      { text: "Cancel" },
      {
        text: "Delete",
        style: "destructive",
        onPress: async () => {
          try {
            if (item.source === "local") {
              await removeFile(item.name);
            } else {
              const deviceUid = await SecureStore.getItemAsync("device_uid");

              await fetch(
                `${BASE_URL}/delete?key=${encodeURIComponent(
                  item.key
                )}&device_uid=${deviceUid}`,
                { method: "DELETE" }
              );
            }

            await loadFiles();
          } catch (err) {
            console.log("❌ delete error:", err);
          }
        },
      },
    ]);
  };

  // ================= CARD =================

  const renderItem = ({ item }) => {
    const id = getId(item);
    const isSelected = selected[id];
    const filename = item.name || item.key?.split("/").pop();

    return (
      <TouchableOpacity onPress={() => toggleSelect(item)}>
        <View
          style={{
            backgroundColor: isSelected ? "#064e3b" : "#1e293b",
            padding: 16,
            borderRadius: 14,
            marginBottom: 12,
            borderWidth: isSelected ? 1 : 0,
            borderColor: "#22c55e",
          }}
        >
          <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
            <View style={{ flexDirection: "row", alignItems: "center" }}>
              <Feather name="file-text" size={16} color="#fff" />
              <Text style={{ color: "white", marginLeft: 8 }}>
                {filename}
              </Text>
            </View>

            <Feather
              name={isSelected ? "check-circle" : "circle"}
              size={20}
              color={isSelected ? "#22c55e" : "#64748b"}
            />
          </View>

          <Text style={{
            color: item.source === "local" ? "#facc15" : "#38bdf8",
            marginTop: 6,
            fontSize: 12,
          }}>
            {item.source === "local" ? "LOCAL FILE" : "CLOUD FILE"}
          </Text>

          <View style={{ marginTop: 8 }}>
            <Text style={{ color: "#94a3b8" }}>
              Uploaded: {formatDate(item.uploaded_at)}
            </Text>
            <Text style={{ color: "#94a3b8" }}>
              Size: {formatSize(item.size)}
            </Text>
          </View>
        </View>
      </TouchableOpacity>
    );
  };

  // ================= UI =================

  return (
    <View style={{ flex: 1, backgroundColor: "#020617", padding: 16 }}>
      <Text style={{ color: "white", fontSize: 22, fontWeight: "800" }}>
        Your Files
      </Text>

      <TouchableOpacity
        onPress={handlePickFile}
        style={{
          backgroundColor: "#0ea5e9",
          padding: 12,
          borderRadius: 10,
          marginVertical: 12,
          alignItems: "center",
        }}
      >
        <Text style={{ color: "white", fontWeight: "700" }}>
          Add File (Local)
        </Text>
      </TouchableOpacity>

      <Text style={{ color: "#94a3b8" }}>
        {selectedCount} selected
      </Text>

      {loading ? (
        <ActivityIndicator color="#00ffcc" />
      ) : (
        <FlatList
          data={files}
          keyExtractor={(item) => getId(item)}
          renderItem={renderItem}
        />
      )}

      <TouchableOpacity
        onPress={saveSelection}
        style={{
          position: "absolute",
          bottom: 20,
          left: 16,
          right: 16,
          backgroundColor: "#22c55e",
          padding: 14,
          borderRadius: 12,
          alignItems: "center",
        }}
      >
        <Text style={{ color: "#020617", fontWeight: "800" }}>
          Save Selection
        </Text>
      </TouchableOpacity>
    </View>
  );
}