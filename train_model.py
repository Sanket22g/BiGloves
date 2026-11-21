"""
BiGlove ESP32 - Upgraded Neural Network Trainer (v3)
- Handles flex sensor bends properly with smart features
- Wider/deeper network optimized for bend pattern separation
- Exports gesture_model.tflite for Android
"""

import json
import os
import sys
from pathlib import Path

# Redirect Keras config to avoid permission errors
os.environ["KERAS_HOME"] = str(Path(".keras").resolve())
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
Path(".keras").mkdir(exist_ok=True)
with open(Path(".keras") / "keras.json", "w") as _kf:
    _kf.write('{"floatx": "float32", "epsilon": 1e-07, "backend": "tensorflow", "image_data_format": "channels_last"}')

import numpy as np
import pandas as pd
import joblib
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

DATASET_PATH = Path("dataset.csv")
TFLITE_PATH  = Path("gesture_model.tflite")
LABELS_PATH  = Path("labels.txt")
METADATA_PATH = Path("gesture_metadata.json")

MASTER_METADATA = {
    "idle":       {"marathi": "हात सैल",         "english": "Relaxed Hand",          "tts": "हात सैल"},
    "all_good":   {"marathi": "ठीक आहे",          "english": "All Good (Thumbs Up)",  "tts": "ठीक आहे"},
    "be_quiet":   {"marathi": "शांतता",           "english": "Be Quiet",              "tts": "शांतता"},
    "take_photo": {"marathi": "फोटो काढ",         "english": "Take a Photo (V-Sign)", "tts": "फोटो काढ"},
    "perfect":    {"marathi": "उत्तम",            "english": "Perfect (OK Sign)",     "tts": "उत्तम"},
    "well_done":  {"marathi": "शाब्बास",          "english": "Well Done (Fist)",      "tts": "शाब्बास"},
    "promise":    {"marathi": "प्रॉमिस / शब्द दे","english": "Promise",              "tts": "प्रॉमिस"},
    "give_food":  {"marathi": "जेवायला दे",       "english": "Give me Food",          "tts": "जेवायला दे"},
    "come_here":  {"marathi": "इकडे या",          "english": "Come Here",             "tts": "इकडे या"},
    "need_help":  {"marathi": "मदत हवी",          "english": "Need Help",             "tts": "मदत हवी"},
    "sorry":      {"marathi": "माफ करा",          "english": "Sorry",                 "tts": "माफ करा"},
}

# Bend thresholds from actual sensor calibration
# F1 Thumb:  DECREASES when bent  (straight ~210, bent <170)
# F2 Pinky:  DECREASES when bent  (straight ~650, bent <350)
# F3 Index:  DECREASES when bent  (straight ~125, bent <90)
# F4 Ring:   INCREASES when bent  (straight ~44,  bent >65)
# F5 Middle: INCREASES when bent  (straight ~48,  bent >65)

def compute_bend_flags(f1, f2, f3, f4, f5):
    b1 = (f1 < 170).astype(np.float32)
    b2 = (f2 < 350).astype(np.float32)
    b3 = (f3 < 90).astype(np.float32)
    b4 = (f4 > 65).astype(np.float32)
    b5 = (f5 > 65).astype(np.float32)
    return b1, b2, b3, b4, b5

def extract_features(df):
    """
    20-feature vector combining:
    - Raw flex values (5)
    - Bend binary flags (5)   -- discrete bend/straight per finger
    - Normalized values (5)   -- removes per-session DC voltage offset
    - Cross-finger diffs (4)  -- highlights relative bend patterns
    - Total bend count (1)
    """
    f1 = df["f1"].values.astype(np.float32)
    f2 = df["f2"].values.astype(np.float32)
    f3 = df["f3"].values.astype(np.float32)
    f4 = df["f4"].values.astype(np.float32)
    f5 = df["f5"].values.astype(np.float32)

    b1, b2, b3, b4, b5 = compute_bend_flags(f1, f2, f3, f4, f5)
    bend_sum = b1 + b2 + b3 + b4 + b5

    row_sum = f1 + f2 + f3 + f4 + f5 + 1e-6
    n1, n2, n3, n4, n5 = f1/row_sum, f2/row_sum, f3/row_sum, f4/row_sum, f5/row_sum

    d_thumb_index  = f1 - f3
    d_index_middle = f3 - f5
    d_ring_pinky   = f4 - f2
    d_thumb_pinky  = f1 - f2

    return np.column_stack([
        f1, f2, f3, f4, f5,
        b1, b2, b3, b4, b5,
        n1, n2, n3, n4, n5,
        d_thumb_index, d_index_middle, d_ring_pinky, d_thumb_pinky,
        bend_sum,
    ]).astype(np.float32)

