# 🚴 DietOrDie

App personale e multi-utente (progettata per smartphone) per il tracciamento nutrizionale assistito da AI, monitoraggio della salute (BMI, BMR, deficit calorico) e gamificazione degli allenamenti su cyclette con percorsi epici (**Il Viaggio dell'Anello**, **Elden Ring**).

---

## 🚀 Caratteristiche Principali

### 1. 🍽️ Diario Nutrizionale & Vision AI (OpenRouter)
- Ripartizione automatica dei pasti: Colazione, Pranzo, Cena, Spuntini.
- **Scanner Pasti con AI Visiva**: scatta una foto al piatto dallo smartphone. L'endpoint integrato interroga **OpenRouter (modello gratuito Llama 3.2 11B Vision)** e restituisce stima di calorie, proteine, carboidrati, grassi e porzioni.
- Possibilità di rivedere e modificare le stime prima del salvataggio.

### 2. 🚴 Cyclette & Telemetria Live (MQTT + WebSockets)
- Registrazione manuale o streaming in tempo reale dalla cyclette.
- **Calibrazione Cyclette**: 5.30 metri virtuali per impulso reed (sviluppo metrico standard per pedalata).
- **Architettura Ibrida**:
  - **ESP32 (Edge)**: timer hardware in microsecondi per misurare velocità istantanea e RPM senza ritardi di rete; conteggio cumulativo per zero perdita di dati.
  - **Server (Cloud)**: calcolo calorie su misura (peso Mario/Anna, altezza, età, BMI, resistenza 1-8 su curva progressiva $0.75 + 0.13 \times \text{level}$) e push WebSocket alla PWA.
- **Protocollo MQTT (Mosquitto)**: broker integrato su porta 1883, pacchetti compatti < 100 byte ogni 1.5s.

### 3. 🗺️ Gamificazione: 10 Percorsi Nerd Epici
- Ogni pedalata fa avanzare il personaggio sulla mappa selezionata:
  1. **Il Signore degli Anelli: Il Viaggio dell'Anello** (2.200 km da Hobbiville a Monte Fato).
  2. **Elden Ring: La Marcia del Senzaluce** (500 km con backtracking tra Sepolcride, Grantempesta, Liurnia, Caelid e l'Albero Madre).
  3. **L'Espresso per Hogwarts** (800 km - tappa singola diretta dal Binario 9 ¾ a Hogsmeade).
  4. **The Witcher 3: Sulle Tracce di Ciri** (1.200 km).
  5. **Skyrim: La Via dei Barbagrigia** (650 km).
  6. **Pokémon: Il Giro della Lega di Kanto** (450 km).
  7. **Dragon Ball: Il Serpentone dell'Aldilà** (1.000 km).
  8. **Dune: Il Cammino dei Fremen** (1.500 km).
  9. **Zelda: Il Risveglio di Hyrule** (750 km).
  10. **Star Wars: La Rotta di Kessel** (1.800 km).
- Calcolo automatico delle calorie totali e rimanenti per ciascun viaggio.
- Sblocco tappe con lore originale e celebrazioni visive con coriandoli (`canvas-confetti`).

### 4. 👤 Profilo, BMI e Salute Metabolica
- Calcolo automatico del **BMI** con categoria e barra visiva colorata.
- Calcolo del **BMR** (Mifflin-St Jeor) e **TDEE** (fabbisogno calorico giornaliero in base al livello di attività).
- Suggerimento del target calorico giornaliero con deficit controllato per la perdita di peso.
- Storico del peso corporeo con tracciamento differenziale.
- Switch istantaneo tra utenti (es. Marito e Moglie).

---

## 🔌 Codice ESP32 per la Cyclette (Arduino / PlatformIO)

Quando l'ESP32 termina una sessione (o a intervalli regolari), può inviare i dati tramite una semplice richiesta HTTP POST in formato JSON:

```cpp
#include <WiFi.h>
#include <HTTPClient.h>

const char* ssid     = "IL_TUO_WIFI";
const char* password = "LA_TUA_PASSWORD";

// Endpoint sulla tua VPS (dietordie.duckdns.org)
const char* serverUrl = "https://dietordie.duckdns.org/api/rides/esp32";
const char* apiKey    = "esp32-dietordie-secret-token";

void sendRideSession(const char* username, float distanceKm, int durationSeconds, float avgSpeedKmh, float calories) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverUrl);
    http.addHeader("Content-Type", "application/json");

    String json = "{\"api_key\":\"" + String(apiKey) + "\","
                  "\"username\":\"" + String(username) + "\","
                  "\"distance_km\":" + String(distanceKm, 2) + ","
                  "\"duration_seconds\":" + String(durationSeconds) + ","
                  "\"avg_speed_kmh\":" + String(avgSpeedKmh, 1) + ","
                  "\"calories_burned\":" + String(calories, 1) + "}";

    int httpResponseCode = http.POST(json);
    Serial.print("HTTP Response code: ");
    Serial.println(httpResponseCode);

    http.end();
  }
}
```

---

## 🗄️ Database: Perché SQLite invece di Postgres?

- **Memoria RAM**: PostgreSQL gira come un processo demone server separato (50-150MB di RAM costanti). Su una VPS da 1.6 GB che ospita già altri servizi, SQLite è integrato nel processo Python con **zero overhead di RAM aggiuntivo**.
- **Performance**: In modalità WAL (`Write-Ahead Logging`), SQLite gestisce centinaia di scritture concorrenti al secondo. Per due persone (marito e moglie), la latenza è a sub-millisecondo senza connessioni di rete TCP intermedie.
- **Backup**: L'intero database è un singolo file (`data/dietordie.db`). Fare un backup equivale a una semplice copia file o snapshot rsync.

---

## 🌐 Configurazione Reverse Proxy Caddy (`dietordie.duckdns.org`)

Nel file Caddyfile della VPS, aggiungi questo blocco per gestire l'SSL automatico Let's Encrypt verso il container locale sulla porta `8088`:

```caddyfile
dietordie.duckdns.org {
    reverse_proxy 127.0.0.1:8088
}
```
Poi ricarica Caddy con:
```bash
sudo systemctl reload caddy
# oppure nel container caddy: docker exec -w /etc/caddy laminiel-caddy caddy reload
```

---

## 📦 Deploy con Docker Compose

1. Copia i file sulla VPS o clona la cartella in `/home/deploy/DietOrDie`.
2. Crea il file `.env` inserendo la tua chiave OpenRouter:
   ```bash
   OPENROUTER_API_KEY=la_tua_chiave_openrouter
   ESP32_API_KEY=esp32-dietordie-secret-token
   DOMAIN=dietordie.duckdns.org
   ```
3. Avvia il container:
   ```bash
   docker compose up -d --build
   ```
