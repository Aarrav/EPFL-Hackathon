#include <WiFi.h>
#include <ESPAsyncWebServer.h>
#include <AsyncTCP.h>

#ifndef WIFI_SSID
#define WIFI_SSID "YOUR_WIFI_SSID"
#endif

#ifndef WIFI_PASSWORD
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"
#endif

// WiFi credentials are supplied by PlatformIO build flags.
const char* ssid = WIFI_SSID;
const char* password = WIFI_PASSWORD;

// ── Pin ───────────────────────────────────────────
#define HALL_SENSOR_PIN 4

// ── WebSocket server ──────────────────────────────
AsyncWebServer server(80);
AsyncWebSocket ws("/ws");

// ── State ─────────────────────────────────────────
int  counter        = 0;
bool magnetDetected = false;
bool lastState      = false;   // tracks previous sensor state
unsigned long lastTriggerTime = 0;
const unsigned long COOLDOWN_MS = 15000;

// ── WebSocket event handler ───────────────────────
void onWsEvent(AsyncWebSocket* server, AsyncWebSocketClient* client,
               AwsEventType type, void* arg, uint8_t* data, size_t len) {
  if (type == WS_EVT_CONNECT) {
    Serial.printf("Client #%u connected\n", client->id());
    // Send current state immediately on connect
    String json = buildJson();
    client->text(json);
  } else if (type == WS_EVT_DISCONNECT) {
    Serial.printf("Client #%u disconnected\n", client->id());
  }
}

// ── Build JSON payload ────────────────────────────
String buildJson() {
  String json = "";
  json += "{";
  json += "\"count\":"    + String(counter);
  json += ",\"plucked\":" + String(magnetDetected ? "true" : "false");
  json += ",\"cooldown\":" + String(millis() - lastTriggerTime);
  json += "}";
  return json;
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  pinMode(HALL_SENSOR_PIN, INPUT);

  // ── Connect to WiFi ──
  Serial.print("Connecting to WiFi");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected! IP: " + WiFi.localIP().toString());

  // ── Start WebSocket ──
  ws.onEvent(onWsEvent);
  server.addHandler(&ws);
  server.begin();
  Serial.println("WebSocket server started on ws://" + WiFi.localIP().toString() + "/ws");
}

void loop() {
  int  sensorState    = digitalRead(HALL_SENSOR_PIN);
  bool currentMagnet  = (sensorState == HIGH);   // LOW = magnet present (A3144/KY-003)
  unsigned long now   = millis();

  // ── Detect a fresh LOW transition ────────────────
  // Triggers only on the FALLING edge (moment magnet arrives)
  // AND only if 5 seconds have passed since the last count
  if (currentMagnet && !lastState) {
    if (now - lastTriggerTime >= COOLDOWN_MS) {
      counter++;
      lastTriggerTime = now;
      Serial.printf("Magnet detected! Count: %d\n", counter);
    } else {
      unsigned long remaining = (COOLDOWN_MS - (now - lastTriggerTime)) / 1000;
      Serial.printf("Cooldown active - %lus remaining, count ignored\n", remaining);
    }
  }

  // ── Update state ──────────────────────────────────
  magnetDetected = currentMagnet;
  lastState      = currentMagnet;

  if (currentMagnet) {
    Serial.println("Magnet Detected");
  } else {
    Serial.println("No Magnet");
  }

  // ── Broadcast to all connected browsers ──────────
  if (ws.count() > 0) {
    ws.textAll(buildJson());
  }

  ws.cleanupClients();
  delay(200);
}
