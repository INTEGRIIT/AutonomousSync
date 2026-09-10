import { BASE_URL } from "../../config";

export async function fetchBackupPreferences(deviceUid) {
  const res = await fetch(`${BASE_URL}/devices/${deviceUid}/preferences`);
  return await res.json();
}

export async function saveBackupPreferences(deviceUid, preferences) {
  const res = await fetch(`${BASE_URL}/devices/${deviceUid}/preferences`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ preferences }),
  });

  return await res.json();
}