import { uploadSelectedFilesTracked } from "./fileService";
import { enqueue, flush } from "./uploadQueue";

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

        // Queue before attempting. A phone that was just dropped may
        // lose connectivity or be killed mid-transfer; the queued entry
        // survives both and is retried with backoff.
        try {
          await enqueue({
            snapshot_id: data.snapshot.id,
            device_uid: data.device_uid,
            device_name: data.device_name,
          });
          await flush(async (entry) => {
            const r = await uploadSelectedFilesTracked(entry.device_uid, entry.device_name, entry.snapshot_id, true);
            return !!r?.ok;
          });
        } catch (err) {
          console.log("upload dispatch failed:", err?.message || err);
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