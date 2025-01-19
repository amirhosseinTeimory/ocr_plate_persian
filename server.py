import os
import cv2
import numpy as np
from flask import Flask, request, jsonify, send_from_directory
import requests
from datetime import datetime
import json
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app)

# Configuration
OCR_API_URL = "https://www.eboo.ir/api/ocr/getway"
USER_TOKEN = "XtPn2XoQL0t7XYKo7rZ3omkrqKeIeSgJ"
MIN_AREA = 1500
MIN_ASPECT_RATIO = 2.5
MAX_ASPECT_RATIO = 5.0
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ESP32-CAM LED Control
# http://192.168.1.100/control_led
ESP32_CAM_LED_URL = "http://192.168.135.194/control_led"

@app.route('/toggle_led', methods=['POST'])
def toggle_led():
    data = request.get_json()
    if not data or "state" not in data:
        return jsonify({"error": "Invalid request"}), 400

    led_state = data["state"]  # "on" یا "off"
    try:
        # ارسال درخواست به ESP32 برای تغییر وضعیت LED
        response = requests.get(f"{ESP32_CAM_LED_URL}?state={led_state}")
        if response.status_code == 200:
            return jsonify({"message": "LED state updated successfully"}), 200
        else:
            return jsonify({"error": "Failed to update LED state"}), 500
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

# Error logging
def log_error(step, error_message):
    print(f"⚠ {step} - {error_message}")

# Notify clients via WebSocket
def notify_android(plate_text, image_url):
    try:
        socketio.emit('new_plate', {
            'plate_text': plate_text,  # متن پلاک پاکسازی‌شده
            'image_url': image_url     # URL تصویر
        })
        print(f"🟢 JSON Sent to Mobile: {plate_text}")
    except Exception as e:
        log_error("WebSocket", str(e))



# Function to detect license plate with extended crop area
def detect_license_plate(image, margin=20):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    for contour in contours:
        if cv2.contourArea(contour) > MIN_AREA:
            approx = cv2.approxPolyDP(contour, 0.02 * cv2.arcLength(contour, True), True)
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(approx)
                aspect_ratio = w / float(h)
                if MIN_ASPECT_RATIO < aspect_ratio < MAX_ASPECT_RATIO:
                    # Add margin to the crop
                    x_start = max(0, x - margin)
                    y_start = max(0, y - margin)
                    x_end = min(image.shape[1], x + w + margin)
                    y_end = min(image.shape[0], y + h + margin)
                    
                    # Crop with margin
                    plate = image[y_start:y_end, x_start:x_end]
                    return plate
    return None

# Upload image to OCR API
def upload_file(file_path):
    if not os.path.exists(file_path):
        log_error("Upload", f"File not found: {file_path}")
        return None

    try:
        with open(file_path, "rb") as file:
            upload = {'filehandle': (file_path, file, 'multipart/form-data')}
            payload = {"token": USER_TOKEN, "command": "addfile"}
            
            # اضافه کردن تایم‌اوت به درخواست
            response = requests.post(OCR_API_URL, data=payload, files=upload, timeout=10)

            if response.status_code == 200:
                try:
                    data = response.json()
                    print("🟢 Upload Successful:", data)

                    # بررسی وجود FileToken در پاسخ
                    file_token = data.get("FileToken")
                    if not file_token:
                        log_error("Upload", "FileToken not returned by API")
                        return None
                    return file_token
                except json.JSONDecodeError:
                    log_error("Upload", "Invalid JSON response from API")
            else:
                log_error("Upload", f"HTTP {response.status_code} - {response.text}")
    except requests.exceptions.Timeout:
        log_error("Upload", "Request timed out")
    except requests.exceptions.RequestException as e:
        log_error("Upload", f"Request error: {e}")
    except Exception as e:
        log_error("Upload", f"Unexpected error: {e}")
    return None



# Convert file to extract text
def process_extracted_text(raw_text):
    # حذف کاراکترهای اضافی مانند \r و \n
    cleaned_text = raw_text.replace("\r", "").replace("\n", " ").strip()
    return cleaned_text

def convert_file(file_token):
    try:
        payload = {
            "token": USER_TOKEN,
            "command": "convert",
            "filetoken": file_token,
            "method": 4,  # OCR text extraction
            "output": "txtrawjson"  # دریافت خروجی به صورت JSON
        }
        response = requests.post(OCR_API_URL, data=payload)

        print("🔍 Raw Convert Response (JSON):", response.text)

        if response.status_code == 200:
            try:
                response_data = response.json()
                if response_data.get("Status") == "Done":
                    # پاکسازی متن استخراج‌شده
                    cleaned_text = process_extracted_text(response_data.get("Text", ""))
                    return cleaned_text
                else:
                    log_error("Convert", "Conversion not completed by API.")
                    return None
            except json.JSONDecodeError:
                log_error("Convert", "Invalid JSON response from API")
                return None
        else:
            log_error("Convert", f"HTTP Error: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        log_error("Convert", f"Request error: {e}")
        return None



# API Routes
@app.route('/upload', methods=['POST'])
def upload():
    if 'image' not in request.files:
        return jsonify({"status": "error", "message": "No image file provided"}), 400

    file = request.files['image']
    if not file or file.filename == '':
        return jsonify({"status": "error", "message": "Invalid or missing file"}), 400

    # ذخیره فایل تصویر
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)
    print(f"🟢 Image saved at {file_path}")

    # پردازش تصویر برای تشخیص پلاک
    image = cv2.imread(file_path)
    if image is None:
        log_error("Upload", "Failed to read uploaded image")
        return jsonify({"status": "error", "message": "Failed to read uploaded image"}), 400

    plate = detect_license_plate(image, margin=20)
    if plate is not None:
        # ذخیره تصویر تشخیص داده‌شده
        plate_filename = f"plate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        plate_path = os.path.join(UPLOAD_FOLDER, plate_filename)
        cv2.imwrite(plate_path, plate)
        print(f"🟢 Plate detected and saved at {plate_path}")

        # ارسال لینک تصویر به کلاینت
        image_url = f"http://{request.host}:5000/uploads/{os.path.basename(plate_path)}"

        # ارسال اطلاعات اولیه به کلاینت
        notify_android("Processing...", image_url)

        # پردازش OCR به صورت آسنکرون
        file_token = upload_file(plate_path)
        if file_token:
            extracted_text = convert_file(file_token)
            if extracted_text:
                notify_android(extracted_text, image_url)
                return jsonify({"status": "success", "image_url": image_url}), 200

        return jsonify({"status": "error", "message": "OCR failed"}), 500
    else:
        return jsonify({"status": "error", "message": "No plate detected"}), 400

@socketio.on('connect')
def handle_connect():
    print("🟢 Client connected")

@app.route('/status', methods=['GET'])
def status():
    return jsonify({"status": "Server is running"}), 200

@app.route('/uploads/<filename>', methods=['GET'])
def uploaded_file(filename):
    # سرو کردن فایل‌های ذخیره‌شده در پوشه uploads
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
