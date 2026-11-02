import React, { useState, useEffect } from 'react';
import { User } from './types';
import { getMe, removeAuthToken } from './api';
import { Navbar } from './components/Navbar';
import { AuthModal } from './components/AuthModal';
import { NutritionTab } from './components/NutritionTab';
import { CycletteTab } from './components/CycletteTab';
import { ProfileTab } from './components/ProfileTab';
import { Utensils, Bike, User as UserIcon } from 'lucide-react';

export const App: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'nutrition' | 'cyclette' | 'profile'>('nutrition');
  const [selectedDate, setSelectedDate] = useState<string>(
    new Date().toISOString().split('T')[0]
  );
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  const fetchCurrentUser = async () => {
    try {
      const u = await getMe();
      setUser(u);
      setIsAuthModalOpen(false);
    } catch {
      setUser(null);
      setIsAuthModalOpen(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCurrentUser();
  }, []);

  const handleLogout = () => {
    removeAuthToken();
    setUser(null);
    setIsAuthModalOpen(true);
  };

  const handleSwitchUser = () => {
    setIsAuthModalOpen(true);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center text-slate-400 text-xs">
        <div className="w-8 h-8 border-2 border-amber-500 border-t-transparent rounded-full animate-spin mb-3" />
        <span>Caricamento DietOrDie...</span>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 flex justify-center">
      {/* Mobile Screen Container */}
      <div className="w-full max-w-md min-h-screen bg-slate-950 border-x border-slate-900 flex flex-col relative pb-20 shadow-2xl">
        {/* Mobile Header */}
        <Navbar
          user={user}
          onLogout={handleLogout}
          onSwitchUser={handleSwitchUser}
          selectedDate={selectedDate}
          onDateChange={setSelectedDate}
          activeTab={activeTab}
          setActiveTab={setActiveTab}
        />

        {/* Tab Content */}
        <main className="flex-1 p-4 overflow-y-auto">
          {user ? (
            <>
              {activeTab === 'nutrition' && (
                <NutritionTab user={user} selectedDate={selectedDate} />
              )}
              {activeTab === 'cyclette' && (
                <CycletteTab user={user} />
              )}
              {activeTab === 'profile' && (
                <ProfileTab user={user} onProfileUpdated={fetchCurrentUser} />
              )}
            </>
          ) : (
            <div className="p-8 text-center text-slate-500 text-xs mt-12">
              Effettua l'accesso per visualizzare i tuoi dati.
            </div>
          )}
        </main>

        {/* Fixed Mobile Bottom Navigation Bar */}
        <nav className="fixed bottom-0 left-0 right-0 z-40 bg-slate-900/95 backdrop-blur-lg border-t border-slate-800/90 py-1.5 px-6 max-w-md mx-auto">
          <div className="flex items-center justify-around">
            <button
              onClick={() => setActiveTab('nutrition')}
              className={`flex flex-col items-center py-1 px-3 rounded-2xl transition ${
                activeTab === 'nutrition'
                  ? 'text-amber-400 font-bold scale-105'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Utensils className={`w-5 h-5 mb-0.5 ${activeTab === 'nutrition' ? 'stroke-[2.5]' : 'stroke-2'}`} />
              <span className="text-[10px] tracking-tight">Diario</span>
            </button>

            <button
              onClick={() => setActiveTab('cyclette')}
              className={`flex flex-col items-center py-1 px-3 rounded-2xl transition ${
                activeTab === 'cyclette'
                  ? 'text-amber-400 font-bold scale-105'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Bike className={`w-5 h-5 mb-0.5 ${activeTab === 'cyclette' ? 'stroke-[2.5]' : 'stroke-2'}`} />
              <span className="text-[10px] tracking-tight">Cyclette</span>
            </button>

            <button
              onClick={() => setActiveTab('profile')}
              className={`flex flex-col items-center py-1 px-3 rounded-2xl transition ${
                activeTab === 'profile'
                  ? 'text-amber-400 font-bold scale-105'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <UserIcon className={`w-5 h-5 mb-0.5 ${activeTab === 'profile' ? 'stroke-[2.5]' : 'stroke-2'}`} />
              <span className="text-[10px] tracking-tight">Profilo</span>
            </button>
          </div>
        </nav>

        {/* Login / Register Modal */}
        <AuthModal
          isOpen={isAuthModalOpen}
          onSuccess={fetchCurrentUser}
          onClose={() => {
            if (user) setIsAuthModalOpen(false);
          }}
        />
      </div>
    </div>
  );
};

export default App;
