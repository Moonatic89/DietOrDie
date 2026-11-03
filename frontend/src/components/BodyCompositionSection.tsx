import React, { useState, useEffect } from 'react';
import {
  BodyCompositionLog,
  BodyCompositionCreateInput,
  BodyCompositionBulkInput,
  AIProgressReview
} from '../types';
import {
  getBodyCompositionLogs,
  addBodyCompositionLog,
  addBodyCompositionBulkJson,
  deleteBodyCompositionLog,
  getBodyCompositionAiReview
} from '../api';
import {
  Activity,
  Plus,
  Trash2,
  Sparkles,
  RefreshCw,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  TrendingDown,
  TrendingUp,
  Flame,
  Droplet,
  Dumbbell,
  HeartPulse,
  Scale,
  Calendar,
  X
} from 'lucide-react';

interface BodyCompositionSectionProps {
  onWeightChanged?: () => void;
}

const SAMPLE_SCALE_JSON = `{
  "peso": "122.40 kg",
  "bmi": 38.2,
  "grasso_corporeo": "37.4%",
  "grasso_sottocutaneo": "31.7%",
  "grasso_viscerale": 20,
  "massa_muscolare": "72.83 kg",
  "percentuale_muscolo_scheletrica": "40.2%",
  "massa_ossea": "3.79 kg",
  "peso_senza_grassi": "76.62 kg",
  "età_metabolica": 43,
  "bmr": 2006,
  "acqua_corporea": "45.2%",
  "proteine": "14.3%"
}`;

