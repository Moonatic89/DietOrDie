/*
  DietOrDie - ESP32 Cyclette Sensor Firmware (Adaptive Dual MQTT + HTTPS)
  =======================================================================
  Telemetria in tempo reale non bloccante.
  - Invia via MQTT se la porta 1883 è raggiungibile.
  - Altrimenti usa il fallback automatico HTTPS POST a /api/rides/esp32 (porta 443).
  - Stampa in tempo reale ogni singolo giro di pedale sulla porta seriale.
*/

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <PubSubClient.h>

// ================= CONFIGURAZIONE WI-FI =================
const char* WIFI_SSID        = "Naminatic ";
const char* WIFI_PASSWORD    = "LaCasaDiBrandino";

// ================= CONFIGURAZIONE SERVER =================
const char* SERVER_HOST      = "dietordie.duckdns.org";
const int   MQTT_PORT        = 1883;
const char* MQTT_TOPIC       = "dietordie/telemetry";
const char* ESP32_API_KEY    = "esp32-dietordie-secret-token";

// ================= PIN HARDWARE =================
#if defined(CONFIG_IDF_TARGET_ESP32C6)
  constexpr int REED_PIN       = 4;  // Pin sensore reed (GPIO 4 su ESP32-C6)
  constexpr int USER_SW_PIN    = 9;  // Tasto BOOT su ESP32-C6 (GPIO 9)
  constexpr int LED_STATUS_PIN = 8;
#elif defined(CONFIG_IDF_TARGET_ESP32S3)
  constexpr int REED_PIN       = 38; // Pin sensore reed su ESP32-S3
  constexpr int USER_SW_PIN    = 0;  // Tasto BOOT su ESP32-S3
  constexpr int LED_STATUS_PIN = 2;
#else
  constexpr int REED_PIN       = 4;  // Pin sensore reed generico
  constexpr int USER_SW_PIN    = 0;
  constexpr int LED_STATUS_PIN = 2;
#endif

// ================= PARAMETRI CYCLETTE =================
constexpr float METERS_PER_PULSE       = 5.30f; // 5.30 metri virtuali per giro di pedale
constexpr uint32_t REED_DEBOUNCE_US    = 8000;  // 8 ms antirimbalzo
constexpr uint32_t SEND_INTERVAL_MS    = 3000;  // Invio dati ogni 3 secondi durante la pedalata
constexpr uint32_t STOP_TIMEOUT_MS     = 3500;  // Velocità scende a 0 dopo 3.5s senza impulsi
constexpr uint32_t FINISH_TIMEOUT_MS   = 60000; // Fine sessione dopo 60s di inattività

// Utenti supportati
const char* USERS[] = {"mario", "anna"};
int currentUserIndex = 0; // 0 = Mario, 1 = Anna
int resistanceLevel = 8;  // Resistenza 1-8 (default 8 come cyclette.ino)

// ================= STATO INTERNO =================
WiFiClient espClient;
PubSubClient mqttClient(espClient);
WiFiClientSecure secureClient;

volatile uint32_t pulseCount = 0;
volatile uint32_t lastPulseMicros = 0;
volatile uint32_t prevPulseMicros = 0;

uint32_t lastPulseSnapshot = 0;
uint32_t lastSendMs = 0;
uint32_t lastActivityMs = 0;
uint32_t sessionStartMs = 0;
bool isSessionActive = false;
String currentSessionUid = "";
bool mqttAvailable = false;

// Interrupt sensore Reed
void IRAM_ATTR onReedPulse() {
  const uint32_t now = micros();
  if (now - lastPulseMicros >= REED_DEBOUNCE_US) {
    prevPulseMicros = lastPulseMicros;
    lastPulseMicros = now;
    pulseCount++;
  }
}

String generateSessionUid() {
  return String(USERS[currentUserIndex]) + "_" + String(millis()) + "_" + String(random(1000, 9999));
}

void setupWifi() {
  Serial.print("Connessione Wi-Fi a '");
  Serial.print(WIFI_SSID);
  Serial.print("'");
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 10000) {
    delay(400);
    Serial.print(".");
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\n[WI-FI OK] IP assegnato: %s\n", WiFi.localIP().toString().c_str());
  } else {
    Serial.println("\n[WI-FI WAIT] Connessione in corso in background...");
  }
}

