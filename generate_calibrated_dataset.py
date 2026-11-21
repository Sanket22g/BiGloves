"""
Generates a pristine, perfectly calibrated training dataset strictly for the 5 Flex Sensors:
- Thumb (F1):  Straight ~ 210 | Bent ~ 125
- Pinky (F2):  Straight ~ 650 | Bent ~  70
- Index (F3):  Straight ~ 125 | Bent ~  15
- Ring  (F4):  Straight ~  44 | Bent ~ 120
- Middle(F5):  Straight ~  48 | Bent ~ 130
MPU/IMU is excluded.
"""

import csv
import numpy as np
from pathlib import Path

DATASET_PATH = Path("dataset.csv")

FINGER_RANGES = {
    # [straight_mean, straight_std, bent_mean, bent_std]
    "thumb":  [210.0, 10.0, 125.0, 8.0],
    "pinky":  [650.0, 30.0,  70.0, 6.0],
    "index":  [125.0,  6.0,  15.0, 4.0],
    "ring":   [ 44.0,  4.0, 120.0, 7.0],
    "middle": [ 48.0,  4.0, 130.0, 7.0],
}

GESTURE_SPECS = {
    "idle": {
        "thumb": False, "index": False, "middle": False, "ring": False, "pinky": False
    },
    "take_photo": {  # Victory V: Index & Middle STRAIGHT, others BENT
        "thumb": True, "index": False, "middle": False, "ring": True, "pinky": True
    },
    "promise": {     # Crossed: Index & Middle STRAIGHT, others BENT
        "thumb": True, "index": False, "middle": False, "ring": True, "pinky": True
    },
    "perfect": {     # OK sign: Thumb & Index BENT in circle, other 3 STRAIGHT
        "thumb": True, "index": True, "middle": False, "ring": False, "pinky": False
    },
    "all_good": {    # Thumbs Up: Thumb STRAIGHT, 4 fingers BENT
        "thumb": False, "index": True, "middle": True, "ring": True, "pinky": True
    },
    "need_help": {   # Cupped hand (all fingers gently straight/curved)
        "thumb": False, "index": False, "middle": False, "ring": False, "pinky": False
    },
    "come_here": {   # Beckoning, 4 fingers curled, thumb out
        "thumb": False, "index": True, "middle": True, "ring": True, "pinky": True
    },
    "give_food": {   # Eating mudra, 5 fingertips pinched
        "thumb": True, "index": True, "middle": True, "ring": True, "pinky": True
    },
    "sorry": {       # Flat hand
        "thumb": False, "index": False, "middle": False, "ring": False, "pinky": False
    },
    "well_done": {   # Solid closed fist (all 5 bent)
        "thumb": True, "index": True, "middle": True, "ring": True, "pinky": True
    },
    "be_quiet": {    # Index upright, other 4 BENT
        "thumb": True, "index": False, "middle": True, "ring": True, "pinky": True
    }
}

def generate_samples(samples_per_class=500):
    np.random.seed(42)
    rows = []
    
    for label, f_cfg in GESTURE_SPECS.items():
        for _ in range(samples_per_class):
            t_mean, t_std = FINGER_RANGES["thumb"][2:4] if f_cfg["thumb"] else FINGER_RANGES["thumb"][0:2]
            f1 = float(np.clip(np.random.normal(t_mean, t_std), 80, 240))
            
            p_mean, p_std = FINGER_RANGES["pinky"][2:4] if f_cfg["pinky"] else FINGER_RANGES["pinky"][0:2]
            f2 = float(np.clip(np.random.normal(p_mean, p_std), 40, 800))
            
            i_mean, i_std = FINGER_RANGES["index"][2:4] if f_cfg["index"] else FINGER_RANGES["index"][0:2]
            f3 = float(np.clip(np.random.normal(i_mean, i_std), 5, 150))
            
            r_mean, r_std = FINGER_RANGES["ring"][2:4] if f_cfg["ring"] else FINGER_RANGES["ring"][0:2]
            f4 = float(np.clip(np.random.normal(r_mean, r_std), 30, 150))
            
            m_mean, m_std = FINGER_RANGES["middle"][2:4] if f_cfg["middle"] else FINGER_RANGES["middle"][0:2]
            f5 = float(np.clip(np.random.normal(m_mean, m_std), 30, 160))
            
            rows.append([round(f1, 1), round(f2, 1), round(f3, 1), round(f4, 1), round(f5, 1), label])
            
    with open(DATASET_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["f1", "f2", "f3", "f4", "f5", "label"])
        writer.writerows(rows)
        
    print(f"✅ Generated clean flex-only dataset: {DATASET_PATH}")
    print(f"   Total samples: {len(rows)} ({samples_per_class} per class across {len(GESTURE_SPECS)} gestures)")

if __name__ == "__main__":
    generate_samples(500)
