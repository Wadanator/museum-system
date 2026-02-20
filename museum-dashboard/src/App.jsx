import { Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { useSocket } from './context/SocketContext';
import { useAuth } from './context/AuthContext';
import { AlertTriangle } from 'lucide-react';

// Import nového Layoutu
import AppLayout from './components/Layout/AppLayout';

// Import Views
import MainDashboard from './components/Views/MainDashboard';
import ScenesView from './components/Views/ScenesView';
import CommandsView from './components/Views/CommandsView';
import LogsView from './components/Views/LogsView';
import StatsView from './components/Views/StatsView';
import SystemView from './components/Views/SystemView';
import LoginView from './components/Views/LoginView';
import MediaManager from './components/Views/MediaManager';
import LiveView from './components/Views/LiveView';

import './styles/layout.css'; 

function App() {
  const { isConnected } = useSocket();
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
        <div className="app-loading-screen">
            Načítavam...
        </div>
    );
  }

  if (!isAuthenticated) {
      return (
        <>
            <Toaster position="top-center" />
            <LoginView />
        </>
      );
  }

  return (
    <>
      <Toaster position="top-center" toastOptions={{ duration: 3000 }} />

      <AppLayout>
        <Routes>
          <Route path="/" element={<MainDashboard />} />
          <Route path="/live" element={<LiveView />} />
          <Route path="/scenes" element={<ScenesView />} />
          <Route path="/media" element={<MediaManager />} />
          <Route path="/commands" element={<CommandsView />} />
          <Route path="/logs" element={<LogsView />} />
          <Route path="/stats" element={<StatsView />} />
          <Route path="/system" element={<SystemView />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppLayout>
      
      {!isConnected && (
        <div className="notification error show" style={{ 
            position: 'fixed', bottom: 20, right: 20, top: 'auto', zIndex: 9999, 
            display: 'flex', alignItems: 'center', gap: 10 
        }}>
            <AlertTriangle size={24} /> Odpojené od servera
        </div>
      )}
    </>
  );
}

export default App;