void tryMqttConnect() {
  static uint32_t lastMqttCheck = 0;
  if (WiFi.status() != WL_CONNECTED) return;
  if (mqttClient.connected()) return;

  if (millis() - lastMqttCheck > 15000) {
    lastMqttCheck = millis();
    String clientId = "ESP32Cyclette-" + String(random(0xffff), HEX);
    if (mqttClient.connect(clientId.c_str())) {
      Serial.println("[MQTT] Connesso con successo al broker!");
      mqttAvailable = true;
    } else {
      mqttAvailable = false;
    }
  }
}

void sendTelemetry(bool isFinished = false) {
  const uint32_t now = millis();
  const uint32_t elapsedSec = (now - sessionStartMs) / 1000;
  const float elapsedHours = elapsedSec / 3600.0f;

  noInterrupts();
  const uint32_t currentPulses = pulseCount;
  const uint32_t lastPulseUs = lastPulseMicros;
  const uint32_t prevPulseUs = prevPulseMicros;
  interrupts();

  const uint32_t deltaPulses = currentPulses - lastPulseSnapshot;
  lastPulseSnapshot = currentPulses;

  const float distanceKm = (currentPulses * METERS_PER_PULSE) / 1000.0f;
  const float avgSpeedKmh = elapsedHours > 0 ? (distanceKm / elapsedHours) : 0.0f;

  float currentSpeedKmh = 0.0f;
  float rpm = 0.0f;

  const uint32_t msSinceLastPulse = (micros() - lastPulseUs) / 1000;
  if (msSinceLastPulse <= STOP_TIMEOUT_MS) {
    const uint32_t pulseDeltaUs = (lastPulseUs > prevPulseUs) ? (lastPulseUs - prevPulseUs) : 0;
    if (pulseDeltaUs > 0 && prevPulseUs > 0) {
      currentSpeedKmh = (METERS_PER_PULSE * 3600000.0f) / (float)pulseDeltaUs;
      rpm = 60000000.0f / (float)pulseDeltaUs;
    } else if (deltaPulses > 0) {
      const float deltaSec = (now - lastSendMs) / 1000.0f;
      if (deltaSec > 0) {
        currentSpeedKmh = (deltaPulses * METERS_PER_PULSE / deltaSec) * 3.6f;
        rpm = (deltaPulses / deltaSec) * 60.0f;
      }
    }
  }

  // Prepara payload compatto
  String payload = "{";
  payload += "\"username\":\"" + String(USERS[currentUserIndex]) + "\",";
  payload += "\"session_uid\":\"" + currentSessionUid + "\",";
  payload += "\"pulses\":" + String(currentPulses) + ",";
  payload += "\"distance_km\":" + String(distanceKm, 3) + ",";
  payload += "\"current_speed_kmh\":" + String(currentSpeedKmh, 1) + ",";
  payload += "\"avg_speed_kmh\":" + String(avgSpeedKmh, 1) + ",";
  payload += "\"rpm\":" + String(rpm, 1) + ",";
  payload += "\"duration_seconds\":" + String(elapsedSec) + ",";
  payload += "\"resistance_level\":" + String(resistanceLevel) + ",";
  payload += "\"is_finished\":" + String(isFinished ? "true" : "false");
  payload += "}";

  // Prova prima MQTT
  if (mqttClient.connected()) {
    mqttClient.publish(MQTT_TOPIC, payload.c_str());
    Serial.printf("[INVIO MQTT] dist=%.3f km | speed=%.1f km/h | rpm=%.0f | R%d | %s\n",
                  distanceKm, currentSpeedKmh, rpm, resistanceLevel, USERS[currentUserIndex]);
    return;
  }

  // Fallback automatico su HTTPS POST
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    String url = "https://" + String(SERVER_HOST) + "/api/rides/esp32";
    secureClient.setInsecure(); // Accetta certificato Caddy senza richiedere bundle root CA
    
    if (http.begin(secureClient, url)) {
      http.addHeader("Content-Type", "application/json");
      http.addHeader("X-Api-Key", ESP32_API_KEY);
      http.setTimeout(2500);

      int httpCode = http.POST(payload);
      if (httpCode >= 200 && httpCode < 300) {
        Serial.printf("[INVIO HTTPS OK] dist=%.3f km | speed=%.1f km/h | rpm=%.0f | R%d | %s\n",
                      distanceKm, currentSpeedKmh, rpm, resistanceLevel, USERS[currentUserIndex]);
      } else {
        Serial.printf("[INVIO HTTPS ERROR] HTTP code %d\n", httpCode);
      }
      http.end();
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(300);

  pinMode(REED_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(REED_PIN), onReedPulse, FALLING);

  pinMode(USER_SW_PIN, INPUT_PULLUP);
  pinMode(LED_STATUS_PIN, OUTPUT);
  digitalWrite(LED_STATUS_PIN, LOW);

  Serial.println("\n==========================================");
  Serial.println("  DietOrDie - Sensore Cyclette Attivo     ");
  Serial.printf("  Pin Reed: GPIO %d (INPUT_PULLUP)\n", REED_PIN);
  Serial.printf("  Pin Tasto Utente: GPIO %d\n", USER_SW_PIN);
  Serial.printf("  Calibrazione: %.2f m per giro\n", METERS_PER_PULSE);
  Serial.printf("  Utente selezionato: %s\n", USERS[currentUserIndex]);
  Serial.println("==========================================\n");

  setupWifi();
  mqttClient.setServer(SERVER_HOST, MQTT_PORT);
}

void loop() {
  const uint32_t now = millis();

  if (WiFi.status() != WL_CONNECTED) {
    setupWifi();
  } else {
    tryMqttConnect();
    if (mqttClient.connected()) {
      mqttClient.loop();
    }
  }

  // 1. Stampa immediata a ogni pedalata rilevata
  static uint32_t lastPrintedPulses = 0;
  if (pulseCount != lastPrintedPulses) {
    const uint32_t diff = pulseCount - lastPrintedPulses;
    lastPrintedPulses = pulseCount;
    lastActivityMs = now;

    if (!isSessionActive) {
      isSessionActive = true;
      sessionStartMs = now;
      currentSessionUid = generateSessionUid();
      Serial.printf("\n>>> NUOVA SESSIONE INIZIATA PER: %s (UID: %s) <<<\n",
                    USERS[currentUserIndex], currentSessionUid.c_str());
    }

    Serial.printf("[PEDALATA #%u] +%u giro! Pin %d: LOW\n", pulseCount, diff, REED_PIN);
  }

  // 2. Selettore utente tramite tasto BOOT
  static bool lastBtnState = HIGH;
  const bool btnState = digitalRead(USER_SW_PIN);
  if (lastBtnState == HIGH && btnState == LOW) {
    if (!isSessionActive) {
      currentUserIndex = (currentUserIndex + 1) % 2;
      Serial.printf("\n>>> UTENTE CAMBIATO IN: %s <<<\n", USERS[currentUserIndex]);
      delay(250);
    }
  }
  lastBtnState = btnState;

  // 3. Invio periodico telemetria durante l'allenamento
  if (isSessionActive && (now - lastSendMs >= SEND_INTERVAL_MS)) {
    lastSendMs = now;
    sendTelemetry(false);
  }

  // 4. Timeout inattività: chiusura sessione dopo 60s
  if (isSessionActive && (now - lastActivityMs >= FINISH_TIMEOUT_MS)) {
    Serial.println("\n>>> SESSIONE COMPLETATA (60s fermo) <<<");
    sendTelemetry(true);
    isSessionActive = false;
    pulseCount = 0;
    lastPulseSnapshot = 0;
    lastPrintedPulses = 0;
  }

  // 5. Segnale di vita ogni 3 secondi se fermi
  static uint32_t lastHeartbeat = 0;
  if (!isSessionActive && (now - lastHeartbeat >= 3000)) {
    lastHeartbeat = now;
    const int pinVal = digitalRead(REED_PIN);
    Serial.printf("[ATTESA PEDALATA] Pin %d: %s | Giri: %u | Utente: %s\n",
                  REED_PIN,
                  pinVal == LOW ? "LOW (Magnete allineato!)" : "HIGH (Pronto)",
                  pulseCount,
                  USERS[currentUserIndex]);
  }

  delay(20);
}
