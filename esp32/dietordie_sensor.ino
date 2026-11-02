/*
  DietOrDie - ESP32 Cyclette Sensor Firmware (MQTT Version)
  ========================================================
  Telemetria in tempo reale ad alta efficienza tramite protocollo MQTT.
  Libreria richiesta: PubSubClient (installabile dal gestore librerie di Arduino IDE / PlatformIO).

  Architettura di Calcolo Ibrida:
  - ESP32 (Edge): misura con precisione microsecondi (micros) l'intervallo tra pedalate,
                  calcola cadenza (RPM) e velocita istantanea senza subire ritardi di rete,
                  mantiene il contatore cumulativo degli impulsi e distanza.
  - Server (Cloud): calcola calorie personalizzate (peso, altezza, eta, BMI, resistenza),
                    fa avanzare il percorso RPG ed emette WebSocket push ai telefoni connessi.

  Calibrazione:
  - REED_PIN: GPIO 38 (o personalizzabile in base alla board ESP32)
  - REED_DEBOUNCE_US: 8000 us (8 ms antirimbalzo)
  - METERS_PER_PULSE: 5.30 m (sviluppo metrico calcolato da cyclette.ino)
  - MQTT_INTERVAL_MS: 1500 ms (invio frequente ed ultraleggero, latenza sub-secondo)
  - SELETTORE UTENTE: GPIO 0 (pulsante BOOT su ESP32 per alternare tra Mario e Anna)
*/

#include <WiFi.h>
#include <PubSubClient.h>

// ================= CONFIGURAZIONE WI-FI & MQTT =================
const char* WIFI_SSID        = "IL_TUO_WIFI";
const char* WIFI_PASSWORD    = "LA_TUA_PASSWORD";

// Broker MQTT (Server VPS DietOrDie)
const char* MQTT_SERVER      = "dietordie.duckdns.org"; // oppure IP locale in test
const int   MQTT_PORT        = 1883;
const char* MQTT_TOPIC       = "dietordie/telemetry";
const char* MQTT_USER        = ""; // Lasciare vuoto se anonimo
const char* MQTT_PASS        = "";

// Pin hardware
constexpr int REED_PIN       = 38;  // Pin sensore reed magnetico della cyclette
constexpr int USER_SW_PIN    = 0;   // Pulsante BOOT su scheda ESP32 per cambiare utente
constexpr int LED_STATUS_PIN = 2;   // LED di stato (acceso durante trasmissione / connesso)

// Parametri di calcolo cyclette (estratti da cyclette.ino)
constexpr float METERS_PER_PULSE       = 5.30f; // 5.30 metri virtuali per impulso (1 pedalata)
constexpr uint32_t REED_DEBOUNCE_US    = 8000;  // 8 ms antirimbalzo hardware
constexpr uint32_t MQTT_INTERVAL_MS    = 1500;  // Frequenza invio telemetria MQTT (1.5 secondi)
constexpr uint32_t STOP_TIMEOUT_MS     = 3500;  // Se nessun impulso per 3.5s, velocita scende a 0
constexpr uint32_t FINISH_TIMEOUT_MS   = 60000; // Fine sessione se fermi da 60s

// Utenti supportati
const char* USERS[] = {"mario", "anna"};
int currentUserIndex = 0; // 0 = Mario, 1 = Anna

// Livello di resistenza meccanica della cyclette (da 1 a 8)
int resistanceLevel = 3;

// ================= STATO INTERNO =================
WiFiClient espClient;
PubSubClient mqttClient(espClient);

volatile uint32_t pulseCount = 0;
volatile uint32_t lastPulseMicros = 0;
volatile uint32_t prevPulseMicros = 0;

uint32_t lastPulseSnapshot = 0;
uint32_t lastMqttSendMs = 0;
uint32_t lastActivityMs = 0;
uint32_t sessionStartMs = 0;
bool isSessionActive = false;
String currentSessionUid = "";

// Interrupt sensore Reed con antirimbalzo a 8ms
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
  Serial.print("Connessione a ");
  Serial.println(WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.printf("\nWi-Fi Connesso! IP: %s\n", WiFi.localIP().toString().c_str());
}

