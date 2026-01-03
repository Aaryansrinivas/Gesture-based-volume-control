/* ================= ELEMENTS ================= */
const distanceText = document.getElementById("distanceText");
const volumeText = document.getElementById("volumeText");
const volumeMetric = document.getElementById("volumeMetric");
const volumeState = document.getElementById("volumeState");
const fpsText = document.getElementById("fpsText");

const startCalBtn = document.getElementById("startCalBtn");
const stopCalBtn = document.getElementById("stopCalBtn");
const resetCalBtn = document.getElementById("resetCalBtn");
const defaultCalBtn = document.getElementById("defaultCalBtn");

const calibrationStatus = document.getElementById("calibrationStatus");
const minValueText = document.getElementById("minValue");
const maxValueText = document.getElementById("maxValue");

const calibrationBadge = document.getElementById("calibrationBadge");
const toast = document.getElementById("toast");
const distanceFill = document.getElementById("distanceFill");


/* ================= FPS ================= */
let lastTime = performance.now();

/* ================= TOAST ================= */
function showToast(msg) {
    toast.innerText = msg;
    toast.classList.remove("hidden");
    toast.classList.add("show");

    setTimeout(() => {
        toast.classList.remove("show");
        setTimeout(() => toast.classList.add("hidden"), 300);
    }, 2500);
}

/* ================= REMINDER ================= */
let reminderInterval = null;

/* ================= BUTTONS ================= */

// START
startCalBtn.onclick = () => {
    fetch("/calibration/custom/start").then(() => {
        startCalBtn.disabled = true;
        calibrationBadge.classList.remove("hidden");
        calibrationStatus.innerText =
            "Calibrating... move thumb & index slowly";
        calibrationStatus.style.color = "#2563eb";

        showToast("Calibration started");

        reminderInterval = setInterval(() => {
            showToast("Please STOP calibration when done");
        }, 6000);
    });
};

// STOP
stopCalBtn.onclick = () => {
    clearInterval(reminderInterval);

    fetch("/calibration/custom/stop")
        .then(r => r.json())
        .then(d => {
            startCalBtn.disabled = false;
            calibrationBadge.classList.add("hidden");

            calibrationStatus.innerText =
                `Calibration saved (MIN=${d.min}px, MAX=${d.max}px)`;
            calibrationStatus.style.color = "#16a34a";

            showToast("Calibration stopped");
        });
};

// RESET
resetCalBtn.onclick = () => {
    clearInterval(reminderInterval);

    fetch("/calibration/custom/reset")
        .then(r => r.json())
        .then(d => {
            startCalBtn.disabled = false;
            calibrationBadge.classList.add("hidden");

            calibrationStatus.innerText =
                `Reset to app defaults (MIN=${d.min}px, MAX=${d.max}px)`;
            calibrationStatus.style.color = "#ef4444";

            minValueText.innerText = d.min + " px";
            maxValueText.innerText = d.max + " px";

            showToast("Calibration reset");
        });
};

// DEFAULT
defaultCalBtn.onclick = () => {
    clearInterval(reminderInterval);

    fetch("/calibration/default")
        .then(r => r.json())
        .then(d => {
            startCalBtn.disabled = false;
            calibrationBadge.classList.add("hidden");

            calibrationStatus.innerText =
                `System default applied (MIN=${d.min}px, MAX=${d.max}px)`;
            calibrationStatus.style.color = "#22c55e";

            minValueText.innerText = d.min + " px";
            maxValueText.innerText = d.max + " px";

            showToast("System default restored");
        });
};

/* ================= GRAPH ================= */
const ctx = document.getElementById("volChart").getContext("2d");
const chart = new Chart(ctx, {
    type: "line",
    data: { labels: [], datasets: [{ data: [], borderColor: "#3b82f6", borderWidth: 2, tension: 0.35, pointRadius: 0 }] },
    options: { responsive: true, maintainAspectRatio: false, animation: false, scales: { y: { min: 0, max: 100 } }, plugins: { legend: { display: false } } }
});

let idx = 0;
const MAX_POINTS = 120;

/* ================= LOOP ================= */
function updateData() {
    fetch("/data").then(r => r.json()).then(d => {

        /* ---------- TEXT METRICS ---------- */
        distanceText.innerText = d.distance + " px";
        volumeText.innerText = d.volume + "%";
        volumeMetric.innerText = d.volume + "%";

        minValueText.innerText = d.min + " px";
        maxValueText.innerText = d.max + " px";

        /* ---------- VOLUME STATE ---------- */
        /* ---------- VOLUME STATE BADGE ---------- */
volumeState.className = "volume-badge";

if (d.volume === 0) {
    volumeState.innerText = "Muted";
    volumeState.classList.add("muted");
}
else if (d.volume < 35) {
    volumeState.innerText = "Low";
    volumeState.classList.add("low");
}
else if (d.volume < 70) {
    volumeState.innerText = "Medium";
    volumeState.classList.add("medium");
}
else {
    volumeState.innerText = "High";
    volumeState.classList.add("high");
}


        /* ---------- DISTANCE VISUAL BAR ---------- */
        let percent = 0;
        if (d.max > d.min) {
            percent = ((d.distance - d.min) / (d.max - d.min)) * 100;
            percent = Math.max(0, Math.min(100, percent));
        }
        distanceFill.style.width = percent + "%";

        /* ---------- FPS ---------- */
        const now = performance.now();
        fpsText.innerText = Math.round(1000 / (now - lastTime));
        lastTime = now;

        /* ---------- GRAPH ---------- */
        chart.data.labels.push(idx++);
        chart.data.datasets[0].data.push(d.volume);

        if (chart.data.labels.length > MAX_POINTS) {
            chart.data.labels.shift();
            chart.data.datasets[0].data.shift();
        }

        chart.update();
    });
}

setInterval(updateData, 150);
updateData();

/* ================= END ================= */