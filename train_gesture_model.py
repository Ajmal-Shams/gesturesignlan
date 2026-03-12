"""
Train a custom gesture classifier with 18 HaGRID gestures.

Downloads the HaGRID 100-image/class subset from Hugging Face (~402MB),
extracts hand landmarks using MediaPipe Hands (already installed),
trains a TensorFlow/Keras classifier on the landmark features,
and exports to TFLite for fast inference.

Gestures (18): call, dislike, fist, four, like, mute, ok, one, palm, peace,
               peace_inverted, rock, stop, stop_inverted, three, three2,
               two_up, two_up_inverted

Usage:
    python train_gesture_model.py
"""

import os
import sys
import shutil
import zipfile
import random
import json
import time
import glob

import cv2
import numpy as np
import mediapipe as mp
import tensorflow as tf
from tensorflow import keras

# ── Configuration ──────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "hagrid_data")
LANDMARKS_DIR = os.path.join(DATA_DIR, "landmarks")
EXPORT_DIR = os.path.join(SCRIPT_DIR, "exported_model")
MODEL_SAVE_PATH = os.path.join(EXPORT_DIR, "gesture_classifier.tflite")
LABELS_SAVE_PATH = os.path.join(EXPORT_DIR, "gesture_labels.json")

# Deploy paths
DEPLOY_MODEL_PATH = os.path.join(SCRIPT_DIR, "videoapp", "gesture_classifier.tflite")
DEPLOY_LABELS_PATH = os.path.join(SCRIPT_DIR, "videoapp", "gesture_labels.json")

# Hugging Face HaGRID subset: 500 images/class, 18 classes, ~2.0GB
DATASET_URL = "https://huggingface.co/datasets/GestureDetectionConnoisseurs/hagrid_subsets/resolve/main/hagrid-export_500_images.zip?download=true"
DATASET_ZIP = os.path.join(DATA_DIR, "hagrid-export_500_images.zip")

# Max images per class to use for training
MAX_IMAGES_PER_CLASS = 500

# The script will now dynamically detect all classes (approx 36-39)
# instead of hardcoding a list of 18.

# MediaPipe Hands
mp_hands = mp.solutions.hands


def download_dataset():
    """Download the HaGRID 100-image subset from Hugging Face."""
    import urllib.request

    os.makedirs(DATA_DIR, exist_ok=True)

    if os.path.exists(DATASET_ZIP):
        size_mb = os.path.getsize(DATASET_ZIP) / (1024 * 1024)
        if size_mb > 500:  # Valid zip should be >500MB
            print(f"✅ Dataset zip already exists: {DATASET_ZIP} ({size_mb:.0f}MB)")
            return True
        else:
            print(f"⚠️ Existing zip seems corrupted ({size_mb:.0f}MB), re-downloading...")
            os.remove(DATASET_ZIP)

    print(f"📥 Downloading HaGRID 500-image subset (~2.0GB)...")
    print(f"   Source: Hugging Face")
    print(f"   URL: {DATASET_URL}")

    try:
        req = urllib.request.Request(DATASET_URL, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        })
        response = urllib.request.urlopen(req, timeout=600)
        total_size = int(response.headers.get('Content-Length', 0))

        downloaded = 0
        start_time = time.time()
        with open(DATASET_ZIP, 'wb') as f:
            while True:
                chunk = response.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                elapsed = time.time() - start_time
                speed = downloaded / (elapsed + 0.001) / (1024 * 1024)
                if total_size > 0:
                    pct = (downloaded / total_size) * 100
                    eta = (total_size - downloaded) / (speed * 1024 * 1024 + 1)
                    print(f"\r   {downloaded/(1024*1024):.0f}MB / {total_size/(1024*1024):.0f}MB ({pct:.0f}%) - {speed:.1f}MB/s - ETA: {eta:.0f}s", end="", flush=True)
                else:
                    print(f"\r   {downloaded/(1024*1024):.0f}MB - {speed:.1f}MB/s", end="", flush=True)
        print()
        print(f"✅ Download complete! ({downloaded/(1024*1024):.0f}MB)")
        return True

    except Exception as e:
        print(f"\n❌ Download failed: {e}")
        if os.path.exists(DATASET_ZIP):
            os.remove(DATASET_ZIP)
        return False


