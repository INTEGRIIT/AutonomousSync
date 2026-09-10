import * as DocumentPicker from "expo-document-picker";
import * as FileSystem from "expo-file-system/legacy";
import AsyncStorage from "@react-native-async-storage/async-storage";
import * as SecureStore from "expo-secure-store";
import { v4 as uuidv4 } from "uuid";
import "react-native-get-random-values";

const BASE_URL = "https://api.autonomous-sync.com";
const STORAGE_KEY = "selected_files";

// ================= PICK =================

export async function pickFile() {
  try {
    const result = await DocumentPicker.getDocumentAsync({
      copyToCacheDirectory: true,
      multiple: false,
    });

    if (result.canceled) return null;

    const asset = result.assets?.[0];

    if (!asset?.uri) return null;

    return {
      uri: asset.uri,
      name: asset.name || `file_${Date.now()}`,
      size: asset.size || 0,
      type: asset.mimeType || "application/octet-stream",
    };
  } catch (err) {
    console.error("❌ File pick error:", err);
    return null;
  }
}

// ================= PERSIST =================

export async function persistFile(file) {
  try {
    if (!file?.uri || !file?.name) return null;

    const docDir = FileSystem.documentDirectory;
    if (!docDir) return null;

    const safeName = `${Date.now()}_${file.name.replace(/\s+/g, "_")}`;
    const newPath = docDir + safeName;

    const info = await FileSystem.getInfoAsync(file.uri);
    if (!info.exists) return null;

    await FileSystem.copyAsync({
      from: file.uri,
      to: newPath,
    });

    const now = new Date().toISOString();

    return {
      uri: newPath,
      name: safeName,
      type: file.type,
      size: file.size || 0,
      uploaded_at: now,
      last_synced: null,
      source: "local",
    };
  } catch (err) {
    console.error("❌ persistFile error:", err);
    return null;
  }
}

// ================= STORAGE =================

export async function getStoredFiles() {
  try {
    const data = await AsyncStorage.getItem(STORAGE_KEY);
    return data ? JSON.parse(data) : [];
  } catch {
    return [];
  }
}

export async function saveFile(file) {
  try {
    const existing = await getStoredFiles();

    const updated = [
      ...existing.filter((f) => f.name !== file.name),
      file,
    ];

    await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  } catch (err) {
    console.error("❌ Save file error:", err);
  }
}

// ================= SYNC TRACKING =================

export async function markFileAsSynced(fileName) {
  try {
    const files = await getStoredFiles();

    const updated = files.map((f) =>
      f.name === fileName
        ? { ...f, last_synced: new Date().toISOString() }
        : f
    );

    await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(updated));

    console.log("🔄 FILE SYNCED:", fileName);
  } catch (err) {
    console.error("❌ markFileAsSynced error:", err);
  }
}

// ================= REMOVE =================

export async function removeFile(fileName) {
  try {
    const files = await getStoredFiles();

    const target = files.find((f) => f.name === fileName);

    if (target?.uri) {
      await FileSystem.deleteAsync(target.uri, { idempotent: true });
    }

    const updated = files.filter((f) => f.name !== fileName);

    await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(updated));

    console.log("🗑️ FILE REMOVED:", fileName);
  } catch (err) {
    console.error("❌ Remove file error:", err);
  }
}

// ================= UPLOAD =================

export async function uploadFile(file, deviceUid, deviceName, snapshotId) {
  try {
    if (!file || !deviceUid || !deviceName) return null;

    if (!snapshotId) snapshotId = uuidv4();

    const formData = new FormData();

    formData.append("device_uid", deviceUid);
    formData.append("device_name", deviceName);
    formData.append("user_id", deviceUid);
    formData.append("snapshot_id", snapshotId);

    // 🔥 FILE
    formData.append("file", {
      uri: file.uri,
      name: file.name,
      type: file.type,
    });

    // 🔥 CRITICAL FIX
    formData.append("size", String(file.size || 0));

    const res = await fetch(`${BASE_URL}/upload`, {
      method: "POST",
      body: formData,
    });

    const text = await res.text();

    try {
      return JSON.parse(text);
    } catch {
      return null;
    }
  } catch (err) {
    console.error("❌ Upload failed:", err);
    return null;
  }
}

// ================= SELECTED =================

async function getSelectedFiles() {
  try {
    const raw = await SecureStore.getItemAsync("selected_files");
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

// ================= AUTO UPLOAD =================

export async function uploadSelectedFiles(deviceUid, deviceName, snapshotId) {
  try {
    if (!deviceUid || !deviceName) return;

    const files = await getSelectedFiles();

    if (!files.length) return;

    if (!snapshotId) snapshotId = uuidv4();

    for (const file of files) {

      // 🚫 SKIP already synced
      if (file.last_synced) {
        console.log("⏭️ SKIP (already synced):", file.name);
        continue;
      }

      if (file.source === "local") {
        const result = await uploadFile(file, deviceUid, deviceName, snapshotId);

        if (result?.ok) {
          await markFileAsSynced(file.name); // ✅ CRITICAL FIX
        }
      }
    }

  } catch (err) {
    console.error("❌ uploadSelectedFiles error:", err);
  }
}