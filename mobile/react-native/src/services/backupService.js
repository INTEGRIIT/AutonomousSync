import * as SecureStore from "expo-secure-store";

const KEY = "backup_files";

/**
 * ➕ Add file to backup list (SAFE + NO DUPLICATES)
 */
export async function addBackupFile(file) {
  try {
    if (!file?.uri || !file?.name) {
      console.log("🚨 Invalid file not added:", file);
      return;
    }

    const existing = await getBackupFiles();

    // 🔥 Prevent duplicates (by uri)
    const alreadyExists = existing.some(f => f.uri === file.uri);

    if (alreadyExists) {
      console.log("⚠️ File already in backup list:", file.name);
      return;
    }

    const updated = [...existing, file];

    await SecureStore.setItemAsync(KEY, JSON.stringify(updated));

    console.log("💾 Added to backup list:", file.name);

  } catch (err) {
    console.log("❌ addBackupFile error:", err);
  }
}

/**
 * 📦 Get all backup files (CLEAN + SAFE)
 */
export async function getBackupFiles() {
  try {
    const raw = await SecureStore.getItemAsync(KEY);

    const parsed = raw ? JSON.parse(raw) : [];

    // 🔥 Clean corrupted entries
    const clean = parsed.filter(f => f && f.uri && f.name);

    if (clean.length !== parsed.length) {
      console.log("⚠️ Cleaned corrupted backup entries");
      await SecureStore.setItemAsync(KEY, JSON.stringify(clean));
    }

    return clean;

  } catch (err) {
    console.log("❌ getBackupFiles error:", err);
    return [];
  }
}

/**
 * 🗑️ Remove one file from backup list
 */
export async function removeBackupFile(uri) {
  try {
    const existing = await getBackupFiles();

    const updated = existing.filter(f => f.uri !== uri);

    await SecureStore.setItemAsync(KEY, JSON.stringify(updated));

    console.log("🗑️ Removed from backup list:", uri);

  } catch (err) {
    console.log("❌ removeBackupFile error:", err);
  }
}

/**
 * 🧹 Clear all backup files
 */
export async function clearBackupFiles() {
  try {
    await SecureStore.deleteItemAsync(KEY);
    console.log("🧹 Backup list cleared");
  } catch (err) {
    console.log("❌ clearBackupFiles error:", err);
  }
}