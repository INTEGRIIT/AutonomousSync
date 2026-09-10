import { uploadAllStoredFiles } from "../utils/fileManager"; // 🔥 ADD THIS

export function createWebSocket(url, handlers = {}) {
  console.log("🌐 Creating WebSocket:", url);

  const ws = new WebSocket(url);

  ws.onopen = () => {
    console.log("🔥 WS CONNECTED");
    handlers.onOpen?.(ws);
  };

  ws.onmessage = async (event) => {
    try {
      const data = JSON.parse(event.data);

      // ==========================================
      // 🔥 EVENT-BASED AUTO UPLOAD (CRITICAL FIX)
      // ==========================================
      if (data?.trigger_upload && data?.snapshot?.id) {
        console.log("🚀 EVENT TRIGGERED UPLOAD");
        console.log("📦 SNAPSHOT:", data.snapshot.id);

        try {
          await uploadAllStoredFiles(
            data.device_uid,
            data.device_name,
            data.snapshot.id
          );
        } catch (err) {
          console.log("❌ AUTO UPLOAD FAILED:", err);
        }
      }

      // ==========================================
      // NORMAL HANDLER FLOW
      // ==========================================
      handlers.onMessage?.(data);

    } catch (e) {
      console.log("WS PARSE ERROR:", e);
    }
  };

  ws.onerror = (e) => {
    console.log("🚨 WS ERROR:", e?.message || e);
    handlers.onError?.(e);
  };

  ws.onclose = (e) => {
    console.log("❌ WS CLOSED:", e.code);
    handlers.onClose?.(e);
  };

  return ws;
}