"""
BiGlove ESP32 - Live Sensor Diagnostic Inspector
Displays real-time raw values for each finger to verify exact hardware calibration.
"""

import asyncio
import sys
from bleak import BleakScanner, BleakClient

DEVICE_NAME = "BiGlove_ESP32"
CHARACTERISTIC_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"

def notification_handler(sender, data):
    try:
        raw_text = data.decode("utf-8", errors="ignore").strip()
        if not raw_text:
            return
        parts = raw_text.split(",")
        if len(parts) >= 5:
            v1, v2, v3, v4, v5 = [float(p) for p in parts[:5]]
            ax = float(parts[5]) if len(parts) > 5 else 0.0
            ay = float(parts[6]) if len(parts) > 6 else 0.0
            az = float(parts[7]) if len(parts) > 7 else 0.0
            
            sys.stdout.write(
                f"\rVal1:{int(v1):<5} Val2:{int(v2):<5} Val3:{int(v3):<5} Val4:{int(v4):<5} Val5:{int(v5):<5} | aX:{ax:5.2f} aY:{ay:5.2f} aZ:{az:5.2f}"
            )
            sys.stdout.flush()
    except Exception:
        pass

async def main():
    print("=" * 70)
    print(" BiGlove Live Sensor Inspector")
    print(" Bend each finger one by one to see which Value changes!")
    print("=" * 70)
    
    print("\nScanning for BiGlove_ESP32...")
    devices = await BleakScanner.discover(timeout=5.0)
    device = next((d for d in devices if d.name == DEVICE_NAME), None)
    if not device:
        print(f"❌ '{DEVICE_NAME}' not found! Check power & Bluetooth.")
        return

    print(f"Connected to {device.name}!\n")
    async with BleakClient(device) as client:
        await client.start_notify(CHARACTERISTIC_UUID, notification_handler)
        print("Live Sensor Stream (Val 1 to 5 + 3D Tilt):")
        print("-" * 70)
        try:
            while True:
                await asyncio.sleep(0.5)
        except KeyboardInterrupt:
            print("\nStopped.")
        finally:
            await client.stop_notify(CHARACTERISTIC_UUID)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
