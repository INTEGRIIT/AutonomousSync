import { Accelerometer, Gyroscope, Magnetometer } from "expo-sensors";

export function startSensors(accRef, gyrRef, magRef) {
  Accelerometer.setUpdateInterval(50);
  Gyroscope.setUpdateInterval(50);
  Magnetometer.setUpdateInterval(100);

  const a = Accelerometer.addListener((d) => (accRef.current = d));
  const g = Gyroscope.addListener((d) => (gyrRef.current = d));
  const m = Magnetometer.addListener((d) => (magRef.current = d));

  return () => {
    a.remove();
    g.remove();
    m.remove();
  };
}