# 🧤 BiGlove ESP32 - Smart Glove Sign Language Translation

BiGlove is a wearable assistive technology glove that translates sign language gestures into Marathi speech and text in real-time. It uses 5 high-precision flex sensors connected to an ESP32 microcontroller, streaming telemetry over Bluetooth Low Energy (BLE) to an on-device Deep Neural Network.

---

## 🌟 Key Features
- **5 Flex Sensors**: Continuous curvature sensing across all digits (Thumb, Index, Middle, Ring, Pinky).
- **ESP32 BLE GATT Streaming**: Low-latency 10 Hz continuous telemetry packet streaming.
- **Deep Neural Network (TFLite)**: 4-layer Deep MLP trained on 22,500 real glove samples.
- **20 Biomechanical Features**: Raw flex values, binary bend state indicators, normalized dynamic range, cross-finger differences, and total bend metrics.
- **Android Ready**: Exported as `gesture_model.tflite` (60 KB) with full opcode backward-compatibility for Android devices.
- **10 Core Marathi Signs + Idle**:
  1. **हात सैल** (Idle / Relaxed Hand)
  2. **ठीक आहे** (All Good / Thumbs Up)
  3. **शांतता** (Be Quiet)
  4. **फोटो काढ** (Take a Photo / V-Sign)
  5. **उत्तम** (Perfect / OK Sign)
  6. **शाब्बास** (Well Done / Fist)
  7. **प्रॉमिस** (Promise / Pinky)
  8. **जेवायला दे** (Give Food)
  9. **इकडे या** (Come Here)
  10. **मदत हवी** (Need Help)
  11. **माफ करा** (Sorry)

---

## 📂 Repository Structure
```
├── BiGlove_ESP32.ino          # ESP32 firmware (ADC sampling & BLE GATT notification)
├── collect_data.py            # Real-time BLE data collection & append tool
├── train_model.py             # 20-feature neural network training & TFLite export
├── live_test.py               # Real-time PC inference with Marathi TTS voice output
├── dataset.csv                # 22,500 real glove sensor recordings
├── gesture_model.tflite       # Trained TensorFlow Lite mobile model
├── labels.txt                 # 11-class gesture labels
├── gesture_metadata.json      # Marathi text & TTS translation metadata
└── BIGLOVE_PROJECT_REPORT.md  # Detailed project engineering report
```

---

## 🚀 Quick Start

### 1. Hardware Firmware
Upload `BiGlove_ESP32.ino` to your ESP32 board using Arduino IDE.

### 2. Python Environment Setup
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install bleak tensorflow pandas scikit-learn pygame gTTS
```

### 3. Real-Time Inference
Run live testing with voice output:
```powershell
python live_test.py
```

### 4. Retraining Model
Train on `dataset.csv`:
```powershell
python train_model.py
```
Outputs `gesture_model.tflite` ready for Android app deployment.