def extract_dataset():
    """Extract the downloaded zip file."""
    # Find extracted directory
    extract_base = os.path.join(DATA_DIR, "extracted")

    # Check if already extracted
    if os.path.exists(extract_base):
        # Look for gesture folders (directories with .jpg files)
        for root, dirs, files in os.walk(extract_base):
            if any(f.endswith('.jpg') for f in files) or len(dirs) > 20:
                print(f"✅ Dataset already extracted at: {root}")
                return root

    print(f"📦 Extracting dataset...")
    os.makedirs(extract_base, exist_ok=True)

    with zipfile.ZipFile(DATASET_ZIP, 'r') as zf:
        total = len(zf.namelist())
        for i, member in enumerate(zf.namelist()):
            zf.extract(member, extract_base)
            if (i + 1) % 500 == 0:
                print(f"\r   Extracted: {i+1}/{total} files", end="", flush=True)
        print(f"\r   Extracted: {total}/{total} files")

    # Find the gesture folder root
    for root, dirs, files in os.walk(extract_base):
        if len(dirs) > 20: # HaGRID has ~38 classes
            print(f"✅ Found gesture data at: {root}")
            return root

    print(f"❌ Could not find gesture folders after extraction")
    # Debug: show what was extracted
    for root, dirs, files in os.walk(extract_base):
        print(f"   {root}: {dirs[:10]}")
        if len(dirs) > 0:
            break

    return extract_base


