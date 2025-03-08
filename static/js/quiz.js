document.addEventListener("DOMContentLoaded", function () {
    const quizContainer = document.getElementById("quiz-container");
    const startQuizContainer = document.getElementById("start-quiz");
    const questionImage = document.getElementById("question-image");
    const choicesContainer = document.getElementById("choices");
    const resultText = document.getElementById("result-text");
    const nextButton = document.getElementById("next-question");
    const scoreText = document.getElementById("score");
    const questionCountInput = document.getElementById("question-count");
    const startButton = document.querySelector("#start-quiz button");

    let timerText = document.createElement("p");
    timerText.id = "timer-text";
    timerText.style.fontSize = "20px";
    timerText.style.marginTop = "10px";
    timerText.style.color = "#00c8ff";
    quizContainer.insertBefore(timerText, resultText);

    let signs = [];
    const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    const numbers = "0123456789";

    letters.split("").forEach(letter => {
        signs.push({ image: `/static/images/asl/${letter}.jpeg`, answer: letter });
    });

    numbers.split("").forEach(number => {
        signs.push({ image: `/static/images/asl/${number}.jpeg`, answer: number });
    });

    let selectedQuestions = [];
    let currentQuestion = 0;
    let score = 0;
    let timer;
    let timeLeft = 10;

    // Sounds
    const correctSound = new Audio('/static/sounds/correct.mp3');
    const wrongSound = new Audio('/static/sounds/wrong.mp3');
    const countdownSound = new Audio('/static/sounds/tick.mp3');

    startButton.addEventListener("click", startQuiz);

    function startQuiz() {
        let questionCount = parseInt(questionCountInput.value);
        if (isNaN(questionCount) || questionCount < 5) {
            questionCount = 5;
        } else if (questionCount > 36) {
            questionCount = 36;
        }

        selectedQuestions = signs.sort(() => Math.random() - 0.5).slice(0, questionCount);
        startQuizContainer.style.display = "none";
        quizContainer.style.display = "block";
        loadQuestion();
    }

    function loadQuestion() {
        if (currentQuestion >= selectedQuestions.length) {
            quizContainer.innerHTML = `<h2>Quiz Completed! 🎉</h2><p>Final Score: ${score}/${selectedQuestions.length}</p>`;
            return;
        }

        let sign = selectedQuestions[currentQuestion];
        questionImage.src = sign.image;
        choicesContainer.innerHTML = "";
        resultText.textContent = "";
        nextButton.style.display = "none";

        let options = selectedQuestions.map(s => s.answer).sort(() => Math.random() - 0.5).slice(0, 4);
        if (!options.includes(sign.answer)) options[Math.floor(Math.random() * options.length)] = sign.answer;

        options.forEach(option => {
            let button = document.createElement("button");
            button.classList.add("choice");
            button.textContent = option;
            button.onclick = () => checkAnswer(option, sign.answer);
            choicesContainer.appendChild(button);
        });

        resetTimer();
        startTimer();
    }

    function checkAnswer(selected, correct) {
        clearInterval(timer);
        stopTickingSound(); // STOP ticking sound immediately
        resultText.textContent = selected === correct ? "✅ Correct!" : `❌ Wrong! Correct: ${correct}`;
        if (selected === correct) {
            score++;
            correctSound.play();
        } else {
            wrongSound.play();
        }
        scoreText.textContent = `Score: ${score}`;
        nextButton.style.display = "block";
    }

    // Countdown Overlay for Delay
    let countdownOverlay = document.createElement("div");
    countdownOverlay.id = "countdown-overlay";
    countdownOverlay.style.position = "fixed";
    countdownOverlay.style.top = "0";
    countdownOverlay.style.left = "0";
    countdownOverlay.style.width = "100%";
    countdownOverlay.style.height = "100%";
    countdownOverlay.style.background = "rgba(0, 0, 0, 0.8)";
    countdownOverlay.style.color = "white";
    countdownOverlay.style.fontSize = "50px";
    countdownOverlay.style.display = "none";
    countdownOverlay.style.alignItems = "center";
    countdownOverlay.style.justifyContent = "center";
    countdownOverlay.style.zIndex = "1000";
    document.body.appendChild(countdownOverlay);

    function showCountdownOverlay(callback) {
        countdownOverlay.style.display = "flex";
        let countdown = 3;

        let countdownInterval = setInterval(() => {
            countdownOverlay.textContent = `Next question in ${countdown}...`;
            countdown--;

            if (countdown < 0) {
                clearInterval(countdownInterval);
                countdownOverlay.style.display = "none";
                callback();
            }
        }, 1000);
    }

    function startTimer() {
        timeLeft = 10;
        updateTimerUI();

        timer = setInterval(() => {
            timeLeft--;
            updateTimerUI();

            if (timeLeft <= 5 && timeLeft > 0) {
                countdownSound.currentTime = 0;
                countdownSound.play();
            }

            if (timeLeft === 0) {
                clearInterval(timer);
                stopTickingSound();
                resultText.textContent = `⏳ Time's up! Correct answer: ${selectedQuestions[currentQuestion].answer}`;
                wrongSound.play();
                showCountdownOverlay(() => {
                    currentQuestion++;
                    loadQuestion();
                });
            }
        }, 1000);
    }

    function resetTimer() {
        clearInterval(timer);
        stopTickingSound();
        timerText.style.color = "#00c8ff";
        timerText.style.fontSize = "20px";
        timerText.style.animation = "none";
    }

    function updateTimerUI() {
        timerText.textContent = `⏳ Time Left: ${timeLeft}s`;
        if (timeLeft <= 5) {
            timerText.style.color = "red";
            timerText.style.fontSize = "24px";
            timerText.style.animation = "pulse 0.5s infinite alternate";
        } else {
            timerText.style.color = "#00c8ff";
            timerText.style.fontSize = "20px";
            timerText.style.animation = "none";
        }
    }

    function stopTickingSound() {
        countdownSound.pause();
        countdownSound.currentTime = 0;
    }

    nextButton.onclick = function () {
        stopTickingSound();
        showCountdownOverlay(() => {
            currentQuestion++;
            loadQuestion();
        });
    };
});
