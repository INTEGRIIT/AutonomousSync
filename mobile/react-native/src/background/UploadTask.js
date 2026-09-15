import * as SecureStore from "expo-secure-store";
import { uploadSelectedFilesTracked } from "../services/fileService";
import { enqueue, flush } from "../services/uploadQueue";

export default async (taskData) => {
  try {
    const deviceUid = await SecureStore.getItemAsync("device_uid");
    const deviceName = await SecureStore.getItemAsync("device_name");
    if (!deviceUid) return;

    const snapshotId = taskData?.snapshot?.id || taskData?.snapshot_id || null;

    // Queue first, upload second. If the process dies mid-upload — which
    // is plausible on a phone that was just dropped — the entry survives.
    await enqueue({ snapshot_id: snapshotId, device_uid: deviceUid,
                    device_name: deviceName });

    await flush(async (entry) => {
      const r = await uploadSelectedFilesTracked(entry.device_uid, entry.device_name, entry.snapshot_id);
      return !!r?.ok;
    });
  } catch (e) {
    console.log("headless task error:", e);
  }
};
