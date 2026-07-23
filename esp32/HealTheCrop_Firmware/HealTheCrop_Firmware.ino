/*
 * HealTheCrop — ESP32 Field Node Firmware
 * ----------------------------------------
 * Reads soil moisture (FC-28), temperature/humidity (DHT11), soil pH
 * (Analog pH Sensor Module V1.1), and optionally NPK (RS485 Modbus sensor),
 * then POSTs a JSON reading to the HealTheCrop backend every
 * SENSOR_READ_INTERVAL_MS. Handles Wi-Fi drops with automatic reconnect and
 * degrades gracefully (sends null for any sensor that fails to read) instead
 * of crashing or blocking the whole upload.
 *
 * Board:   ESP32-WROOM-32 DevKit
 * Libraries required (install via Arduino Library Manager):
 *   - DHT sensor library (Adafruit)
 *   - Adafruit Unified Sensor
 *   - ArduinoJson (>= 6.x)
 *   - ModbusMaster (only if NPK_SENSOR_ATTACHED is true)
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include "config.h"

#if NPK_SENSOR_ATTACHED
#include <ModbusMaster.h>
#include <HardwareSerial.h>
HardwareSerial NpkSerial(2);
ModbusMaster npkNode;
#endif

DHT dht(PIN_DHT11, DHT11);

unsigned long lastReadMillis = 0;
unsigned long lastWifiAttemptMillis = 0;
bool wifiWasConnected = false;

// ----------------------------------------------------------------------------
// Wi-Fi connection management with non-blocking auto-reconnect
// ----------------------------------------------------------------------------
void connectToWiFi() {
  Serial.printf("[WiFi] Connecting to \"%s\"...\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < WIFI_CONNECT_TIMEOUT_MS) {
    delay(250);
    Serial.print(".");
    digitalWrite(PIN_STATUS_LED, !digitalRead(PIN_STATUS_LED));
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("[WiFi] Connected. IP address: %s\n", WiFi.localIP().toString().c_str());
    digitalWrite(PIN_STATUS_LED, HIGH);
    wifiWasConnected = true;
  } else {
    Serial.println("[WiFi] Connection attempt timed out; will retry.");
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
// Sensor reads — each returns NAN on failure so a bad sensor never blocks
// the others or crashes the upload.
// ----------------------------------------------------------------------------
float readSoilMoisturePercent() {
  int raw = analogRead(PIN_SOIL_MOISTURE);
  if (raw <= 0) return NAN;
  float percent = 100.0f * (float)(SOIL_ADC_DRY - raw) / (float)(SOIL_ADC_DRY - SOIL_ADC_WET);
  if (percent < 0) percent = 0;
  if (percent > 100) percent = 100;
  return percent;
}

float readSoilPH() {
  int raw = analogRead(PIN_PH_SENSOR);
  if (raw <= 0) return NAN;
  float voltage = (raw / ADC_RESOLUTION) * ADC_VREF;
  // Two-point linear calibration between pH 4.0 and pH 7.0 buffer readings
  float slope = (7.0 - 4.0) / (PH_VOLTAGE_7 - PH_VOLTAGE_4);
  float ph = 7.0 + slope * (voltage - PH_VOLTAGE_7);
  if (ph < 0 || ph > 14) return NAN;
  return ph;
}

bool readDHT(float &temperature, float &humidity) {
  temperature = dht.readTemperature();
  humidity = dht.readHumidity();
  if (isnan(temperature) || isnan(humidity)) {
    Serial.println("[DHT11] Read failed — check wiring/pull-up resistor.");
    return false;
  }
  return true;
}

#if NPK_SENSOR_ATTACHED
bool readNPK(float &n, float &p, float &k) {
  uint8_t result = npkNode.readHoldingRegisters(0x00, 3);
  if (result != npkNode.ku8MBSuccess) {
    Serial.printf("[NPK] Modbus read failed (code %d)\n", result);
    return false;
  }
  n = npkNode.getResponseBuffer(0);
  p = npkNode.getResponseBuffer(1);
  k = npkNode.getResponseBuffer(2);
  return true;
}
#endif

// ----------------------------------------------------------------------------
// Build and send the JSON payload to the backend
// ----------------------------------------------------------------------------
void addOrNull(JsonDocument &doc, const char *key, float value) {
  if (isnan(value)) {
    doc[key] = nullptr;
  } else {
    doc[key] = value;
  }
}

void sendReading() {
  float moisture = readSoilMoisturePercent();
  float ph = readSoilPH();
  float temperature = NAN, humidity = NAN;
  bool dhtOk = readDHT(temperature, humidity);
  if (!dhtOk) {
    temperature = NAN;
    humidity = NAN;
  }

  float nitrogen = NAN, phosphorus = NAN, potassium = NAN;
#if NPK_SENSOR_ATTACHED
  readNPK(nitrogen, phosphorus, potassium);
#endif

  StaticJsonDocument<512> doc;
  doc["device_uid"] = DEVICE_UID;
  addOrNull(doc, "moisture", moisture);
  addOrNull(doc, "ph", ph);
  addOrNull(doc, "temperature", temperature);
  addOrNull(doc, "humidity", humidity);
  addOrNull(doc, "nitrogen", nitrogen);
  addOrNull(doc, "phosphorus", phosphorus);
  addOrNull(doc, "potassium", potassium);
  doc["rainfall"] = nullptr; // rainfall is sourced from the weather API server-side, not a field sensor

  String payload;
  serializeJson(doc, payload);
  Serial.print("[Upload] Payload: ");
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
  Serial.println("\n=== HealTheCrop ESP32 Field Node booting ===");

  pinMode(PIN_STATUS_LED, OUTPUT);
  digitalWrite(PIN_STATUS_LED, LOW);

  analogReadResolution(12); // 0-4095, matches ADC_RESOLUTION in config.h
  dht.begin();

#if NPK_SENSOR_ATTACHED
  NpkSerial.begin(4800, SERIAL_8N1, PIN_NPK_RX, PIN_NPK_TX);
  npkNode.begin(1, NpkSerial); // slave ID 1 — adjust to match your NPK sensor
#endif

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
