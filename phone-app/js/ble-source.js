/**
 * MGB Dash 2026 — Web Bluetooth CAN relay client.
 *
 * Connects to the body controller ESP32 BLE peripheral.
 * CAN Relay characteristic sends 12-byte notifications:
 *   bytes 0-3: uint32 LE arbitration ID
 *   bytes 4-11: 8-byte CAN data payload
 */

import { decodeAndStore } from "./can-decoder.js";

const SERVICE_UUID   = "4d474200-4247-4d00-0000-000000000001";
const CAN_RELAY_UUID = "4d474200-4247-4d00-0000-000000000002";

export class BleSource {
    constructor(state) {
        this._state = state;
        this._device = null;
        this._characteristic = null;
        this._onStatus = null;  // callback(message)
    }

    set onStatus(fn) {
        this._onStatus = fn;
    }

    get connected() {
        return this._device !== null &&
               this._device.gatt.connected;
    }

    get deviceName() {
        return this._device ? this._device.name || "Unknown" : null;
    }

    async connect() {
        if (!navigator.bluetooth) {
            this._notify("Web Bluetooth not available. Use Chrome over HTTPS.");
            return false;
        }

        try {
            this._notify("Requesting BLE device...");
            this._device = await navigator.bluetooth.requestDevice({
                filters: [{ services: [SERVICE_UUID] }],
                optionalServices: [SERVICE_UUID],
            });

            this._device.addEventListener("gattserverdisconnected", () => {
                this._notify("BLE disconnected.");
                this._characteristic = null;
            });

            this._notify("Connecting GATT...");
            const server = await this._device.gatt.connect();

            this._notify("Getting CAN relay service...");
            const service = await server.getPrimaryService(SERVICE_UUID);

            this._notify("Getting CAN relay characteristic...");
            this._characteristic = await service.getCharacteristic(CAN_RELAY_UUID);

            this._characteristic.addEventListener(
                "characteristicvaluechanged",
                (event) => this._onNotify(event)
            );

            await this._characteristic.startNotifications();
            this._notify("Connected — receiving CAN frames.");
            return true;

        } catch (err) {
            if (err.name === "NotFoundError") {
                this._notify("No device selected.");
            } else {
                this._notify(`BLE error: ${err.message}`);
            }
            return false;
        }
    }

    disconnect() {
        if (this._device && this._device.gatt.connected) {
            this._device.gatt.disconnect();
        }
        this._device = null;
        this._characteristic = null;
    }

    _onNotify(event) {
        const buf = event.target.value;  // DataView
        if (buf.byteLength < 12) return;

        const arbId = buf.getUint32(0, true);  // LE
        const data = new Uint8Array(buf.buffer, buf.byteOffset + 4, 8);
        decodeAndStore(this._state, arbId, data);
    }

    _notify(msg) {
        if (this._onStatus) this._onStatus(msg);
    }
}
