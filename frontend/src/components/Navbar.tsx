import React, { useState, useEffect } from 'react';
import { User } from '../types';
import { getUsersList, removeAuthToken } from '../api';
import { Utensils, Bike, User as UserIcon, Flame, LogOut, ChevronLeft, ChevronRight, Calendar, Users } from 'lucide-react';

interface NavbarProps {
  user: User | null;
  onLogout: () => void;
  onSwitchUser: () => void;
  selectedDate: string;
  onDateChange: (newDate: string) => void;
  activeTab: 'nutrition' | 'cyclette' | 'profile';
  setActiveTab: (tab: 'nutrition' | 'cyclette' | 'profile') => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  user,
  onLogout,
  onSwitchUser,
  selectedDate,
  onDateChange,
  activeTab,
  setActiveTab
}) => {
  const [systemUsers, setSystemUsers] = useState<Array<{ id: number; username: string; full_name?: string }>>([]);
  const [showUsersDropdown, setShowUsersDropdown] = useState(false);

  useEffect(() => {
    if (user) {
      getUsersList().then(setSystemUsers).catch(() => {});
    }
  }, [user]);

  const handlePrevDay = () => {
    const d = new Date(selectedDate);
    d.setDate(d.getDate() - 1);
    onDateChange(d.toISOString().split('T')[0]);
  };

  const handleNextDay = () => {
    const d = new Date(selectedDate);
    d.setDate(d.getDate() + 1);
    onDateChange(d.toISOString().split('T')[0]);
  };

  const handleToday = () => {
    onDateChange(new Date().toISOString().split('T')[0]);
  };

  const isToday = selectedDate === new Date().toISOString().split('T')[0];

  return (
    <header className="sticky top-0 z-40 bg-slate-900/90 backdrop-blur-md border-b border-slate-800">
      <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
        {/* Logo */}
        <div className="flex items-center space-x-2">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-amber-600 via-rose-600 to-amber-400 flex items-center justify-center shadow-lg shadow-rose-950/40">
            <Flame className="w-5 h-5 text-white animate-pulse" />
          </div>
          <div>
            <h1 className="text-lg font-black tracking-wider bg-gradient-to-r from-amber-400 via-orange-300 to-rose-400 bg-clip-text text-transparent">
              DietOrDie
            </h1>
            <span className="text-[10px] uppercase font-bold text-slate-400 tracking-widest block -mt-1">
              Personal Edition
            </span>
          </div>
        </div>

        {/* Date Selector (Only in nutrition view) */}
        {activeTab === 'nutrition' && (
          <div className="flex items-center space-x-1 bg-slate-800/80 px-2 py-1 rounded-lg border border-slate-700/60 text-xs">
            <button onClick={handlePrevDay} className="p-1 hover:text-amber-400 transition" title="Giorno precedente">
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={handleToday}
              className={`px-2 py-0.5 rounded font-medium ${isToday ? 'bg-amber-500/20 text-amber-400' : 'text-slate-300 hover:text-white'}`}
            >
              {isToday ? 'Oggi' : selectedDate}
            </button>
            <button onClick={handleNextDay} className="p-1 hover:text-amber-400 transition" title="Giorno successivo">
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* User Pill / Switcher */}
        {user ? (
          <div className="relative">
            <button
              onClick={() => setShowUsersDropdown(!showUsersDropdown)}
              className="flex items-center space-x-2 bg-slate-800 hover:bg-slate-700/80 border border-slate-700 px-2.5 py-1.5 rounded-full text-xs font-medium transition"
            >
              <div className="w-6 h-6 rounded-full bg-amber-500/20 text-amber-400 flex items-center justify-center font-bold">
                {user.full_name ? user.full_name[0].toUpperCase() : user.username[0].toUpperCase()}
              </div>
              <span className="max-w-[90px] truncate text-slate-200">{user.full_name || user.username}</span>
            </button>

            {showUsersDropdown && (
              <div className="absolute right-0 mt-2 w-48 bg-slate-800 border border-slate-700 rounded-xl shadow-2xl py-2 z-50 text-xs animate-in fade-in zoom-in-95">
                <div className="px-3 py-1.5 border-b border-slate-700/50 text-slate-400 font-semibold">
                  Cambia Profilo
                </div>
                <button
                  onClick={() => {
                    setShowUsersDropdown(false);
                    onSwitchUser();
                  }}
                  className="w-full text-left px-3 py-2 text-amber-400 hover:bg-slate-700 flex items-center space-x-2"
                >
                  <Users className="w-3.5 h-3.5" />
                  <span>Accedi con altro account</span>
                </button>
                <button
                  onClick={() => {
                    setShowUsersDropdown(false);
                    onLogout();
                  }}
                  className="w-full text-left px-3 py-2 text-rose-400 hover:bg-slate-700 flex items-center space-x-2"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span>Disconnetti</span>
                </button>
              </div>
            )}
          </div>
        ) : (
          <button
            onClick={onSwitchUser}
            className="text-xs bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold px-3 py-1.5 rounded-lg transition"
          >
            Accedi
          </button>
        )}
      </div>
    </header>
  );
};
