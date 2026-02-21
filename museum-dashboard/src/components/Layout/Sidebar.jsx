import { NavLink } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { 
  Home, Drama, FolderOpen, Zap, ClipboardList, 
  BarChart3, Settings, LogOut, Landmark
} from 'lucide-react';

export default function Sidebar() {
  const { logout } = useAuth();

  const navItems = [
    { to: "/", icon: Home, label: "Prehľad" },
    { to: "/scenes", icon: Drama, label: "Scény" },
    { to: "/media", icon: FolderOpen, label: "Médiá" },
    { to: "/commands", icon: Zap, label: "Ovládanie" },
    { to: "/logs", icon: ClipboardList, label: "Logy" },
    { to: "/stats", icon: BarChart3, label: "Štatistiky" },
    { to: "/system", icon: Settings, label: "Systém" },
  ];

  return (
    <aside className="sidebar">
      {/* 1. Brand / Logo Sekcia */}
      <div className="sidebar-header">
        <div className="brand-icon">
            <Landmark size={24} />
        </div>
        <div className="brand-text">
            <h1>MUSEUM</h1>
            <span>Control System</span>
        </div>
      </div>

      {/* 2. Navigácia */}
      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <NavLink 
            key={item.to} 
            to={item.to}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <item.icon size={20} className="nav-icon" />
            <span className="nav-label">{item.label}</span>
            {/* Active Indicator (čiarka vpravo) */}
            <div className="active-indicator"></div>
          </NavLink>
        ))}
      </nav>

      {/* 3. Pätička s užívateľom a odhlásením */}
      <div className="sidebar-footer">
        <div className="user-info">
            <div className="user-avatar">A</div>
            <div className="user-details">
                <span className="name">Admin</span>
                <span className="role">Správca</span>
            </div>
        </div>
        <button onClick={logout} className="logout-btn" title="Odhlásiť">
            <LogOut size={18} />
        </button>
      </div>
    </aside>
  );
}