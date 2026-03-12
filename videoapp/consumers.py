import os
import json
import base64
import time
import cv2
import numpy as np
import mediapipe as mp
import tensorflow as tf
from difflib import get_close_matches
from collections import deque
from channels.generic.websocket import AsyncWebsocketConsumer

# ✅ Set correct model paths
asl_model_path = os.path.abspath("F:/Django/Client/gesturesignlan/models/slr_model.tflite")

# ✅ New gesture classifier model (18 gestures, trained on HaGRID)
gesture_tflite_path = os.path.abspath("F:/Django/Client/gesturesignlan/videoapp/gesture_classifier.tflite")
gesture_labels_path = os.path.abspath("F:/Django/Client/gesturesignlan/videoapp/gesture_labels.json")

# ✅ Load gesture labels
GESTURE_LABELS = {}
try:
    with open(gesture_labels_path, "r") as f:
        GESTURE_LABELS = json.load(f)
    print(f"✅ Gesture labels loaded: {len(GESTURE_LABELS)} gestures")
    print(f"   Gestures: {list(GESTURE_LABELS.values())}")
except Exception as e:
    print(f"❌ Error loading gesture labels: {e}")

# ✅ Load gesture TFLite model
gesture_interpreter = None
try:
    gesture_interpreter = tf.lite.Interpreter(model_path=gesture_tflite_path)
    gesture_interpreter.allocate_tensors()
    print(f"✅ Gesture classifier loaded: {gesture_tflite_path}")
except Exception as e:
    print(f"❌ Error loading gesture classifier: {e}")

# ✅ Ensure ASL model exists
if not os.path.exists(asl_model_path):
    print(f"❌ Error: ASL model file NOT found at {asl_model_path}")
else:
    print(f"✅ ASL model file found at: {asl_model_path}")

# ASL Label Mapping
ASL_LABELS = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "K", "L", "M", "N", "O",
              "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Space", "Del"]

WORD_DICTIONARY = ["HELLO", "WORLD", "SIGN", "LANGUAGE", "CAT", "DOG", "YES", "NO", "PLEASE", "THANK YOU"]

# ✅ ASL Sign Language Recognition Model
class KeyPointClassifier:
    def __init__(self, model_path):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"❌ ASL Model not found at {model_path}")
        self.interpreter = tf.lite.Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

    def classify(self, landmark_list):
        self.interpreter.set_tensor(self.input_details[0]['index'], np.array([landmark_list], dtype=np.float32))
        self.interpreter.invoke()
        result = self.interpreter.get_tensor(self.output_details[0]['index'])
        confidence = float(np.max(result))
        if confidence > 0.6:
            return ASL_LABELS[np.argmax(result)], confidence
        return "Unknown", confidence

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.6, min_tracking_confidence=0.6)
classifier = KeyPointClassifier(asl_model_path)