def extract_landmarks(dataset_root):
    """Extract hand landmarks from all gesture images."""
    print(f"\n🔍 Extracting hand landmarks from images...")

    os.makedirs(LANDMARKS_DIR, exist_ok=True)

    # Check for cached landmarks
    x_path = os.path.join(LANDMARKS_DIR, "X.npy")
    y_path = os.path.join(LANDMARKS_DIR, "y.npy")
    labels_path = os.path.join(LANDMARKS_DIR, "label_map.json")

    if os.path.exists(x_path) and os.path.exists(y_path) and os.path.exists(labels_path):
        print(f"✅ Found cached landmarks, loading...")
        X = np.load(x_path)
        y = np.load(y_path)
        with open(labels_path, 'r') as f:
            label_map = json.load(f)
        print(f"   {len(X)} samples, {len(label_map)} classes")
        return X, y, label_map

    hands = mp_hands.Hands(
        static_image_mode=True,
        max_num_hands=1,
        min_detection_confidence=0.5
    )

    all_landmarks = []
    all_labels = []
    label_map = {}

    # Get classes available in the dataset dynamically
    available_classes = []
    
    # We assume dataset_root contains directories for each class
    for item in os.listdir(dataset_root):
        cls_dir = os.path.join(dataset_root, item)
        if os.path.isdir(cls_dir) and item != "annotations": # Skip any annotation dirs
            images = [f for f in os.listdir(cls_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            if len(images) >= 5:
                available_classes.append(item)
                
    available_classes.sort()

    print(f"   Found {len(available_classes)} gesture classes in dataset")

    for idx, cls in enumerate(available_classes):
        label_map[str(idx)] = cls
        cls_dir = os.path.join(dataset_root, cls)
        images = [f for f in os.listdir(cls_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

        if len(images) > MAX_IMAGES_PER_CLASS:
            random.seed(42)
            images = random.sample(images, MAX_IMAGES_PER_CLASS)

        detected = 0
        for img_name in images:
            img_path = os.path.join(cls_dir, img_name)
            image = cv2.imread(img_path)
            if image is None:
                continue

            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = hands.process(image_rgb)

            if results.multi_hand_landmarks:
                landmarks = results.multi_hand_landmarks[0]
                # Extract 21 landmarks × 2 (x, y) = 42 features
                # Using x, y only (more stable than z)
                landmark_list = np.array(
                    [[lm.x, lm.y] for lm in landmarks.landmark],
                    dtype=np.float32
                )

                # Normalize relative to wrist + scale
                wrist = landmark_list[0]
                landmark_list = landmark_list - wrist
                max_val = np.max(np.abs(landmark_list)) or 1
                landmark_list = landmark_list / max_val
                flat = landmark_list.flatten().tolist()

                all_landmarks.append(flat)
                all_labels.append(idx)
                
                # Data augmentation: Horizontal mirror
                mirrored = landmark_list.copy()
                mirrored[:, 0] = -mirrored[:, 0]
                flat_mirrored = mirrored.flatten().tolist()
                
                all_landmarks.append(flat_mirrored)
                all_labels.append(idx)

                detected += 1

        pct = (detected / len(images) * 100) if images else 0
        print(f"   ✅ {cls:20s}: {detected:3d}/{len(images):3d} hands detected ({pct:.0f}%)")

    hands.close()

    X = np.array(all_landmarks, dtype=np.float32)
    y = np.array(all_labels, dtype=np.int32)

    # Cache
    np.save(x_path, X)
    np.save(y_path, y)
    with open(labels_path, 'w') as f:
        json.dump(label_map, f, indent=2)

    print(f"\n📊 Landmarks extracted:")
    print(f"   Total samples: {len(X)}")
    print(f"   Features per sample: {X.shape[1]}")
    print(f"   Classes: {len(label_map)}")

    return X, y, label_map


def train_classifier(X, y, label_map):
    """Train a Keras classifier and export to TFLite."""
    print(f"\n🏋️ Training gesture classifier...")
    print("=" * 60)

    num_classes = len(label_map)
    input_dim = X.shape[1]

    # Shuffle
    indices = np.arange(len(X))
    np.random.seed(42)
    np.random.shuffle(indices)
    X = X[indices]
    y = y[indices]

    # Split: 80% train, 10% val, 10% test
    n = len(X)
    train_end = int(0.8 * n)
    val_end = int(0.9 * n)

    X_train, y_train = X[:train_end], y[:train_end]
    X_val, y_val = X[train_end:val_end], y[train_end:val_end]
    X_test, y_test = X[val_end:], y[val_end:]

    print(f"   Training: {len(X_train)} samples")
    print(f"   Validation: {len(X_val)} samples")
    print(f"   Test: {len(X_test)} samples")
    print(f"   Classes: {num_classes}")
    print(f"   Input features: {input_dim}")

    # Build classifier model (Tuned for >90% accuracy)
    model = keras.Sequential([
        keras.layers.Input(shape=(input_dim,)),
        keras.layers.Dense(512, activation='relu'),
        keras.layers.Dropout(0.2),
        keras.layers.Dense(256, activation='relu'),
        keras.layers.Dropout(0.2),
        keras.layers.Dense(128, activation='relu'),
        keras.layers.Dropout(0.1),
        keras.layers.Dense(64, activation='relu'),
        keras.layers.Dense(num_classes, activation='softmax')
    ])

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.001),
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy']
    )

    model.summary()

    callbacks = [
        keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss', patience=15, factor=0.5, min_lr=1e-6
        ),
        keras.callbacks.EarlyStopping(
            monitor='val_accuracy', patience=40,
            restore_best_weights=True, min_delta=0.0005
        ),
    ]

    print(f"\n🚀 Training for up to 250 epochs with early stopping...")
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=250,
        batch_size=32,
        callbacks=callbacks,
        verbose=1
    )

    # Evaluate
    print(f"\n📊 Evaluating on test set...")
    test_loss, test_accuracy = model.evaluate(X_test, y_test, verbose=0)
    accuracy_pct = test_accuracy * 100

    print(f"\n{'=' * 60}")
    print(f"📊 RESULTS:")
    print(f"   Test Loss: {test_loss:.4f}")
    print(f"   Test Accuracy: {accuracy_pct:.2f}%")
    print(f"{'=' * 60}")

    if accuracy_pct >= 85:
        print(f"   ✅ Target 85% ACHIEVED! ({accuracy_pct:.1f}%)")
    else:
        print(f"   ⚠️ Below 85% target ({accuracy_pct:.1f}%)")

    # Per-class accuracy and save to report
    report_path = os.path.join(SCRIPT_DIR, "train_accuracy_report.txt")
    with open(report_path, "w") as f:
        f.write(f"Gesture Recognition Model Training Report\n")
        f.write(f"=========================================\n")
        f.write(f"Overall Test Accuracy: {accuracy_pct:.2f}%\n")
        f.write(f"Overall Test Loss: {test_loss:.4f}\n\n")
        f.write(f"Per-class Accuracy:\n")
        f.write(f"-----------------------------------------\n")
        
        y_pred = np.argmax(model.predict(X_test, verbose=0), axis=1)
        print(f"\n📋 Per-class accuracy:")
        for k in sorted(label_map.keys(), key=lambda x: int(x)):
            mask = y_test == int(k)
            if mask.sum() > 0:
                acc = (y_pred[mask] == y_test[mask]).mean() * 100
                line_msg = f"{label_map[k]:20s}: {acc:5.1f}% ({mask.sum()} test samples)"
                print(f"   {line_msg}")
                f.write(f"{line_msg}\n")
    
    print(f"\n✅ Wrote detailed accuracy report to {report_path}")

    # Export to TFLite
    print(f"\n📦 Exporting model...")
    os.makedirs(EXPORT_DIR, exist_ok=True)

    # Save Keras H5
    h5_path = os.path.join(EXPORT_DIR, "gesture_classifier.h5")
    model.save(h5_path)
    print(f"   Keras: {h5_path}")

    # Convert to TFLite
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    tflite_model = converter.convert()

    with open(MODEL_SAVE_PATH, 'wb') as f:
        f.write(tflite_model)

    size_kb = os.path.getsize(MODEL_SAVE_PATH) / 1024
    print(f"   TFLite: {MODEL_SAVE_PATH} ({size_kb:.1f} KB)")

    # Save labels
    with open(LABELS_SAVE_PATH, 'w') as f:
        json.dump(label_map, f, indent=2)
    print(f"   Labels: {LABELS_SAVE_PATH}")

    return accuracy_pct


