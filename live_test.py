"""
BiGlove ESP32 - High-Precision Flex-Only Gesture Inference Engine v3
Runs strictly on 5 Flex Sensors (No MPU/IMU).
Uses 20-feature extraction matching train_model.py v3.
"""

import asyncio
import json
import os
import queue
import sys
import threading
import time
from pathlib import Path
from bleak import BleakScanner, BleakClient
import numpy as np

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

DEVICE_NAME       = "BiGlove_ESP32"
CHARACTERISTIC_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"
TFLITE_PATH       = Path("gesture_model.tflite")
LABELS_PATH       = Path("labels.txt")
METADATA_PATH     = Path("gesture_metadata.json")
AUDIO_DIR         = Path("audio_mr")

# ── Audio Worker (non-blocking Marathi TTS) ─────────────────────────────────
_speech_queue = queue.Queue()

def audio_worker():
    import pygame
    pygame.mixer.init()
    sounds = {}
    if AUDIO_DIR.exists():
        for f in AUDIO_DIR.glob("*.mp3"):
            try:
                sounds[f.stem] = pygame.mixer.Sound(str(f))
            except Exception:
                pass

    while True:
        key, tts_text = _speech_queue.get()
        sound_file = AUDIO_DIR / f"{key}.mp3"
        if key not in sounds:
            try:
                AUDIO_DIR.mkdir(parents=True, exist_ok=True)
                from gtts import gTTS
                tts = gTTS(text=tts_text, lang="mr")
                tts.save(str(sound_file))
                sounds[key] = pygame.mixer.Sound(str(sound_file))
            except Exception as e:
                print(f"TTS error: {e}")
        if key in sounds:
            try:
                pygame.mixer.stop()
                sounds[key].play()
            except Exception:
                pass

_audio_thread = threading.Thread(target=audio_worker, daemon=True)
_audio_thread.start()

def speak_marathi(key, tts_text):
    _speech_queue.put((key, tts_text))

# ── 20-Feature Extraction (must match train_model.py v3) ────────────────────
# Bend thresholds from calibration:
# F1 Thumb:  DECREASES when bent  → bent when < 170
# F2 Pinky:  DECREASES when bent  → bent when < 350
# F3 Index:  DECREASES when bent  → bent when < 90
# F4 Ring:   INCREASES when bent  → bent when > 65
# F5 Middle: INCREASES when bent  → bent when > 65

def compute_bend_flags(f1, f2, f3, f4, f5):
    b1 = 1.0 if f1 < 170 else 0.0  # Thumb
    b2 = 1.0 if f2 < 350 else 0.0  # Pinky
    b3 = 1.0 if f3 < 90  else 0.0  # Index
    b4 = 1.0 if f4 > 65  else 0.0  # Ring
    b5 = 1.0 if f5 > 65  else 0.0  # Middle
    return b1, b2, b3, b4, b5

def extract_features_single(f1, f2, f3, f4, f5):
    """Extract 20 features from a single sensor reading."""
    b1, b2, b3, b4, b5 = compute_bend_flags(f1, f2, f3, f4, f5)
    bend_sum = b1 + b2 + b3 + b4 + b5

    row_sum = f1 + f2 + f3 + f4 + f5 + 1e-6
    n1, n2, n3, n4, n5 = f1/row_sum, f2/row_sum, f3/row_sum, f4/row_sum, f5/row_sum

    d_thumb_index  = f1 - f3
    d_index_middle = f3 - f5
    d_ring_pinky   = f4 - f2
    d_thumb_pinky  = f1 - f2

    return np.array([[
        f1, f2, f3, f4, f5,
        b1, b2, b3, b4, b5,
        n1, n2, n3, n4, n5,
        d_thumb_index, d_index_middle, d_ring_pinky, d_thumb_pinky,
        bend_sum,
    ]], dtype=np.float32)

