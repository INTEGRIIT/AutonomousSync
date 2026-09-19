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

/**
 * Whether a file differs from what was last uploaded.
 *
 * Returns true if it has never synced, if its size or modification
 * time has moved since, or if the file cannot be inspected. The last
 * case errs toward uploading: a redundant transfer costs bandwidth,
 * a missed one costs the data the system exists to protect.
 */
export async function fileChangedSinceSync(file) {
  if (!file?.last_synced) return true;
  if (!file?.uri) return true;
  try {
    const info = await FileSystem.getInfoAsync(file.uri);
    if (!info?.exists) return false;
    if (file.synced_size == null && file.synced_mtime == null) {
      // Synced before change tracking existed. Treat as unchanged so
      // an upgrade does not trigger a re-upload of everything.
      return false;
    }
    if (file.synced_size != null && info.size !== file.synced_size) return true;
    if (file.synced_mtime != null &&
        info.modificationTime !== file.synced_mtime) return true;
    return false;
  } catch {
    return true;
  }
}


export async function markFileAsSynced(fileName) {
  try {
    const files = await getStoredFiles();

    // Record what was synced, not merely that something was. Storing
    // only a timestamp means a file can never be re-protected after
    // its first upload, however much it changes afterwards. Size and
    // modification time let the next hazard ask whether this specific
    // content has already been sent.
    const target = files.find((f) => f.name === fileName);
    let syncedSize = target?.size ?? null;
    let syncedMtime = null;
    if (target?.uri) {
      try {
        const info = await FileSystem.getInfoAsync(target.uri);
        if (info?.exists) {
          syncedSize = info.size ?? syncedSize;
          syncedMtime = info.modificationTime ?? null;
        }
      } catch { /* fall back to the stored size */ }
    }

    const updated = files.map((f) =>
      f.name === fileName
        ? {
            ...f,
            last_synced: new Date().toISOString(),
            synced_size: syncedSize,
            synced_mtime: syncedMtime,
          }
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

/**
 * The selected files, with sync state merged in from the catalogue.
 *
 * Two stores are in play and both are legitimate. SecureStore holds
 * which files the user ticked; AsyncStorage holds the catalogue of
 * every added file along with its metadata and sync state. The
 * selection is written once as a snapshot of the records at save
 * time, so when markFileAsSynced updates the catalogue those copies
 * never see it.
 *
 * Reading the selection alone therefore always reports last_synced
 * as absent, nothing is ever skipped, and every hazard re-uploads
 * everything. One pilot session produced 160 uploads of three files.
 *
 * The selection decides what to consider; the catalogue decides
 * whether it has already been sent.
 */
async function getSelectedFiles() {
  try {
    const raw = await SecureStore.getItemAsync("selected_files");
    const selected = raw ? JSON.parse(raw) : [];
    if (!selected.length) return [];

    const catalogue = await getStoredFiles();
    const byName = {};
    for (const f of catalogue) byName[f.name] = f;

    return selected.map((sel) => ({ ...sel, ...(byName[sel.name] || {}) }));
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

// ---------------------------------------------------------------
// Queue-facing wrapper.
//
// uploadSelectedFiles() returns undefined on success, on "no files",
// and on error alike, and swallows exceptions. The upload queue needs
// to know whether an attempt actually worked, so this variant reports
// per-file outcomes without changing the existing call sites.
// ---------------------------------------------------------------

export async function uploadSelectedFilesTracked(deviceUid, deviceName,
                                                 snapshotId,
                                                 force = false) {
  if (!deviceUid || !deviceName) return { ok: false, reason: "missing_ids" };

  const files = await getSelectedFiles();
  if (!files.length) return { ok: true, uploaded: 0, reason: "no_files" };

  if (!snapshotId) snapshotId = uuidv4();

  let uploaded = 0;
  let failed = 0;
  let skipped = 0;

  for (const file of files) {
    if (file.source !== "local") continue;
    // Skip only content that has genuinely already been sent. force
    // overrides this entirely and uploads regardless, which is useful
    // for isolating transfer latency from the change-detection path.
    if (!force && !(await fileChangedSinceSync(file))) {
      skipped += 1;
      continue;
    }
    try {
      const result = await uploadFile(file, deviceUid, deviceName, snapshotId);
      if (result?.ok) {
        await markFileAsSynced(file.name);
        uploaded += 1;
      } else {
        failed += 1;
      }
    } catch (err) {
      console.log("upload error:", file.name, err?.message || err);
      failed += 1;
    }
  }

  return { ok: failed === 0, uploaded, failed, skipped,
           snapshot_id: snapshotId };
}
