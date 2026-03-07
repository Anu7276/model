document.addEventListener('DOMContentLoaded', () => {
    // --- Navigation Logic ---
    const navLinks = document.querySelectorAll('.nav-links li:not(.nav-header)');
    const topNav = document.querySelector('.top-nav');
    const tabContents = document.querySelectorAll('.tab-content');
    const pageTitle = document.getElementById('page-title');
    const pageSubtitle = document.getElementById('page-subtitle');

    const pageInfo = {
        dashboard: { title: "Intelligence Dashboard", sub: "Overview of preventive health and biomechanical systems." },
        diabetes: { title: "Diabetes Intelligence", sub: "Clinical-grade risk assessment via Random Forest." },
        bp: { title: "Hypertension Intelligence", sub: "Predictive blood pressure diagnostics." },
        obesity: { title: "Obesity Profiling", sub: "Comprehensive body mass and lifestyle behavior assessment." },
        fitness: { title: "AI Biomechanics Coach", sub: "Real-time posture and movement analysis." },
        analytics: { title: "Session Analytics", sub: "Deep insights into performance and stability over time." }
    };

    // --- Theme Switching Logic ---
    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon = themeToggle.querySelector('i');
    const body = document.body;

    const setTheme = (isLight) => {
        if (isLight) {
            body.classList.add('light-mode');
            themeIcon.classList.replace('fa-moon', 'fa-sun');
            localStorage.setItem('theme', 'light');
        } else {
            body.classList.remove('light-mode');
            themeIcon.classList.replace('fa-sun', 'fa-moon');
            localStorage.setItem('theme', 'dark');
        }
    };

    // Load saved theme
    if (localStorage.getItem('theme') === 'light') {
        setTheme(true);
    }

    themeToggle.addEventListener('click', () => {
        setTheme(!body.classList.contains('light-mode'));
    });

    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            const target = link.getAttribute('data-target');

            // Stop fitness camera if switching away
            if (fitnessActive && target !== 'fitness') {
                stopFitness();
            }

            // Update Active States
            navLinks.forEach(l => l.classList.remove('active'));
            tabContents.forEach(t => t.classList.remove('active'));

            link.classList.add('active');
            const targetEl = document.getElementById(target);
            if (targetEl) targetEl.classList.add('active');

            // Update Header Text
            if (pageInfo[target]) {
                pageTitle.innerText = pageInfo[target].title;
                pageSubtitle.innerText = pageInfo[target].sub;
            }

            // Trigger chart animations if Analytics
            if (target === 'analytics' && !chartsInitialized) {
                initCharts();
            }
        });
    });

    // --- Circular Progress Animation Generator ---
    const generateRingResultHTML = (percentage, label, description, riskCategoryCls, riskCategoryName) => {
        // Circumference calculation
        const radius = 110;
        const circumference = 2 * Math.PI * radius;
        const offset = circumference - (percentage / 100) * circumference;

        return `
            <div class="prediction-circle ${riskCategoryCls}">
                <svg viewBox="0 0 250 250">
                    <circle class="circle-bg" cx="125" cy="125" r="${radius}"></circle>
                    <circle class="circle-progress" cx="125" cy="125" r="${radius}" 
                            style="stroke-dasharray: ${circumference}; stroke-dashoffset: ${offset};"></circle>
                </svg>
                <div class="prob-text">${percentage}%</div>
                <div class="prob-label">${label}</div>
            </div>
            <div class="risk-badge ${riskCategoryCls}">${riskCategoryName}</div>
            <p class="prediction-desc">${description}</p>
        `;
    };

    // --- UI Helpers: Count-up Animation ---
    const animateValue = (id, start, end, duration = 500) => {
        const obj = document.getElementById(id);
        if (!obj) return;
        const range = end - start;
        if (range === 0) {
            obj.innerText = id.includes('val') ? end : (id.includes('score') ? end + '%' : end);
            return;
        }
        const minTimer = 50;
        let stepTime = Math.abs(Math.floor(duration / range));
        stepTime = Math.max(stepTime, minTimer);
        const startTime = new Date().getTime();
        const endTime = startTime + duration;
        let timer;

        function run() {
            const now = new Date().getTime();
            const remaining = Math.max((endTime - now) / duration, 0);
            const value = Math.round(end - (remaining * range));
            obj.innerText = id.includes('val') ? value : (id.includes('score') ? value + '%' : value);
            if (value == end) clearInterval(timer);
        }

        timer = setInterval(run, stepTime);
        run();
    };

    const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
    const lerp = (from, to, alpha) => from + (to - from) * alpha;
    const isTouchViewport = () => window.matchMedia('(max-width: 900px), (hover: none) and (pointer: coarse)').matches;

    if (window.matchMedia('(hover: none), (pointer: coarse)').matches) {
        document.body.classList.add('touch-device');
    }

    // --- Form Handling & Visual Result Displays ---
    const handleForm = async (formId, endpoint, resultContainerId, processFunc) => {
        const form = document.getElementById(formId);
        const resultContainer = document.getElementById(resultContainerId);

        if (!form) return;

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(form);
            const data = Object.fromEntries(formData.entries());

            // 🦴 Skeleton Loading State
            resultContainer.innerHTML = `
                <div class="waiting-state">
                    <div class="skeleton-ring"></div>
                    <p class="animate-pulse">AI Engine analyzing clinical markers...</p>
                </div>
            `;

            try {
                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                const result = await response.json();

                setTimeout(() => {
                    if (result.status === 'success') {
                        resultContainer.style.opacity = '0';
                        resultContainer.innerHTML = processFunc(result);
                        requestAnimationFrame(() => {
                            resultContainer.style.transition = 'opacity 0.5s ease-in';
                            resultContainer.style.opacity = '1';
                        });
                    } else {
                        resultContainer.innerHTML = `<div class="waiting-state"><p style="color:var(--status-error)">Engine Delay: ${result.message}</p></div>`;
                    }
                }, 800);
            } catch (error) {
                resultContainer.innerHTML = `<div class="waiting-state"><p style="color:var(--status-error)">Satellite Sync Failed.</p></div>`;
            }
        });
    };

    // Diabetes Result Processor
    handleForm('diabetes-form', '/predict/diabetes', 'diabetes-result-container', (data) => {
        let themeCls = "theme-low";
        let riskDesc = "Patient shows excellent markers. Maintain current clinical lifestyle.";

        if (data.risk_category.includes("High")) {
            themeCls = "theme-high";
            riskDesc = "Critical indicators detected. Immediate consultation with an endocrinologist advised.";
        } else if (data.risk_category.includes("Moderate")) {
            themeCls = "theme-mod";
            riskDesc = "Elevated risk factors present. Recommend lifestyle intervention.";
        }

        return generateRingResultHTML(data.probability, "Diabetes Prob", riskDesc, themeCls, data.risk_category);
    });

    // BP Result Processor
    handleForm('bp-form', '/predict/bp', 'bp-result-container', (data) => {
        let themeCls = "theme-low";
        let riskDesc = "Blood pressure indicators look normal within safe thresholds.";

        if (data.risk_category === "High") {
            themeCls = "theme-high";
            riskDesc = "Hypertension risk is dangerously high. Review medication and sodium intake instantly.";
        } else if (data.risk_category === "Elevated") {
            themeCls = "theme-mod";
            riskDesc = "Borderline hypertension indicators detected. Monitor stress and sleep closely.";
        }

        return generateRingResultHTML(data.probability, "BP Risk", riskDesc, themeCls, `${data.risk_category} Risk`);
    });

    // Obesity Result Processor
    handleForm('obesity-form', '/predict/obesity', 'obesity-result-container', (data) => {
        // Fake a percentage based on the label for unified UI
        let pct = 20;
        let themeCls = "theme-low";
        let riskDesc = "Patient maintains a healthy BMI and lifestyle composition.";

        if (data.simplified === "Obese") {
            pct = 95; themeCls = "theme-high";
            riskDesc = `Severe metabolic imbalance (${data.prediction}). Clinical intervention required.`;
        } else if (data.simplified === "Overweight") {
            pct = 65; themeCls = "theme-mod";
            riskDesc = "Metabolic markers indicate overweight status. Adjust caloric intake.";
        } else if (data.simplified === "Underweight") {
            pct = 15; themeCls = "theme-mod";
            riskDesc = "Patient displays insufficient mass metrics. Recommend nutritional review.";
        }

        return generateRingResultHTML(pct, "Mass Index", riskDesc, themeCls, data.simplified);
    });

    // --- Analytics Session Charts (Chart.js Dummy Data) ---
    let chartsInitialized = false;
    const initCharts = () => {
        chartsInitialized = true;

        Chart.defaults.color = '#9FB3C8';
        Chart.defaults.font.family = "'Inter', sans-serif";

        // Quality Distributions
        new Chart(document.getElementById('qualityChart'), {
            type: 'bar',
            data: {
                labels: ['Squats', 'Pushups', 'Side Weight Holding', 'Lunges'],
                datasets: [{
                    label: 'Avg Form Score %',
                    data: [92, 78, 88, 85],
                    backgroundColor: 'rgba(20, 184, 166, 0.6)',
                    borderColor: '#14B8A6',
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: { y: { beginAtZero: true, max: 100, grid: { color: 'rgba(255,255,255,0.05)' } }, x: { grid: { display: false } } },
                plugins: { legend: { display: false } }
            }
        });

        // Stability Curve
        new Chart(document.getElementById('stabilityChart'), {
            type: 'line',
            data: {
                labels: ['W1', 'W2', 'W3', 'W4', 'W5', 'W6'],
                datasets: [{
                    label: 'Stability Index',
                    data: [65, 72, 70, 85, 88, 94],
                    borderColor: '#F59E0B',
                    tension: 0.4,
                    fill: true,
                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                    pointBackgroundColor: '#F59E0B'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: { y: { grid: { color: 'rgba(255,255,255,0.05)' } }, x: { grid: { display: false } } },
                plugins: { legend: { display: false } }
            }
        });

        // Fatigue Curve
        new Chart(document.getElementById('fatigueChart'), {
            type: 'line',
            data: {
                labels: ['0m', '5m', '10m', '15m', '20m', '25m'],
                datasets: [{
                    label: 'Fatigue Accumulation',
                    data: [5, 12, 25, 45, 68, 89],
                    borderColor: '#EF4444',
                    borderDash: [5, 5],
                    tension: 0.3,
                    pointRadius: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: { y: { grid: { color: 'rgba(255,255,255,0.05)' } }, x: { grid: { display: false } } },
                plugins: { legend: { display: false } }
            }
        });
    };

    // --- Fitness AI Logic Overhaul ---
    const EXERCISE_META = {
        pushup: {
            label: "Push-Ups",
            accent: "#00e5ff",
            tips: ["Elbows at 45°", "Chest near floor", "Lock out at top", "Keep core tight"]
        },
        squat: {
            label: "Squats",
            accent: "#c962ff",
            tips: ["Knees over toes", "Reach parallel depth", "Chest upright", "Drive through heels"]
        },
        sidearm: {
            label: "Side Weight Holding",
            accent: "#00e676",
            tips: ["Hold weight at side line", "No torso lean", "Elbow straight", "Controlled hold 2-3 sec"]
        }
    };

    let fitnessActive = false;
    let fitnessPaused = false;
    let currentExercise = 'pushup';
    let detector = null;
    let scoreHistory = [];
    let commandLog = [];
    let voiceEnabled = true;
    let activeFacingMode = isTouchViewport() ? 'environment' : 'user';
    let cameraSwitchInProgress = false;
    let backendInFlight = false;
    let backendController = null;
    let lastBackendTick = 0;
    let lastSparklinePaint = 0;
    let lastWarningText = '';
    let lastWarningAt = 0;
    let uiAnimationId = null;
    const DESKTOP_BACKEND_INTERVAL_MS = 140;
    const MOBILE_BACKEND_INTERVAL_MS = 220;
    const uiRenderState = {
        score: 100,
        targetScore: 100,
        avg: 100,
        targetAvg: 100,
        stability: 0,
        targetStability: 0
    };
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition = null;

    const videoElement = document.getElementById('input_video');
    const canvasElement = document.getElementById('output_canvas');
    const canvasCtx = canvasElement.getContext('2d');
    const feedbackBox = document.getElementById('web-feedback');
    const feedbackText = document.getElementById('feedback-text');
    const coachRoot = document.getElementById('coach2-root');

    const ui = {
        rep: document.getElementById('web-rep-val'),
        score: document.getElementById('web-score-val'),
        avg: document.getElementById('coach2-avg-score'),
        avgText: document.getElementById('coach2-avg-text'),
        timer: document.getElementById('web-timer'),
        stability: document.getElementById('web-stability'),
        fatigue: document.getElementById('web-fatigue'),
        scoreBar: document.getElementById('web-score-bar'),
        state: document.getElementById('coach2-track-state'),
        stateDot: document.getElementById('coach2-track-dot'),
        tipsTitle: document.getElementById('coach2-tips-title'),
        tipsList: document.getElementById('coach2-tips-list'),
        spark: document.getElementById('coach2-sparkline'),
        log: document.getElementById('coach2-command-log'),
        startBtn: document.getElementById('start-camera'),
        stopBtn: document.getElementById('stop-camera'),
        pauseBtn: document.getElementById('pause-camera'),
        switchCamBtn: document.getElementById('switch-camera'),
        voiceToggle: document.getElementById('coach2-voice-toggle'),
        micBtn: document.getElementById('coach2-mic-btn'),
        pipeCam: document.getElementById('pipe-cam'),
        pipeTrack: document.getElementById('pipe-track'),
        pipeScore: document.getElementById('pipe-score'),
        pipeVoice: document.getElementById('pipe-voice')
    };

    const setPipe = (el, ready) => {
        if (!el) return;
        el.innerText = ready ? "READY" : "IDLE";
        el.style.color = ready ? "var(--status-success)" : "#475569";
        el.style.background = ready ? "rgba(16,185,129,.15)" : "rgba(255,255,255,.06)";
    };

    const releaseCameraStream = () => {
        if (!videoElement.srcObject) return;
        videoElement.srcObject.getTracks().forEach(track => track.stop());
        videoElement.srcObject = null;
    };

    const updateCameraToggleUi = () => {
        if (!ui.switchCamBtn) return;
        const mobile = isTouchViewport();
        const supportsCameraApi = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
        const canSwitch = mobile && supportsCameraApi;
        if (!mobile) activeFacingMode = 'user';
        ui.switchCamBtn.classList.toggle('hidden', !canSwitch);
        ui.switchCamBtn.disabled = cameraSwitchInProgress;
        ui.switchCamBtn.innerText = activeFacingMode === 'environment' ? "BACK CAM" : "FRONT CAM";
    };

    const getVideoConstraints = () => {
        const mobile = isTouchViewport();
        if (mobile) {
            return {
                facingMode: { ideal: activeFacingMode },
                width: { ideal: activeFacingMode === 'environment' ? 960 : 720, max: 1280 },
                height: { ideal: activeFacingMode === 'environment' ? 720 : 540, max: 960 },
                frameRate: { ideal: 24, max: 30 }
            };
        }

        return {
            facingMode: 'user',
            width: { ideal: 1280, max: 1920 },
            height: { ideal: 720, max: 1080 },
            frameRate: { ideal: 30, max: 30 }
        };
    };

    const attachStreamToVideo = async (stream) => {
        videoElement.srcObject = stream;
        if (videoElement.readyState >= 1) {
            await videoElement.play();
            return;
        }

        await new Promise((resolve) => {
            videoElement.onloadedmetadata = async () => {
                try {
                    await videoElement.play();
                } catch (err) {
                    console.warn("Video play warning:", err);
                }
                resolve();
            };
        });
    };

    const requestCameraStream = async () => {
        const primary = getVideoConstraints();
        try {
            return await navigator.mediaDevices.getUserMedia({ video: primary });
        } catch (err) {
            // If facing-mode preference fails, fall back to any available camera.
            if (isTouchViewport()) {
                return await navigator.mediaDevices.getUserMedia({
                    video: {
                        width: { ideal: 720, max: 1280 },
                        height: { ideal: 540, max: 960 },
                        frameRate: { ideal: 24, max: 30 }
                    }
                });
            }
            throw err;
        }
    };

    const formatClock = (secs = 0) => new Date((secs || 0) * 1000).toISOString().substr(14, 5);

    const setCoachTheme = () => {
        const ex = EXERCISE_META[currentExercise];
        coachRoot.style.setProperty("--coach-accent", ex.accent);
        ui.tipsTitle.innerText = `Form Tips - ${ex.label}`;
        ui.tipsList.innerHTML = ex.tips.map((tip) => `<li>${tip}</li>`).join("");
        document.querySelectorAll('.coach2-ex-btn').forEach((btn) => {
            btn.classList.toggle('active', btn.dataset.ex === currentExercise);
        });
    };

    const addLog = (text) => {
        commandLog = [{ text, time: new Date().toLocaleTimeString() }, ...commandLog].slice(0, 7);
        ui.log.innerHTML = commandLog.map((item) =>
            `<div class="log-item"><span>${item.text}</span><span>${item.time}</span></div>`
        ).join("");
    };

    const triggerWarning = (msg) => {
        const now = Date.now();
        if (msg === lastWarningText && (now - lastWarningAt) < 1400) return;
        lastWarningText = msg;
        lastWarningAt = now;

        feedbackText.innerText = msg;
        feedbackBox.classList.remove('hidden');
        clearTimeout(window.warningTimeout);
        window.warningTimeout = setTimeout(() => feedbackBox.classList.add('hidden'), 2600);
    };

    const updateSparkline = () => {
        if (!ui.spark) return;
        if (scoreHistory.length < 2) {
            ui.spark.innerHTML = '';
            return;
        }

        const values = scoreHistory.slice(-(isTouchViewport() ? 24 : 32));
        const min = Math.min(...values);
        const max = Math.max(...values);
        const range = Math.max(1, max - min);
        const points = values.map((v, i) => {
            const x = (i / (values.length - 1)) * 420;
            const y = 80 - ((v - min) / range) * 70;
            return `${x},${y}`;
        }).join(' ');

        ui.spark.innerHTML = `
            <polyline points="0,90 ${points} 420,90" fill="color-mix(in srgb, var(--coach-accent) 18%, transparent)" stroke="none"></polyline>
            <polyline points="${points}" fill="none" stroke="var(--coach-accent)" stroke-width="3" stroke-linejoin="round"></polyline>
        `;
    };

    const applyScoreTone = (score) => {
        if (score > 85) {
            ui.score.style.color = 'var(--status-success)';
            ui.scoreBar.style.background = 'var(--status-success)';
        } else if (score > 65) {
            ui.score.style.color = 'var(--status-warning)';
            ui.scoreBar.style.background = 'var(--status-warning)';
        } else {
            ui.score.style.color = 'var(--status-error)';
            ui.scoreBar.style.background = 'var(--status-error)';
        }
    };

    const renderFitnessUiFrame = () => {
        uiRenderState.score = lerp(uiRenderState.score, uiRenderState.targetScore, 0.22);
        uiRenderState.avg = lerp(uiRenderState.avg, uiRenderState.targetAvg, 0.2);
        uiRenderState.stability = lerp(uiRenderState.stability, uiRenderState.targetStability, 0.25);

        if (Math.abs(uiRenderState.score - uiRenderState.targetScore) < 0.1) uiRenderState.score = uiRenderState.targetScore;
        if (Math.abs(uiRenderState.avg - uiRenderState.targetAvg) < 0.1) uiRenderState.avg = uiRenderState.targetAvg;
        if (Math.abs(uiRenderState.stability - uiRenderState.targetStability) < 0.001) uiRenderState.stability = uiRenderState.targetStability;

        const scoreRounded = Math.round(uiRenderState.score);
        const avgRounded = Math.round(uiRenderState.avg);
        ui.score.innerText = `${scoreRounded}%`;
        ui.avg.innerText = `${avgRounded}%`;
        ui.avgText.innerText = `AVG ${avgRounded}%`;
        ui.stability.innerText = Number(uiRenderState.stability).toFixed(3);
        ui.scoreBar.style.width = `${clamp(uiRenderState.score, 0, 100).toFixed(1)}%`;
        applyScoreTone(scoreRounded);

        uiAnimationId = requestAnimationFrame(renderFitnessUiFrame);
    };

    const ensureFitnessUiLoop = () => {
        if (uiAnimationId) return;
        uiAnimationId = requestAnimationFrame(renderFitnessUiFrame);
    };

    let lastRepCount = 0;
    const updateFitnessUI = (stats) => {
        const newCounter = stats.counter ?? 0;
        if (newCounter !== lastRepCount) {
            animateValue('web-rep-val', lastRepCount, newCounter, 260);
            lastRepCount = newCounter;
        }

        const score = Math.round(stats.form_score ?? 100);
        const avg = Math.round(stats.avg_score ?? score);
        uiRenderState.targetScore = score;
        uiRenderState.targetAvg = avg;
        ui.timer.innerText = formatClock(stats.elapsed_time ?? 0);
        uiRenderState.targetStability = stats.stats_v2?.stability !== undefined ? Number(stats.stats_v2.stability) : 0;

        scoreHistory.push(score);
        scoreHistory = scoreHistory.slice(-80);
        const now = performance.now();
        if ((now - lastSparklinePaint) > 180) {
            updateSparkline();
            lastSparklinePaint = now;
        }

        const fatigue = (stats.fatigue_status || "OPTIMAL").toUpperCase();
        ui.fatigue.innerText = fatigue;
        if (fatigue.includes("HIGH") || fatigue.includes("FATIG")) {
            ui.fatigue.style.color = 'var(--status-error)';
        } else if (fatigue.includes("MOD")) {
            ui.fatigue.style.color = 'var(--status-warning)';
        } else {
            ui.fatigue.style.color = 'var(--status-success)';
        }

        if (stats.feedback && !["Good job!", "Keep going!", "Analyzing..."].includes(stats.feedback)) {
            triggerWarning(stats.feedback);
        }

        ensureFitnessUiLoop();
    };

    const drawSkeleton = (keypoints) => {
        const connections = [
            [11, 12], [11, 13], [13, 15], [12, 14], [14, 16],
            [11, 23], [12, 24], [23, 24],
            [23, 25], [25, 27], [24, 26], [26, 28],
            [27, 29], [29, 31], [27, 31],
            [28, 30], [30, 32], [28, 32]
        ];

        canvasCtx.fillStyle = '#ffffff';
        canvasCtx.strokeStyle = 'rgba(0, 229, 255, 0.92)';
        canvasCtx.lineWidth = 2.5;

        connections.forEach(([i, j]) => {
            const kp1 = keypoints[i];
            const kp2 = keypoints[j];
            if (kp1 && kp2 && (kp1.score > 0.25 || kp1.visibility > 0.25) && (kp2.score > 0.25 || kp2.visibility > 0.25)) {
                canvasCtx.beginPath();
                canvasCtx.moveTo(kp1.x, kp1.y);
                canvasCtx.lineTo(kp2.x, kp2.y);
                canvasCtx.stroke();
            }
        });

        keypoints.forEach((kp, idx) => {
            if (idx <= 32 && (kp.score > 0.25 || kp.visibility > 0.25)) {
                canvasCtx.beginPath();
                canvasCtx.arc(kp.x, kp.y, idx > 10 ? 3 : 2, 0, 2 * Math.PI);
                canvasCtx.fill();
            }
        });
    };

    const runDetection = async () => {
        if (!fitnessActive || !detector) return;

        const poses = await detector.estimatePoses(videoElement);
        const now = performance.now();

        if (canvasElement.width !== videoElement.videoWidth || canvasElement.height !== videoElement.videoHeight) {
            canvasElement.width = videoElement.videoWidth;
            canvasElement.height = videoElement.videoHeight;
        }

        canvasCtx.save();
        canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);
        canvasCtx.drawImage(videoElement, 0, 0, canvasElement.width, canvasElement.height);

        if (poses && poses.length > 0) {
            const landmarks = poses[0].keypoints;
            drawSkeleton(landmarks);

            const backendInterval = isTouchViewport() ? MOBILE_BACKEND_INTERVAL_MS : DESKTOP_BACKEND_INTERVAL_MS;
            const shouldProcess = !fitnessPaused && !backendInFlight && ((now - lastBackendTick) >= backendInterval);
            if (shouldProcess) {
                backendInFlight = true;
                lastBackendTick = now;
                const controller = new AbortController();
                backendController = controller;

                fetch('/process_pose', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ exercise_type: currentExercise, landmarks }),
                    signal: controller.signal
                })
                    .then((response) => response.json())
                    .then((stats) => {
                        if (stats.status !== "error") {
                            updateFitnessUI(stats);
                            setPipe(ui.pipeTrack, true);
                            setPipe(ui.pipeScore, true);
                        }
                    })
                    .catch((err) => {
                        if (err?.name !== 'AbortError') {
                            console.error("Pose logic error:", err);
                            setPipe(ui.pipeTrack, false);
                            setPipe(ui.pipeScore, false);
                        }
                    })
                    .finally(() => {
                        if (backendController === controller) backendController = null;
                        backendInFlight = false;
                    });
            }
        }
        canvasCtx.restore();

        if (fitnessActive) requestAnimationFrame(runDetection);
    };

    const initFitness = async () => {
        if (detector) return;
        const useLiteModel = isTouchViewport();
        detector = await poseDetection.createDetector(poseDetection.SupportedModels.BlazePose, {
            runtime: 'mediapipe',
            solutionPath: 'https://cdn.jsdelivr.net/npm/@mediapipe/pose',
            modelType: useLiteModel ? 'lite' : 'full'
        });
    };

    const setCoachState = () => {
        if (!fitnessActive) {
            ui.state.innerText = "STANDBY";
            ui.stateDot.style.background = "#334155";
        } else if (fitnessPaused) {
            ui.state.innerText = "PAUSED";
            ui.stateDot.style.background = "var(--status-warning)";
        } else {
            ui.state.innerText = "TRACKING";
            ui.stateDot.style.background = "var(--status-success)";
        }

        ui.startBtn.classList.toggle('hidden', fitnessActive);
        ui.pauseBtn.classList.toggle('hidden', !fitnessActive);
        ui.stopBtn.classList.toggle('hidden', !fitnessActive);
        ui.pauseBtn.innerText = fitnessPaused ? "RESUME" : "PAUSE";
    };

    const resetCoachMetrics = () => {
        lastRepCount = 0;
        scoreHistory = [];
        uiRenderState.score = 100;
        uiRenderState.targetScore = 100;
        uiRenderState.avg = 100;
        uiRenderState.targetAvg = 100;
        uiRenderState.stability = 0;
        uiRenderState.targetStability = 0;
        ui.rep.innerText = '0';
        ui.score.innerText = '100%';
        ui.avg.innerText = '100%';
        ui.avgText.innerText = 'AVG 100%';
        ui.timer.innerText = '00:00';
        ui.stability.innerText = '0.000';
        ui.fatigue.innerText = 'OPTIMAL';
        ui.fatigue.style.color = 'var(--status-success)';
        ui.scoreBar.style.width = '100%';
        applyScoreTone(100);
        updateSparkline();
        ensureFitnessUiLoop();
    };

    const startFitness = async () => {
        await initFitness();
        fitnessActive = true;
        fitnessPaused = false;
        backendInFlight = false;
        lastBackendTick = 0;
        resetCoachMetrics();
        setCoachState();
        updateCameraToggleUi();

        try {
            if (!videoElement.srcObject) {
                const stream = await requestCameraStream();
                await attachStreamToVideo(stream);
                requestAnimationFrame(runDetection);
            } else {
                requestAnimationFrame(runDetection);
            }
            setPipe(ui.pipeCam, true);
            const camLabel = activeFacingMode === 'environment' ? 'back camera' : 'front camera';
            addLog(`${EXERCISE_META[currentExercise].label} session started (${camLabel})`);
        } catch (err) {
            console.error("Camera access error:", err);
            fitnessActive = false;
            setCoachState();
            setPipe(ui.pipeCam, false);
            triggerWarning("Camera access denied or unavailable");
        }
    };

    const stopFitness = () => {
        fitnessActive = false;
        fitnessPaused = false;
        backendInFlight = false;
        lastBackendTick = 0;
        if (backendController) {
            backendController.abort();
            backendController = null;
        }
        releaseCameraStream();
        canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);
        if (uiAnimationId) {
            cancelAnimationFrame(uiAnimationId);
            uiAnimationId = null;
        }
        fetch('/reset_fitness', { method: 'POST' });
        setPipe(ui.pipeCam, false);
        setPipe(ui.pipeTrack, false);
        setPipe(ui.pipeScore, false);
        setCoachState();
        addLog("Session stopped");
        resetCoachMetrics();
    };

    const pauseFitness = () => {
        if (!fitnessActive) return;
        fitnessPaused = !fitnessPaused;
        setCoachState();
        addLog(fitnessPaused ? "Tracking paused" : "Tracking resumed");
    };

    const switchCamera = async () => {
        if (!isTouchViewport() || cameraSwitchInProgress) return;
        cameraSwitchInProgress = true;
        updateCameraToggleUi();

        const previousFacing = activeFacingMode;
        activeFacingMode = activeFacingMode === 'environment' ? 'user' : 'environment';
        updateCameraToggleUi();

        if (!fitnessActive) {
            addLog(`Camera preset: ${activeFacingMode === 'environment' ? 'back' : 'front'}`);
            cameraSwitchInProgress = false;
            updateCameraToggleUi();
            return;
        }

        try {
            if (backendController) {
                backendController.abort();
                backendController = null;
            }
            backendInFlight = false;
            releaseCameraStream();

            const stream = await requestCameraStream();
            await attachStreamToVideo(stream);
            setPipe(ui.pipeCam, true);
            addLog(`Switched to ${activeFacingMode === 'environment' ? 'back' : 'front'} camera`);
        } catch (err) {
            console.error("Camera switch error:", err);
            activeFacingMode = previousFacing;
            updateCameraToggleUi();
            triggerWarning("Could not switch camera");
            addLog("Camera switch failed");
        } finally {
            cameraSwitchInProgress = false;
            updateCameraToggleUi();
        }
    };

    const setExercise = (id) => {
        currentExercise = id;
        setCoachTheme();
        fetch('/reset_fitness', { method: 'POST' });
        resetCoachMetrics();
        addLog(`Exercise set to ${EXERCISE_META[id].label}`);
    };

    const parseVoiceCommand = (text) => {
        const t = (text || '').toLowerCase();
        if (t.includes('unmute')) return 'unmute';
        if (t.includes('start')) return 'start';
        if (t.includes('stop')) return 'stop';
        if (t.includes('pause')) return 'pause';
        if (t.includes('resume')) return 'resume';
        if (t.includes('push')) return 'pushup';
        if (t.includes('squat')) return 'squat';
        if (t.includes('side') || t.includes('raise') || t.includes('stretch') || t.includes('weight') || t.includes('hold')) return 'sidearm';
        if (t.includes('switch camera') || t.includes('swap camera') || t.includes('flip camera') || t.includes('back camera') || t.includes('rear camera') || t.includes('front camera')) return 'camera';
        if (t.includes('mute')) return 'mute';
        return '';
    };

    const runCommand = (cmd) => {
        if (!cmd) return;
        addLog(`Voice: "${cmd}"`);
        if (cmd === 'start') startFitness();
        else if (cmd === 'stop') stopFitness();
        else if (cmd === 'pause') { if (!fitnessPaused) pauseFitness(); }
        else if (cmd === 'resume') { if (fitnessPaused) pauseFitness(); }
        else if (cmd === 'pushup' || cmd === 'squat' || cmd === 'sidearm') setExercise(cmd);
        else if (cmd === 'camera') switchCamera();
        else if (cmd === 'mute') {
            voiceEnabled = false;
            ui.voiceToggle.innerText = "OFF";
            setPipe(ui.pipeVoice, false);
        } else if (cmd === 'unmute') {
            voiceEnabled = true;
            ui.voiceToggle.innerText = "ON";
            setPipe(ui.pipeVoice, true);
        }
    };

    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.lang = 'en-US';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;
        recognition.onresult = (event) => {
            const transcript = event.results?.[0]?.[0]?.transcript || '';
            const command = parseVoiceCommand(transcript);
            if (command) runCommand(command);
        };
        recognition.onerror = () => addLog("Voice recognition failed");
    } else {
        ui.micBtn.disabled = true;
        ui.micBtn.innerText = "mic unsupported";
    }

    document.getElementById('start-camera').addEventListener('click', startFitness);
    document.getElementById('stop-camera').addEventListener('click', stopFitness);
    document.getElementById('pause-camera').addEventListener('click', pauseFitness);
    if (ui.switchCamBtn) {
        ui.switchCamBtn.addEventListener('click', () => {
            switchCamera();
        });
    }

    document.querySelectorAll('.coach2-ex-btn').forEach((btn) => {
        btn.addEventListener('click', () => setExercise(btn.dataset.ex));
    });

    document.querySelectorAll('.coach2-cmd').forEach((btn) => {
        btn.addEventListener('click', () => runCommand(btn.dataset.cmd));
    });

    ui.voiceToggle.addEventListener('click', () => {
        voiceEnabled = !voiceEnabled;
        ui.voiceToggle.innerText = voiceEnabled ? "ON" : "OFF";
        setPipe(ui.pipeVoice, voiceEnabled);
        addLog(voiceEnabled ? "Voice enabled" : "Voice muted");
    });

    ui.micBtn.addEventListener('click', () => {
        if (!voiceEnabled || !recognition) return;
        addLog("Listening...");
        try {
            recognition.start();
        } catch (err) {
            addLog("Mic busy, try again");
        }
    });

    let lastTouchViewport = isTouchViewport();
    window.addEventListener('resize', () => {
        const nextTouchViewport = isTouchViewport();
        if (nextTouchViewport !== lastTouchViewport) {
            lastTouchViewport = nextTouchViewport;
            if (!nextTouchViewport) activeFacingMode = 'user';
            if (nextTouchViewport) activeFacingMode = 'environment';
            updateCameraToggleUi();
        }
    });

    setCoachTheme();
    updateCameraToggleUi();
    setCoachState();
    setPipe(ui.pipeCam, false);
    setPipe(ui.pipeTrack, false);
    setPipe(ui.pipeScore, false);
    setPipe(ui.pipeVoice, true);
    resetCoachMetrics();
    addLog("Coach ready");

    // --- BMI Calculator Logic ---
    const calcBmiBtn = document.getElementById('calc-bmi-btn');
    const bmiWeightInput = document.getElementById('bmi-weight');
    const bmiHeightInput = document.getElementById('bmi-height');
    const bmiResult = document.getElementById('bmi-result');

    if (calcBmiBtn) {
        calcBmiBtn.addEventListener('click', () => {
            const weight = parseFloat(bmiWeightInput.value);
            const heightCm = parseFloat(bmiHeightInput.value);

            if (!weight || !heightCm) {
                alert("Please enter valid weight and height.");
                return;
            }

            const heightM = heightCm / 100;
            const bmi = weight / (heightM * heightM);
            const bmiFixed = bmi.toFixed(1);

            let label = "Normal";
            let color = "var(--status-success)";

            if (bmi < 18.5) {
                label = "Underweight";
                color = "var(--status-warning)";
            } else if (bmi >= 25 && bmi < 30) {
                label = "Overweight";
                color = "var(--status-warning)";
            } else if (bmi >= 30) {
                label = "Obese";
                color = "var(--status-error)";
            }

            bmiResult.classList.remove('hidden');
            const bmiValEl = bmiResult.querySelector('.bmi-val');
            const bmiLabelEl = bmiResult.querySelector('.bmi-label');

            bmiValEl.innerText = bmiFixed;
            bmiValEl.style.color = color;
            bmiLabelEl.innerText = label;
            bmiLabelEl.style.color = color;
        });
    }
});
