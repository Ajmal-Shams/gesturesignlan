const video = document.getElementById("video");
const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");
const gestureDisplay = document.getElementById("gesture");

// Open WebSocket connection
const socket = new WebSocket("ws://localhost:8000/ws/gesture/");

let lastSpokenGesture = ""; // Track last spoken gesture
let isSpeaking = false; // Prevent overlapping speech
let lastGestureTime = Date.now(); // Track last gesture timestamp
let noHandTimeout = null; // Timeout for "No hand detected"

socket.onmessage = function (event) {
    try {
        const data = JSON.parse(event.data);
        let detectedGesture = data.gesture || "none";

        // Remove underscores and format text
        detectedGesture = detectedGesture.replace(/_/g, " ").trim();

        // If gesture is detected, clear "No hand detected" timeout
        if (detectedGesture.toLowerCase() !== "none") {
            lastGestureTime = Date.now(); // Update last gesture time
            if (noHandTimeout) {
                clearTimeout(noHandTimeout);
                noHandTimeout = null;
            }
        }

        // Schedule "No hand detected" only if no gestures are detected for 1 second
        if (detectedGesture.toLowerCase() === "none") {
            noHandTimeout = setTimeout(() => {
                if (Date.now() - lastGestureTime >= 1000) {
                    detectedGesture = "No hand detected";
                    updateUIandSpeak(detectedGesture);
                }
            }, 1000); // 1-second delay before announcing "No hand detected"
            return;
        }

        updateUIandSpeak(detectedGesture);
    } catch (error) {
        console.error("Error processing WebSocket message:", error);
    }
};

// Function to update UI and speak
function updateUIandSpeak(detectedGesture) {
    // Prevent repeating the same gesture
    if (detectedGesture !== lastSpokenGesture && !isSpeaking) {
        lastSpokenGesture = detectedGesture;
        gestureDisplay.textContent = detectedGesture; // Update UI
        speakText(detectedGesture);
    }
}

// Function to access webcam
async function startVideo() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        video.srcObject = stream;
    } catch (error) {
        console.error("Error accessing webcam:", error);
    }
}

// Function to send frames to WebSocket
function sendFrame() {
    if (!video.videoWidth || !video.videoHeight) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Convert frame to Base64
    const frameData = canvas.toDataURL("image/jpeg").split(",")[1];

    // Send to WebSocket
    if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ frame: frameData }));
    }
}

// Function to speak detected text
function speakText(text) {
    if ("speechSynthesis" in window) {
        speechSynthesis.cancel(); // Stop any ongoing speech

        let utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = "en-US"; // Set language
        utterance.rate = 1; // Normal speed

        isSpeaking = true;
        utterance.onend = () => isSpeaking = false; // Reset when speech ends

        speechSynthesis.speak(utterance);
    } else {
        console.warn("Speech synthesis not supported in this browser.");
    }
}

// Capture and send frames every 100ms
setInterval(sendFrame, 100);

// Start webcam
startVideo();
