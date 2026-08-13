/*
 * HealTheCrop — ESP32 Field Node Firmware (USB-only)
 * -----------------------------------------------------
 * Reads soil moisture (FC-28), temperature/humidity (DHT11), and soil pH
 * (Analog pH Sensor Module V1.1), then prints one bare JSON object over USB
 * serial every SENSOR_READ_INTERVAL_MS. That's the only transport this
 * firmware uses — no Wi-Fi, no Bluetooth, no network stack at all. The
 * website's Dashboard reads this JSON directly from the serial port via the
 * Web Serial API (Chrome/Edge) and is itself the one that talks to the
 * backend over HTTP, so sensor data only ever leaves this board over the
 * USB cable.
 *
 * Board:   ESP32-WROOM-32 DevKit
 * Library required (install via Arduino Library Manager):
 *   - DHT sensor library (Adafruit) + its Adafruit Unified Sensor dependency
 * No ArduinoJson dependency — JSON is hand-built as a String.
 */

#include <DHT.h>
#include "config.h"

DHT dht(PIN_DHT11, DHT11);

unsigned long lastReadMillis = 0;

// ----------------------------------------------------------------------------
// Sensor reads — each returns -1 on failure so a bad sensor never blocks
// the others or crashes the reading.
// ----------------------------------------------------------------------------

// A disconnected/floating analog pin doesn't read 0 — it picks up EMI and
// capacitive noise, swinging wildly between rapid consecutive samples. A
// physically connected sensor's signal barely moves over a few milliseconds.
// Sampling multiple times and checking that spread is the standard way to
// tell "real but noisy" from "not actually connected" apart — a plain
// `raw <= 0` check essentially never catches this, which is why a
// disconnected sensor could show plausible-looking, ever-changing values
// instead of being reported as missing.
int readStableAnalog(int pin) {
  int minRaw = 4095;
  int maxRaw = 0;
  long sum = 0;
  for (int i = 0; i < ADC_SAMPLE_COUNT; i++) {
    int raw = analogRead(pin);
    minRaw = min(minRaw, raw);
    maxRaw = max(maxRaw, raw);
    sum += raw;
    delay(ADC_SAMPLE_DELAY_MS);
  }
  if (maxRaw - minRaw > ADC_NOISE_THRESHOLD) {
    return -1;
  }
  int average = sum / ADC_SAMPLE_COUNT;
  return average > 0 ? average : -1;
}

float readSoilMoisture() {
  int raw = readStableAnalog(PIN_SOIL_MOISTURE);
  if (raw < 0) {
    return -1;
  }
  float moisture = 100.0 * (SOIL_ADC_DRY - raw) / (SOIL_ADC_DRY - SOIL_ADC_WET);
  return constrain(moisture, 0.0, 100.0);
}

float readPH() {
  int raw = readStableAnalog(PIN_PH_SENSOR);
  if (raw < 0) {
    return -1;
  }
  float voltage = (raw / ADC_RESOLUTION) * ADC_VREF;
  float slope = (7.0 - 4.0) / (PH_VOLTAGE_7 - PH_VOLTAGE_4);
  float ph = 7.0 + slope * (voltage - PH_VOLTAGE_7);
  if (ph < 0 || ph > 14) {
    return -1;
  }
  return ph;
}

// ----------------------------------------------------------------------------
// Build and print the reading as JSON. Field names match backend/app/
// schemas/sensor.py's SensorReadingIn exactly: device_uid, temperature,
// humidity, moisture, ph, nitrogen, phosphorus, potassium, rainfall.
// ----------------------------------------------------------------------------
void sendReading() {
  float temperature = dht.readTemperature();
  float humidity = dht.readHumidity();
  bool temperatureValid = !isnan(temperature);
  bool humidityValid = !isnan(humidity);

  float moisture = readSoilMoisture();
  float ph = readPH();

  String json = "{";

  json += "\"device_uid\":\"";
  json += DEVICE_UID;
  json += "\"";

  json += ",\"temperature\":";
  json += temperatureValid ? String(temperature, 2) : String("null");

  json += ",\"humidity\":";
  json += humidityValid ? String(humidity, 2) : String("null");

  json += ",\"moisture\":";
  json += (moisture >= 0) ? String(moisture, 2) : String("null");

  json += ",\"ph\":";
  json += (ph >= 0) ? String(ph, 2) : String("null");

  // NPK is not currently connected on this field node.
  json += ",\"nitrogen\":null,\"phosphorus\":null,\"potassium\":null";

  // Rainfall is sourced from the weather API server-side, not a field sensor.
  json += ",\"rainfall\":null";

  json += "}";

  Serial.println(json);
}

// ----------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(500);

  pinMode(PIN_STATUS_LED, OUTPUT);
  digitalWrite(PIN_STATUS_LED, HIGH); // on = board powered and running; no Wi-Fi state to reflect

  analogReadResolution(12); // 0-4095, matches ADC_RESOLUTION in config.h
  dht.begin();
  delay(1500); // DHT11 needs a moment after power-up before its first read is reliable

  sendReading();
}

void loop() {
  unsigned long now = millis();
  if (now - lastReadMillis >= SENSOR_READ_INTERVAL_MS) {
    lastReadMillis = now;
    sendReading();
  }

  delay(50);
}
