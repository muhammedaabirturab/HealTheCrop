import { create } from 'zustand'
import {
  connectESP32, disconnectESP32, isESP32Connected, isWebSerialSupported, type ESP32SensorData,
} from '../lib/esp32Serial'

export type ESP32ConnectionStatus = 'unsupported' | 'disconnected' | 'connecting' | 'connected'
export type ESP32ErrorReason = 'lost' | 'failed' | null

interface ESP32State {
  status: ESP32ConnectionStatus
  reading: ESP32SensorData | null
  lastUpdated: Date | null
  errorReason: ESP32ErrorReason
  connect: (targetPort?: SerialPort) => Promise<void>
  disconnect: () => Promise<void>
}

let connecting = false

/**
 * Global ESP32 connection manager. State lives here — not inside any page
 * component — so the USB serial connection survives navigating between
 * routes instead of being torn down whenever the connecting page unmounts.
 * The underlying port/reader singleton lives in lib/esp32Serial.ts; this
 * store just makes its status/readings reactive for React components.
 */
export const useESP32Store = create<ESP32State>((set) => ({
  status: isWebSerialSupported() ? 'disconnected' : 'unsupported',
  reading: null,
  lastUpdated: null,
  errorReason: null,

  connect: async (targetPort) => {
    if (connecting || isESP32Connected()) return
    connecting = true
    set({ status: 'connecting', errorReason: null })
    try {
      await connectESP32(
        (data) => set({ reading: data, lastUpdated: new Date(), errorReason: null }),
        () => {
          // The board dropped the connection unexpectedly (unplugged, reset, etc).
          // Readings reset immediately — a disconnected sensor must never keep
          // showing its last value.
          set({ status: 'disconnected', reading: null, lastUpdated: null, errorReason: 'lost' })
        },
        targetPort,
      )
      set({ status: 'connected' })
    } catch {
      set({ status: 'disconnected', errorReason: 'failed' })
    } finally {
      connecting = false
    }
  },

  disconnect: async () => {
    await disconnectESP32()
    set({ status: 'disconnected', reading: null, lastUpdated: null, errorReason: null })
  },
}))

// Registered once when this module first loads (app startup) — not tied to
// any single page's mount/unmount — so a previously-authorized port
// reconnects silently on load, and a physical unplug is detected even while
// the user is on a page with no serial UI at all.
if (isWebSerialSupported()) {
  navigator.serial.getPorts().then((ports) => {
    if (ports.length > 0) useESP32Store.getState().connect(ports[0])
  })

  navigator.serial.addEventListener('connect', () => {
    navigator.serial.getPorts().then((ports) => {
      if (ports.length > 0) useESP32Store.getState().connect(ports[0])
    })
  })

  navigator.serial.addEventListener('disconnect', () => {
    useESP32Store.getState().disconnect()
  })
}
