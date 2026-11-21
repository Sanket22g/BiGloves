"""
BiGlove ESP32 - Real Data Collection Pipeline with APPEND Mode
Allows you to continuously add new real data rows without deleting existing data.
E.g., 11k rows + 11k rows = 22,000 total rows in `dataset.csv`.
"""

import asyncio
import csv
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from bleak import BleakScanner, BleakClient

# Ensure UTF-8 output
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

DEVICE_NAME = "BiGlove_ESP32"
CHARACTERISTIC_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"
DATASET_PATH = Path("dataset.csv")

# 10 Image Gestures + 1 Idle Rest State
GESTURES = [
    {
        "id": "idle",
        "marathi": "हात सैल",
        "english": "Relaxed Hand (Idle)",
        "desc": "Flat relaxed hand resting naturally, fingers not bent"
    },
    {
        "id": "take_photo",
        "marathi": "फोटो काढ",
        "english": "Take a Photo",
        "desc": "Victory 'V' Sign: Index & Middle straight, other 3 bent"
    },
    {
        "id": "promise",
        "marathi": "प्रॉमिस / शब्द दे",
        "english": "Promise",
        "desc": "Pinky Promise: Pinky straight, others folded into fist"
    },
    {
        "id": "perfect",
        "marathi": "उत्तम",
        "english": "Perfect (OK Sign)",
        "desc": "Thumb & Index tips touching in a ring, other 3 straight"
    },
    {
        "id": "all_good",
        "marathi": "ठीक आहे",
        "english": "All Good (Thumbs Up)",
        "desc": "Thumb pointing straight up, 4 fingers folded into fist"
    },
    {
        "id": "need_help",
        "marathi": "मदत हवी",
        "english": "Need Help",
        "desc": "Cupped hand: all fingers curved at 50% half-bend"
    },
    {
        "id": "come_here",
        "marathi": "इकडे या",
        "english": "Come Here",
        "desc": "Index finger curled/hooked only — Thumb, Middle, Ring, Pinky fully STRAIGHT"
    },
    {
        "id": "give_food",
        "marathi": "जेवायला दे",
        "english": "Give me Food",
        "desc": "Thumb + Index + Middle pinched together, Ring & Pinky relaxed"
    },
    {
        "id": "sorry",
        "marathi": "माफ करा",
        "english": "Sorry / Apology",
        "desc": "4 fingers straight, Thumb folded flat across palm"
    },
    {
        "id": "well_done",
        "marathi": "शाब्बास",
        "english": "Well Done",
        "desc": "Firm solid closed fist: all 5 fingers tightly folded"
    },
    {
        "id": "be_quiet",
        "marathi": "शांतता",
        "english": "Be Quiet",
        "desc": "Index finger extended upright, other 4 fingers curled"
    }
]

SAMPLES_PER_GESTURE = 1500  # 1,500 samples per gesture per session
PREP_COUNTDOWN_SEC = 5      # 5 seconds prep countdown

current_buffer = []
is_recording = False
latest_packet = None

def sound_beep(freq=1000, dur_ms=100):
    try:
        import winsound
        winsound.Beep(freq, dur_ms)
    except Exception:
        sys.stdout.write("\a")
        sys.stdout.flush()

def notification_handler(sender, data):
    global latest_packet, current_buffer, is_recording
    try:
        raw_text = data.decode("utf-8", errors="ignore").strip()
        if not raw_text:
            return
        parts = raw_text.split(",")
        if len(parts) >= 5:
            f1 = float(parts[0])
            f2 = float(parts[1])
            f3 = float(parts[2])
            f4 = float(parts[3])
            f5 = float(parts[4])
            latest_packet = (f1, f2, f3, f4, f5)
            if is_recording:
                current_buffer.append(latest_packet)
    except Exception:
        pass