void reconnectMqtt() {
  while (!mqttClient.connected()) {
    Serial.print("Tentativo connessione MQTT...");
    String clientId = "ESP32Cyclette-" + String(random(0xffff), HEX);

    bool ok = (strlen(MQTT_USER) > 0)
      ? mqttClient.connect(clientId.c_str(), MQTT_USER, MQTT_PASS)
      : mqttClient.connect(clientId.c_str());

    if (ok) {
      Serial.println(" CONNESSO!");
      digitalWrite(LED_STATUS_PIN, HIGH);
    } else {
      Serial.printf(" Fallito, rc=%d. Riprovo tra 3 secondi...\n", mqttClient.state());
      digitalWrite(LED_STATUS_PIN, LOW);
      delay(3000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(500);

  pinMode(REED_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(REED_PIN), onReedPulse, FALLING);

  pinMode(USER_SW_PIN, INPUT_PULLUP);
  pinMode(LED_STATUS_PIN, OUTPUT);
  digitalWrite(LED_STATUS_PIN, LOW);

  Serial.println("\n==========================================");
  Serial.println("  DietOrDie - ESP32 Cyclette (MQTT Live)  ");
  Serial.printf("  Calibrazione: %.2f m per pedalata\n", METERS_PER_PULSE);
  Serial.printf("  Broker: %s:%d\n", MQTT_SERVER, MQTT_PORT);
  Serial.printf("  Utente attivo: %s\n", USERS[currentUserIndex]);
  Serial.println("==========================================\n");

  setupWifi();
  mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
}

void sendMqttTelemetry(bool isFinished = false) {
  if (!mqttClient.connected()) {
    reconnectMqtt();
  }

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

  // 1. Distanza cumulativa (in km)
  const float distanceKm = (currentPulses * METERS_PER_PULSE) / 1000.0f;

  // 2. Velocita media complessiva
  const float avgSpeedKmh = elapsedHours > 0 ? (distanceKm / elapsedHours) : 0.0f;

  // 3. Velocita istantanea e Cadenza (RPM) basate sul delta intervallo
  float currentSpeedKmh = 0.0f;
  float rpm = 0.0f;

  const uint32_t msSinceLastPulse = (micros() - lastPulseUs) / 1000;
  if (msSinceLastPulse <= STOP_TIMEOUT_MS && deltaPulses > 0) {
    const float deltaSec = (now - lastMqttSendMs) / 1000.0f;
    if (deltaSec > 0) {
      const float meters = deltaPulses * METERS_PER_PULSE;
      currentSpeedKmh = (meters / deltaSec) * 3.6f;
      rpm = (deltaPulses / deltaSec) * 60.0f;
    }
  }

  // Prepara payload compatto in formato JSON
  String payload = "{";
  payload += "\"user\":\"" + String(USERS[currentUserIndex]) + "\",";
  payload += "\"session_uid\":\"" + currentSessionUid + "\",";
  payload += "\"pulses\":" + String(currentPulses) + ",";
  payload += "\"distance_km\":" + String(distanceKm, 3) + ",";
  payload += "\"current_speed_kmh\":" + String(currentSpeedKmh, 1) + ",";
  payload += "\"avg_speed_kmh\":" + String(avgSpeedKmh, 1) + ",";
  payload += "\"rpm\":" + String(rpm, 1) + ",";
  payload += "\"duration_sec\":" + String(elapsedSec) + ",";
  payload += "\"resistance\":" + String(resistanceLevel) + ",";
  payload += "\"is_finished\":" + String(isFinished ? "true" : "false");
  payload += "}";

  boolean published = mqttClient.publish(MQTT_TOPIC, payload.c_str());
  if (published) {
    Serial.printf("[MQTT LIVE] dist=%.3f km | speed=%.1f km/h | rpm=%.0f | R%d | %s\n",
                  distanceKm, currentSpeedKmh, rpm, resistanceLevel, USERS[currentUserIndex]);
  } else {
    Serial.println("[MQTT ERROR] Pubblicazione fallita");
  }
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    setupWifi();
  }
  if (!mqttClient.connected()) {
    reconnectMqtt();
  }
  mqttClient.loop();

  const uint32_t now = millis();

  // 1. Selettore utente rapido tramite pulsante BOOT (GPIO 0)
  static bool lastBtnState = HIGH;
  const bool btnState = digitalRead(USER_SW_PIN);
  if (lastBtnState == HIGH && btnState == LOW) {
    if (!isSessionActive) {
      currentUserIndex = (currentUserIndex + 1) % 2;
      Serial.printf("\n>>> UTENTE ATTIVO CAMBIATO IN: %s <<<\n", USERS[currentUserIndex]);
      delay(300);
    }
  }
  lastBtnState = btnState;

  // 2. Rilevamento pedalata
  noInterrupts();
  const uint32_t currentPulses = pulseCount;
  interrupts();

  if (currentPulses > lastPulseSnapshot) {
    lastActivityMs = now;

    if (!isSessionActive) {
      isSessionActive = true;
      sessionStartMs = now;
      currentSessionUid = generateSessionUid();
      Serial.printf("\n>>> INIZIO SESSIONE ALLENAMENTO PER %s (UID: %s) <<<\n",
                    USERS[currentUserIndex], currentSessionUid.c_str());
    }
  }

  // 3. Invio periodico live via MQTT
  if (isSessionActive && (now - lastMqttSendMs >= MQTT_INTERVAL_MS)) {
    sendMqttTelemetry(false);
    lastMqttSendMs = now;
  }

  // 4. Timeout inattivita: se fermi per oltre 60s, finalizza la sessione
  if (isSessionActive && (now - lastActivityMs >= FINISH_TIMEOUT_MS)) {
    Serial.println("\n>>> TIMEOUT FERMO: CHIUSURA SESSIONE <<<");
    sendMqttTelemetry(true);
    isSessionActive = false;
    pulseCount = 0;
    lastPulseSnapshot = 0;
  }

  delay(20);
}
