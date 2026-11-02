import React, { useState, useEffect } from 'react';
import { User, RideSession, MilestoneUnlockCelebration, UserJourneyProgress } from '../types';
import { getRides, logRide, getActiveRide } from '../api';
import { JourneyMap } from './JourneyMap';
import {
  Bike,
  Plus,
  Flame,
  Gauge,
  Cpu,
  ChevronDown,
  ChevronUp,
  History,
  Copy,
  Zap,
  Sliders,
  Radio,
  Timer
} from 'lucide-react';

interface CycletteTabProps {
  user: User;
}

export const CycletteTab: React.FC<CycletteTabProps> = ({ user }) => {
  const [rides, setRides] = useState<RideSession[]>([]);
  const [activeRide, setActiveRide] = useState<RideSession | null>(null);
  const [liveProgress, setLiveProgress] = useState<UserJourneyProgress | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [celebration, setCelebration] = useState<MilestoneUnlockCelebration | null>(null);

  // Form states
  const [distanceKm, setDistanceKm] = useState<string>('');
  const [durationMin, setDurationMin] = useState<string>('');
  const [durationSec, setDurationSec] = useState<string>('');
  const [resistanceLevel, setResistanceLevel] = useState<number>(3);
  const [customCalories, setCustomCalories] = useState<string>('');
  const [notes, setNotes] = useState<string>('');
  const [showEsp32Guide, setShowEsp32Guide] = useState(false);
  const [copied, setCopied] = useState(false);

  const fetchRides = async () => {
    try {
      const data = await getRides();
      setRides(data);
    } catch (err) {
      console.error('Error fetching rides:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRides();

    // 1. Connessione WebSocket push in tempo reale (latenza sub-secondo da broker MQTT)
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/ws/rides`;

    let ws: WebSocket | null = null;
    let retryTimer: any = null;

    const connectWs = () => {
      try {
        ws = new WebSocket(wsUrl);

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'ride_tick' && data.ride) {
              if (!data.ride.username || data.ride.username === user.username) {
                setActiveRide(data.ride);
                if (data.progress) {
                  setLiveProgress(data.progress);
                }
                if (data.celebration) {
                  setCelebration(data.celebration);
                }
                fetchRides();
              }
            }
          } catch (e) {
            console.error('Error parsing WebSocket message:', e);
          }
        };

        ws.onclose = () => {
          retryTimer = setTimeout(connectWs, 3000);
        };

        ws.onerror = () => {
          ws?.close();
        };
      } catch (e) {
        retryTimer = setTimeout(connectWs, 3000);
      }
    };

    connectWs();

    // 2. Polling di riserva ogni 10s se WebSocket e offline
    const fallbackInterval = setInterval(async () => {
      try {
        const live = await getActiveRide();
        setActiveRide(live);
      } catch (err) {}
    }, 10000);

    return () => {
      if (ws) ws.close();
      clearTimeout(retryTimer);
      clearInterval(fallbackInterval);
    };
  }, [user.username]);

  const totalSec = (Number(durationMin) || 0) * 60 + (Number(durationSec) || 0);
  const distNum = Number(distanceKm) || 0;
  const calculatedSpeed = totalSec > 0 && distNum > 0 ? ((distNum / (totalSec / 3600))).toFixed(1) : '0.0';

  const weight = user.profile?.current_weight_kg || 70;
  const speedVal = Number(calculatedSpeed);
  const baseMet = speedVal < 15 ? 4.8 : speedVal < 20 ? 6.8 + (speedVal - 15) * 0.4 : speedVal < 25 ? 8.8 + (speedVal - 20) * 0.44 : 11.0;
  const resistanceFactor = 1.0 + (resistanceLevel - 1) * 0.14;
  const calculatedCal = distNum > 0 && totalSec > 0
    ? Math.round((baseMet * resistanceFactor * 3.5 * weight / 200) * (totalSec / 60))
    : 0;

  const handleLogRide = async (e: React.FormEvent) => {
    e.preventDefault();
    if (distNum <= 0 || totalSec <= 0) {
      alert('Inserisci una distanza e una durata valide');
      return;
    }

    setSubmitting(true);
    try {
      const result = await logRide({
        duration_seconds: totalSec,
        distance_km: distNum,
        avg_speed_kmh: Number(calculatedSpeed),
        calories_burned: customCalories ? Number(customCalories) : calculatedCal,
        resistance_level: resistanceLevel,
        notes: notes || undefined
      });

      setDistanceKm('');
      setDurationMin('');
      setDurationSec('');
      setCustomCalories('');
      setNotes('');

      fetchRides();

      if (result.newly_unlocked_milestone) {
        setCelebration(result.newly_unlocked_milestone);
      }
    } catch (err: any) {
      alert(err.message || 'Errore nella registrazione della sessione');
    } finally {
      setSubmitting(false);
    }
  };

  const esp32SampleCode = `// ESP32 Cyclette MQTT Telemetry (PubSubClient)
#include <WiFi.h>
#include <PubSubClient.h>

const char* ssid        = "IL_TUO_WIFI";
const char* password    = "LA_TUA_PASSWORD";
const char* mqttServer  = "dietordie.duckdns.org";
const int   mqttPort    = 1883;
const char* mqttTopic   = "dietordie/telemetry";

WiFiClient espClient;
PubSubClient client(espClient);

void sendMqttTelemetry(const char* user, const String& sessionUid, float km, float speedKmh, float rpm, int durationSec, int resistance) {
  if (client.connected()) {
    String json = "{\\"user\\":\\"" + String(user) + "\\","
                  "\\"session_uid\\":\\"" + sessionUid + "\\","
                  "\\"distance_km\\":" + String(km, 3) + ","
                  "\\"current_speed_kmh\\":" + String(speedKmh, 1) + ","
                  "\\"rpm\\":" + String(rpm, 1) + ","
                  "\\"duration_sec\\":" + String(durationSec) + ","
                  "\\"resistance\\":" + String(resistance) + "}";
    client.publish(mqttTopic, json.c_str());
  }
}`;

  const copyCode = () => {
    navigator.clipboard.writeText(esp32SampleCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };


  return (
    <div className="space-y-4">
      {/* Live ESP32 Telemetry HUD Banner (se attivo negli ultimi 15s) */}
      {activeRide && (
        <div className="p-4 rounded-3xl bg-gradient-to-r from-emerald-950/80 via-zinc-900 to-zinc-950 border-2 border-emerald-500/50 shadow-2xl shadow-emerald-950/30 animate-pulse">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping" />
              <Radio className="w-4 h-4 text-emerald-400" />
              <span className="text-xs font-black tracking-wider uppercase text-emerald-300">
                Live Telemetria Cyclette
              </span>
            </div>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-bold">
              Aggiornamento 5s
            </span>
          </div>

          <div className="grid grid-cols-4 gap-2 text-center">
            <div className="p-2 rounded-2xl bg-zinc-900/80 border border-white/5">
              <span className="text-[9px] uppercase tracking-wider text-zinc-400 block font-semibold">
                {activeRide.current_speed_kmh && activeRide.current_speed_kmh > 0 ? 'Velocità' : 'Media'}
              </span>
              <span className="text-lg font-black text-emerald-400 font-mono">
                {activeRide.current_speed_kmh && activeRide.current_speed_kmh > 0
                  ? activeRide.current_speed_kmh.toFixed(1)
                  : activeRide.avg_speed_kmh.toFixed(1)}
              </span>
              <span className="text-[9px] text-zinc-500 block">km/h</span>
            </div>

            <div className="p-2 rounded-2xl bg-zinc-900/80 border border-white/5">
              <span className="text-[9px] uppercase tracking-wider text-zinc-400 block font-semibold">
                {activeRide.rpm && activeRide.rpm > 0 ? 'Cadenza' : 'Cad. Media'}
              </span>
              <span className="text-lg font-black text-amber-400 font-mono">
                {activeRide.rpm && activeRide.rpm > 0
                  ? Math.round(activeRide.rpm)
                  : (activeRide.duration_seconds > 0
                      ? Math.round((activeRide.distance_km * 1000 / 3.50) / (activeRide.duration_seconds / 60))
                      : '0')}
              </span>
              <span className="text-[9px] text-zinc-500 block">RPM</span>
            </div>

            <div className="p-2 rounded-2xl bg-zinc-900/80 border border-white/5">
              <span className="text-[9px] uppercase tracking-wider text-zinc-400 block font-semibold">Distanza</span>
              <span className="text-lg font-black text-sky-400 font-mono">
                {activeRide.distance_km.toFixed(2)}
              </span>
              <span className="text-[9px] text-zinc-500 block">km</span>
            </div>

            <div className="p-2 rounded-2xl bg-zinc-900/80 border border-white/5">
              <span className="text-[9px] uppercase tracking-wider text-zinc-400 block font-semibold">Calorie</span>
              <span className="text-lg font-black text-rose-400 font-mono">
                {Math.round(activeRide.calories_burned)}
              </span>
              <span className="text-[9px] text-zinc-500 block">kcal</span>
            </div>
          </div>

          <div className="mt-2.5 pt-2 border-t border-white/5 flex items-center justify-between text-[11px] text-zinc-400 px-1">
            <div className="flex items-center space-x-1.5">
              <Timer className="w-3.5 h-3.5 text-zinc-400" />
              <span>Durata: <strong className="text-white">{Math.floor(activeRide.duration_seconds / 60)}m {activeRide.duration_seconds % 60}s</strong></span>
            </div>
            <div>
              <span>Resistenza: <strong className="text-amber-400">Livello {activeRide.resistance_level || 1}</strong></span>
            </div>
          </div>
        </div>
      )}

      {/* Interactive Quest Map */}
      <JourneyMap
        liveProgress={liveProgress}
        onProgressUpdated={fetchRides}
        celebration={celebration}
        onClearCelebration={() => setCelebration(null)}
      />


      {/* Manual & Sensor Logger Card */}
      <div className="glass-panel rounded-3xl p-5 shadow-2xl border border-white/10">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center">
              <Bike className="w-4 h-4" />
            </div>
            <h3 className="font-semibold text-zinc-100 text-sm">Registra Pedalata</h3>
          </div>
          <button
            type="button"
            onClick={() => setShowEsp32Guide(!showEsp32Guide)}
            className="flex items-center space-x-1 text-[11px] text-amber-400 font-bold bg-amber-500/10 hover:bg-amber-500/20 px-2.5 py-1 rounded-xl border border-amber-500/20 transition active:scale-95"
          >
            <Cpu className="w-3.5 h-3.5" />
            <span>Setup ESP32</span>
            {showEsp32Guide ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>
        </div>

        {/* ESP32 Collapsible Telemetry Info */}
        {showEsp32Guide && (
          <div className="mb-4 p-4 rounded-2xl bg-zinc-950/95 border border-amber-500/30 text-xs space-y-3 animate-in fade-in">
            <div className="flex items-center justify-between">
              <span className="font-bold text-amber-400 flex items-center space-x-1.5">
                <Cpu className="w-4 h-4" />
                <span>Telemetria ESP32 MQTT & WebSocket Live</span>
              </span>
              <button
                onClick={copyCode}
                className="flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-[10px] font-semibold transition"
              >
                <Copy className="w-3 h-3" />
                <span>{copied ? 'Copiato!' : 'Copia C++'}</span>
              </button>
            </div>

            <div className="space-y-1.5 text-[11px] text-zinc-300 leading-relaxed">
              <p>
                🚴‍♂️ <strong>Calcolo Ibrido Edge / Cloud:</strong> L'ESP32 misura con precisione al microsecondo (<code className="text-amber-300">micros()</code>) il tempo tra le pedalate (sviluppo metrico di <strong>5.30 metri/pedalata</strong>) e trasmette i dati al broker MQTT.
              </p>
              <p>
                ⚡ <strong>MQTT &amp; WebSockets:</strong> Connessione TCP persistente ultraleggera (&lt; 100 byte/pacchetto). Lo smartphone riceve la telemetria via push istantaneo con latenza sub-secondo.
              </p>
              <p>
                ⚙️ <strong>Broker & Parametri:</strong> Host: <code className="text-amber-300">dietordie.duckdns.org:1883</code> • Topic: <code className="text-amber-300">dietordie/telemetry</code>
              </p>
            </div>

            <div className="p-2.5 rounded-xl bg-zinc-900 font-mono text-[10px] text-amber-300 break-all border border-white/5">
              MQTT Broker: dietordie.duckdns.org:1883 | Topic: dietordie/telemetry
            </div>

            <p className="text-[10px] text-zinc-500 italic">
              Lo sketch completo Arduino/ESP32 con supporto PubSubClient e switch Mario/Anna tramite tasto BOOT è pronto in <code className="text-zinc-400">esp32/dietordie_sensor.ino</code>.
            </p>
          </div>
        )}

        <form onSubmit={handleLogRide} className="space-y-3.5">
          <div className="grid grid-cols-2 gap-2.5">
            <div>
              <label className="text-[10px] font-medium text-zinc-400 block mb-1">Distanza (km)</label>
              <div className="relative">
                <input
                  type="number"
                  step="0.1"
                  required
                  placeholder="es. 15.5"
                  value={distanceKm}
                  onChange={(e) => setDistanceKm(e.target.value)}
                  className="w-full bg-zinc-900 border border-white/10 rounded-xl px-3 py-2 text-sm text-white font-bold focus:outline-none focus:border-amber-500"
                />
                <span className="absolute right-3 top-2.5 text-xs text-zinc-500">km</span>
              </div>
            </div>

            <div>
              <label className="text-[10px] font-medium text-zinc-400 block mb-1">Durata</label>
              <div className="flex space-x-1.5">
                <div className="relative flex-1">
                  <input
                    type="number"
                    placeholder="Min"
                    value={durationMin}
                    onChange={(e) => setDurationMin(e.target.value)}
                    className="w-full bg-zinc-900 border border-white/10 rounded-xl px-2 py-2 text-sm text-center text-white font-bold focus:outline-none focus:border-amber-500"
                  />
                  <span className="text-[9px] text-zinc-500 block text-center mt-0.5">min</span>
                </div>
                <div className="relative flex-1">
                  <input
                    type="number"
                    placeholder="Sec"
                    value={durationSec}
                    onChange={(e) => setDurationSec(e.target.value)}
                    className="w-full bg-zinc-900 border border-white/10 rounded-xl px-2 py-2 text-sm text-center text-white font-bold focus:outline-none focus:border-amber-500"
                  />
                  <span className="text-[9px] text-zinc-500 block text-center mt-0.5">sec</span>
                </div>
              </div>
            </div>
          </div>

          {/* Resistance Level Selector (1 to 8) */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-[10px] font-medium text-zinc-400 flex items-center space-x-1">
                <Sliders className="w-3 h-3 text-amber-400" />
                <span>Resistenza Cyclette: </span>
                <strong className="text-amber-400 text-xs font-black ml-1">Livello {resistanceLevel}</strong>
              </label>
              <span className="text-[10px] text-zinc-500">
                {resistanceLevel <= 2 ? 'Pianura / Agile' : resistanceLevel <= 5 ? 'Resistenza Media' : 'Salita Ripida'}
              </span>
            </div>
            <div className="grid grid-cols-8 gap-1">
              {[1, 2, 3, 4, 5, 6, 7, 8].map((lvl) => (
                <button
                  key={lvl}
                  type="button"
                  onClick={() => setResistanceLevel(lvl)}
                  className={`py-1.5 rounded-xl text-xs font-black transition border ${
                    resistanceLevel === lvl
                      ? 'bg-amber-500 text-zinc-950 border-amber-400 shadow-sm'
                      : 'bg-zinc-900/60 border-white/5 text-zinc-400 hover:text-white'
                  }`}
                >
                  {lvl}
                </button>
              ))}
            </div>
          </div>

          {/* Real-time stats preview with accurate formula */}
          {distNum > 0 && totalSec > 0 && (
            <div className="grid grid-cols-2 gap-2 p-2.5 rounded-2xl bg-zinc-950/70 border border-white/5 text-xs">
              <div className="flex items-center space-x-2 text-zinc-400">
                <Gauge className="w-4 h-4 text-amber-400 flex-shrink-0" />
                <span className="truncate">Media: <strong className="text-zinc-100">{calculatedSpeed} km/h</strong></span>
              </div>
              <div className="flex items-center space-x-2 text-zinc-400">
                <Flame className="w-4 h-4 text-rose-500 flex-shrink-0" />
                <span className="truncate">Calorie: <strong className="text-rose-400 font-bold">{customCalories || calculatedCal} kcal</strong></span>
              </div>
            </div>
          )}

          <div>
            <input
              type="text"
              placeholder="Note sessione (opzionale)"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full bg-zinc-900 border border-white/10 rounded-xl px-3 py-2 text-xs text-white placeholder-zinc-600 focus:outline-none focus:border-amber-500"
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full py-3 bg-gradient-to-r from-amber-500 via-orange-500 to-rose-500 hover:opacity-95 active:scale-[0.98] text-zinc-950 font-bold rounded-2xl transition flex items-center justify-center space-x-2 shadow-lg shadow-rose-950/20 disabled:opacity-50 text-xs"
          >
            <Plus className="w-4 h-4" />
            <span>{submitting ? 'Registrazione in corso...' : 'Salva Sessione e Avanza nel Percorso'}</span>
          </button>
        </form>
      </div>

      {/* Ride History */}
      <div className="glass-panel-subtle rounded-3xl p-5 border border-white/5">
        <h3 className="text-xs font-bold text-zinc-300 uppercase tracking-wider mb-3 flex items-center space-x-2">
          <History className="w-4 h-4 text-amber-400" />
          <span>Ultime Pedalata Registrate</span>
        </h3>

        {rides.length === 0 ? (
          <p className="text-xs text-zinc-600 italic py-2 text-center">Nessuna pedalata registrata finora.</p>
        ) : (
          <div className="space-y-2">
            {rides.map((r) => {
              const dateFormatted = new Date(r.created_at).toLocaleDateString('it-IT', {
                day: '2-digit',
                month: 'short',
                hour: '2-digit',
                minute: '2-digit'
              });
              const mins = Math.round(r.duration_seconds / 60);

              return (
                <div
                  key={r.id}
                  className="flex items-center justify-between p-3 rounded-2xl bg-zinc-950/60 border border-white/5 text-xs"
                >
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center font-bold">
                      <Bike className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-bold text-white text-sm">{r.distance_km} km</span>
                        <span className="text-[10px] text-zinc-500">• {mins} min</span>
                        {r.resistance_level && (
                          <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-zinc-800 text-amber-400/90 border border-white/5">
                            R{r.resistance_level}
                          </span>
                        )}
                      </div>
                      <p className="text-[10px] text-zinc-400">{dateFormatted}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="font-bold text-emerald-400 block text-xs font-mono">-{Math.round(r.calories_burned)} kcal</span>
                    <span className="text-[10px] text-zinc-500">{r.avg_speed_kmh} km/h</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
