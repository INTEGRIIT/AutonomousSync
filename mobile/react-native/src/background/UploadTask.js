import * as SecureStore from "expo-secure-store";
import { uploadSelectedFiles } from "../services/fileService";

export default async (taskData) => {
  try {
    console.log("🤖 HEADLESS TASK TRIGGERED:", taskData);

    const deviceUid = await SecureStore.getItemAsync("device_uid");

    if (!deviceUid) {
      console.log("❌ No device UID");
      return;
    }

    await uploadSelectedFiles(deviceUid);

    console.log("✅ Background upload complete");
  } catch (e) {
    console.log("❌ Headless task error:", e);
  }
};