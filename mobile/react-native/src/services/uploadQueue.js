// src/services/uploadQueue.js
//
// Durable upload queue for emergency snapshots.
//
// WHY THIS EXISTS
// Before this, a failed upload was simply lost: UploadTask.js called
// uploadSelectedFiles, caught the exception, and logged it. If the
// network dropped at the moment of impact — which is exactly when a
// dropped phone is most likely to lose connectivity — the snapshot
// never reached the server and the system silently failed at the one
// job it exists to do.
//
// The queue persists pending uploads across app restarts, retries with
// exponential backoff, and flushes whenever connectivity returns or the
// app comes back to the foreground.
//
// It deliberately does NOT delete a pending entry until an upload
// reports success, so a crash mid-upload leaves the entry in place to
// be retried rather than dropping it.

import AsyncStorage from "@react-native-async-storage/async-storage";
import * as Network from "expo-network";

const QUEUE_KEY = "upload_queue_v1";
const MAX_ATTEMPTS = 8;
const BASE_DELAY_MS = 2000;      // 2s, doubling: 2, 4, 8 ... capped
const MAX_DELAY_MS = 5 * 60 * 1000;

let flushing = false;
let timer = null;

async function readQueue() {
  try {
    const raw = await AsyncStorage.getItem(QUEUE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

async function writeQueue(q) {
  try {
    await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(q));
  } catch (err) {
    console.log("queue write failed:", err?.message || err);
  }
}

function backoffFor(attempts) {
  return Math.min(BASE_DELAY_MS * 2 ** attempts, MAX_DELAY_MS);
}

/**
 * Add a pending upload. Safe to call from an emergency path — it only
 * touches AsyncStorage and returns immediately.
 */
export async function enqueue(entry) {
  const q = await readQueue();
  // Same snapshot queued twice is a duplicate, not two uploads.
  if (entry.snapshot_id && q.some((e) => e.snapshot_id === entry.snapshot_id)) {
    return q.length;
  }
  q.push({
    ...entry,
    queued_at: Date.now(),
    attempts: 0,
    next_attempt_at: Date.now(),
    last_error: null,
  });
  await writeQueue(q);
  console.log(`upload queued (${q.length} pending):`, entry.snapshot_id);
  return q.length;
}

export async function queueDepth() {
  return (await readQueue()).length;
}

export async function pending() {
  return await readQueue();
}

export async function clearQueue() {
  await AsyncStorage.removeItem(QUEUE_KEY);
}

/**
 * Attempt every due entry once.
 *
 * @param uploadFn async (entry) => boolean   the real upload call
 * @returns {sent, failed, remaining}
 */
export async function flush(uploadFn) {
  if (flushing) return { sent: 0, failed: 0, remaining: -1 };
  flushing = true;

  let sent = 0;
  let failed = 0;

  try {
    // Don't burn attempts while plainly offline.
    try {
      const net = await Network.getNetworkStateAsync();
      if (!net?.isConnected) {
        const q = await readQueue();
        return { sent: 0, failed: 0, remaining: q.length };
      }
    } catch {
      // if the check itself fails, try the upload anyway
    }

    const q = await readQueue();
    const now = Date.now();
    const keep = [];

    for (const entry of q) {
      if (entry.next_attempt_at > now) {
        keep.push(entry);
        continue;
      }
      if (entry.attempts >= MAX_ATTEMPTS) {
        // Keep it rather than discard: a permanently failed upload is
        // data the user still expects to exist, and it is evidence for
        // the reliability evaluation.
        keep.push({ ...entry, status: "exhausted" });
        failed += 1;
        continue;
      }

      let ok = false;
      let err = null;
      try {
        ok = await uploadFn(entry);
      } catch (e) {
        err = String(e?.message || e);
      }

      if (ok) {
        sent += 1;
        console.log("upload succeeded:", entry.snapshot_id);
      } else {
        const attempts = entry.attempts + 1;
        keep.push({
          ...entry,
          attempts,
          next_attempt_at: now + backoffFor(attempts),
          last_error: err || "upload returned false",
        });
        failed += 1;
        console.log(
          `upload failed (attempt ${attempts}/${MAX_ATTEMPTS}):`,
          entry.snapshot_id, err || ""
        );
      }
    }

    await writeQueue(keep);
    return { sent, failed, remaining: keep.length };
  } finally {
    flushing = false;
  }
}

/**
 * Periodic flush. Call once at app start; call stopAutoFlush on teardown.
 */
export function startAutoFlush(uploadFn, intervalMs = 30000) {
  stopAutoFlush();
  flush(uploadFn);
  timer = setInterval(() => flush(uploadFn), intervalMs);
  return () => stopAutoFlush();
}

export function stopAutoFlush() {
  if (timer) {
    clearInterval(timer);
    timer = null;
  }
}

export default {
  enqueue, flush, queueDepth, pending, clearQueue,
  startAutoFlush, stopAutoFlush,
};
