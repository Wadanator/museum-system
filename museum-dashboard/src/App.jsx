import { Routes, Route, NavLink, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { 
  Home, 
  Drama, 
  FolderOpen, 
  Zap, 
  ClipboardList, 
  BarChart3, 
  Settings, 
  AlertTriangle 
} from 'lucide-react';

import { useSocket } from './context/SocketContext';
import { useAuth } from './context/AuthContext';

import Header from './components/Layout/Header';
import MainDashboard from './components/Views/MainDashboard';
import ScenesView from './components/Views/ScenesView';
import CommandsView from './components/Views/CommandsView';
import LogsView from './components/Views/LogsView';
import StatsView from './components/Views/StatsView';
import SystemView from './components/Views/SystemView';
import LoginView from './components/Views/LoginView';
import MediaManager from './components/Views/MediaManager';

function App() {
  const { isConnected } = useSocket();
  const { isAuthenticated, isLoading, logout } = useAuth();

  if (isLoading) return <div style={{padding: 50, textAlign: 'center'}}>Načítavam...</div>;

  if (!isAuthenticated) {
      return (
        <>
            <Toaster position="top-center" />
            <LoginView />
        </>
      );
  }

  // Pomocný komponent pre NavLink s ikonou
  const NavItem = ({ to, icon: Icon, label }) => (
    <NavLink to={to} className={({ isActive }) => `tab ${isActive ? 'active' : ''}`}>
      <Icon size={18} style={{ marginRight: 8 }} />
      {label}
    </NavLink>
  );

  return (
    <div className="container">
      <Toaster position="top-center" toastOptions={{ duration: 3000 }} />

      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
        <Header />
        <button onClick={logout} className="btn btn-secondary btn-small" style={{marginBottom: '20px'}}>Odhlásiť</button>
      </div>

      <nav className="tabs">
        <NavItem to="/" icon={Home} label="Hlavná" />
        <NavItem to="/scenes" icon={Drama} label="Scény" />
        <NavItem to="/media" icon={FolderOpen} label="Médiá" />
        <NavItem to="/commands" icon={Zap} label="Príkazy" />
        <NavItem to="/logs" icon={ClipboardList} label="Logy" />
        <NavItem to="/stats" icon={BarChart3} label="Štatistiky" />
        <NavItem to="/system" icon={Settings} label="Systém" />
      </nav>

      <div className="content-area">
        <Routes>
          <Route path="/" element={<MainDashboard />} />
          <Route path="/scenes" element={<ScenesView />} />
          <Route path="/media" element={<MediaManager />} />
          <Route path="/commands" element={<CommandsView />} />
          <Route path="/logs" element={<LogsView />} />
          <Route path="/stats" element={<StatsView />} />
          <Route path="/system" element={<SystemView />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
      
      {!isConnected && (
        <div className="notification error show" style={{ position: 'fixed', bottom: 20, right: 20, top: 'auto', zIndex: 9999, display: 'flex', alignItems: 'center', gap: 10 }}>
            <AlertTriangle size={24} /> Odpojené od servera
        </div>
      )}
    </div>
  );
}

export default App;