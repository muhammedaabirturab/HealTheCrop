# HealTheCrop ESP32 Firmware

Firmware for the ESP32-WROOM-32 field node that reads soil/environmental sensors and
prints readings over USB serial. This is a USB-only device — there is no Wi-Fi,
Bluetooth, or any other network transport in this firmware. The website's Dashboard
reads the sensor data directly from the serial port (via the Chrome/Edge Web Serial
API) over the same USB cable used to power and program the board, and is itself the
one that talks to the backend over HTTP — sensor data never leaves this board except
over USB.

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
   - `ModbusMaster` (only if `NPK_SENSOR_ATTACHED` is `true` in `config.h`)
4. Open `HealTheCrop_Firmware/HealTheCrop_Firmware.ino`.
5. Copy `config.h.example` to `config.h` and edit it:
   - `DEVICE_UID` — a unique name if running multiple nodes.
   - Calibrate `SOIL_ADC_DRY` / `SOIL_ADC_WET` and `PH_VOLTAGE_4` / `PH_VOLTAGE_7` against your
     specific sensors (see calibration notes in the file).
6. Select **Board: ESP32 Dev Module**, the correct COM port, then Upload.
7. Open the Serial Monitor at 115200 baud to confirm one JSON reading line prints every
   `SENSOR_READ_INTERVAL_MS`.
8. On the website, connect via USB from the Dashboard page ("Connect ESP32 via USB")
   using the same USB cable — the browser reads the serial output directly.

## Behavior

- **USB-only**: no Wi-Fi or Bluetooth code exists in this firmware at all — it never
  attempts a network connection of any kind.
- **Graceful sensor failure**: if any individual sensor fails to read (e.g. DHT11 timing
  glitch, or an analog sensor reporting as disconnected), that field is sent as `null`
  rather than aborting the whole reading — the backend and ML pipeline both tolerate
  missing fields.
- **Disconnected-sensor detection**: a floating (unplugged) analog pin swings noisily
  between rapid consecutive reads, unlike a real sensor's stable signal — the firmware
  samples several times and checks that spread before trusting a reading (see
  `ADC_SAMPLE_COUNT`/`ADC_NOISE_THRESHOLD` in `config.h`), so an unplugged sensor is
  reported as missing instead of showing a plausible-looking fake value.
- **Auto-registration**: the backend's `/sensors/ingest` endpoint (called by the browser,
  not this board) auto-creates a `Device` record on first contact from a new
  `device_uid` — no manual pairing step required.