export const BodyCompositionSection: React.FC<BodyCompositionSectionProps> = ({ onWeightChanged }) => {
  const [logs, setLogs] = useState<BodyCompositionLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [modalTab, setModalTab] = useState<'bulk' | 'manual'>('bulk');
  const [showHistory, setShowHistory] = useState(false);
  const [copiedTemplate, setCopiedTemplate] = useState(false);

  // AI Review states
  const [aiReview, setAiReview] = useState<AIProgressReview | null>(null);
  const [loadingAi, setLoadingAi] = useState(false);
  const [showAiCard, setShowAiCard] = useState(false);

  // Bulk input form
  const [bulkDate, setBulkDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [rawJson, setRawJson] = useState<string>('');
  const [bulkError, setBulkError] = useState<string | null>(null);

  // Manual input form
  const [manualForm, setManualForm] = useState<BodyCompositionCreateInput>({
    recorded_at: new Date().toISOString().split('T')[0],
    weight_kg: 0,
    bmi: undefined,
    body_fat_pct: undefined,
    subcutaneous_fat_pct: undefined,
    visceral_fat: undefined,
    muscle_mass_kg: undefined,
    skeletal_muscle_pct: undefined,
    bone_mass_kg: undefined,
    fat_free_mass_kg: undefined,
    metabolic_age: undefined,
    bmr_kcal: undefined,
    body_water_pct: undefined,
    protein_pct: undefined,
    notes: ''
  });
  const [submitting, setSubmitting] = useState(false);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const data = await getBodyCompositionLogs();
      setLogs(data);
    } catch (err) {
      console.error('Error fetching body composition logs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  const handleFetchAiReview = async () => {
    setLoadingAi(true);
    setShowAiCard(true);
    try {
      const review = await getBodyCompositionAiReview();
      setAiReview(review);
    } catch (err: any) {
      alert(err.message || 'Errore nella valutazione IA dei progressi');
    } finally {
      setLoadingAi(false);
    }
  };

  const handleCopySample = () => {
    navigator.clipboard.writeText(SAMPLE_SCALE_JSON);
    setCopiedTemplate(true);
    setTimeout(() => setCopiedTemplate(false), 2000);
    if (!rawJson) {
      setRawJson(SAMPLE_SCALE_JSON);
    }
  };

  const handleBulkSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBulkError(null);
    if (!rawJson.trim()) {
      setBulkError('Incolla la stringa JSON dei dati della bilancia');
      return;
    }

    setSubmitting(true);
    try {
      await addBodyCompositionBulkJson({
        recorded_at: bulkDate || undefined,
        raw_json: rawJson
      });
      setShowModal(false);
      setRawJson('');
      await fetchLogs();
      if (onWeightChanged) onWeightChanged();
    } catch (err: any) {
      setBulkError(err.message || 'Errore durante il salvataggio dei dati');
    } finally {
      setSubmitting(false);
    }
  };

  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualForm.weight_kg || manualForm.weight_kg <= 0) {
      alert('Inserisci un valore valido per il peso');
      return;
    }

    setSubmitting(true);
    try {
      await addBodyCompositionLog(manualForm);
      setShowModal(false);
      setManualForm({
        recorded_at: new Date().toISOString().split('T')[0],
        weight_kg: 0,
        bmi: undefined,
        body_fat_pct: undefined,
        subcutaneous_fat_pct: undefined,
        visceral_fat: undefined,
        muscle_mass_kg: undefined,
        skeletal_muscle_pct: undefined,
        bone_mass_kg: undefined,
        fat_free_mass_kg: undefined,
        metabolic_age: undefined,
        bmr_kcal: undefined,
        body_water_pct: undefined,
        protein_pct: undefined,
        notes: ''
      });
      await fetchLogs();
      if (onWeightChanged) onWeightChanged();
    } catch (err: any) {
      alert(err.message || 'Errore durante il salvataggio');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Sei sicuro di voler eliminare questa rilevazione?')) return;
    try {
      await deleteBodyCompositionLog(id);
      await fetchLogs();
      if (onWeightChanged) onWeightChanged();
    } catch (err: any) {
      alert('Errore eliminazione rilevazione');
    }
  };

  const latest = logs.length > 0 ? logs[0] : null;

  // Helper per badge delta
  const renderDelta = (
    val: number | undefined | null,
    unit: string = '',
    reverseGood: boolean = false
  ) => {
    if (val === undefined || val === null || val === 0) return null;
    const isPositive = val > 0;
    // Per peso o grasso: negativo è buono (perdita di grasso)
    // Per muscolo o acqua: positivo è buono (aumento muscolare/idratazione)
    const isGood = reverseGood ? isPositive : !isPositive;

    return (
      <span
        className={`ml-1 text-[10px] font-semibold px-1.5 py-0.5 rounded-full inline-flex items-center space-x-0.5 ${
          isGood
            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
            : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
        }`}
      >
        <span>{isPositive ? `+${val}` : val}</span>
        {unit && <span className="opacity-80">{unit}</span>}
      </span>
    );
  };

  // Helper per renderizzare il Markdown dell'AI
  const renderSimpleMarkdown = (content: string) => {
    const lines = content.split('\n');
    return lines.map((line, idx) => {
      const trimmed = line.trim();
      if (!trimmed) return <div key={idx} className="h-2" />;

      if (trimmed.startsWith('### ')) {
        return (
          <h3 key={idx} className="text-sm font-bold text-amber-400 mt-3 mb-1">
            {trimmed.replace('### ', '')}
          </h3>
        );
      }
      if (trimmed.startsWith('#### ')) {
        return (
          <h4 key={idx} className="text-xs font-bold text-amber-300 mt-2 mb-1">
            {trimmed.replace('#### ', '')}
          </h4>
        );
      }
      if (trimmed.startsWith('- ')) {
        const bulletText = trimmed.replace('- ', '');
        return (
          <li key={idx} className="text-xs text-slate-300 ml-4 list-disc my-0.5 leading-relaxed">
            {renderBoldText(bulletText)}
          </li>
        );
      }

      return (
        <p key={idx} className="text-xs text-slate-300 my-1 leading-relaxed">
          {renderBoldText(trimmed)}
        </p>
      );
    });
  };

  const renderBoldText = (text: string) => {
    const parts = text.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return (
          <strong key={i} className="text-white font-bold">
            {part.slice(2, -2)}
          </strong>
        );
      }
      return part;
    });
  };

  return (
    <div className="space-y-4">
      {/* Header Sezione */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="p-2 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400">
            <Scale className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center space-x-2">
              <span>Bilancia Smart & Bioimpedenza</span>
            </h2>
            <p className="text-[11px] text-slate-400">
              Parametri corporei BIA settimanali (13 indicatori)
            </p>
          </div>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="px-3 py-2 bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-bold text-xs rounded-xl shadow-lg shadow-amber-500/20 flex items-center space-x-1.5 transition"
        >
          <Plus className="w-4 h-4 stroke-[2.5]" />
          <span>Nuova Pesata</span>
        </button>
      </div>

      {/* Scheda Rilevazione Recente */}
      {latest ? (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 shadow-xl relative overflow-hidden">
          {/* Header Ultima Pesata */}
          <div className="flex items-center justify-between mb-4 border-b border-slate-800/80 pb-3">
            <div>
              <div className="text-[11px] uppercase tracking-wider font-semibold text-slate-400 flex items-center space-x-1.5">
                <Calendar className="w-3.5 h-3.5 text-amber-400" />
                <span>Rilevazione del {new Date(latest.recorded_at).toLocaleDateString('it-IT', { day: '2-digit', month: 'long', year: 'numeric' })}</span>
                {latest.delta?.days && (
                  <span className="text-slate-500 text-[10px]">({latest.delta.days}gg fa)</span>
                )}
              </div>
            </div>

            <button
              onClick={handleFetchAiReview}
              disabled={loadingAi}
              className="px-2.5 py-1.5 bg-indigo-500/15 hover:bg-indigo-500/25 border border-indigo-500/30 text-indigo-300 font-semibold text-xs rounded-lg flex items-center space-x-1.5 transition"
            >
              <Sparkles className="w-3.5 h-3.5 text-indigo-400 animate-pulse" />
              <span>{loadingAi ? 'Analisi IA...' : 'Analisi Nutrizionista IA'}</span>
            </button>
          </div>

          {/* Griglia Parametri Principali (Stile App Bilancia Smart) */}
          <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
            {/* Peso */}
            <div className="bg-slate-950/70 border border-slate-800/80 rounded-xl p-3 flex flex-col justify-between">
              <span className="text-[11px] font-medium text-slate-400">Peso Corporeo</span>
              <div className="mt-1 flex items-baseline justify-between">
                <div className="text-xl font-black text-white">
                  {latest.weight_kg.toFixed(2)} <span className="text-xs font-normal text-slate-400">kg</span>
                </div>
                {renderDelta(latest.delta?.weight_kg, 'kg')}
              </div>
            </div>

            {/* BMI */}
            <div className="bg-slate-950/70 border border-slate-800/80 rounded-xl p-3 flex flex-col justify-between">
              <span className="text-[11px] font-medium text-slate-400">BMI</span>
              <div className="mt-1 flex items-baseline justify-between">
                <div className="text-xl font-black text-amber-400">
                  {latest.bmi ? latest.bmi.toFixed(1) : '--'}
                </div>
                {renderDelta(latest.delta?.bmi)}
              </div>
            </div>

            {/* Grasso Corporeo */}
            <div className="bg-slate-950/70 border border-slate-800/80 rounded-xl p-3 flex flex-col justify-between">
              <span className="text-[11px] font-medium text-slate-400">Grasso Corporeo</span>
              <div className="mt-1 flex items-baseline justify-between">
                <div className="text-xl font-black text-rose-400">
                  {latest.body_fat_pct ? `${latest.body_fat_pct.toFixed(1)}%` : '--'}
                </div>
                {renderDelta(latest.delta?.body_fat_pct, '%')}
              </div>
            </div>

            {/* Grasso Viscerale */}
            <div className="bg-slate-950/70 border border-slate-800/80 rounded-xl p-3 flex flex-col justify-between">
              <span className="text-[11px] font-medium text-slate-400">Grasso Viscerale</span>
              <div className="mt-1 flex items-baseline justify-between">
                <div className="text-xl font-black flex items-center space-x-1.5">
                  <span className={latest.visceral_fat && latest.visceral_fat >= 15 ? 'text-red-400' : latest.visceral_fat && latest.visceral_fat >= 10 ? 'text-amber-400' : 'text-emerald-400'}>
                    {latest.visceral_fat ?? '--'}
                  </span>
                  <span className="text-[10px] px-1 py-0.2 rounded font-semibold bg-slate-800 text-slate-300">
                    {latest.visceral_fat && latest.visceral_fat >= 15 ? 'Alto' : latest.visceral_fat && latest.visceral_fat >= 10 ? 'Medio' : 'Ottimo'}
                  </span>
                </div>
                {renderDelta(latest.delta?.visceral_fat)}
              </div>
            </div>

            {/* Massa Muscolare */}
            <div className="bg-slate-950/70 border border-slate-800/80 rounded-xl p-3 flex flex-col justify-between">
              <span className="text-[11px] font-medium text-slate-400">Massa Muscolare</span>
              <div className="mt-1 flex items-baseline justify-between">
                <div className="text-lg font-black text-emerald-400">
                  {latest.muscle_mass_kg ? `${latest.muscle_mass_kg.toFixed(2)}` : '--'} <span className="text-xs font-normal text-slate-400">kg</span>
                </div>
                {renderDelta(latest.delta?.muscle_mass_kg, 'kg', true)}
              </div>
            </div>

            {/* Muscolo Scheletrico */}
            <div className="bg-slate-950/70 border border-slate-800/80 rounded-xl p-3 flex flex-col justify-between">
              <span className="text-[11px] font-medium text-slate-400">Muscolo Scheletrico</span>
              <div className="mt-1 flex items-baseline justify-between">
                <div className="text-lg font-black text-emerald-400">
                  {latest.skeletal_muscle_pct ? `${latest.skeletal_muscle_pct.toFixed(1)}%` : '--'}
                </div>
                {renderDelta(latest.delta?.skeletal_muscle_pct, '%', true)}
              </div>
            </div>

            {/* Acqua Corporea */}
            <div className="bg-slate-950/70 border border-slate-800/80 rounded-xl p-3 flex flex-col justify-between">
              <span className="text-[11px] font-medium text-slate-400">Acqua Corporea</span>
              <div className="mt-1 flex items-baseline justify-between">
                <div className="text-lg font-black text-cyan-400">
                  {latest.body_water_pct ? `${latest.body_water_pct.toFixed(1)}%` : '--'}
                </div>
                {renderDelta(latest.delta?.body_water_pct, '%', true)}
              </div>
            </div>

            {/* Proteine */}
            <div className="bg-slate-950/70 border border-slate-800/80 rounded-xl p-3 flex flex-col justify-between">
              <span className="text-[11px] font-medium text-slate-400">Proteine</span>
              <div className="mt-1 flex items-baseline justify-between">
                <div className="text-lg font-black text-indigo-400">
                  {latest.protein_pct ? `${latest.protein_pct.toFixed(1)}%` : '--'}
                </div>
                {renderDelta(latest.delta?.protein_pct, '%', true)}
              </div>
            </div>
          </div>

          {/* Scheda Altri Parametri Bioimpedenza */}
          <div className="mt-3 pt-3 border-t border-slate-800/60 grid grid-cols-3 sm:grid-cols-5 gap-2 text-center text-xs">
            <div className="bg-slate-950/50 rounded-lg p-2 border border-slate-800/40">
              <span className="text-[10px] text-slate-500 block">Grasso Sottocutaneo</span>
              <span className="font-bold text-slate-300">{latest.subcutaneous_fat_pct ? `${latest.subcutaneous_fat_pct}%` : '--'}</span>
            </div>
            <div className="bg-slate-950/50 rounded-lg p-2 border border-slate-800/40">
              <span className="text-[10px] text-slate-500 block">Massa Magra (FFM)</span>
              <span className="font-bold text-slate-300">{latest.fat_free_mass_kg ? `${latest.fat_free_mass_kg} kg` : '--'}</span>
            </div>
            <div className="bg-slate-950/50 rounded-lg p-2 border border-slate-800/40">
              <span className="text-[10px] text-slate-500 block">Massa Ossea</span>
              <span className="font-bold text-slate-300">{latest.bone_mass_kg ? `${latest.bone_mass_kg} kg` : '--'}</span>
            </div>
            <div className="bg-slate-950/50 rounded-lg p-2 border border-slate-800/40">
              <span className="text-[10px] text-slate-500 block">Età Metabolica</span>
              <span className="font-bold text-amber-300">{latest.metabolic_age ? `${latest.metabolic_age} anni` : '--'}</span>
            </div>
            <div className="bg-slate-950/50 rounded-lg p-2 border border-slate-800/40 col-span-2 sm:col-span-1">
              <span className="text-[10px] text-slate-500 block">Metabolismo (BMR)</span>
              <span className="font-bold text-amber-400">{latest.bmr_kcal ? `${Math.round(latest.bmr_kcal)} kcal` : '--'}</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 text-center">
          <Scale className="w-10 h-10 text-slate-600 mx-auto mb-2" />
          <h3 className="text-sm font-bold text-white mb-1">Nessuna Pesata Registrata</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto mb-4">
            Incolla il risultato JSON dalla tua bilancia o inserisci i dati per iniziare a tracciare la composizione corporea con l'IA.
          </p>
          <button
            onClick={() => setShowModal(true)}
            className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs rounded-xl transition inline-flex items-center space-x-1.5"
          >
            <Plus className="w-4 h-4" />
            <span>Inserisci la Prima Pesata</span>
          </button>
        </div>
      )}

      {/* Card Valutazione Nutrizionista IA */}
      {showAiCard && (
        <div className="bg-gradient-to-br from-indigo-950/40 to-slate-900 border border-indigo-500/30 rounded-2xl p-4 shadow-xl">
          <div className="flex items-center justify-between mb-3 border-b border-indigo-500/20 pb-2.5">
            <div className="flex items-center space-x-2">
              <div className="p-1.5 rounded-lg bg-indigo-500/20 text-indigo-400">
                <Sparkles className="w-4 h-4" />
              </div>
              <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                Valutazione Nutrizionista IA
              </h3>
            </div>
            {aiReview?.overall_trend && (
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full uppercase bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                Trend: {aiReview.overall_trend}
              </span>
            )}
          </div>

          {loadingAi ? (
            <div className="py-6 text-center space-y-2">
              <RefreshCw className="w-6 h-6 text-indigo-400 animate-spin mx-auto" />
              <p className="text-xs text-indigo-200">
                L'IA sta elaborando la tua bioimpedenza e confrontando i trend di massa magra e grasso...
              </p>
            </div>
          ) : aiReview ? (
            <div className="space-y-3">
              <div className="text-xs leading-relaxed text-slate-200">
                {renderSimpleMarkdown(aiReview.review_markdown)}
              </div>

              {aiReview.recommendations && aiReview.recommendations.length > 0 && (
                <div className="mt-3 pt-3 border-t border-indigo-500/20">
                  <h4 className="text-[11px] font-bold text-indigo-300 uppercase tracking-wider mb-2">
                    Consigli per la Settimana:
                  </h4>
                  <ul className="space-y-1.5">
                    {aiReview.recommendations.map((rec, i) => (
                      <li key={i} className="text-xs text-slate-300 flex items-start space-x-2">
                        <span className="text-indigo-400 font-bold">•</span>
                        <span>{rec}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : null}
        </div>
      )}

      {/* Accordion Storico Pesate */}
      {logs.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
          <button
            onClick={() => setShowHistory(!showHistory)}
            className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-slate-850 transition"
          >
            <div className="flex items-center space-x-2">
              <Calendar className="w-4 h-4 text-slate-400" />
              <span className="text-xs font-bold text-slate-300">
                Cronologia Rilevazioni ({logs.length})
              </span>
            </div>
            {showHistory ? (
              <ChevronUp className="w-4 h-4 text-slate-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-slate-400" />
            )}
          </button>

          {showHistory && (
            <div className="border-t border-slate-800 divide-y divide-slate-800/60 max-h-80 overflow-y-auto">
              {logs.map((log) => (
                <div key={log.id} className="p-3 flex items-center justify-between hover:bg-slate-850/50">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-bold text-white">
                        {new Date(log.recorded_at).toLocaleDateString('it-IT')}
                      </span>
                      <span className="text-xs font-black text-amber-400">
                        {log.weight_kg.toFixed(2)} kg
                      </span>
                      {renderDelta(log.delta?.weight_kg, 'kg')}
                    </div>
                    <div className="text-[11px] text-slate-400 flex flex-wrap gap-x-3">
                      <span>Grasso: <strong className="text-rose-400">{log.body_fat_pct ? `${log.body_fat_pct}%` : '--'}</strong></span>
                      <span>Muscolo: <strong className="text-emerald-400">{log.muscle_mass_kg ? `${log.muscle_mass_kg} kg` : '--'}</strong></span>
                      <span>Viscerale: <strong className="text-amber-300">{log.visceral_fat ?? '--'}</strong></span>
                      <span>Acqua: <strong className="text-cyan-400">{log.body_water_pct ? `${log.body_water_pct}%` : '--'}</strong></span>
                    </div>
                  </div>

                  <button
                    onClick={() => handleDelete(log.id)}
                    className="p-1.5 text-slate-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition"
                    title="Elimina rilevazione"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* MODAL NUOVA PESATA */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg shadow-2xl p-4 my-8 relative">
            <button
              onClick={() => setShowModal(false)}
              className="absolute top-4 right-4 p-1 text-slate-400 hover:text-white rounded-lg"
            >
              <X className="w-5 h-5" />
            </button>

            <h3 className="text-base font-bold text-white mb-1 flex items-center space-x-2">
              <Scale className="w-5 h-5 text-amber-400" />
              <span>Nuova Rilevazione Bilancia Smart</span>
            </h3>
            <p className="text-xs text-slate-400 mb-4">
              Aggiungi i dati della pesata settimanale per calcolare i trend di massa magra e grasso.
            </p>

            {/* Tab switch: Bulk JSON vs Manuale */}
            <div className="flex rounded-xl bg-slate-950 p-1 mb-4 border border-slate-800">
              <button
                type="button"
                onClick={() => setModalTab('bulk')}
                className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition ${
                  modalTab === 'bulk'
                    ? 'bg-amber-500 text-slate-950 shadow'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Incolla JSON Bilancia
              </button>
              <button
                type="button"
                onClick={() => setModalTab('manual')}
                className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition ${
                  modalTab === 'manual'
                    ? 'bg-amber-500 text-slate-950 shadow'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Inserimento Manuale
              </button>
            </div>

            {/* TAB 1: BULK JSON */}
            {modalTab === 'bulk' ? (
              <form onSubmit={handleBulkSubmit} className="space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <label className="text-xs font-semibold text-slate-300 block">Data Rilevazione</label>
                    <input
                      type="date"
                      value={bulkDate}
                      onChange={(e) => setBulkDate(e.target.value)}
                      className="mt-1 bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:border-amber-500"
                    />
                  </div>

                  <button
                    type="button"
                    onClick={handleCopySample}
                    className="text-[11px] font-semibold text-amber-400 hover:text-amber-300 flex items-center space-x-1 px-2.5 py-1.5 bg-amber-500/10 border border-amber-500/20 rounded-lg transition"
                  >
                    {copiedTemplate ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copiedTemplate ? 'Copiato!' : 'Copia Template Esempio'}</span>
                  </button>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-xs font-semibold text-slate-300">
                      Oggetto JSON con i dati della bilancia
                    </label>
                    <span className="text-[10px] text-slate-500">Accetta stringhe con unità (es. 122,4 kg, 37.4%)</span>
                  </div>
                  <textarea
                    rows={9}
                    value={rawJson}
                    onChange={(e) => setRawJson(e.target.value)}
                    placeholder={SAMPLE_SCALE_JSON}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 font-mono text-xs text-slate-200 focus:outline-none focus:border-amber-500"
                  />
                </div>

                {bulkError && (
                  <div className="p-2.5 bg-red-500/15 border border-red-500/30 rounded-xl text-xs text-red-300 flex items-start space-x-2">
                    <AlertCircle className="w-4 h-4 flex-shrink-0 text-red-400 mt-0.5" />
                    <span>{bulkError}</span>
                  </div>
                )}

                <div className="flex justify-end space-x-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowModal(false)}
                    className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-xl"
                  >
                    Annulla
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-bold rounded-xl transition"
                  >
                    {submitting ? 'Elaborazione in corso...' : 'Salva Rilevazione da JSON'}
                  </button>
                </div>
              </form>
            ) : (
              /* TAB 2: MANUALE */
              <form onSubmit={handleManualSubmit} className="space-y-3">
                <div className="grid grid-cols-2 gap-2.5">
                  <div>
                    <label className="text-xs font-semibold text-slate-300 block mb-1">Data</label>
                    <input
                      type="date"
                      value={manualForm.recorded_at}
                      onChange={(e) => setManualForm({ ...manualForm, recorded_at: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:border-amber-500"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-slate-300 block mb-1">
                      Peso (kg) <span className="text-amber-400">*</span>
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      required
                      placeholder="122.40"
                      value={manualForm.weight_kg || ''}
                      onChange={(e) => setManualForm({ ...manualForm, weight_kg: parseFloat(e.target.value) || 0 })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-white font-bold focus:outline-none focus:border-amber-500"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-2">
                  <div>
                    <label className="text-[11px] font-semibold text-slate-400 block mb-1">Grasso (%)</label>
                    <input
                      type="number"
                      step="0.1"
                      placeholder="37.4"
                      value={manualForm.body_fat_pct ?? ''}
                      onChange={(e) => setManualForm({ ...manualForm, body_fat_pct: e.target.value ? parseFloat(e.target.value) : undefined })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-amber-500"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] font-semibold text-slate-400 block mb-1">Massa Musc. (kg)</label>
                    <input
                      type="number"
                      step="0.01"
                      placeholder="72.83"
                      value={manualForm.muscle_mass_kg ?? ''}
                      onChange={(e) => setManualForm({ ...manualForm, muscle_mass_kg: e.target.value ? parseFloat(e.target.value) : undefined })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-amber-500"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] font-semibold text-slate-400 block mb-1">Grasso Viscerale</label>
                    <input
                      type="number"
                      step="1"
                      placeholder="20"
                      value={manualForm.visceral_fat ?? ''}
                      onChange={(e) => setManualForm({ ...manualForm, visceral_fat: e.target.value ? parseFloat(e.target.value) : undefined })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-amber-500"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-2">
                  <div>
                    <label className="text-[11px] font-semibold text-slate-400 block mb-1">Acqua (%)</label>
                    <input
                      type="number"
                      step="0.1"
                      placeholder="45.2"
                      value={manualForm.body_water_pct ?? ''}
                      onChange={(e) => setManualForm({ ...manualForm, body_water_pct: e.target.value ? parseFloat(e.target.value) : undefined })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-amber-500"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] font-semibold text-slate-400 block mb-1">Proteine (%)</label>
                    <input
                      type="number"
                      step="0.1"
                      placeholder="14.3"
                      value={manualForm.protein_pct ?? ''}
                      onChange={(e) => setManualForm({ ...manualForm, protein_pct: e.target.value ? parseFloat(e.target.value) : undefined })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-amber-500"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] font-semibold text-slate-400 block mb-1">BMI</label>
                    <input
                      type="number"
                      step="0.1"
                      placeholder="38.2"
                      value={manualForm.bmi ?? ''}
                      onChange={(e) => setManualForm({ ...manualForm, bmi: e.target.value ? parseFloat(e.target.value) : undefined })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-amber-500"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-2">
                  <div>
                    <label className="text-[11px] font-semibold text-slate-400 block mb-1">Musc. Schel. (%)</label>
                    <input
                      type="number"
                      step="0.1"
                      placeholder="40.2"
                      value={manualForm.skeletal_muscle_pct ?? ''}
                      onChange={(e) => setManualForm({ ...manualForm, skeletal_muscle_pct: e.target.value ? parseFloat(e.target.value) : undefined })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-amber-500"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] font-semibold text-slate-400 block mb-1">Massa Ossea (kg)</label>
                    <input
                      type="number"
                      step="0.01"
                      placeholder="3.79"
                      value={manualForm.bone_mass_kg ?? ''}
                      onChange={(e) => setManualForm({ ...manualForm, bone_mass_kg: e.target.value ? parseFloat(e.target.value) : undefined })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-amber-500"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] font-semibold text-slate-400 block mb-1">Massa Magra (kg)</label>
                    <input
                      type="number"
                      step="0.01"
                      placeholder="76.62"
                      value={manualForm.fat_free_mass_kg ?? ''}
                      onChange={(e) => setManualForm({ ...manualForm, fat_free_mass_kg: e.target.value ? parseFloat(e.target.value) : undefined })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-amber-500"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2.5">
                  <div>
                    <label className="text-[11px] font-semibold text-slate-400 block mb-1">Età Metabolica</label>
                    <input
                      type="number"
                      placeholder="43"
                      value={manualForm.metabolic_age ?? ''}
                      onChange={(e) => setManualForm({ ...manualForm, metabolic_age: e.target.value ? parseInt(e.target.value) : undefined })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:border-amber-500"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] font-semibold text-slate-400 block mb-1">BMR (kcal)</label>
                    <input
                      type="number"
                      placeholder="2006"
                      value={manualForm.bmr_kcal ?? ''}
                      onChange={(e) => setManualForm({ ...manualForm, bmr_kcal: e.target.value ? parseFloat(e.target.value) : undefined })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:border-amber-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-300 block mb-1">Note</label>
                  <input
                    type="text"
                    placeholder="Es. Pesata del lunedì mattina a digiuno"
                    value={manualForm.notes || ''}
                    onChange={(e) => setManualForm({ ...manualForm, notes: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:border-amber-500"
                  />
                </div>

                <div className="flex justify-end space-x-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowModal(false)}
                    className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-xl"
                  >
                    Annulla
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-bold rounded-xl transition"
                  >
                    {submitting ? 'Salvataggio...' : 'Salva Rilevazione'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
