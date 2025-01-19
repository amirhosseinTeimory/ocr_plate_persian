#include <WiFi.h>
#include "esp_camera.h"
#include <WebServer.h> // برای ایجاد سرور HTTP

#define CAMERA_MODEL_AI_THINKER
#include "camera_pins.h"

// اطلاعات Wi-Fi
const char* ssid = "Amir's A23";           // نام وای‌فای
const char* password = "amir1397";          // رمز عبور وای‌فای

const char* serverName = "192.168.135.49";   // آدرس سرور (IP سیستم میزبان)
const int serverPort = 5000;   
// شماره پین LED (LED داخلی ESP32-CAM)
#define LED_PIN 4

// ایجاد سرور HTTP روی پورت 80
WebServer server(80);

// تنظیمات دوربین
void initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_QVGA;
  config.jpeg_quality = 12;
  config.fb_count = 1;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x\n", err);
    ESP.restart();
  } else {
    Serial.println("Camera initialized successfully!");
  }
}

// مسیر کنترل LED
void handleLedControl() {
  if (server.hasArg("state")) { // بررسی وجود پارامتر "state"
    String state = server.arg("state");
    if (state == "on") {
      digitalWrite(LED_PIN, HIGH); // روشن کردن LED
      server.send(200, "text/plain", "LED is ON");
    } else if (state == "off") {
      digitalWrite(LED_PIN, LOW); // خاموش کردن LED
      server.send(200, "text/plain", "LED is OFF");
    } else {
      server.send(400, "text/plain", "Invalid state");
    }
  } else {
    server.send(400, "text/plain", "Missing state parameter");
  }
}

void setup() {
  Serial.begin(115200);

  // اتصال به Wi-Fi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected!");

  // تنظیمات LED
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW); // پیش‌فرض خاموش

  // تنظیمات دوربین
  initCamera();

  // تعریف مسیر کنترل LED
  server.on("/control_led", handleLedControl);

  // شروع سرور
  server.begin();
  Serial.println("HTTP server started");
}

void loop() {
  // پردازش درخواست‌های HTTP
  server.handleClient();

  // گرفتن تصویر و ارسال به سرور (کد فعلی شما بدون تغییر)
  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Camera capture failed");
    delay(1000);
    return;
  }

  // ایجاد اتصال به سرور
  WiFiClient client;
  if (client.connect(serverName, serverPort)) { // استفاده از WiFiClient برای HTTP
    Serial.println("Connected to server, sending image...");

    // ساخت درخواست HTTP POST
    String head = "--boundary\r\nContent-Disposition: form-data; name=\"image\"; filename=\"image.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n";
    String tail = "\r\n--boundary--\r\n";

    client.println("POST /upload HTTP/1.1");
    client.println("Host: " + String(serverName));
    client.println("Content-Type: multipart/form-data; boundary=boundary");
    client.println("Content-Length: " + String(head.length() + tail.length() + fb->len));
    client.println();
    client.print(head);
    client.write(fb->buf, fb->len); // ارسال داده‌های تصویر
    client.print(tail);

    // دریافت پاسخ سرور
    while (client.connected()) {
      String response = client.readString();
      Serial.println("Response from server: " + response);
      break;
    }

    client.stop(); // پایان اتصال
  } else {
    Serial.println("Failed to connect to server");
  }

  esp_camera_fb_return(fb); // بازگرداندن بافر تصویر
  delay(5000); // فاصله زمانی بین ارسال‌ها
}
