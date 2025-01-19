# License Plate Recognition with ESP32-CAM

This project allows you to use the **ESP32-CAM module** to detect vehicle license plates, process the images on a Flask server, and display the results on a mobile application or browser.

### **Features**
- **License Plate Detection:** The **ESP32-CAM module** captures images of vehicle license plates.
- **Image Processing:** The captured images are sent to a **Flask server**, where OCR is applied to extract the license plate text.
- **Display on Mobile:** The license plate images are displayed in real-time via WebSocket in a mobile application or browser.
- **LED Control:** The connected **ESP32** LED can be toggled via WebSocket or HTTP requests.

### **Project Structure**
- **ESP32-CAM:** The camera module used for capturing images and sending them to the server.
- **Flask Server:** The Flask server processes the incoming requests, handles image data, and controls the LED status.
- **WebSocket:** Used to display the real-time updates to the mobile application or browser.

### **Prerequisites**
- **ESP32-CAM Module:** The ESP32 camera module.
- **Arduino IDE:** Used for programming the ESP32 module.
- **Flask:** For creating the image processing server.
- **OpenCV:** For image processing and license plate detection.
- **Tesseract OCR:** For extracting text from images.

### **Installation and Setup**

#### **1. Install Dependencies**
To install the necessary dependencies for the Flask server, run the following command:
```bash
pip install flask opencv-python requests

