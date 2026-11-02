import React, { useState, useEffect } from 'react';
import { login, register, getUsersList } from '../api';
import { User } from '../types';
import { Lock, User as UserIcon, LogIn, UserPlus, Flame, Users } from 'lucide-react';

interface AuthModalProps {
  isOpen: boolean;
  onSuccess: () => void;
  onClose?: () => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onSuccess, onClose }) => {
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [existingUsers, setExistingUsers] = useState<Array<{ id: number; username: string; full_name?: string }>>([]);

  useEffect(() => {
    if (isOpen) {
      getUsersList().then(setExistingUsers).catch(() => {});
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (isRegister) {
        await register(username, password, fullName);
      } else {
        await login(username, password);
      }
      onSuccess();
    } catch (err: any) {
      setError(err.message || 'Errore durante l\'autenticazione');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectExistingUser = (u: { username: string; full_name?: string }) => {
    setUsername(u.username);
    setFullName(u.full_name || '');
    setIsRegister(false);
    setPassword('');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in">
      <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden p-6 relative">
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-gradient-to-tr from-amber-500 to-rose-500 text-white mb-3 shadow-lg shadow-rose-950/50">
            <Flame className="w-6 h-6" />
          </div>
          <h2 className="text-xl font-black text-white tracking-wide">
            {isRegister ? 'Crea il tuo Account' : 'Bentornato su DietOrDie'}
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            {isRegister
              ? 'Registrati per iniziare a monitorare pasti, BMI e le tue pedalate.'
              : 'Seleziona il tuo profilo o inserisci le credenziali.'}
          </p>
        </div>

        {/* Quick User Picker */}
        {!isRegister && existingUsers.length > 0 && (
          <div className="mb-5">
            <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-2">
              Profili Salvati
            </label>
            <div className="grid grid-cols-2 gap-2">
              {existingUsers.map((u) => (
                <button
                  key={u.id}
                  type="button"
                  onClick={() => handleSelectExistingUser(u)}
                  className={`p-2.5 rounded-xl border text-left flex items-center space-x-2 transition ${
                    username === u.username
                      ? 'bg-amber-500/10 border-amber-500/50 text-amber-300'
                      : 'bg-slate-800/60 border-slate-700/60 hover:bg-slate-800 text-slate-300'
                  }`}
                >
                  <div className="w-7 h-7 rounded-full bg-slate-700 flex items-center justify-center text-xs font-bold text-amber-400">
                    {u.full_name ? u.full_name[0].toUpperCase() : u.username[0].toUpperCase()}
                  </div>
                  <div className="overflow-hidden">
                    <p className="text-xs font-bold truncate">{u.full_name || u.username}</p>
                    <p className="text-[10px] text-slate-400 truncate">@{u.username}</p>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs text-center">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {isRegister && (
            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">Nome Completo</label>
              <div className="relative">
                <UserIcon className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="es. Mario o Anna"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-amber-500 transition"
                />
              </div>
            </div>
          )}

          <div>
            <label className="text-xs font-semibold text-slate-300 block mb-1">Nome Utente</label>
            <div className="relative">
              <UserIcon className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value.toLowerCase().trim())}
                placeholder="es. mario"
                className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-amber-500 transition"
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-300 block mb-1">Password</label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-amber-500 transition"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-2 bg-gradient-to-r from-amber-500 to-rose-500 hover:from-amber-400 hover:to-rose-400 text-slate-950 font-black py-2.5 rounded-xl transition shadow-lg shadow-rose-950/30 flex items-center justify-center space-x-2 disabled:opacity-50"
          >
            {loading ? (
              <span className="text-sm">Accesso in corso...</span>
            ) : isRegister ? (
              <>
                <UserPlus className="w-4 h-4" />
                <span className="text-sm">Registrati</span>
              </>
            ) : (
              <>
                <LogIn className="w-4 h-4" />
                <span className="text-sm">Entra nel Profilo</span>
              </>
            )}
          </button>
        </form>

        <div className="mt-5 text-center">
          <button
            type="button"
            onClick={() => {
              setIsRegister(!isRegister);
              setError(null);
            }}
            className="text-xs text-amber-400 hover:underline font-medium"
          >
            {isRegister
              ? 'Hai già un account? Accedi qui'
              : 'Non hai ancora un account? Creane uno nuovo'}
          </button>
        </div>
      </div>
    </div>
  );
};
