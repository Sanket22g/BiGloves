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


import os
import sys

# Ensure UTF-8 console output for Marathi Devanagari script
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Suppress pygame startup prompt
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import queue
import threading

# Marathi Phrases & Audio Map
GESTURES = {
    "hello": {
        "marathi": "नमस्कार (Namaskar - Hello)",
        "tts": "नमस्कार",
        "file": "audio_mr/hello.mp3"
    },
    "how_are_you": {
        "marathi": "तुम्ही कसे आहात? (Tumhi kase aahat? - How are you?)",
        "tts": "तुम्ही कसे आहात?",
        "file": "audio_mr/how_are_you.mp3"
    },
    "yes": {
        "marathi": "हो (Ho - Yes)",
        "tts": "हो",
        "file": "audio_mr/yes.mp3"
    },
    "thank_you": {
        "marathi": "धन्यवाद (Dhanyavaad - Thank you)",
        "tts": "धन्यवाद",
        "file": "audio_mr/thank_you.mp3"
    },
    "please": {
        "marathi": "कृपया (Krupaya - Please)",
        "tts": "कृपया",
        "file": "audio_mr/please.mp3"
    },
    "stop": {
        "marathi": "थांबा (Thamba - Stop)",
        "tts": "थांबा",
        "file": "audio_mr/stop.mp3"
    },
    "kapish": {
        "marathi": "कपिश, काय करतोय रे! (Kapish, kay kartoy re!)",
        "tts": "कपिश, काय करतोय रे!",
        "file": "audio_mr/kapish_kay_kartoy_re.mp3"
    },
    "bhikarchot": {
        "marathi": "ओये भिकारचोट! (Oye bhikarchot!)",
        "tts": "ओये भिकारचोट!",
        "file": "audio_mr/bhikarchot.mp3"
    },
    "yash_chapri": {
        "marathi": "यश छपरी! (Yash chapri!)",
        "tts": "यश छपरी!",
        "file": "audio_mr/yash_chapri.mp3"
    }
}

# Pre-generate any missing audio clips
os.makedirs("audio_mr", exist_ok=True)
try:
    from gtts import gTTS
    for key, info in GESTURES.items():
        if not os.path.exists(info["file"]):
            tts = gTTS(text=info["tts"], lang="mr")
            tts.save(info["file"])
except Exception as e:
    print("TTS cache error:", e)

# Dedicated thread worker for audio playback (avoids Windows COM apartment conflicts with Bleak)
_audio_queue = queue.Queue()


def _audio_worker():
    import pygame
    pygame.mixer.init()
    sounds = {}
    for key, info in GESTURES.items():
        if os.path.exists(info["file"]):
            try:
                sounds[key] = pygame.mixer.Sound(info["file"])
            except Exception:
                pass

    while True:
        gesture_key = _audio_queue.get()
        if gesture_key in sounds:
            try:
                pygame.mixer.stop()
                sounds[gesture_key].play()
            except Exception:
                pass


_audio_thread = threading.Thread(target=_audio_worker, daemon=True)
_audio_thread.start()


def speak_marathi(gesture_key):
    """Sends gesture to audio thread for non-blocking Marathi speech."""
    _audio_queue.put(gesture_key)


# Calibrated thresholds based on your hardware data:
# Value 1 = Pinky  (Straight ~450-780, Bent <200 or >3500)
# Value 2 = Index  (Straight ~115-135, Bent <85)
# Value 3 = Thumb  (Straight ~38-48,   Bent <28)
# Value 4 = Middle (Straight ~110-125, Bent <80)
# Value 5 = Ring   (Straight ~270-520, Bent <100)
THRESHOLDS = {
    "pinky": 200,   # Bent if <200 or >3500
    "index": 85,    # Bent if <85
    "thumb": 28,    # Bent if <28
    "middle": 80,   # Bent if <80 or >3500
    "ring": 100     # Bent if <100
}

last_gesture = None


