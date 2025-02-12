import cv2 as cv
import numpy as np
import mediapipe as mp
import tensorflow as tf
import base64
import json
import time
from difflib import get_close_matches
from collections import deque
from channels.generic.websocket import AsyncWebsocketConsumer

ASL_LABELS = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "K", "L", "M", "N", "O",
              "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Space", "Del"]

WORD_DICTIONARY = ["HELLO", "WORLD", "SIGN", "LANGUAGE", "CAT", "DOG", "YES", "NO", "PLEASE", "THANK YOU"]

class KeyPointClassifier:
    def __init__(self, model_path='G:/Django Projects/Personal/lansign/video_stream/models/slr_model.tflite'):
        self.interpreter = tf.lite.Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

    def classify(self, landmark_list):
        self.interpreter.set_tensor(self.input_details[0]['index'], np.array([landmark_list], dtype=np.float32))
        self.interpreter.invoke()
        result = self.interpreter.get_tensor(self.output_details[0]['index'])

        confidence = float(np.max(result))  # Convert float32 → float for JSON
        if confidence > 0.6:
            return ASL_LABELS[np.argmax(result)], confidence
        return "Unknown", confidence

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.6, min_tracking_confidence=0.6)
classifier = KeyPointClassifier()

def preprocess_landmarks(landmarks):
    landmark_list = np.array([[lm.x, lm.y] for lm in landmarks.landmark], dtype=np.float32)
    wrist = landmark_list[0]
    landmark_list -= wrist  
    max_value = np.max(np.abs(landmark_list)) or 1  
    return (landmark_list.flatten() / max_value).tolist()

class VideoProcessorConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_signs = deque(maxlen=10)  
        self.sentence = ""
        self.current_word = ""
        self.last_update_time = time.time()

    async def connect(self):
        await self.accept()
        print("Client connected to WebSocket")

    async def disconnect(self, close_code):
        print("Client disconnected")

    def get_predicted_word(self):
        if not self.current_word.strip():
            return "..."
        refined_word = "".join(c for i, c in enumerate(self.current_word) if i == 0 or c != self.current_word[i - 1])
        matches = get_close_matches(refined_word.lower(), WORD_DICTIONARY, n=1, cutoff=0.7)
        return matches[0].upper() if matches else refined_word

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            frame_data = data.get('image')

            if not frame_data:
                return

            image_bytes = base64.b64decode(frame_data)
            np_arr = np.frombuffer(image_bytes, np.uint8)
            frame = cv.imdecode(np_arr, cv.IMREAD_COLOR)

            if frame is None:
                return

            frame = cv.flip(frame, 1)
            image_rgb = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
            results = hands.process(image_rgb)

            detected_sign = "No Hand Detected"
            confidence = 0.0

            if results.multi_hand_landmarks:
                for landmarks in results.multi_hand_landmarks:
                    processed_landmarks = preprocess_landmarks(landmarks)
                    detected_sign, confidence = classifier.classify(processed_landmarks)

            if time.time() - self.last_update_time > 1.5:
                self.current_word = ""
            self.last_update_time = time.time()

            if confidence > 0.6:
                self.last_signs.append(detected_sign)

            # ✅ Fix: Ensure deque is not empty before using max()
            most_common_sign = "Unknown"
            if self.last_signs:
                most_common_sign = max(set(self.last_signs), key=self.last_signs.count)

            if most_common_sign not in ["Unknown", "No Hand Detected"] and most_common_sign != self.current_word[-1:]:
                if most_common_sign == "Space":
                    if self.current_word:
                        self.sentence += self.get_predicted_word() + " "
                        self.current_word = ""
                elif most_common_sign == "Del":
                    self.current_word = self.current_word[:-1]
                else:
                    self.current_word += most_common_sign

            # ✅ Fix: Convert float32 values to float before JSON serialization
            response_data = {
                'prediction': most_common_sign,
                'confidence': round(float(confidence), 2),
                'current_word': self.get_predicted_word(),
                'sentence': self.sentence.strip()
            }

            await self.send(text_data=json.dumps(response_data))

        except Exception as e:
            print(f"WebSocket receive error: {e}")