# ── Classifier ───────────────────────────────────────────────────────────────
class FlexGestureClassifier:
    def __init__(self, model_path, labels_path, metadata_path):
        import tensorflow as tf
        self.interpreter = tf.lite.Interpreter(model_path=str(model_path))
        self.interpreter.allocate_tensors()
        self.input_details  = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

        with open(labels_path, "r", encoding="utf-8") as f:
            self.labels = [line.strip() for line in f if line.strip()]

        self.metadata = {}
        if metadata_path.exists():
            with open(metadata_path, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)

        expected_shape = self.input_details[0]["shape"]
        self.expected_features = int(expected_shape[-1])
        print(f"Model expects {self.expected_features} input features.")

    def predict(self, f1, f2, f3, f4, f5):
        feat = extract_features_single(f1, f2, f3, f4, f5)

        # Safety: pad or trim if model shape differs
        if feat.shape[1] != self.expected_features:
            if feat.shape[1] < self.expected_features:
                pad = np.zeros((1, self.expected_features - feat.shape[1]), dtype=np.float32)
                feat = np.concatenate([feat, pad], axis=1)
            else:
                feat = feat[:, :self.expected_features]

        self.interpreter.set_tensor(self.input_details[0]["index"], feat)
        self.interpreter.invoke()
        probs = self.interpreter.get_tensor(self.output_details[0]["index"])[0]

        pred_idx = int(np.argmax(probs))
        label = self.labels[pred_idx]
        conf  = float(probs[pred_idx])

        # Physical rules override for unambiguous poses
        b1, b2, b3, b4, b5 = compute_bend_flags(f1, f2, f3, f4, f5)
        bent_count = int(b1 + b2 + b3 + b4 + b5)

        # Rule: All straight → idle
        if bent_count == 0:
            label, conf = "idle", 0.99
        # Rule: All 5 bent → well_done (fist)
        elif bent_count == 5:
            label, conf = "well_done", 0.98

        meta = self.metadata.get(label, {
            "marathi": label,
            "english": label.replace("_", " ").title(),
            "tts": label
        })
        return label, conf, meta, (b1, b2, b3, b4, b5)

# ── BLE Streaming + Debounce ─────────────────────────────────────────────────
classifier = None
last_spoken = None
consecutive = 0
DEBOUNCE_FRAMES = 3    # need 3 same frames before speaking
CONF_THRESHOLD  = 0.65 # minimum confidence

def notification_handler(sender, data):
    global classifier, last_spoken, consecutive
    try:
        raw = data.decode("utf-8", errors="ignore").strip()
        if not raw or not classifier:
            return
        parts = raw.split(",")
        if len(parts) < 5:
            return

        f1, f2, f3, f4, f5 = float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
        label, conf, meta, (b1, b2, b3, b4, b5) = classifier.predict(f1, f2, f3, f4, f5)

        # Debounce
        if label != "idle" and conf >= CONF_THRESHOLD:
            if label == last_spoken:
                consecutive += 1
            else:
                consecutive = 1
                last_spoken = label

            if consecutive == DEBOUNCE_FRAMES:
                print(f"\n[DETECTED] {meta['marathi']} ({meta['english']}) | Conf: {conf*100:.0f}%")
                speak_marathi(label, meta["tts"])
        else:
            if label == "idle":
                last_spoken = None
                consecutive = 0

        # Live display
        fingers = ["Th" if b1 else "--", "In" if b3 else "--", "Mi" if b5 else "--",
                   "Ri" if b4 else "--", "Pi" if b2 else "--"]
        bent_str = " ".join(fingers)
        sys.stdout.write(
            f"\r[{bent_str}] -> {meta['marathi']:<14} ({conf*100:4.0f}%) | "
            f"F1-5:[{int(f1)},{int(f2)},{int(f3)},{int(f4)},{int(f5)}]   "
        )
        sys.stdout.flush()
    except Exception:
        pass

# ── Main ──────────────────────────────────────────────────────────────────────
async def main():
    global classifier

    print("=" * 70)
    print("  BiGlove ESP32 - Flex-Only Translation Engine v3")
    print("=" * 70)

    if not TFLITE_PATH.exists() or not LABELS_PATH.exists():
        print("ERROR: gesture_model.tflite or labels.txt not found!")
        print("Run:  .venv\\Scripts\\python.exe train_model.py")
        return

    print("\nLoading TFLite model...")
    classifier = FlexGestureClassifier(TFLITE_PATH, LABELS_PATH, METADATA_PATH)
    print(f"Loaded {len(classifier.labels)} gestures:")
    for lbl in classifier.labels:
        meta = classifier.metadata.get(lbl, {})
        print(f"  {lbl:<15} -> {meta.get('marathi', '')} ({meta.get('english', '')})")

    print("\nScanning for BiGlove_ESP32...")
    devices = await BleakScanner.discover(timeout=5.0)
    device = next((d for d in devices if d.name == DEVICE_NAME), None)
    if not device:
        print(f"ERROR: '{DEVICE_NAME}' not found! Check power & Bluetooth.")
        return

    print(f"Found {device.name}. Connecting...")
    async with BleakClient(device) as client:
        print("Connected to BiGlove! Stream active.\n")
        await client.start_notify(CHARACTERISTIC_UUID, notification_handler)
        print("READY! Perform gestures. Press Ctrl+C to stop.\n")
        print("Display: [Th In Mi Ri Pi] -> Marathi (Confidence%)")
        print("         Th=Thumb In=Index Mi=Middle Ri=Ring Pi=Pinky\n")
        try:
            while True:
                await asyncio.sleep(0.5)
        except (KeyboardInterrupt, asyncio.CancelledError):
            print("\nStopping...")
        finally:
            await client.stop_notify(CHARACTERISTIC_UUID)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
