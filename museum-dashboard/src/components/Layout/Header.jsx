export default function Header() {
  return (
    <div className="header">
        <div className="header-title-group">
            <span className="header-icon pulse">🏛️</span>
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