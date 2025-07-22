#include <WiFi.h>
#include <WebSocketsServer.h>
#include <ArduinoJson.h>
#include <Ticker.h>

// ==== CONFIGURACIÓN WiFi ====
const char* ssid = "CamiS";
const char* password = "camilacamila";

// ==== CONFIGURACIÓN WebSocket ====
WebSocketsServer webSocket(81);
bool measuring = false;

// ==== CONFIGURACIÓN DE PINES ====
const int PIN_32 = 33;
const int PIN_35 = 35;
const int LED_BUILTIN = 2;

// ==== TICKER PARA MEDICIÓN ====
Ticker measurementTicker;
const float measurementIntervalSec = 0.005; // ~60 Hz

// ==== SUAVIZADO ====
const int windowSize = 20;
int buffer32[windowSize] = {0};
int buffer35[windowSize] = {0};
int bufferIndex = 0;

// ==== TIEMPOS ====
unsigned long measurementStartTime = 0;
unsigned long measurementDuration = 10000;

// ==== PROTOTIPOS ====
void setupWiFi();
void setupWebSocket();
void actualizarWebSocket();
void webSocketEvent(uint8_t num, WStype_t type, uint8_t * payload, size_t length);
void startMeasurement(int durationSeconds);
void stopMeasurement();
void performMeasurement();
void sendResponse(uint8_t clientNum, const char* type, const char* message);
int movingAverage(int* buffer);

// ==== SETUP ====
void setup() {
  Serial.begin(115200);

  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);
  pinMode(PIN_32, INPUT);
  pinMode(PIN_35, INPUT);

  setupWiFi();
  setupWebSocket();
}

// ==== LOOP ====
void loop() {
  actualizarWebSocket();

  if (measuring && millis() - measurementStartTime >= measurementDuration) {
    stopMeasurement();
  }
}

// ==== WiFi ====
void setupWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  Serial.print("Conectando a WiFi");
  int retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries < 20) {
    delay(500);
    Serial.print(".");
    retries++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.print("✅ Conectado! IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n❌ No se pudo conectar al WiFi.");
  }
}

// ==== WebSocket ====
void setupWebSocket() {
  webSocket.begin();
  webSocket.onEvent(webSocketEvent);
  Serial.println("🛰️ WebSocket iniciado en puerto 81");
  Serial.printf("Conectarse a: ws://%s:81\n", WiFi.localIP().toString().c_str());
}

void actualizarWebSocket() {
  webSocket.loop();
}

void webSocketEvent(uint8_t num, WStype_t type, uint8_t * payload, size_t length) {
  switch(type) {
    case WStype_DISCONNECTED:
      Serial.printf("Cliente [%u] desconectado\n", num);
      if (measuring) stopMeasurement();
      break;

    case WStype_CONNECTED: {
      IPAddress ip = webSocket.remoteIP(num);
      Serial.printf("Cliente [%u] conectado desde %s\n", num, ip.toString().c_str());
      sendResponse(num, "status", "Conectado a ESP32");
      break;
    }

    case WStype_TEXT: {
      DynamicJsonDocument doc(200);
      DeserializationError err = deserializeJson(doc, payload);
      if (err) {
        sendResponse(num, "error", "JSON inválido");
        return;
      }

      String action = doc["action"];
      if (action == "start_measurement") {
        int duration = doc.containsKey("duration") ? doc["duration"] : 10;
        startMeasurement(duration);
        sendResponse(num, "status", "Mediciones iniciadas");
      } else if (action == "stop_measurement") {
        stopMeasurement();
        sendResponse(num, "status", "Mediciones detenidas");
      } else {
        sendResponse(num, "error", "Comando no reconocido");
      }
      break;
    }
    default:
      break;
  }
}

// ==== MEDICIÓN ====
void startMeasurement(int durationSeconds) {
  measuring = true;
  measurementStartTime = millis();
  measurementDuration = durationSeconds * 1000;
  digitalWrite(LED_BUILTIN, HIGH);
  Serial.printf("🟢 Iniciando mediciones por %d segundos...\n", durationSeconds);

  // Resetear buffers
  for (int i = 0; i < windowSize; i++) {
    buffer32[i] = 0;
    buffer35[i] = 0;
  }
  bufferIndex = 0;

  measurementTicker.attach(measurementIntervalSec, performMeasurement);
}

void stopMeasurement() {
  measuring = false;
  digitalWrite(LED_BUILTIN, LOW);
  Serial.println("🔴 Mediciones detenidas.");

  measurementTicker.detach();

  DynamicJsonDocument doc(200);
  doc["type"] = "measurement_finished";
  doc["message"] = "Mediciones completadas";

  String response;
  serializeJson(doc, response);
  webSocket.broadcastTXT(response);
}

void performMeasurement() {
  int value32 = analogRead(PIN_32);
  delayMicroseconds(100);
  int value35 = analogRead(PIN_35);

  // Guardar en buffers circulares
  buffer32[bufferIndex] = value32;
  buffer35[bufferIndex] = value35;
  bufferIndex = (bufferIndex + 1) % windowSize;

  // Calcular promedio móvil
  int avg32 = movingAverage(buffer32);
  int avg35 = movingAverage(buffer35);

  DynamicJsonDocument doc(200);
  doc["type"] = "measurement";
  doc["pin32"] = avg32;
  doc["pin35"] = avg35;
  doc["timestamp"] = millis();

  String response;
  serializeJson(doc, response);
  webSocket.broadcastTXT(response);

  Serial.printf("Pin32: %d, Pin35: %d\n", avg32, avg35);
}

int movingAverage(int* buffer) {
  long sum = 0;
  for (int i = 0; i < windowSize; i++) {
    sum += buffer[i];
  }
  return sum / windowSize;
}

void sendResponse(uint8_t clientNum, const char* type, const char* message) {
  DynamicJsonDocument doc(200);
  doc["type"] = type;
  doc["message"] = message;

  String response;
  serializeJson(doc, response);
  webSocket.sendTXT(clientNum, response);
}