def save_gesture_samples(label, records):
    """ALWAYS APPENDS new real data to dataset.csv without deleting existing rows."""
    file_exists = DATASET_PATH.exists() and DATASET_PATH.stat().st_size > 0
    header = ["f1", "f2", "f3", "f4", "f5", "label"]
    
    with open(DATASET_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(header)
        for r in records:
            writer.writerow(list(r) + [label])

def get_current_dataset_stats():
    if not DATASET_PATH.exists() or DATASET_PATH.stat().st_size == 0:
        return 0, {}
    import pandas as pd
    try:
        df = pd.read_csv(DATASET_PATH)
        counts = df["label"].value_counts().to_dict()
        return len(df), counts
    except Exception:
        return 0, {}

async def record_single_gesture(client, gesture_info, target_samples=SAMPLES_PER_GESTURE):
    global is_recording, current_buffer
    
    print("\n" + "=" * 70)
    print(f"👉 GESTURE: {gesture_info['marathi']} ({gesture_info['english']})")
    print(f"   Pose: {gesture_info['desc']}")
    print("=" * 70)
    
    print(f"\n[Get Ready] Form pose now! Recording starts in {PREP_COUNTDOWN_SEC}s:")
    for i in range(PREP_COUNTDOWN_SEC, 0, -1):
        if i <= 3:
            sound_beep(900, 120)
        else:
            sound_beep(600, 70)
        print(f"   ⏱️  {i}...")
        await asyncio.sleep(1.0)
    
    # Start Recording
    current_buffer = []
    is_recording = True
    sound_beep(1300, 250)
    print(f"\n🟢 RECORDING! Collecting {target_samples} real rows from glove...")
    
    start_time = time.time()
    while len(current_buffer) < target_samples:
        count = len(current_buffer)
        remaining = max(0.0, (target_samples - count) / 10.0)
        pct = min(100, int((count / target_samples) * 100))
        bar = "█" * (pct // 4) + "-" * (25 - (pct // 4))
        lp = latest_packet if latest_packet else (0, 0, 0, 0, 0)
        sys.stdout.write(
            f"\r[{bar}] {count}/{target_samples} rows ({pct}%) | ⏱️ {remaining:.1f}s left | F1..F5: [{int(lp[0])},{int(lp[1])},{int(lp[2])},{int(lp[3])},{int(lp[4])}]"
        )
        sys.stdout.flush()
        await asyncio.sleep(0.05)
    
    is_recording = False
    sound_beep(900, 150)
    sound_beep(1100, 200)
    print(f"\n\n✅ COMPLETED {gesture_info['english']}! Captured {len(current_buffer)} real rows in {time.time() - start_time:.1f}s.")
    
    save_gesture_samples(gesture_info["id"], current_buffer)
    total_now, _ = get_current_dataset_stats()
    print(f"💾 Added {len(current_buffer)} rows. Total in dataset.csv is now: {total_now} rows!")
    print("✋ Relax your hand for 3 seconds...")
    await asyncio.sleep(3.0)

async def run_pipeline():
    total_start, counts_start = get_current_dataset_stats()
    print("=" * 70)
    print(" BiGlove ESP32 - Real Data Collection Pipeline")
    print(f" Current dataset.csv: {total_start} existing rows.")
    print("=" * 70)
    
    print("\nScanning for BiGlove_ESP32...")
    devices = await BleakScanner.discover(timeout=5.0)
    device = next((d for d in devices if d.name == DEVICE_NAME), None)
    if not device:
        print(f"\n❌ Could not find '{DEVICE_NAME}'. Make sure ESP32 is powered ON and nearby!")
        return
        
    print(f"Found {device.name}. Connecting...")
    async with BleakClient(device) as client:
        print("Connected to ESP32! Telemetry stream ready.\n")
        await client.start_notify(CHARACTERISTIC_UUID, notification_handler)
        await asyncio.sleep(1.0)
        
        while True:
            total_now, _ = get_current_dataset_stats()
            print("\n" + "=" * 60)
            print(f" DATA COLLECTION MENU (Current Dataset: {total_now} Total Rows)")
            print("=" * 60)
            print("1. APPEND MORE DATA (Adds +1,500 rows to each gesture -> 16,500 total!)")
            print("2. Add +1,000 rows to ONE Specific Gesture")
            print("3. View Current Dataset Counts")
            print("4. Clear Dataset & Start Fresh From 0")
            print("5. Exit")
            
            choice = input("\nEnter choice (1-5): ").strip()
            
            if choice == "1":
                print(f"\n🟢 Starting Collection session (Adding 1,000 rows to all 11 gestures)...")
                print(f"Existing rows will be KEPT. Dataset will grow by +11,000 rows!\n")
                for g in GESTURES:
                    await record_single_gesture(client, g, target_samples=SAMPLES_PER_GESTURE)
                
                final_total, _ = get_current_dataset_stats()
                print("\n" + "=" * 70)
                print(f"🎉 COLLECTION ROUND FINISHED! Dataset now has {final_total} TOTAL ROWS!")
                print("=" * 70)
                
                train_now = input("\nDo you want to train the model on this dataset now? (y/n): ").strip().lower()
                if train_now == "y":
                    print("\n🚀 Training Deep Neural Network on your dataset...")
                    subprocess.run([sys.executable, "train_model.py"])
                    break
                    
            elif choice == "2":
                print("\nSelect Gesture to Add 1,000 rows to:")
                for idx, g in enumerate(GESTURES, 1):
                    print(f" {idx:2d}. {g['marathi']:<16} ({g['english']})")
                try:
                    g_idx = int(input("\nEnter number (1-11): ").strip())
                    if 1 <= g_idx <= len(GESTURES):
                        await record_single_gesture(client, GESTURES[g_idx - 1], target_samples=SAMPLES_PER_GESTURE)
                    else:
                        print("Invalid selection.")
                except ValueError:
                    print("Please enter a valid number.")
                    
            elif choice == "3":
                total, counts = get_current_dataset_stats()
                print(f"\n--- Current Dataset Summary: {total} Total Rows ---")
                for lbl, c in counts.items():
                    print(f"  • {lbl:<15}: {c} rows")
                    
            elif choice == "4":
                confirm = input("\n⚠️ Are you sure you want to delete and reset dataset.csv to 0? (y/n): ").strip().lower()
                if confirm == "y":
                    if DATASET_PATH.exists():
                        DATASET_PATH.unlink()
                    print("Dataset cleared to 0 rows.")
                    
            elif choice == "5":
                print("Exiting...")
                break
                
        await client.stop_notify(CHARACTERISTIC_UUID)

if __name__ == "__main__":
    try:
        asyncio.run(run_pipeline())
    except KeyboardInterrupt:
        print("\nCollection stopped.")
