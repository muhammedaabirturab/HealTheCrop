import { api } from './api'

export interface ESP32SensorData {
  device_uid: string
  temperature: number | null
  humidity: number | null
  moisture: number | null
  ph: number | null
  nitrogen: number | null
  phosphorus: number | null
  potassium: number | null
  rainfall: number | null
}

const BAUD_RATE = 115200

let port: SerialPort | null = null
let reader: ReadableStreamDefaultReader<string> | null = null
let keepReading = false

export function isWebSerialSupported(): boolean {
  return typeof navigator !== 'undefined' && 'serial' in navigator
}

export function isESP32Connected(): boolean {
  return port !== null
}

function isValidReading(data: unknown): data is ESP32SensorData {
  return typeof data === 'object' && data !== null && typeof (data as { device_uid?: unknown }).device_uid === 'string'
}

async function readSerialData(onReading: (data: ESP32SensorData) => void, onError?: (error: unknown) => void) {
  if (!reader) return
  let buffer = ''

  try {
    while (keepReading) {
      const { value, done } = await reader.read()
      if (done) break
      if (!value) continue

      buffer += value
      // The firmware prints one bare JSON object per line.
      const lines = buffer.split(/\r?\n/)
      buffer = lines.pop() || '' // keep the incomplete tail line for the next chunk

      for (const line of lines) {
        const text = line.trim()
        if (!text) continue

        let data: unknown
        try {
          data = JSON.parse(text)
        } catch (error) {
          console.warn('Could not parse ESP32 line:', text, error)
          continue
        }

        if (!isValidReading(data)) {
          console.warn('ESP32 line missing device_uid:', data)
          continue
        }

        // Store the reading even if the upload fails — the UI should still
        // reflect what the board just sent, and the next 5s cycle will retry.
        api.post('/sensors/ingest', data).catch((error) => {
          console.error('Backend sensor upload failed:', error)
        })

        onReading(data)
      }
    }
  } catch (error) {
    if (keepReading) {
      console.error('ESP32 serial reading error:', error)
      onError?.(error)
    }
  } finally {
    reader = null
  }
}

/**
 * Opens a serial connection and starts streaming readings.
 * Pass an already-authorized `targetPort` (from `navigator.serial.getPorts()`)
 * to reconnect silently; omit it to show the browser's device picker.
 */
export async function connectESP32(
  onReading: (data: ESP32SensorData) => void,
  onError?: (error: unknown) => void,
  targetPort?: SerialPort,
): Promise<void> {
  if (!isWebSerialSupported()) {
    throw new Error('Web Serial is not supported by this browser.')
  }
  if (port) return // already connected

  try {
    port = targetPort ?? (await navigator.serial.requestPort())
    await port.open({ baudRate: BAUD_RATE })

    if (!port.readable) {
      throw new Error('ESP32 serial port is not readable.')
    }

    const decoder = new TextDecoderStream()
    // Not awaited intentionally — this pipe runs for the lifetime of the
    // connection; disconnectESP32() tears it down via reader.cancel().
    port.readable.pipeTo(decoder.writable as WritableStream<Uint8Array>).catch((error) => {
      if (keepReading) {
        console.error('Serial pipe error:', error)
        onError?.(error)
      }
    })

    reader = decoder.readable.getReader()
    keepReading = true
    void readSerialData(onReading, onError)
  } catch (error) {
    console.error('ESP32 connection failed:', error)
    port = null
    onError?.(error)
    throw error
  }
}

export async function disconnectESP32(): Promise<void> {
  keepReading = false

  try {
    await reader?.cancel()
  } catch {
    // reader may already be closed
  }
  try {
    await port?.close()
  } catch {
    // port may already be closed
  }

  reader = null
  port = null
}
