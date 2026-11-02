import React, { useState, useEffect } from 'react';
import confetti from 'canvas-confetti';
import {
  Journey,
  UserJourneyProgress,
  MilestoneUnlockCelebration
} from '../types';
import { getJourneys, getActiveJourney, activateJourney } from '../api';
import {
  MapPin,
  CheckCircle2,
  Lock,
  Compass,
  Trophy,
  Flame,
  Sparkles,
  ChevronRight,
  X,
  Layers,
  ArrowRight,
  Shield,
  Zap
} from 'lucide-react';

interface JourneyMapProps {
  onProgressUpdated?: () => void;
  celebration?: MilestoneUnlockCelebration | null;
  onClearCelebration?: () => void;
  liveProgress?: UserJourneyProgress | null;
}

export const JourneyMap: React.FC<JourneyMapProps> = ({
  onProgressUpdated,
  celebration,
  onClearCelebration,
  liveProgress
}) => {
  const [allJourneys, setAllJourneys] = useState<Journey[]>([]);
  const [progress, setProgress] = useState<UserJourneyProgress | null>(null);
  const [loading, setLoading] = useState(true);
  const [switching, setSwitching] = useState(false);
  const [isPickerOpen, setIsPickerOpen] = useState(false);

  const fetchJourneyData = async () => {
    try {
      const [jList, activeP] = await Promise.all([getJourneys(), getActiveJourney()]);
      setAllJourneys(jList);
      setProgress(activeP);
    } catch (err) {
      console.error('Error fetching journeys:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJourneyData();
  }, []);

  useEffect(() => {
    if (liveProgress) {
      setProgress(liveProgress);
    }
  }, [liveProgress]);

  useEffect(() => {
    if (celebration) {
      confetti({
        particleCount: 140,
        spread: 80,
        origin: { y: 0.6 }
      });
    }
  }, [celebration]);

  const handleSelectJourney = async (journeyId: number) => {
    if (progress?.journey.id === journeyId) {
      setIsPickerOpen(false);
      return;
    }
    setSwitching(true);
    try {
      const updated = await activateJourney(journeyId);
      setProgress(updated);
      setIsPickerOpen(false);
      onProgressUpdated?.();
    } catch (err) {
      alert('Errore nel cambio percorso');
    } finally {
      setSwitching(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8 text-center text-zinc-500 text-xs animate-pulse">
        Caricamento avventure e percorsi epici...
      </div>
    );
  }

  const currentJourney = progress?.journey;
  const milestones = currentJourney?.milestones || [];
  const cumKm = progress?.cumulative_distance_km || 0;
  const totalKm = currentJourney?.total_distance_km || 1;
  const percentage = progress?.progress_percentage || 0;

  const calTotal = progress?.estimated_calories_total || 0;
  const calRemaining = progress?.estimated_calories_remaining || 0;

  return (
    <div className="space-y-4">
      {/* Sleek Journey Header & Selector Button */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
          <span className="text-[11px] font-bold text-zinc-400 uppercase tracking-wider">
            Percorso Attivo ({allJourneys.length} disponibili)
          </span>
        </div>
        <button
          onClick={() => setIsPickerOpen(true)}
          className="flex items-center space-x-1 px-3 py-1.5 rounded-xl bg-zinc-900 border border-white/10 hover:border-amber-500/40 text-amber-400 text-xs font-bold transition active:scale-95 shadow-sm"
        >
          <Compass className="w-3.5 h-3.5" />
          <span>Cambia Avventura</span>
        </button>
      </div>

      {/* Main Expedition Card */}
      {currentJourney && (
        <div className="glass-panel rounded-3xl p-5 relative overflow-hidden shadow-2xl border border-white/10">
          {/* Subtle background glow */}
          <div className="absolute -top-12 -right-12 w-36 h-36 bg-amber-500/10 rounded-full blur-2xl pointer-events-none" />

          <div className="flex items-start justify-between mb-3 relative">
            <div>
              <span className="text-[10px] uppercase font-black tracking-widest text-amber-400 block mb-0.5">
                {currentJourney.universe}
              </span>
              <h2 className="text-lg font-black text-white tracking-tight leading-snug">
                {currentJourney.title}
              </h2>
            </div>
            <div className="text-right flex-shrink-0 ml-3">
              <span className="text-2xl font-black text-amber-400 font-mono">{percentage}%</span>
              <span className="text-[9px] text-zinc-500 block uppercase font-bold">Completato</span>
            </div>
          </div>

          <p className="text-xs text-zinc-400 mb-4 leading-relaxed line-clamp-3">
            {currentJourney.description}
          </p>

          {/* Progress bar */}
          <div className="w-full bg-zinc-900/90 rounded-full h-3 p-0.5 border border-white/5 relative mb-3">
            <div
              className="h-full rounded-full bg-gradient-to-r from-amber-500 via-orange-500 to-rose-500 transition-all duration-700 shadow-sm shadow-amber-500/30"
              style={{ width: `${Math.min(100, percentage)}%` }}
            />
          </div>

          {/* Distance & Calorie Breakdown */}
          <div className="grid grid-cols-2 gap-2 text-xs pt-3 border-t border-white/5">
            <div className="bg-zinc-900/50 p-2.5 rounded-2xl border border-white/5">
              <span className="text-[10px] text-zinc-500 font-medium block">Distanza</span>
              <div className="flex items-baseline space-x-1 mt-0.5">
                <span className="font-black text-white text-sm">{cumKm}</span>
                <span className="text-zinc-500 text-[10px]">/ {totalKm} km</span>
              </div>
              <span className="text-[9px] text-amber-400/90 block mt-0.5 font-medium">
                Mancano {progress?.remaining_distance_km} km
              </span>
            </div>

            <div className="bg-zinc-900/50 p-2.5 rounded-2xl border border-white/5">
              <span className="text-[10px] text-zinc-500 font-medium block flex items-center space-x-1">
                <Flame className="w-3 h-3 text-rose-500" />
                <span>Calorie Richieste</span>
              </span>
              <div className="flex items-baseline space-x-1 mt-0.5">
                <span className="font-black text-rose-400 text-sm">~{calTotal.toLocaleString('it-IT')}</span>
                <span className="text-zinc-500 text-[10px]">kcal</span>
              </div>
              <span className="text-[9px] text-zinc-400 block mt-0.5 font-medium">
                ~{calRemaining.toLocaleString('it-IT')} kcal rimanenti
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Milestones Vertical Quest Log */}
      <div className="glass-panel-subtle rounded-3xl p-5 border border-white/5">
        <h3 className="text-xs font-bold text-zinc-300 uppercase tracking-wider mb-4 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <MapPin className="w-4 h-4 text-amber-400" />
            <span>Tappe & Checkpoint del Viaggio</span>
          </div>
          <span className="text-[10px] text-zinc-500 font-mono">
            {progress?.unlocked_milestones_count} / {milestones.length}
          </span>
        </h3>

        <div className="space-y-3 relative before:absolute before:inset-0 before:left-3.5 before:w-0.5 before:bg-zinc-800">
          {milestones.map((ms, index) => {
            const isUnlocked = cumKm >= ms.distance_km;
            const isNext = !isUnlocked && (index === 0 || cumKm >= milestones[index - 1].distance_km);

            return (
              <div key={ms.id} className="relative flex items-start space-x-3 text-xs pl-0.5">
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 z-10 transition border ${
                    isUnlocked
                      ? 'bg-amber-500 text-zinc-950 border-amber-400 shadow-md shadow-amber-500/20'
                      : isNext
                      ? 'bg-zinc-900 text-amber-400 border-amber-500/60 animate-pulse'
                      : 'bg-zinc-950 text-zinc-600 border-zinc-800'
                  }`}
                >
                  {isUnlocked ? (
                    <CheckCircle2 className="w-4 h-4" />
                  ) : isNext ? (
                    <Compass className="w-4 h-4" />
                  ) : (
                    <Lock className="w-3.5 h-3.5" />
                  )}
                </div>

                <div
                  className={`flex-1 p-3 rounded-2xl border transition ${
                    isUnlocked
                      ? 'bg-zinc-900/60 border-white/10 text-zinc-200'
                      : isNext
                      ? 'bg-amber-500/5 border-amber-500/30 text-zinc-300 shadow-sm'
                      : 'bg-zinc-950/40 border-white/5 text-zinc-500'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <h4 className={`font-bold tracking-tight ${isUnlocked ? 'text-amber-400' : isNext ? 'text-zinc-100' : 'text-zinc-500'}`}>
                      {ms.name}
                    </h4>
                    <div className="flex items-center space-x-1">
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-zinc-900 border border-white/5 text-zinc-400 font-mono">
                        {ms.distance_km} km
                      </span>
                    </div>
                  </div>

                  {ms.lore_text && (
                    <p className={`text-[11px] leading-relaxed italic ${isUnlocked ? 'text-zinc-300' : 'text-zinc-500'}`}>
                      "{ms.lore_text}"
                    </p>
                  )}

                  {isNext && (
                    <div className="mt-2 pt-2 border-t border-amber-500/20 flex items-center justify-between text-[10px] font-semibold text-amber-400">
                      <span className="flex items-center space-x-1">
                        <Sparkles className="w-3 h-3" />
                        <span>Mancano {Math.max(0, Math.round((ms.distance_km - cumKm) * 10) / 10)} km</span>
                      </span>
                      {ms.estimated_calories && (
                        <span className="text-rose-400 flex items-center space-x-0.5">
                          <Flame className="w-2.5 h-2.5" />
                          <span>~{Math.max(0, Math.round((ms.distance_km - cumKm) * 26))} kcal</span>
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Modern Journey Picker Modal Drawer */}
      {isPickerOpen && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 bg-black/85 backdrop-blur-md animate-in fade-in">
          <div className="w-full max-w-md bg-zinc-950 border-t sm:border border-white/10 rounded-t-3xl sm:rounded-3xl shadow-2xl overflow-hidden max-h-[85vh] flex flex-col">
            <div className="w-12 h-1.5 bg-zinc-700/60 rounded-full mx-auto mt-2.5 sm:hidden" />

            <div className="px-5 py-3.5 border-b border-white/10 flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Compass className="w-4 h-4 text-amber-400" />
                <h3 className="font-bold text-white text-sm">Seleziona Avventura</h3>
              </div>
              <button
                onClick={() => setIsPickerOpen(false)}
                className="p-1 rounded-full text-zinc-400 hover:text-white hover:bg-white/5 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* List of 10 Nerdy Journeys */}
            <div className="p-4 overflow-y-auto space-y-2.5">
              {allJourneys.map((j) => {
                const isActive = currentJourney?.id === j.id;
                return (
                  <div
                    key={j.id}
                    onClick={() => handleSelectJourney(j.id)}
                    className={`p-3.5 rounded-2xl border cursor-pointer transition active:scale-[0.99] flex items-center justify-between ${
                      isActive
                        ? 'bg-amber-500/10 border-amber-500/60 shadow-md shadow-amber-500/10'
                        : 'bg-zinc-900/60 border-white/5 hover:border-white/15 hover:bg-zinc-900'
                    }`}
                  >
                    <div className="overflow-hidden pr-2">
                      <div className="flex items-center space-x-2 mb-0.5">
                        <span className="text-[9px] font-black uppercase tracking-wider text-amber-400">
                          {j.universe}
                        </span>
                        {isActive && (
                          <span className="text-[9px] font-bold px-1.5 py-0.2 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                            Attivo
                          </span>
                        )}
                      </div>
                      <h4 className="font-bold text-xs text-white truncate">{j.title}</h4>
                      <div className="flex items-center space-x-3 text-[10px] text-zinc-400 mt-1">
                        <span>{j.total_distance_km} km totali</span>
                        <span>•</span>
                        <span className="flex items-center space-x-1 text-rose-400">
                          <Flame className="w-2.5 h-2.5" />
                          <span>~{j.estimated_calories_total?.toLocaleString('it-IT')} kcal</span>
                        </span>
                      </div>
                    </div>

                    <div className="flex-shrink-0">
                      {isActive ? (
                        <div className="w-7 h-7 rounded-full bg-amber-500 text-zinc-950 flex items-center justify-center font-bold">
                          <CheckCircle2 className="w-4 h-4" />
                        </div>
                      ) : (
                        <div className="w-7 h-7 rounded-full bg-zinc-800 text-zinc-400 flex items-center justify-center group-hover:bg-zinc-700 transition">
                          <ChevronRight className="w-4 h-4" />
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Milestone Celebration Popup */}
      {celebration && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-in zoom-in-95">
          <div className="w-full max-w-sm glass-panel border-2 border-amber-500/60 rounded-3xl p-6 text-center shadow-2xl relative">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/40 mb-4 animate-bounce">
              <Trophy className="w-8 h-8" />
            </div>

            <span className="text-[10px] uppercase font-black tracking-widest text-amber-400 block mb-1">
              Nuovo Checkpoint Sbloccato!
            </span>
            <h3 className="text-xl font-black text-white mb-1.5">{celebration.milestone_name}</h3>
            <p className="text-xs font-semibold text-amber-300/80 mb-3">{celebration.distance_km} km nel {celebration.journey_title}</p>

            {celebration.lore_text && (
              <p className="text-xs text-zinc-300 italic bg-zinc-950/80 p-3 rounded-2xl border border-white/5 mb-5 leading-relaxed">
                "{celebration.lore_text}"
              </p>
            )}

            <button
              onClick={onClearCelebration}
              className="w-full py-3 bg-gradient-to-r from-amber-500 to-rose-500 text-zinc-950 font-black rounded-xl text-xs hover:opacity-90 active:scale-95 transition shadow-lg shadow-rose-950/30"
            >
              Continua a Pedalare!
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