def augment_real_data(df, target_per_class=1000, verbose=True):
    augmented = []
    np.random.seed(42)

    for label, group in df.groupby("label"):
        rows = group[["f1","f2","f3","f4","f5"]].values
        n_real = len(rows)
        if verbose:
            print(f"  {label:15s}: {n_real:5d} real rows -> augmenting to {target_per_class}")

        for _ in range(target_per_class):
            base = rows[np.random.randint(0, n_real)].copy().astype(np.float64)
            drift = np.random.uniform(0.95, 1.05)
            noise = np.random.normal(0, base * 0.03)
            row = base * drift + noise
            if np.random.rand() < 0.02:
                row[np.random.randint(0, 5)] *= np.random.uniform(0.5, 1.5)
            augmented.append(list(row) + [label])

    return pd.DataFrame(augmented, columns=["f1","f2","f3","f4","f5","label"])

def build_model(num_classes, input_dim=20):
    inp = keras.Input(shape=(input_dim,), name="flex_input")
    x = layers.Normalization(name="norm")(inp)
    x = layers.Dense(256, activation="relu", name="d1")(x)
    x = layers.BatchNormalization(name="bn1")(x)
    x = layers.Dropout(0.25, name="dp1")(x)
    x = layers.Dense(128, activation="relu", name="d2")(x)
    x = layers.BatchNormalization(name="bn2")(x)
    x = layers.Dropout(0.20, name="dp2")(x)
    x = layers.Dense(64, activation="relu", name="d3")(x)
    x = layers.BatchNormalization(name="bn3")(x)
    x = layers.Dropout(0.15, name="dp3")(x)
    x = layers.Dense(32, activation="relu", name="d4")(x)
    out = layers.Dense(num_classes, activation="softmax", name="output")(x)
    return keras.Model(inputs=inp, outputs=out, name="BiGloveNet_v3")

