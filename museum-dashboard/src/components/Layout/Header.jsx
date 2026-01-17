import { Landmark } from 'lucide-react';

export default function Header() {
  return (
    <div className="header">
        <div className="header-title-group">
            <Landmark className="header-icon pulse" size={32} />
            <h1>Museum Control</h1>
        </div>
        
        <div className="header-subtitle-group">
            <p>Ovládanie múzejného systému</p>
            <div className="status-badge dev">
                <span className="dot"></span>
                Windows Dev Mode
            </div>
        </div>
    </div>
  );
}