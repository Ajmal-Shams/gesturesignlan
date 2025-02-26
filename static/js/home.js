function startDetection() {
    let wsUrl = document.getElementById("ws-url").value;

    if (wsUrl.trim() !== "") {
        localStorage.setItem("wsUrl", wsUrl); // Save WebSocket URL
    }

    window.location.href = "/detection"; // Redirect to ASL detection page
}