def main():
    if not DATASET_PATH.exists():
        print("ERROR: dataset.csv not found! Run collect_data.py first.")
        return

    print("=" * 70)
    print("  BiGlove ESP32 - Neural Network Trainer v3 (Bend-Aware)")
    print("=" * 70)

    raw_df = pd.read_csv(DATASET_PATH)
    total_raw = len(raw_df)
    print(f"\nLoaded {total_raw} rows from dataset.csv")
    print("\nRows per gesture:")
    counts = raw_df["label"].value_counts()
    for lbl, cnt in counts.items():
        bar = "#" * (cnt // 200)
        print(f"  {lbl:15s}: {cnt:6d}  {bar}")

    MIN_FOR_DIRECT = 5000
    if total_raw >= MIN_FOR_DIRECT:
        print(f"\n{total_raw} rows >= {MIN_FOR_DIRECT} -> training directly on real data!")
        df = raw_df.copy()
    else:
        target_per_class = max(1000, min(2000, 11000 // 11))
        print(f"\nAugmenting each class to {target_per_class} samples...")
        df = augment_real_data(raw_df, target_per_class=target_per_class, verbose=True)
        print(f"Total after augmentation: {len(df)} rows")

    le = LabelEncoder()
    le.fit(sorted(df["label"].unique()))
    classes = list(le.classes_)
    num_classes = len(classes)
    print(f"\nClasses ({num_classes}): {classes}")

    X = extract_features(df)
    y = le.transform(df["label"].values)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.15, random_state=42, stratify=y
    )
    print(f"\nTrain: {len(X_train)} | Test: {len(X_test)} | Features: {X.shape[1]}")

    tf.random.set_seed(42)
    np.random.seed(42)

    model = build_model(num_classes, input_dim=X.shape[1])
    norm_layer = model.get_layer("norm")
    norm_layer.adapt(X_train)

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.001),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )

    model.summary()

    callbacks = [
        keras.callbacks.EarlyStopping(
            monitor="val_loss", patience=15, restore_best_weights=True, verbose=1
        ),
        keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss", factor=0.5, patience=7, min_lr=1e-5, verbose=1
        ),
    ]

    print("\nTraining...")
    model.fit(
        X_train, y_train,
        validation_split=0.15,
        epochs=100,
        batch_size=64,
        callbacks=callbacks,
        verbose=1,
    )

    loss, acc = model.evaluate(X_test, y_test, verbose=0)
    print(f"\nTest Accuracy: {acc * 100:.2f}%  (Loss: {loss:.4f})")

    preds = np.argmax(model.predict(X_test, verbose=0), axis=1)
    print("\nClassification Report:")
    print(classification_report(y_test, preds, target_names=classes, digits=4))

    print("Confusion Matrix:")
    cm = confusion_matrix(y_test, preds)
    print(f"{'':>12}" + "".join(f"{c[:6]:>8}" for c in classes))
    for i, row_vals in enumerate(cm):
        print(f"{classes[i]:>12}" + "".join(f"{v:>8}" for v in row_vals))

    from sklearn.metrics import f1_score
    f1s = f1_score(y_test, preds, average=None)
    print("\nF1 Scores per gesture:")
    all_good_flag = True
    for lbl, score in zip(classes, f1s):
        icon = "OK" if score >= 0.90 else ("WARN" if score >= 0.70 else "BAD")
        print(f"  [{icon}] {lbl:15s}: {score:.4f}")
        if score < 0.90:
            all_good_flag = False

    if all_good_flag:
        print("\nAll gestures >= 90% F1! Model is ready for Android.")
    else:
        print("\nSome gestures below 90%. Collect MORE real data to improve.")

    # Export TFLite
    print("\nExporting TensorFlow Lite model...")
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    tflite_bytes = converter.convert()

    # Make TFLite backwards-compatible with Android org.tensorflow:tensorflow-lite:2.16.1
    # TensorFlow 2.21+ outputs FULLY_CONNECTED v12, which Android TFLite 2.16 rejects.
    # Patch opcode version to v1 so Android loads it flawlessly.
    import struct
    from tensorflow.lite.python import schema_py_generated as schema_fb
    buf = bytearray(tflite_bytes)
    model_obj = schema_fb.Model.GetRootAsModel(buf, 0)
    for i in range(model_obj.OperatorCodesLength()):
        op = model_obj.OperatorCodes(i)
        if op.BuiltinCode() == 9:  # FULLY_CONNECTED
            offset = op._tab.Offset(8)
            if offset != 0:
                pos = op._tab.Pos + offset
                struct.pack_into('<i', buf, pos, 1)
    tflite_bytes = bytes(buf)
    print("Patched FULLY_CONNECTED opcode to v1 for Android compatibility.")

    with open(TFLITE_PATH, "wb") as f:
        f.write(tflite_bytes)

    with open(LABELS_PATH, "w", encoding="utf-8") as f:
        for lbl in classes:
            f.write(f"{lbl}\n")

    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(MASTER_METADATA, f, ensure_ascii=False, indent=2)

    size_kb = len(tflite_bytes) / 1024
    print(f"\ngesture_model.tflite  -> {TFLITE_PATH}  ({size_kb:.1f} KB)")
    print(f"labels.txt            -> {LABELS_PATH}")
    print(f"gesture_metadata.json -> {METADATA_PATH}")
    print(f"\nTFLite input shape : (1, {X.shape[1]}) float32")
    print(f"TFLite output shape: (1, {num_classes}) softmax probabilities")
    print("=" * 70)
    print("  Copy gesture_model.tflite + labels.txt to your Android assets!")
    print("=" * 70)

if __name__ == "__main__":
    main()
