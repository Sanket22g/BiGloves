import asyncio
import csv
from datetime import datetime
from pathlib import Path

from bleak import BleakScanner, BleakClient

DEVICE_NAME = "BiGlove_ESP32"
CHARACTERISTIC_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"
CSV_PATH = Path("sensor_data_20sec.csv")
RECORD_SECONDS = 100

writer = None


def notification_handler(sender, data):
    global writer

    try:
        value = data.decode("utf-8", errors="ignore").strip()
        if not value:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        if writer is not None:
            writer.writerow([timestamp, value])
        print(timestamp, "->", value)
    except Exception as e:
        print("Data error:", e)


async def main():
    global writer

    print("Scanning for nearby Bluetooth devices...")
    devices = await BleakScanner.discover()

    found = False
    device = None
    for d in devices:
        print(f"{d.name} - {d.address}")
        if d.name == DEVICE_NAME:
            found = True
            device = d
            break

    if not found:
        print()
        print("BiGlove_ESP32 not found!")
        print("Make sure the ESP32 is powered ON and advertising.")
        return

    print()
    print("Found:", device.name)
    print("Address:", device.address)
    print()

    with CSV_PATH.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["timestamp", "sensor_data"])

        async with BleakClient(device.address) as client:
            print("CONNECTED!")
            print(f"Recording sensor data for {RECORD_SECONDS} seconds...")

            await client.start_notify(CHARACTERISTIC_UUID, notification_handler)

            try:
                await asyncio.wait_for(asyncio.sleep(RECORD_SECONDS), timeout=RECORD_SECONDS + 2)
            except asyncio.TimeoutError:
                pass
            finally:
                try:
                    await client.stop_notify(CHARACTERISTIC_UUID)
                except Exception:
                    pass
                print(f"Saved CSV data to {CSV_PATH.resolve()}")


try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("\nStopped by user. CSV file was flushed before exit.")