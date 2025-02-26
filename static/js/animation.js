document.addEventListener("DOMContentLoaded", function () {
    const loadingScreen = document.getElementById("loading-screen");
    const mainContent = document.getElementById("main-content");

    setTimeout(() => {
        loadingScreen.classList.add("hidden"); // Hide loading screen
        mainContent.classList.remove("hidden"); // Show main content
    }, 2000); // 2 seconds delay
});