def classify_gesture(t_bent, p_bent, i_bent, r_bent, m_bent):
    """
    Classifies finger bend states into Marathi words.
    Multi-finger combination gestures are evaluated first.
    """
    # --- Multi-finger Combination Gestures (Checked First) ---

    # 1. Fist (all bent): "stop" -> थांबा (Thamba - Stop)
    if t_bent and p_bent and i_bent and r_bent and m_bent:
        return "stop"

    # 2. Index + Middle together: "yash_chapri" -> यश छपरी!
    if i_bent and m_bent and not (t_bent or p_bent or r_bent):
        return "yash_chapri"

    # 3. Thumb + Middle: "how_are_you" -> तुम्ही कसे आहात?
    if t_bent and m_bent and not (p_bent or i_bent or r_bent):
        return "how_are_you"

    # 4. Thumb + Index: "please" -> कृपया
    if t_bent and i_bent and not (p_bent or r_bent or m_bent):
        return "please"

    # --- Single-finger Gestures ---

    # 5. Middle ONLY: "hello" -> नमस्कार (Namaskar / Namaste)
    if m_bent and not (t_bent or p_bent or i_bent or r_bent):
        return "hello"

    # 6. Index ONLY: "yes" -> हो
    if i_bent and not (t_bent or p_bent or r_bent or m_bent):
        return "yes"

    # 7. Thumb ONLY: "thank_you" -> धन्यवाद
    if t_bent and not (p_bent or i_bent or r_bent or m_bent):
        return "thank_you"

    # 8. Ring ONLY: "bhikarchot" -> ओये भिकारचोट!
    if r_bent and not (t_bent or p_bent or i_bent or m_bent):
        return "bhikarchot"

    # 9. Pinky ONLY: "kapish" -> कपिश, काय करतोय रे!
    if p_bent and not (t_bent or i_bent or r_bent or m_bent):
        return "kapish"

    return None


def notification_handler(sender, data):
    global writer, last_gesture

    try:
        raw_text = data.decode("utf-8", errors="ignore").strip()
        if not raw_text:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        if writer is not None:
            writer.writerow([timestamp, raw_text])

        # Parse sensor readings based on your exact wiring:
        # 1: Pinky | 2: Index | 3: Thumb | 4: Middle | 5: Ring
        parts = raw_text.split(",")
        if len(parts) >= 5:
            pinky = float(parts[0])   # Value 1: Pinky
            index = float(parts[1])   # Value 2: Index
            thumb = float(parts[2])   # Value 3: Thumb
            middle = float(parts[3])  # Value 4: Middle
            ring = float(parts[4])    # Value 5: Ring

            # Determine bent state (True if bent)
            p_bent = (pinky < THRESHOLDS["pinky"]) or (pinky > 3500)
            i_bent = index < THRESHOLDS["index"]
            t_bent = thumb < THRESHOLDS["thumb"]
            m_bent = (middle < THRESHOLDS["middle"]) or (middle > 3500)
            r_bent = ring < THRESHOLDS["ring"]

            gesture_key = classify_gesture(t_bent, p_bent, i_bent, r_bent, m_bent)

            # Debug display for each notification
            bent_list = []
            if t_bent: bent_list.append("Thumb")
            if i_bent: bent_list.append("Index")
            if m_bent: bent_list.append("Middle")
            if r_bent: bent_list.append("Ring")
            if p_bent: bent_list.append("Pinky")
            b_str = "+".join(bent_list) if bent_list else "All Straight"

            # Only trigger speech when a new gesture is recognized
            if gesture_key and gesture_key != last_gesture:
                info = GESTURES[gesture_key]
                print(f"[{b_str}] 👉 Prediction: {info['marathi']}")
                speak_marathi(gesture_key)
                last_gesture = gesture_key
            elif not bent_list:
                # Reset when hand returns to rest position
                last_gesture = None
            else:
                # Print live finger state if gesture is holding
                print(f"[{b_str}] P:{pinky:.0f} I:{index:.0f} T:{thumb:.0f} M:{middle:.0f} R:{ring:.0f}")

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












