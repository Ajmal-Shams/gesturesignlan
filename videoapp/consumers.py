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
asl_model_path = os.path.abspath("G:/Django Projects/Personal/lansign/video_stream/models/slr_model.tflite")


# ✅ Get absolute model path
gesture_model_path = os.path.abspath("G:/Django Projects/Personal/signlan-1/videoapp/gesture_recognizer.task")

# ✅ Debugging: Check if MediaPipe is getting the correct path
print(f"🔹 Using Gesture Model Path: {gesture_model_path}")

# ✅ Read the model file manually
try:
    with open(gesture_model_path, "rb") as f:
        gesture_model_data = f.read()  # ✅ Read file as bytes
    print("✅ Gesture model file read successfully.")
except Exception as e:
    print(f"❌ Error reading Gesture model file: {e}")
    gesture_model_data = None



# ✅ Ensure ASL model exists
if not os.path.exists(asl_model_path):
    print(f"❌ Error: ASL model file NOT found at {asl_model_path}")
else:
    print(f"✅ ASL model file found at: {asl_model_path}")

# ✅ Ensure Gesture model exists
if not os.path.exists(gesture_model_path):
    print(f"❌ Error: Gesture model file NOT found at {gesture_model_path}")
else:
    print(f"✅ Gesture model file found at: {gesture_model_path}")

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

# ✅ Gesture Recognition WebSocket Consumer
class GestureRecognitionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Handles WebSocket connection"""
        await self.accept()
        print("✅ Gesture WebSocket Connected.")

        # ✅ Ensure the model was read correctly
        if gesture_model_data is None:
            print(f"❌ Error: Gesture model file could not be read.")
            self.recognizer = None
            return

        try:
            print(f"🔹 Loading GestureRecognizer from memory...")

            # ✅ Load the model from bytes
            base_options = mp.tasks.BaseOptions(model_asset_buffer=gesture_model_data)
            options = mp.tasks.vision.GestureRecognizerOptions(
                base_options=base_options,
                running_mode=mp.tasks.vision.RunningMode.IMAGE
            )
            self.recognizer = mp.tasks.vision.GestureRecognizer.create_from_options(options)
            print("✅ GestureRecognizer model loaded successfully.")

        except Exception as e:
            print(f"❌ Error initializing GestureRecognizer: {e}")
            self.recognizer = None  # Prevent crashes

    async def disconnect(self, close_code):
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

            print(f"✅ Received frame of shape: {frame.shape}")

            # ✅ Ensure recognizer is initialized
            if not self.recognizer:
                print("❌ Error: GestureRecognizer is not initialized. Skipping processing.")
                return

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

            result = self.recognizer.recognize(mp_image)
            gesture_result = "None"
            if result.gestures:
                gesture_result = result.gestures[0][0].category_name
                print(f"✅ Detected Gesture: {gesture_result}")

            await self.send(text_data=json.dumps({"gesture": gesture_result}))

        except Exception as e:
            print(f"❌ Gesture WebSocket error: {e}")
