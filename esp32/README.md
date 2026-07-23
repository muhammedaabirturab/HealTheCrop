# HealTheCrop ESP32 Firmware

Firmware for the ESP32-WROOM-32 field node that reads soil/environmental sensors and
uploads readings to the HealTheCrop backend over Wi-Fi.

## Hardware

| Component | Model | Interface |
|---|---|---|
| Microcontroller | ESP32-WROOM-32 DevKit | — |
| Soil moisture | FC-28 | Analog (ADC1) |
| Temperature & humidity | DHT11 | Digital, 1-wire |
| Soil pH | Analog pH Sensor Module V1.1 | Analog (ADC1) |
| Soil NPK (optional) | RS485 Modbus 7-in-1 soil sensor | UART/RS485 |

## Wiring

| ESP32 Pin | Connects to |
|---|---|
| GPIO34 (ADC1_CH6) | FC-28 analog output (AO) |
| GPIO35 (ADC1_CH7) | pH sensor analog output (Po) |
| GPIO4 | DHT11 data pin (with 10kΩ pull-up to 3.3V) |
| GPIO16 (RX2) | NPK sensor RS485 module TX (if attached) |
| GPIO17 (TX2) | NPK sensor RS485 module RX (if attached) |
| GPIO2 | Onboard status LED |
| 3.3V | VCC of all sensors |
| GND | GND of all sensors (common ground) |

See [`docs/hardware_wiring.md`](../docs/hardware_wiring.md) for the full circuit diagram.

> **Do not power the FC-28 and pH probes continuously** — corrosion shortens their life.
> For a permanent deployment, switch their VCC through a spare GPIO + transistor and only
> power them on briefly before each reading. The included firmware assumes always-on power
> for simplicity; see the "Future Scope" doc for the low-power variant.

## Setup

1. Install [Arduino IDE](https://www.arduino.cc/en/software) or [PlatformIO](https://platformio.org/).
2. Install the ESP32 board package (Arduino IDE → Boards Manager → search "esp32" → install
   the package by Espressif Systems).
3. Install libraries via Library Manager:
   - `DHT sensor library` (Adafruit)
   - `Adafruit Unified Sensor`
   - `ArduinoJson` (v6+)
   - `ModbusMaster` (only if `NPK_SENSOR_ATTACHED` is `true` in `config.h`)
4. Open `HealTheCrop_Firmware/HealTheCrop_Firmware.ino`.
5. Edit `config.h`:
   - `WIFI_SSID` / `WIFI_PASSWORD` — your network credentials.
   - `API_BASE_URL` — your backend's LAN IP, e.g. `http://192.168.1.42:8000/api/v1/sensors/ingest`.
   - `DEVICE_UID` — a unique name if running multiple nodes.
   - Calibrate `SOIL_ADC_DRY` / `SOIL_ADC_WET` and `PH_VOLTAGE_4` / `PH_VOLTAGE_7` against your
     specific sensors (see calibration notes in the file).
6. Select **Board: ESP32 Dev Module**, the correct COM port, then Upload.
7. Open the Serial Monitor at 115200 baud to confirm Wi-Fi connects and readings upload
   successfully (`HTTP status 201`).

## Behavior

- **Auto-reconnect**: if Wi-Fi drops, the firmware retries every 5 seconds without blocking
  sensor reads, and resumes uploads automatically once reconnected.
- **Graceful sensor failure**: if any individual sensor fails to read (e.g. DHT11 timing
  glitch), that field is sent as `null` rather than aborting the whole upload — the backend
  and ML pipeline both tolerate missing fields.
- **Auto-registration**: the backend's `/sensors/ingest` endpoint auto-creates a `Device`
  record on first contact from a new `device_uid` — no manual pairing step required.
