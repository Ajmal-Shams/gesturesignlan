const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const currentSign = document.getElementById('current-sign');
const currentWordText = document.getElementById('current-word');
const sentenceText = document.getElementById('sentence');

let wsUrl = localStorage.getItem("wsUrl") || "ws://127.0.0.1:8000/ws/video/";
let ws;

function connectWebSocket() {
    ws = new WebSocket(wsUrl);

    ws.onopen = () => console.log("WebSocket connected");

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        const detectedSign = data.prediction || "No Sign";
        const currentWord = data.current_word || "";
        const sentence = data.sentence || "";

        currentSign.innerText = detectedSign;
        currentWordText.innerText = currentWord;
        sentenceText.innerText = sentence;
    };

    ws.onclose = () => {
        console.log("WebSocket disconnected. Reconnecting...");
        setTimeout(connectWebSocket, 2000);
    };
}

connectWebSocket();

// Access webcam
navigator.mediaDevices.getUserMedia({ video: true })
    .then(stream => { video.srcObject = stream; })
    .catch(err => { console.log("Error accessing webcam:", err); });

// Capture frames & send to WebSocket
setInterval(() => {
    const ctx = canvas.getContext('2d');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const imageData = canvas.toDataURL('image/jpeg', 0.5).split(',')[1];

    if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ image: imageData }));
    }
}, 100);