def deploy():
    """Deploy model to the videoapp directory."""
    print(f"\n🚀 Deploying to Django app...")

    # Backup old task file if exists
    old_task = os.path.join(SCRIPT_DIR, "videoapp", "gesture_recognizer.task")
    if os.path.exists(old_task):
        backup = old_task + ".backup"
        if not os.path.exists(backup):
            shutil.copy2(old_task, backup)
            print(f"   Backed up old model: {backup}")

    shutil.copy2(MODEL_SAVE_PATH, DEPLOY_MODEL_PATH)
    shutil.copy2(LABELS_SAVE_PATH, DEPLOY_LABELS_PATH)
    print(f"   ✅ Model: {DEPLOY_MODEL_PATH}")
    print(f"   ✅ Labels: {DEPLOY_LABELS_PATH}")


def main():
    print("=" * 60)
    print("🤖 HaGRID Gesture Classifier Training")
    print("   18 Gestures | MediaPipe Landmarks | TFLite Export")
    print("=" * 60)

    # Check for cached landmarks first
    x_path = os.path.join(LANDMARKS_DIR, "X.npy")
    if os.path.exists(x_path):
        print("\n📂 Found cached landmarks, skipping download...")
        X = np.load(x_path)
        y = np.load(os.path.join(LANDMARKS_DIR, "y.npy"))
        with open(os.path.join(LANDMARKS_DIR, "label_map.json"), 'r') as f:
            label_map = json.load(f)
    else:
        # Step 1: Download dataset
        if not download_dataset():
            print("❌ Cannot proceed without dataset.")
            sys.exit(1)

        # Step 2: Extract dataset
        dataset_root = extract_dataset()

        # Step 3: Extract landmarks
        X, y, label_map = extract_landmarks(dataset_root)

    if len(X) < 100:
        print(f"\n❌ Not enough valid samples ({len(X)}). Check the dataset.")
        sys.exit(1)

    # Step 4: Train
    accuracy = train_classifier(X, y, label_map)

    # Step 5: Deploy
    if accuracy >= 80:
        deploy()
        print(f"\n{'=' * 60}")
        print(f"🎉 SUCCESS!")
        print(f"   Accuracy: {accuracy:.1f}%")
        print(f"   Gestures: {len(label_map)}")
        print(f"   Model: {DEPLOY_MODEL_PATH}")
        print(f"\n   Next step: consumers.py needs to be updated to use")
        print(f"   the new gesture_classifier.tflite (see code changes)")
        print(f"{'=' * 60}")
    else:
        print(f"\n⚠️ Accuracy {accuracy:.1f}% is low. Model still exported.")
        print(f"   Try the 500-image subset for better accuracy.")


if __name__ == "__main__":
    main()
