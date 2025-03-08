const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const currentSign = document.getElementById('current-sign');


let wsUrl = localStorage.getItem("wsUrl") || "ws://127.0.0.1:8000/ws/video/";
let ws;
let lastSpokenText = "";

// Function to connect WebSocket
function connectWebSocket() {
    ws = new WebSocket(wsUrl);

    ws.onopen = () => console.log("WebSocket connected");

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        const detectedSign = data.prediction || "No Sign";
       

        console.log("Received Data:", data); // Debugging log
        currentSign.innerText = detectedSign;
       

        // Speak only if the detected sign is different and not "No Sign"
        if (detectedSign !== lastSpokenText && detectedSign !== "No Sign") {
            console.log("Speaking:", detectedSign);
            lastSpokenText = detectedSign;
            speakText(detectedSign);
        }
    };

    ws.onclose = () => {
        console.log("WebSocket disconnected. Reconnecting...");
        setTimeout(connectWebSocket, 2000);
    };
}

// Function to speak detected text
function speakText(text) {
    if ('speechSynthesis' in window) {
        console.log("Triggering Speech:", text);
        speechSynthesis.cancel();
        let utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'en-US';
        utterance.rate = 1;
        speechSynthesis.speak(utterance);
    } else {
        console.warn("Speech synthesis not supported in this browser.");
    }
}

// Connect WebSocket
connectWebSocket();

// Access webcam
navigator.mediaDevices.getUserMedia({ video: true })
    .then(stream => { video.srcObject = stream; })
    .catch(err => { console.log("Error accessing webcam:", err); });

// Capture frames & send to WebSocket
setInterval(() => {
    if (!video.videoWidth || !video.videoHeight) return;

    const ctx = canvas.getContext('2d');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const imageData = canvas.toDataURL('image/jpeg', 0.5).split(',')[1];

    if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ image: imageData }));
    }
}, 100);
