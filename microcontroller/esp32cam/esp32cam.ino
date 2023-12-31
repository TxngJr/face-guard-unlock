#include <Arduino.h>
#include <WiFi.h>
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"
#include "esp_camera.h"

const char* ssid = "@UTC_WiFi";
const char* password = "";
const char* serverName = "nodered.utc.ac.th";
const int serverPort = 3000;

WiFiClient client;

#define PWDN_GPIO_NUM 32
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 0
#define SIOD_GPIO_NUM 26
#define SIOC_GPIO_NUM 27
#define Y9_GPIO_NUM 35
#define Y8_GPIO_NUM 34
#define Y7_GPIO_NUM 39
#define Y6_GPIO_NUM 36
#define Y5_GPIO_NUM 21
#define Y4_GPIO_NUM 19
#define Y3_GPIO_NUM 18
#define Y2_GPIO_NUM 5
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM 23
#define PCLK_GPIO_NUM 22

#define RELAY_PIN 12
#define IR 13
#define BUZZER_PIN 2

const int timerInterval = 1000;
unsigned long previousMillis = 0;

void setup() {
  pinMode(RELAY_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(IR, INPUT);

  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);
  Serial.begin(115200);

  WiFi.mode(WIFI_STA);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    Serial.print(".");
    delay(500);
  }
  Serial.println();
  Serial.print("ESP32-CAM IP Address: ");
  Serial.println(WiFi.localIP());

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

  if (psramFound()) {
    config.frame_size = FRAMESIZE_SVGA;
    config.jpeg_quality = 10;
    config.fb_count = 2;
  } else {
    config.frame_size = FRAMESIZE_CIF;
    config.jpeg_quality = 12;
    config.fb_count = 1;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    delay(1000);
    ESP.restart();
  }
}

void loop() {
  // unsigned long currentMillis = millis();
  if (!digitalRead(IR)) {
    
    bool checkStatus = sendPhoto();
    // Serial.println(checkStatus);
    if (checkStatus) {
      digitalWrite(RELAY_PIN, HIGH);
      tone(BUZZER_PIN, 1000, 1000);
      delay(1000);
      digitalWrite(BUZZER_PIN, LOW);
      delay(4000);
      digitalWrite(RELAY_PIN, LOW);
    }
    // previousMillis = currentMillis;
  } else {
    digitalWrite(RELAY_PIN, LOW);
  }
}

bool sendPhoto() {
  bool checkStatus = false;
  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Camera capture failed");
    delay(1000);
    ESP.restart();
  }

  Serial.println("Connecting to server: " + String(serverName));

  if (client.connect(serverName, serverPort)) {
    Serial.println("Connection successful!");
    String head = "--Boundary\r\nContent-Disposition: form-data; name=\"imageFile\"; filename=\"esp32-cam.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n";
    String tail = "\r\n--Boundary--\r\n";

    uint32_t imageLen = fb->len;
    uint32_t extraLen = head.length() + tail.length();
    uint32_t totalLen = imageLen + extraLen;

    client.println("POST /check_face_api HTTP/1.1");
    client.println("Host: " + String(serverName));
    client.println("Content-Length: " + String(totalLen));
    client.println("Content-Type: multipart/form-data; boundary=Boundary");
    client.println();
    client.print(head);

    uint8_t* fbBuf = fb->buf;
    size_t fbLen = fb->len;
    size_t bytesSent = 0;

    while (bytesSent < fbLen) {
      size_t bytesToWrite = min(static_cast<size_t>(1024), fbLen - bytesSent);
      client.write(fbBuf + bytesSent, bytesToWrite);
      bytesSent += bytesToWrite;
    }

    client.print(tail);

    esp_camera_fb_return(fb);

    int timeoutTimer = 1500;
    long startTimer = millis();
    String responseHeader = "";

    while ((startTimer + timeoutTimer) > millis()) {
      Serial.print(".");
      delay(100);
      while (client.available()) {
        char c = client.read();
        // Serial.print(c);
        responseHeader += c;
        startTimer = millis();
      }
    }

    bool statusCode = responseHeader.indexOf("HTTP/1.0 200 OK") != -1;


    if (statusCode) {
      Serial.println("Request successful!");
      checkStatus = true;
    } else {
      Serial.println("Invalid HTTP response");
    }
    client.stop();
  } else {
    Serial.println("Connection to " + String(serverName) + " failed.");
  }
  return checkStatus;
}