# ✅ ASL WebSocket Consumer
class VideoProcessorConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_signs = deque(maxlen=10)
        self.sentence = ""
        self.current_word = ""
        self.last_update_time = time.time()

    async def connect(self):
        await self.accept()
        print("✅ ASL WebSocket Connected.")

    async def disconnect(self, close_code):
        print("⚠️ ASL WebSocket Disconnected.")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            frame_data = data.get('image')
            if not frame_data:
                print("⚠️ No frame data received.")
                return

            # Decode frame
            image_bytes = base64.b64decode(frame_data)
            np_arr = np.frombuffer(image_bytes, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if frame is None:
                print("❌ Error: Decoded frame is None.")
                return

            frame = cv2.flip(frame, 1)
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(image_rgb)

            detected_sign = "No Hand Detected"
            confidence = 0.0

            if results.multi_hand_landmarks:
                for landmarks in results.multi_hand_landmarks:
                    landmark_list = np.array([[lm.x, lm.y] for lm in landmarks.landmark], dtype=np.float32)
                    wrist = landmark_list[0]
                    landmark_list -= wrist
                    max_value = np.max(np.abs(landmark_list)) or 1
                    processed_landmarks = (landmark_list.flatten() / max_value).tolist()
                    detected_sign, confidence = classifier.classify(processed_landmarks)

            response_data = {
                'prediction': detected_sign,
                'confidence': round(float(confidence), 2),
            }
            await self.send(text_data=json.dumps(response_data))

        except Exception as e:
            print(f"❌ ASL WebSocket receive error: {e}")

# ✅ Gesture Recognition WebSocket Consumer (18 HaGRID Gestures)
class GestureRecognitionConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.history = deque(maxlen=7)  # Track last 7 frames for smoothing

    async def connect(self):
        """Handles WebSocket connection"""
        await self.accept()
        print("✅ Gesture WebSocket Connected.")

        # Initialize MediaPipe Hands for landmark extraction
        self.hands_detector = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.6
        )

        # Use the global gesture TFLite interpreter
        if gesture_interpreter is None:
            print("❌ Error: Gesture classifier not loaded.")
            self.classifier_ready = False
        else:
            self.classifier_ready = True
            self.input_details = gesture_interpreter.get_input_details()
            self.output_details = gesture_interpreter.get_output_details()
            print(f"✅ Gesture classifier ready ({len(GESTURE_LABELS)} gestures)")

    async def disconnect(self, close_code):
        if hasattr(self, 'hands_detector'):
            self.hands_detector.close()
        print("⚠️ Gesture WebSocket Disconnected.")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            frame_data = data.get("frame", None)
            if not frame_data:
                print("⚠️ No frame data received.")
                return

            # Decode frame
            frame_bytes = base64.b64decode(frame_data)
            np_arr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if frame is None:
                print("❌ Error: Decoded frame is None.")
                return

            # Ensure classifier is ready
            if not self.classifier_ready:
                print("❌ Error: Gesture classifier not ready.")
                return

            # Convert to RGB for MediaPipe
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands_detector.process(frame_rgb)

            gesture_result = "None"
            confidence = 0.0

            if results.multi_hand_landmarks:
                landmarks = results.multi_hand_landmarks[0]

                # Extract 21 landmarks (x, y) = 42 features
                landmark_list = np.array(
                    [[lm.x, lm.y] for lm in landmarks.landmark],
                    dtype=np.float32
                )

                # Normalize relative to wrist + scale
                wrist = landmark_list[0]
                landmark_list = landmark_list - wrist
                max_val = np.max(np.abs(landmark_list)) or 1
                landmark_list = landmark_list / max_val
                processed = landmark_list.flatten()

                # Run TFLite inference
                input_data = np.array([processed], dtype=np.float32)
                gesture_interpreter.set_tensor(
                    self.input_details[0]['index'], input_data
                )
                gesture_interpreter.invoke()
                output_data = gesture_interpreter.get_tensor(
                    self.output_details[0]['index']
                )

                # Get prediction
                confidence = float(np.max(output_data))
                predicted_idx = int(np.argmax(output_data))

                if confidence > 0.6:
                    raw_gesture = GESTURE_LABELS.get(
                        str(predicted_idx), f"gesture_{predicted_idx}"
                    )
                    self.history.append(raw_gesture)
                else:
                    self.history.append("None")
                    
            else:
                self.history.append("None")

            # Temporal smoothing: get most common gesture in last 7 frames
            if len(self.history) > 0:
                from collections import Counter
                counts = Counter(self.history)
                best_gesture, best_count = counts.most_common(1)[0]
                # Require at least 3 occurrences out of 7 to switch
                if best_gesture != "None" and best_count >= 3:
                    gesture_result = best_gesture
                else:
                    gesture_result = "None"
            else:
                gesture_result = "None"

            await self.send(text_data=json.dumps({
                "gesture": gesture_result,
                "confidence": round(confidence, 2)
            }))

        except Exception as e:
            print(f"❌ Gesture WebSocket error: {e}")

