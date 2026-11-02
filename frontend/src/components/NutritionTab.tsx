import React, { useState, useEffect } from 'react';
import { DailyNutritionSummary, MealEntry, User } from '../types';
import { getDailySummary, deleteMeal, createMeal } from '../api';
import { MealPhotoModal } from './MealPhotoModal';
import {
  Camera,
  Plus,
  Trash2,
  Flame,
  Bike,
  Coffee,
  Sun,
  Moon,
  Apple,
  Sparkles,
  ChevronRight,
  Utensils
} from 'lucide-react';

interface NutritionTabProps {
  user: User;
  selectedDate: string;
}

export const NutritionTab: React.FC<NutritionTabProps> = ({ user, selectedDate }) => {
  const [summary, setSummary] = useState<DailyNutritionSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [isPhotoModalOpen, setIsPhotoModalOpen] = useState(false);
  const [isManualModalOpen, setIsManualModalOpen] = useState(false);

  // Manual modal form states
  const [manualTitle, setManualTitle] = useState('');
  const [manualMealType, setManualMealType] = useState('pranzo');
  const [manualCalories, setManualCalories] = useState<number>(0);
  const [manualProtein, setManualProtein] = useState<number>(0);
  const [manualCarbs, setManualCarbs] = useState<number>(0);
  const [manualFat, setManualFat] = useState<number>(0);

  const fetchSummary = async () => {
    setLoading(true);
    try {
      const data = await getDailySummary(selectedDate);
      setSummary(data);
    } catch (err) {
      console.error('Error fetching summary:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSummary();
  }, [selectedDate]);

  const handleDeleteMeal = async (mealId: number) => {
    if (confirm('Vuoi davvero eliminare questo pasto?')) {
      try {
        await deleteMeal(mealId);
        fetchSummary();
      } catch (err) {
        alert('Errore durante l\'eliminazione del pasto');
      }
    }
  };

  const handleCreateManualMeal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualTitle) return;

    try {
      await createMeal({
        meal_type: manualMealType,
        date: selectedDate,
        title: manualTitle,
        total_calories: Number(manualCalories),
        total_protein: Number(manualProtein),
        total_carbs: Number(manualCarbs),
        total_fat: Number(manualFat),
      });
      setIsManualModalOpen(false);
      setManualTitle('');
      setManualCalories(0);
      setManualProtein(0);
      setManualCarbs(0);
      setManualFat(0);
      fetchSummary();
    } catch (err) {
      alert('Errore nel salvataggio del pasto');
    }
  };

  const targetCal = summary?.target_calories || 2000;
  const consumedCal = summary?.consumed_calories || 0;
  const burnedCal = summary?.burned_calories || 0;
  const netCal = summary?.net_calories || 0;
  const remainingCal = Math.round(targetCal - netCal);
  const progressPercent = Math.min(100, Math.max(0, Math.round((netCal / targetCal) * 100)));

  const mealTypes = [
    { key: 'colazione', label: 'Colazione', icon: Coffee, color: 'text-amber-400 bg-amber-500/10 border-amber-500/20' },
    { key: 'pranzo', label: 'Pranzo', icon: Sun, color: 'text-orange-400 bg-orange-500/10 border-orange-500/20' },
    { key: 'cena', label: 'Cena', icon: Moon, color: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20' },
    { key: 'spuntino', label: 'Spuntini', icon: Apple, color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' },
  ];

  return (
    <div className="space-y-4">
      {/* Sleek Caloric HUD Card */}
      <div className="glass-panel rounded-3xl p-5 relative overflow-hidden shadow-2xl">
        <div className="flex items-center justify-between mb-4">
          <div>
            <span className="text-[10px] font-bold tracking-widest uppercase text-zinc-400 block">
              Budget Calorico
            </span>
            <div className="flex items-baseline space-x-1.5 mt-0.5">
              <span className={`text-3xl font-black tracking-tight ${remainingCal >= 0 ? 'text-zinc-100' : 'text-rose-400'}`}>
                {remainingCal}
              </span>
              <span className="text-xs text-zinc-500 font-medium">kcal residue</span>
            </div>
          </div>

          <div className="flex items-center space-x-1.5 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs font-semibold">
            <span className={remainingCal >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
              {progressPercent}%
            </span>
            <span className="text-zinc-500">speso</span>
          </div>
        </div>

        {/* Dual-tone Progress Bar */}
        <div className="w-full bg-zinc-900/90 rounded-full h-2.5 p-0.5 border border-white/5 mb-4">
          <div
            className={`h-full rounded-full transition-all duration-700 ${
              remainingCal < 0
                ? 'bg-rose-500 shadow-md shadow-rose-500/30'
                : 'bg-gradient-to-r from-amber-500 via-orange-500 to-rose-500'
            }`}
            style={{ width: `${progressPercent}%` }}
          />
        </div>

        {/* 3 Metric Pills */}
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <div className="bg-zinc-900/60 p-2.5 rounded-2xl border border-white/5">
            <span className="text-[10px] text-zinc-500 uppercase font-semibold block">Target</span>
            <span className="font-bold text-zinc-200 text-sm">{targetCal}</span>
            <span className="text-[9px] text-zinc-600 block">kcal</span>
          </div>
          <div className="bg-zinc-900/60 p-2.5 rounded-2xl border border-white/5">
            <span className="text-[10px] text-amber-400 uppercase font-semibold block flex items-center justify-center space-x-1">
              <Flame className="w-3 h-3" />
              <span>Assunte</span>
            </span>
            <span className="font-bold text-amber-400 text-sm">{consumedCal}</span>
            <span className="text-[9px] text-zinc-600 block">kcal</span>
          </div>
          <div className="bg-zinc-900/60 p-2.5 rounded-2xl border border-white/5">
            <span className="text-[10px] text-emerald-400 uppercase font-semibold block flex items-center justify-center space-x-1">
              <Bike className="w-3 h-3" />
              <span>Bruciate</span>
            </span>
            <span className="font-bold text-emerald-400 text-sm">-{burnedCal}</span>
            <span className="text-[9px] text-zinc-600 block">kcal</span>
          </div>
        </div>

        {/* Macronutrient Bars */}
        <div className="mt-4 pt-3.5 border-t border-white/5">
          <div className="grid grid-cols-3 gap-2 text-xs">
            {/* Protein */}
            <div className="p-2.5 rounded-2xl bg-sky-500/5 border border-sky-500/15">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-bold text-sky-400 uppercase">Proteine</span>
                <span className="text-xs font-black text-sky-300">{summary?.total_protein || 0}g</span>
              </div>
              <div className="w-full bg-zinc-900 rounded-full h-1 overflow-hidden">
                <div className="h-full bg-sky-400 rounded-full" style={{ width: `${Math.min(100, ((summary?.total_protein || 0) / 140) * 100)}%` }} />
              </div>
            </div>

            {/* Carbs */}
            <div className="p-2.5 rounded-2xl bg-amber-500/5 border border-amber-500/15">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-bold text-amber-400 uppercase">Carbo</span>
                <span className="text-xs font-black text-amber-300">{summary?.total_carbs || 0}g</span>
              </div>
              <div className="w-full bg-zinc-900 rounded-full h-1 overflow-hidden">
                <div className="h-full bg-amber-400 rounded-full" style={{ width: `${Math.min(100, ((summary?.total_carbs || 0) / 220) * 100)}%` }} />
              </div>
            </div>

            {/* Fat */}
            <div className="p-2.5 rounded-2xl bg-rose-500/5 border border-rose-500/15">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-bold text-rose-400 uppercase">Grassi</span>
                <span className="text-xs font-black text-rose-300">{summary?.total_fat || 0}g</span>
              </div>
              <div className="w-full bg-zinc-900 rounded-full h-1 overflow-hidden">
                <div className="h-full bg-rose-400 rounded-full" style={{ width: `${Math.min(100, ((summary?.total_fat || 0) / 65) * 100)}%` }} />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Action Buttons: Vision AI vs Manual */}
      <div className="grid grid-cols-2 gap-2.5">
        <button
          onClick={() => setIsPhotoModalOpen(true)}
          className="p-3.5 bg-gradient-to-r from-amber-500 via-orange-500 to-rose-500 hover:opacity-95 active:scale-[0.98] text-zinc-950 font-bold rounded-2xl transition shadow-lg shadow-rose-950/25 flex items-center justify-center space-x-2"
        >
          <Camera className="w-4 h-4" />
          <span className="text-xs">Foto Pasto (AI)</span>
        </button>
        <button
          onClick={() => setIsManualModalOpen(true)}
          className="p-3.5 bg-zinc-900 hover:bg-zinc-800/80 active:scale-[0.98] border border-white/10 text-zinc-200 font-semibold rounded-2xl transition flex items-center justify-center space-x-2"
        >
          <Plus className="w-4 h-4 text-amber-400" />
          <span className="text-xs">Inserisci Manuale</span>
        </button>
      </div>

      {/* Meals Grouped by Type */}
      <div className="space-y-3 pt-1">
        {mealTypes.map((type) => {
          const mealsOfType = summary?.meals.filter((m) => m.meal_type === type.key) || [];
          const totalOfType = mealsOfType.reduce((acc, m) => acc + m.total_calories, 0);
          const Icon = type.icon;

          return (
            <div key={type.key} className="glass-panel-subtle rounded-2xl p-4 transition hover:border-white/10">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2.5">
                  <div className={`w-7 h-7 rounded-xl border flex items-center justify-center ${type.color}`}>
                    <Icon className="w-3.5 h-3.5" />
                  </div>
                  <h3 className="font-semibold text-xs text-zinc-200 tracking-tight">{type.label}</h3>
                </div>
                <span className="text-xs font-bold text-amber-400 font-mono">{Math.round(totalOfType)} kcal</span>
              </div>

              {mealsOfType.length === 0 ? (
                <p className="text-[11px] text-zinc-600 italic py-1">Nessun pasto registrato.</p>
              ) : (
                <div className="space-y-2 mt-2">
                  {mealsOfType.map((m) => (
                    <div
                      key={m.id}
                      className="flex items-center justify-between p-2.5 rounded-xl bg-zinc-950/60 border border-white/5 hover:border-white/10 transition"
                    >
                      <div className="flex items-center space-x-2.5 overflow-hidden">
                        {m.image_path ? (
                          <img
                            src={m.image_path}
                            alt={m.title}
                            className="w-10 h-10 rounded-xl object-cover flex-shrink-0 border border-white/10"
                          />
                        ) : (
                          <div className="w-10 h-10 rounded-xl bg-zinc-900 border border-white/5 flex items-center justify-center flex-shrink-0 text-zinc-500">
                            <Utensils className="w-4 h-4" />
                          </div>
                        )}
                        <div className="overflow-hidden">
                          <h4 className="text-xs font-bold text-zinc-100 truncate">{m.title}</h4>
                          <p className="text-[10px] text-zinc-400 mt-0.5">
                            <span className="text-amber-400 font-semibold">{m.total_calories} kcal</span>
                            <span className="text-zinc-600"> • </span>
                            P:{m.total_protein}g C:{m.total_carbs}g G:{m.total_fat}g
                          </p>
                        </div>
                      </div>
                      <button
                        onClick={() => handleDeleteMeal(m.id)}
                        className="p-1.5 rounded-lg text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 transition ml-2 flex-shrink-0"
                        title="Elimina"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* AI Photo Modal */}
      <MealPhotoModal
        isOpen={isPhotoModalOpen}
        selectedDate={selectedDate}
        onClose={() => setIsPhotoModalOpen(false)}
        onMealSaved={fetchSummary}
      />

      {/* Manual Meal Modal */}
      {isManualModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in">
          <div className="w-full max-w-sm bg-zinc-950 border border-white/10 rounded-3xl p-5 shadow-2xl">
            <h3 className="font-semibold text-zinc-100 text-sm mb-3.5">Inserimento Pasto Rapido</h3>
            <form onSubmit={handleCreateManualMeal} className="space-y-3">
              <div>
                <label className="text-[10px] font-medium text-zinc-400 block mb-1">Pasto</label>
                <select
                  value={manualMealType}
                  onChange={(e) => setManualMealType(e.target.value)}
                  className="w-full bg-zinc-900 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none"
                >
                  <option value="colazione">Colazione</option>
                  <option value="pranzo">Pranzo</option>
                  <option value="cena">Cena</option>
                  <option value="spuntino">Spuntino</option>
                </select>
              </div>
              <div>
                <label className="text-[10px] font-medium text-zinc-400 block mb-1">Descrizione / Nome</label>
                <input
                  type="text"
                  required
                  placeholder="es. Pasta al pomodoro e parmigiano"
                  value={manualTitle}
                  onChange={(e) => setManualTitle(e.target.value)}
                  className="w-full bg-zinc-900 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none font-medium"
                />
              </div>
              <div className="grid grid-cols-4 gap-2 text-center">
                <div className="bg-zinc-900/60 p-2 rounded-xl border border-white/5">
                  <span className="text-[9px] text-zinc-400 block">Kcal</span>
                  <input
                    type="number"
                    value={manualCalories}
                    onChange={(e) => setManualCalories(Number(e.target.value))}
                    className="w-full bg-transparent text-center text-xs text-amber-400 font-bold focus:outline-none"
                  />
                </div>
                <div className="bg-zinc-900/60 p-2 rounded-xl border border-white/5">
                  <span className="text-[9px] text-sky-400 block">Prot</span>
                  <input
                    type="number"
                    value={manualProtein}
                    onChange={(e) => setManualProtein(Number(e.target.value))}
                    className="w-full bg-transparent text-center text-xs text-sky-400 font-bold focus:outline-none"
                  />
                </div>
                <div className="bg-zinc-900/60 p-2 rounded-xl border border-white/5">
                  <span className="text-[9px] text-amber-300 block">Carb</span>
                  <input
                    type="number"
                    value={manualCarbs}
                    onChange={(e) => setManualCarbs(Number(e.target.value))}
                    className="w-full bg-transparent text-center text-xs text-amber-300 font-bold focus:outline-none"
                  />
                </div>
                <div className="bg-zinc-900/60 p-2 rounded-xl border border-white/5">
                  <span className="text-[9px] text-rose-400 block">Grass</span>
                  <input
                    type="number"
                    value={manualFat}
                    onChange={(e) => setManualFat(Number(e.target.value))}
                    className="w-full bg-transparent text-center text-xs text-rose-400 font-bold focus:outline-none"
                  />
                </div>
              </div>
              <div className="flex space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsManualModalOpen(false)}
                  className="w-1/2 py-2.5 rounded-xl bg-zinc-900 border border-white/10 text-zinc-300 text-xs font-semibold hover:bg-zinc-800 transition"
                >
                  Annulla
                </button>
                <button
                  type="submit"
                  className="w-1/2 py-2.5 rounded-xl bg-amber-500 text-zinc-950 text-xs font-bold hover:bg-amber-400 transition"
                >
                  Salva
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
