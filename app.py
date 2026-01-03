from flask import Flask, render_template, Response, jsonify
import cv2
import mediapipe as mp
import numpy as np
from math import hypot
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from collections import deque

# ================= APP =================
app = Flask(__name__, static_folder="static", template_folder="templates")

# ================= CAMERA =================
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
if not cap.isOpened():
    raise RuntimeError("❌ Camera not accessible")

# ================= STATE =================
latest_distance = 0
latest_volume = 0
calibration_active = False

APP_MIN = 20
APP_MAX = 200
min_gesture_dist = APP_MIN
max_gesture_dist = APP_MAX

# ================= MEDIAPIPE =================
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)
mp_draw = mp.solutions.drawing_utils

# ================= SYSTEM VOLUME =================
devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(
    IAudioEndpointVolume._iid_,
    CLSCTX_ALL,
    None
)
volume = cast(interface, POINTER(IAudioEndpointVolume))
min_vol, max_vol, _ = volume.GetVolumeRange()

# ================= SMOOTHING =================
volume_history = deque(maxlen=5)

# ================= VIDEO STREAM =================
def generate_frames():
    global latest_distance, latest_volume
    global calibration_active, min_gesture_dist, max_gesture_dist

    while True:
        success, img = cap.read()
        if not success:
            continue

        img = cv2.flip(img, 1)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = hands.process(img_rgb)


        raw_distance = 0
        vol_percent = 0

        if results.multi_hand_landmarks:
            hl = results.multi_hand_landmarks[0]

            # Draw landmarks FIRST
            mp_draw.draw_landmarks(img, hl, mp_hands.HAND_CONNECTIONS)

            h, w, _ = img.shape
            lm = hl.landmark

            # Thumb & Index
            x1, y1 = int(lm[4].x * w), int(lm[4].y * h)
            x2, y2 = int(lm[8].x * w), int(lm[8].y * h)

            # Distance
            raw_distance = int(hypot(x2 - x1, y2 - y1))

            # ================= VISUALS (MJPEG SAFE) =================
           
            cv2.line(img, (x1, y1), (x2, y2), (0, 0, 255), 6)  # RED LINE
            cv2.circle(img, (x1, y1), 10, (255, 255, 0), cv2.FILLED)
            cv2.circle(img, (x2, y2), 10, (255, 255, 0), cv2.FILLED)

            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            cv2.circle(img, (cx, cy), 6, (0, 0, 255), cv2.FILLED)

            cv2.putText(
                img,
                f"{raw_distance}px",
                (cx - 40, cy - 15),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2
            )

            # ================= CALIBRATION =================
            if calibration_active:
                min_gesture_dist = min(min_gesture_dist, raw_distance)
                max_gesture_dist = max(max_gesture_dist, raw_distance)

            # ================= VOLUME MAPPING =================
            if min_gesture_dist < max_gesture_dist:
                mapped = np.clip(
                    raw_distance,
                    min_gesture_dist,
                    max_gesture_dist
                )

                raw_volume = np.interp(
                    mapped,
                    [min_gesture_dist, max_gesture_dist],
                    [min_vol, max_vol]
                )

                volume_history.append(raw_volume)
                smooth_volume = sum(volume_history) / len(volume_history)

                volume.SetMasterVolumeLevel(smooth_volume, None)

                vol_percent = int(np.interp(
                    smooth_volume,
                    [min_vol, max_vol],
                    [0, 100]
                ))

        latest_distance = raw_distance
        latest_volume = vol_percent

        ret, buffer = cv2.imencode(".jpg", img)
        frame = buffer.tobytes()

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
        )

# ================= ROUTES =================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/video")
def video():
    return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache"}
    )

@app.route("/data")
def data():
    return jsonify({
        "distance": latest_distance,
        "volume": latest_volume,
        "calibrating": calibration_active,
        "min": min_gesture_dist,
        "max": max_gesture_dist
    })

# ================= CALIBRATION ROUTES =================
@app.route("/calibration/custom/start")
def calibration_start():
    global calibration_active, min_gesture_dist, max_gesture_dist
    calibration_active = True
    min_gesture_dist = 999
    max_gesture_dist = 0
    volume_history.clear()
    return jsonify({"status": "started"})

@app.route("/calibration/custom/stop")
def calibration_stop():
    global calibration_active
    calibration_active = False
    return jsonify({
        "status": "stopped",
        "min": min_gesture_dist,
        "max": max_gesture_dist
    })

@app.route("/calibration/custom/reset")
def calibration_reset():
    global calibration_active, min_gesture_dist, max_gesture_dist
    calibration_active = False
    min_gesture_dist = APP_MIN
    max_gesture_dist = APP_MAX
    volume_history.clear()
    return jsonify({"status": "reset", "min": min_gesture_dist, "max": max_gesture_dist})

@app.route("/calibration/default")
def calibration_default():
    global calibration_active, min_gesture_dist, max_gesture_dist
    calibration_active = False
    min_gesture_dist = APP_MIN
    max_gesture_dist = APP_MAX
    volume_history.clear()
    return jsonify({"status": "default", "min": min_gesture_dist, "max": max_gesture_dist})

# ================= MAIN =================
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
