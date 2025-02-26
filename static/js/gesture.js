const video = document.getElementById("video");
const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");
const gestureDisplay = document.getElementById("gesture");

// Open WebSocket connection
const socket = new WebSocket("ws://localhost:8000/ws/gesture/");

socket.onmessage = function(event) {
    const data = JSON.parse(event.data);
    gestureDisplay.textContent = data.gesture; // Update detected gesture
};

// Access webcam
async function startVideo() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        video.srcObject = stream;
    } catch (error) {
        console.error("Error accessing webcam:", error);
    }
}

function sendFrame() {
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

// Capture and send frames every 100ms
setInterval(sendFrame, 100);

startVideo();
