#include <WiFi.h>
#include <WebSocketsServer.h>
#include <ArduinoJson.h>
#include <Ticker.h>

// ==== CONFIGURACIÓN WiFi ====
const char* ssid = "Prueba_G4";
const char* password = "grupo4<>";

// ==== CONFIGURACIÓN WebSocket ====
WebSocketsServer webSocket(81);
bool measuring = false;

// ==== CONFIGURACIÓN DE PINES ====
const int PIN_32 = 39;  // Entrada analógica 1
const int PIN_35 = 35;  // Entrada analógica 2
const int LED_BUILTIN = 2;  // LED integrado

// ==== TICKER PARA MEDICIÓN ====
Ticker measurementTicker;
const float measurementIntervalSec = 0.1; // 100 ms

// ==== TIEMPOS ====
unsigned long measurementStartTime = 0;
unsigned long measurementDuration = 10000; // en milisegundos

// ==== PROTOTIPOS ====
void setupWiFi();
void setupWebSocket();
void actualizarWebSocket();
void webSocketEvent(uint8_t, WStype_t, uint8_t*, size_t);
void startMeasurement(int durationSeconds);
void stopMeasurement();
void performMeasurement();
void sendResponse(uint8_t clientNum, const char* type, const char* message);

void setup() {
  Serial.begin(115200);

  // Pines
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);
  pinMode(PIN_32, INPUT);
  pinMode(PIN_35, INPUT);

  // Iniciar módulos
  setupWiFi();
  setupWebSocket();
}

void loop() {
  actualizarWebSocket();

  // Verificar si terminó el tiempo de medición
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

// ==== LÓGICA DE MEDICIÓN ====
void startMeasurement(int durationSeconds) {
  measuring = true;
  measurementStartTime = millis();
  measurementDuration = durationSeconds * 1000;
  digitalWrite(LED_BUILTIN, HIGH);
  Serial.printf("🟢 Iniciando mediciones por %d segundos...\n", durationSeconds);

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

// ==== FUNCIÓN MODIFICADA ====
void performMeasurement() {
  // Lectura con delay de 100µs entre mediciones
  int value32 = analogRead(PIN_32);
  delayMicroseconds(100); // Delay agregado aquí
  int value35 = analogRead(PIN_35);

  DynamicJsonDocument doc(200);
  doc["type"] = "measurement";
  doc["pin32"] = value32;
  doc["pin35"] = value35;
  doc["timestamp"] = millis();

  String response;
  serializeJson(doc, response);
  webSocket.broadcastTXT(response);

  // Debug por serial
  Serial.printf("Pin32: %d, Pin35: %d\n", value32, value35);
}

void sendResponse(uint8_t clientNum, const char* type, const char* message) {
  DynamicJsonDocument doc(200);
  doc["type"] = type;
  doc["message"] = message;

  String response;
  serializeJson(doc, response);
  webSocket.sendTXT(clientNum, response);
}