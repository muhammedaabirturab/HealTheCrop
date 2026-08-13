/*
 * HealTheCrop — ESP32 Field Node Firmware
 * ----------------------------------------
 * Reads soil moisture (FC-28), temperature/humidity (DHT11), and soil pH
 * (Analog pH Sensor Module V1.1), then on every read:
 *   1. Always prints one bare JSON object over USB serial, so the website's
 *      Live Sensor (USB) page can read it directly via the Web Serial API —
 *      this never depends on Wi-Fi.
 *   2. Additionally POSTs the exact same JSON string to the HealTheCrop
 *      backend over Wi-Fi (if connected), so the Dashboard's live sensor
 *      panel updates automatically without a USB cable.
 * Wi-Fi being down or slow to connect never blocks or delays the first USB
 * serial reading. A failed sensor read sends JSON null for that field
 * instead of crashing or sending garbage.
 *
 * Board:   ESP32-WROOM-32 DevKit
 * Library required (install via Arduino Library Manager):
 *   - DHT sensor library (Adafruit) + its Adafruit Unified Sensor dependency
 * No ArduinoJson dependency — JSON is hand-built as a String so the serial
 * output and the uploaded reading can never drift apart from each other.
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>
#include "config.h"

DHT dht(PIN_DHT11, DHT11);

unsigned long lastReadMillis = 0;
unsigned long lastWifiAttemptMillis = 0;
bool wifiWasConnected = false;

// ----------------------------------------------------------------------------
// Wi-Fi connection management with retrying auto-reconnect
// ----------------------------------------------------------------------------
void connectToWiFi() {
  Serial.printf("[WiFi] Connecting to \"%s\"...\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < WIFI_CONNECT_TIMEOUT_MS) {
    delay(250);
    digitalWrite(PIN_STATUS_LED, !digitalRead(PIN_STATUS_LED));
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("[WiFi] Connected. IP address: %s\n", WiFi.localIP().toString().c_str());
    digitalWrite(PIN_STATUS_LED, HIGH);
    wifiWasConnected = true;
  } else {
    Serial.println("[WiFi] Connection attempt timed out; will retry in the background.");
    digitalWrite(PIN_STATUS_LED, LOW);
  }
}

void ensureWiFiConnected() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  if (wifiWasConnected) {
    Serial.println("[WiFi] Connection lost. Attempting to reconnect...");
    wifiWasConnected = false;
  }

  unsigned long now = millis();
  if (now - lastWifiAttemptMillis >= WIFI_RECONNECT_INTERVAL_MS) {
    lastWifiAttemptMillis = now;
    connectToWiFi();
  }
}

// ----------------------------------------------------------------------------
// Sensor reads — each returns -1 on failure so a bad sensor never blocks
// the others or crashes the reading.
// ----------------------------------------------------------------------------

// A disconnected/floating analog pin doesn't read 0 — it picks up EMI and
// capacitive noise, swinging wildly between rapid consecutive samples. A
// physically connected sensor's signal barely moves over a few milliseconds.
// Sampling multiple times and checking that spread is the standard way to
// tell "real but noisy" from "not actually connected" apart — a plain
// `raw <= 0` check (the old behavior) essentially never catches this, which
// is why a disconnected sensor could show plausible-looking, ever-changing
// values instead of being reported as missing.
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
// Build the reading as a JSON string once, so the USB serial line and the
// Wi-Fi upload body are always byte-for-byte identical — no separate code
// paths that could silently drift apart from each other.
//
// Field names match backend/app/schemas/sensor.py's SensorReadingIn exactly:
// device_uid, temperature, humidity, moisture, ph, nitrogen, phosphorus,
// potassium, rainfall.
// ----------------------------------------------------------------------------
String buildReadingJson() {
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
  return json;
}

void sendReading() {
  String payload = buildReadingJson();

  // Always printed, regardless of Wi-Fi status — this is what the website's
  // Live Sensor (USB) page reads directly over the serial port.
  Serial.println(payload);

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[Upload] Skipped — Wi-Fi not connected.");
    return;
  }

  HTTPClient http;
  http.setTimeout(HTTP_TIMEOUT_MS);
  http.begin(API_BASE_URL);
  http.addHeader("Content-Type", "application/json");

  int statusCode = http.POST(payload);
  if (statusCode > 0) {
    Serial.printf("[Upload] Server responded with status %d\n", statusCode);
    if (statusCode >= 400) {
      Serial.println("[Upload] Response body: " + http.getString());
    }
  } else {
    Serial.printf("[Upload] HTTP request failed: %s\n", http.errorToString(statusCode).c_str());
  }
  http.end();
}

// ----------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(500);

  pinMode(PIN_STATUS_LED, OUTPUT);
  digitalWrite(PIN_STATUS_LED, LOW);

  analogReadResolution(12); // 0-4095, matches ADC_RESOLUTION in config.h
  dht.begin();
  delay(1500); // DHT11 needs a moment after power-up before its first read is reliable

  // Send the first reading over USB serial before touching Wi-Fi at all, so
  // the Live Sensor (USB) page never has to wait on a network connection
  // attempt (which can take up to WIFI_CONNECT_TIMEOUT_MS) for its first line.
  sendReading();

  connectToWiFi();
}

void loop() {
  ensureWiFiConnected();

  unsigned long now = millis();
  if (now - lastReadMillis >= SENSOR_READ_INTERVAL_MS) {
    lastReadMillis = now;
    sendReading();
  }

  delay(50); // yield to Wi-Fi/TCP stack
}
