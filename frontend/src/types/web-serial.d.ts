// Minimal ambient types for the Web Serial API (Chrome/Edge only).
// Not shipped in TypeScript's DOM lib yet, so we declare just the surface
// this app actually uses rather than pulling in a full @types dependency.
interface SerialPortInfo {
  usbVendorId?: number
  usbProductId?: number
}

interface SerialOptions {
  baudRate: number
}

interface SerialPort extends EventTarget {
  readable: ReadableStream<Uint8Array> | null
  writable: WritableStream<Uint8Array> | null
  open(options: SerialOptions): Promise<void>
  close(): Promise<void>
  getInfo(): SerialPortInfo
}

interface SerialPortRequestOptions {
  filters?: { usbVendorId?: number; usbProductId?: number }[]
}

interface Serial extends EventTarget {
  requestPort(options?: SerialPortRequestOptions): Promise<SerialPort>
  getPorts(): Promise<SerialPort[]>
  addEventListener(type: 'connect' | 'disconnect', listener: (this: Serial, ev: Event) => void): void
  removeEventListener(type: 'connect' | 'disconnect', listener: (this: Serial, ev: Event) => void): void
}

interface Navigator {
  readonly serial: Serial
}
