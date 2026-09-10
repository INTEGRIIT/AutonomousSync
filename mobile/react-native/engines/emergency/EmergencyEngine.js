import { Accelerometer, Gyroscope } from "expo-sensors";
import * as Notifications from "expo-notifications";

const ACCEL_THRESHOLD = 2.7;
const GYRO_THRESHOLD = 4.5;

let accel = { x: 0, y: 0, z: 0 };
let gyro = { x: 0, y: 0, z: 0 };

let accelSub = null;
let gyroSub = null;

function magnitude(v) {
  return Math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z);
}

async function triggerLocalAlert(score) {
  await Notifications.scheduleNotificationAsync({
    content: {
      title: "Impact Detected",
      body: `Impact score: ${score.toFixed(2)}`,
      sound: "default",
    },
    trigger: null,
  });
}

export function startEmergencyEngine(onImpact) {
  Accelerometer.setUpdateInterval(50);
  Gyroscope.setUpdateInterval(50);

  accelSub = Accelerometer.addListener((data) => {
    accel = data;
    evaluate();
  });

  gyroSub = Gyroscope.addListener((data) => {
    gyro = data;
    evaluate();
  });

  function evaluate() {
    const accelMag = magnitude(accel);
    const gyroMag = magnitude(gyro);

    if (accelMag > ACCEL_THRESHOLD && gyroMag > GYRO_THRESHOLD) {
      const impactScore = accelMag + gyroMag;

      console.log("🚨 IMPACT DETECTED", impactScore);

      triggerLocalAlert(impactScore);

      if (onImpact) {
        onImpact({
          ts: Date.now(),
          accel,
          gyro,
          impactScore,
        });
      }
    }
  }
}

export function stopEmergencyEngine() {
  accelSub?.remove();
  gyroSub?.remove();
}