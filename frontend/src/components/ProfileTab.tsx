import React, { useState, useEffect } from 'react';
import { User, WeightLog, HealthMetrics } from '../types';
import { updateProfile, getHealthMetrics, getWeightHistory, addWeightLog } from '../api';
import { BodyCompositionSection } from './BodyCompositionSection';
import {
  User as UserIcon,
  Activity,
  Heart,
  Scale,
  Target,
  TrendingDown,
  TrendingUp,
  Plus,
  Save,
  Check,
  Calendar,
  Zap,
  Sparkles
} from 'lucide-react';

interface ProfileTabProps {
  user: User;
  onProfileUpdated: () => void;
}

export const ProfileTab: React.FC<ProfileTabProps> = ({ user, onProfileUpdated }) => {
  const [metrics, setMetrics] = useState<HealthMetrics | null>(user.metrics || null);
  const [weightLogs, setWeightLogs] = useState<WeightLog[]>([]);
  const [newWeight, setNewWeight] = useState<string>('');
  const [addingWeight, setAddingWeight] = useState(false);
  const [savingProfile, setSavingProfile] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Form states
  const [height, setHeight] = useState<string>(String(user.profile?.height_cm || '175'));
  const [weight, setWeight] = useState<string>(String(user.profile?.current_weight_kg || '75'));
  const [targetWeight, setTargetWeight] = useState<string>(String(user.profile?.target_weight_kg || '70'));
  const [gender, setGender] = useState<string>(user.profile?.gender || 'male');
  const [birthDate, setBirthDate] = useState<string>(user.profile?.birth_date || '1992-01-01');
  const [activityLevel, setActivityLevel] = useState<string>(user.profile?.activity_level || 'sedentary');
  const [calorieTarget, setCalorieTarget] = useState<string>(String(user.profile?.daily_calorie_target || '2000'));

  const fetchData = async () => {
    try {
      const [m, logs] = await Promise.all([getHealthMetrics(), getWeightHistory()]);
      setMetrics(m);
      setWeightLogs(logs);
    } catch (err) {
      console.error('Error fetching profile data:', err);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingProfile(true);
    try {
      await updateProfile({
        height_cm: Number(height),
        current_weight_kg: Number(weight),
        target_weight_kg: Number(targetWeight),
        gender,
        birth_date: birthDate,
        activity_level: activityLevel,
        daily_calorie_target: Number(calorieTarget)
      });
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2500);
      onProfileUpdated();
      fetchData();
    } catch (err: any) {
      alert(err.message || 'Errore durante il salvataggio del profilo');
    } finally {
      setSavingProfile(false);
    }
  };

  const handleAddWeightLog = async (e: React.FormEvent) => {
    e.preventDefault();
    const w = Number(newWeight);
    if (!w || w <= 0) return;

    setAddingWeight(true);
    try {
      await addWeightLog(w);
      setWeight(String(w));
      setNewWeight('');
      fetchData();
      onProfileUpdated();
    } catch (err: any) {
      alert('Errore nel salvataggio del peso');
    } finally {
      setAddingWeight(false);
    }
  };

  const bmiVal = metrics?.bmi || 0;
  const bmiCat = metrics?.bmi_category || 'N/D';

  const getBmiColor = (bmi: number) => {
    if (bmi < 18.5) return 'text-sky-400 bg-sky-500/10 border-sky-500/30';
    if (bmi < 25.0) return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';
    if (bmi < 30.0) return 'text-amber-400 bg-amber-500/10 border-amber-500/30';
    return 'text-rose-400 bg-rose-500/10 border-rose-500/30';
  };

  return (
    <div className="space-y-5 pb-24">
      {/* BMI & Metabolic Health Card */}
      <div className="bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-slate-800 rounded-3xl p-5 shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded-xl bg-amber-500/10 text-amber-400 flex items-center justify-center">
              <Activity className="w-4 h-4" />
            </div>
            <h3 className="font-bold text-white text-sm">Indice di Massa Corporea (BMI)</h3>
          </div>
          <span className={`text-xs font-black px-2.5 py-1 rounded-full border ${getBmiColor(bmiVal)}`}>
            {bmiCat}
          </span>
        </div>

        <div className="flex items-baseline space-x-3 mb-4">
          <span className="text-4xl font-black text-white">{bmiVal}</span>
          <span className="text-xs text-slate-400 font-semibold">BMI calcolato</span>
        </div>

        {/* Visual BMI Bar */}
        <div className="w-full bg-slate-950 rounded-full h-3 p-0.5 border border-slate-800 relative mb-3">
          <div className="w-full h-full rounded-full flex overflow-hidden">
            <div className="w-[18.5%] bg-sky-400/80" title="Sottopeso" />
            <div className="w-[25%] bg-emerald-400/80" title="Normopeso" />
            <div className="w-[20%] bg-amber-400/80" title="Sovrappeso" />
            <div className="w-[36.5%] bg-rose-500/80" title="Obesità" />
          </div>
        </div>

        <div className="flex justify-between text-[9px] text-slate-500 font-bold px-1 mb-4">
          <span>18.5</span>
          <span>25.0</span>
          <span>30.0</span>
          <span>35+</span>
        </div>

        {/* Metabolic Rates */}
        <div className="grid grid-cols-3 gap-2 text-center pt-3 border-t border-slate-800 text-xs">
          <div className="bg-slate-950/50 p-2.5 rounded-xl border border-slate-800">
            <span className="text-[10px] text-slate-400 block font-semibold">BMR Basale</span>
            <span className="font-bold text-slate-200 text-sm">{metrics?.bmr || 0}</span>
            <span className="text-[9px] text-slate-500 block">kcal/giorno</span>
          </div>
          <div className="bg-slate-950/50 p-2.5 rounded-xl border border-slate-800">
            <span className="text-[10px] text-slate-400 block font-semibold">TDEE Totale</span>
            <span className="font-bold text-slate-200 text-sm">{metrics?.tdee || 0}</span>
            <span className="text-[9px] text-slate-500 block">kcal/giorno</span>
          </div>
          <div className="bg-slate-950/50 p-2.5 rounded-xl border border-slate-800">
            <span className="text-[10px] text-amber-400 block font-semibold">Consigliate</span>
            <span className="font-bold text-amber-400 text-sm">{metrics?.recommended_calories || 2000}</span>
            <span className="text-[9px] text-slate-500 block">kcal target</span>
          </div>
        </div>
      </div>

      {/* Bioimpedance Smart Scale & AI Progress Section */}
      <BodyCompositionSection
        onWeightChanged={() => {
          fetchData();
          onProfileUpdated();
        }}
      />

      {/* Quick Weight Logger */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-5 shadow-xl">
        <div className="flex items-center space-x-2 mb-3">
          <Scale className="w-4 h-4 text-amber-400" />
          <h3 className="font-bold text-white text-sm">Registra Peso Odierno</h3>
        </div>

        <form onSubmit={handleAddWeightLog} className="flex space-x-2">
          <div className="relative flex-1">
            <input
              type="number"
              step="0.1"
              required
              placeholder="es. 74.5"
              value={newWeight}
              onChange={(e) => setNewWeight(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white font-bold focus:outline-none focus:border-amber-500"
            />
            <span className="absolute right-3 top-2.5 text-xs text-slate-500">kg</span>
          </div>
          <button
            type="submit"
            disabled={addingWeight}
            className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 font-black rounded-xl text-xs transition flex items-center space-x-1"
          >
            <Plus className="w-4 h-4" />
            <span>{addingWeight ? 'Salvataggio...' : 'Registra'}</span>
          </button>
        </form>

        {/* Weight logs list */}
        {weightLogs.length > 0 && (
          <div className="mt-4 pt-3 border-t border-slate-800/80">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-2">
              Storico Recente
            </span>
            <div className="space-y-1.5 max-h-32 overflow-y-auto pr-1">
              {weightLogs.slice(0, 5).map((log, index) => {
                const prevLog = weightLogs[index + 1];
                const diff = prevLog ? (log.weight_kg - prevLog.weight_kg).toFixed(1) : null;

                return (
                  <div
                    key={log.id}
                    className="flex items-center justify-between p-2 rounded-xl bg-slate-950/60 border border-slate-800/80 text-xs"
                  >
                    <span className="text-slate-400">{log.recorded_at}</span>
                    <div className="flex items-center space-x-2">
                      <span className="font-black text-slate-200">{log.weight_kg} kg</span>
                      {diff && (
                        <span className={`text-[10px] font-bold ${Number(diff) <= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {Number(diff) > 0 ? `+${diff}` : diff} kg
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Edit Personal Profile Parameters */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-5 shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <UserIcon className="w-4 h-4 text-amber-400" />
            <h3 className="font-bold text-white text-sm">Parametri Fisici Personali</h3>
          </div>
          {saveSuccess && (
            <span className="text-xs text-emerald-400 font-bold flex items-center space-x-1 animate-in fade-in">
              <Check className="w-3.5 h-3.5" />
              <span>Salvato!</span>
            </span>
          )}
        </div>

        <form onSubmit={handleSaveProfile} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-slate-400 block mb-1">Sesso</label>
              <select
                value={gender}
                onChange={(e) => setGender(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500"
              >
                <option value="male">Uomo</option>
                <option value="female">Donna</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-400 block mb-1">Data di Nascita</label>
              <input
                type="date"
                value={birthDate}
                onChange={(e) => setBirthDate(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500"
              >
              </input>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2">
            <div>
              <label className="text-xs font-semibold text-slate-400 block mb-1">Altezza (cm)</label>
              <input
                type="number"
                step="0.5"
                value={height}
                onChange={(e) => setHeight(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-2.5 py-2 text-xs text-white font-bold focus:outline-none focus:border-amber-500"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-400 block mb-1">Peso (kg)</label>
              <input
                type="number"
                step="0.1"
                value={weight}
                onChange={(e) => setWeight(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-2.5 py-2 text-xs text-white font-bold focus:outline-none focus:border-amber-500"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-400 block mb-1">Target (kg)</label>
              <input
                type="number"
                step="0.1"
                value={targetWeight}
                onChange={(e) => setTargetWeight(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-2.5 py-2 text-xs text-white font-bold focus:outline-none focus:border-amber-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-slate-400 block mb-1">Livello di Attività</label>
              <select
                value={activityLevel}
                onChange={(e) => setActivityLevel(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500"
              >
                <option value="sedentary">Sedentario (Ufficio)</option>
                <option value="light">Leggero (1-2 allenamenti/sett)</option>
                <option value="moderate">Moderato (3-5 allenamenti/sett)</option>
                <option value="active">Molto attivo (6-7 allenamenti/sett)</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-400 block mb-1">Target Calorie (kcal)</label>
              <input
                type="number"
                value={calorieTarget}
                onChange={(e) => setCalorieTarget(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white font-bold focus:outline-none focus:border-amber-500"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={savingProfile}
            className="w-full py-2.5 bg-slate-800 hover:bg-slate-750 border border-slate-700 text-amber-400 font-bold rounded-xl text-xs transition flex items-center justify-center space-x-2 mt-2"
          >
            <Save className="w-3.5 h-3.5" />
            <span>{savingProfile ? 'Aggiornamento...' : 'Aggiorna Profilo e Ricalcola Parametri'}</span>
          </button>
        </form>
      </div>
    </div>
  );
};
