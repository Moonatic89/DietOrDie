import React, { useState, useRef } from 'react';
import { Camera, Sparkles, Check, X, AlertCircle, RefreshCw, Layers } from 'lucide-react';
import { analyzeFoodPhoto, createMeal } from '../api';
import { AIAnalyzeFoodResponse, FoodItem } from '../types';

interface MealPhotoModalProps {
  isOpen: boolean;
  selectedDate: string;
  onClose: () => void;
  onMealSaved: () => void;
}

export const MealPhotoModal: React.FC<MealPhotoModalProps> = ({
  isOpen,
  selectedDate,
  onClose,
  onMealSaved
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<AIAnalyzeFoodResponse | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form states for final confirmation
  const [mealType, setMealType] = useState('pranzo');
  const [title, setTitle] = useState('');
  const [calories, setCalories] = useState<number>(0);
  const [protein, setProtein] = useState<number>(0);
  const [carbs, setCarbs] = useState<number>(0);
  const [fat, setFat] = useState<number>(0);
  const [items, setItems] = useState<FoodItem[]>([]);

  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      setFile(selected);
      setPreviewUrl(URL.createObjectURL(selected));
      setError(null);
      setAnalysisResult(null);
    }
  };

  const handleAnalyze = async () => {
    if (!file) return;
    setAnalyzing(true);
    setError(null);

    try {
      const res = await analyzeFoodPhoto(file);
      setAnalysisResult(res);
      setTitle(res.dish_name);
      setCalories(res.estimated_calories);
      setProtein(res.protein_g);
      setCarbs(res.carbs_g);
      setFat(res.fat_g);
      setItems(res.suggested_items || []);
    } catch (err: any) {
      setError(err.message || "Errore durante l'analisi visiva");
    } finally {
      setAnalyzing(false);
    }
  };

  const handleSave = async () => {
    if (!title.trim()) {
      setError('Inserisci un titolo per il pasto');
      return;
    }
    setSaving(true);
    setError(null);

    try {
      await createMeal({
        meal_type: mealType,
        date: selectedDate,
        title,
        total_calories: Number(calories),
        total_protein: Number(protein),
        total_carbs: Number(carbs),
        total_fat: Number(fat),
        image_path: analysisResult?.image_url,
        items
      });
      onMealSaved();
      handleClose();
    } catch (err: any) {
      setError(err.message || 'Errore nel salvataggio del pasto');
    } finally {
      setSaving(false);
    }
  };

  const handleClose = () => {
    setFile(null);
    setPreviewUrl(null);
    setAnalysisResult(null);
    setError(null);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 bg-black/80 backdrop-blur-md animate-in fade-in">
      <div className="w-full max-w-lg bg-zinc-950 border-t sm:border border-white/10 rounded-t-3xl sm:rounded-3xl shadow-2xl overflow-hidden max-h-[92vh] flex flex-col">
        {/* Mobile handle indicator */}
        <div className="w-12 h-1.5 bg-zinc-700/60 rounded-full mx-auto mt-2.5 sm:hidden" />

        {/* Header */}
        <div className="px-5 py-3.5 border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center shadow-inner">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-semibold text-zinc-100 text-sm tracking-tight">Vision Scanner AI</h3>
              <p className="text-[11px] text-zinc-400">Riconoscimento automatico del pasto</p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="p-1.5 rounded-full text-zinc-400 hover:text-white hover:bg-white/5 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 overflow-y-auto space-y-4">
          {error && (
            <div className="p-3 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Camera Viewfinder View */}
          {!previewUrl ? (
            <div
              onClick={() => fileInputRef.current?.click()}
              className="relative aspect-video rounded-2xl border border-dashed border-white/15 hover:border-amber-500/50 bg-zinc-900/40 hover:bg-zinc-900/70 p-6 flex flex-col items-center justify-center cursor-pointer transition group"
            >
              {/* Corner Reticles */}
              <div className="absolute top-3 left-3 w-4 h-4 border-t-2 border-l-2 border-zinc-600 group-hover:border-amber-400 transition" />
              <div className="absolute top-3 right-3 w-4 h-4 border-t-2 border-r-2 border-zinc-600 group-hover:border-amber-400 transition" />
              <div className="absolute bottom-3 left-3 w-4 h-4 border-b-2 border-l-2 border-zinc-600 group-hover:border-amber-400 transition" />
              <div className="absolute bottom-3 right-3 w-4 h-4 border-b-2 border-r-2 border-zinc-600 group-hover:border-amber-400 transition" />

              <div className="w-12 h-12 rounded-2xl bg-white/5 border border-white/10 group-hover:border-amber-500/30 group-hover:bg-amber-500/10 text-zinc-400 group-hover:text-amber-400 flex items-center justify-center mb-2.5 transition">
                <Camera className="w-6 h-6" />
              </div>
              <p className="text-xs font-semibold text-zinc-200">Scatta foto o scegli da galleria</p>
              <p className="text-[10px] text-zinc-500 mt-1">Supporta fotocamera smartphone nativa</p>

              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                capture="environment"
                className="hidden"
                onChange={handleFileChange}
              />
            </div>
          ) : (
            <div className="relative rounded-2xl overflow-hidden border border-white/10 bg-black aspect-video flex items-center justify-center shadow-lg">
              <img src={previewUrl} alt="Preview piatto" className="w-full h-full object-cover" />

              {/* Futuristic scanning beam animation when analyzing */}
              {analyzing && (
                <div className="absolute inset-0 bg-gradient-to-b from-transparent via-amber-400/25 to-transparent animate-scan pointer-events-none" />
              )}

              {/* Viewfinder reticles on photo */}
              <div className="absolute top-3 left-3 w-4 h-4 border-t-2 border-l-2 border-amber-400/80 pointer-events-none" />
              <div className="absolute top-3 right-3 w-4 h-4 border-t-2 border-r-2 border-amber-400/80 pointer-events-none" />
              <div className="absolute bottom-3 left-3 w-4 h-4 border-b-2 border-l-2 border-amber-400/80 pointer-events-none" />
              <div className="absolute bottom-3 right-3 w-4 h-4 border-b-2 border-r-2 border-amber-400/80 pointer-events-none" />

              {!analyzing && (
                <button
                  onClick={() => {
                    setFile(null);
                    setPreviewUrl(null);
                    setAnalysisResult(null);
                  }}
                  className="absolute top-2.5 right-2.5 p-1.5 rounded-full bg-black/70 border border-white/10 text-white hover:bg-black transition"
                  title="Nuova foto"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          )}

          {/* Trigger button */}
          {file && !analysisResult && (
            <button
              onClick={handleAnalyze}
              disabled={analyzing}
              className="w-full py-3 bg-gradient-to-r from-amber-500 via-orange-500 to-rose-500 hover:opacity-90 active:scale-[0.98] text-zinc-950 font-bold rounded-2xl transition flex items-center justify-center space-x-2 shadow-lg shadow-rose-950/20 disabled:opacity-50 text-xs"
            >
              <Sparkles className={`w-4 h-4 ${analyzing ? 'animate-spin' : ''}`} />
              <span>{analyzing ? 'Elaborazione Llama 3.2 Vision...' : 'Analizza Piatto con AI'}</span>
            </button>
          )}

          {/* Confirmation & Edit View */}
          {analysisResult && (
            <div className="space-y-4 pt-1 animate-in fade-in">
              {analysisResult.confidence_notes && (
                <div className="p-3 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-[11px] leading-relaxed">
                  <span className="font-semibold text-amber-400">Analisi: </span>
                  {analysisResult.confidence_notes}
                </div>
              )}

              <div className="grid grid-cols-2 gap-2.5">
                <div>
                  <label className="text-[10px] font-medium text-zinc-400 block mb-1">Pasto</label>
                  <select
                    value={mealType}
                    onChange={(e) => setMealType(e.target.value)}
                    className="w-full bg-zinc-900 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500"
                  >
                    <option value="colazione">Colazione</option>
                    <option value="pranzo">Pranzo</option>
                    <option value="cena">Cena</option>
                    <option value="spuntino">Spuntino</option>
                  </select>
                </div>
                <div>
                  <label className="text-[10px] font-medium text-zinc-400 block mb-1">Nome Piatto</label>
                  <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    className="w-full bg-zinc-900 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500 font-medium"
                  />
                </div>
              </div>

              {/* Macro Pills Grid */}
              <div className="grid grid-cols-4 gap-2 text-center">
                <div className="bg-zinc-900/70 border border-white/10 p-2 rounded-2xl">
                  <span className="text-[9px] text-zinc-400 font-bold uppercase block">Kcal</span>
                  <input
                    type="number"
                    value={calories}
                    onChange={(e) => setCalories(Number(e.target.value))}
                    className="w-full bg-transparent text-center font-black text-amber-400 text-sm focus:outline-none"
                  />
                </div>
                <div className="bg-zinc-900/70 border border-white/10 p-2 rounded-2xl">
                  <span className="text-[9px] text-sky-400 font-bold uppercase block">Prot</span>
                  <input
                    type="number"
                    value={protein}
                    onChange={(e) => setProtein(Number(e.target.value))}
                    className="w-full bg-transparent text-center font-black text-sky-400 text-sm focus:outline-none"
                  />
                  <span className="text-[9px] text-zinc-500">g</span>
                </div>
                <div className="bg-zinc-900/70 border border-white/10 p-2 rounded-2xl">
                  <span className="text-[9px] text-amber-300 font-bold uppercase block">Carb</span>
                  <input
                    type="number"
                    value={carbs}
                    onChange={(e) => setCarbs(Number(e.target.value))}
                    className="w-full bg-transparent text-center font-black text-amber-300 text-sm focus:outline-none"
                  />
                  <span className="text-[9px] text-zinc-500">g</span>
                </div>
                <div className="bg-zinc-900/70 border border-white/10 p-2 rounded-2xl">
                  <span className="text-[9px] text-rose-400 font-bold uppercase block">Grass</span>
                  <input
                    type="number"
                    value={fat}
                    onChange={(e) => setFat(Number(e.target.value))}
                    className="w-full bg-transparent text-center font-black text-rose-400 text-sm focus:outline-none"
                  />
                  <span className="text-[9px] text-zinc-500">g</span>
                </div>
              </div>

              {/* Ingredients list */}
              {items.length > 0 && (
                <div className="space-y-1.5 pt-1">
                  <span className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wider block">
                    Componenti Rilevati
                  </span>
                  <div className="space-y-1.5 max-h-32 overflow-y-auto pr-1">
                    {items.map((item, idx) => (
                      <div key={idx} className="flex items-center justify-between p-2 rounded-xl bg-zinc-900/50 border border-white/5 text-xs">
                        <span className="text-zinc-200 font-medium truncate max-w-[200px]">{item.name}</span>
                        <div className="flex items-center space-x-2 text-zinc-400">
                          {item.portion_g && <span>{item.portion_g}g</span>}
                          <span className="text-amber-400 font-bold">{item.calories} kcal</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <button
                onClick={handleSave}
                disabled={saving}
                className="w-full py-3 bg-emerald-500 hover:bg-emerald-400 active:scale-[0.98] text-zinc-950 font-bold rounded-2xl transition flex items-center justify-center space-x-2 shadow-lg shadow-emerald-950/20 text-xs"
              >
                <Check className="w-4 h-4" />
                <span>{saving ? 'Salvataggio...' : 'Conferma e Inserisci nel Diario'}</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
