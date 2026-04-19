import Sidebar from './Sidebar';

export default function AppLayout({ children, theme, onToggleTheme }) {
  return (
    <div className="app-layout">
      <Sidebar theme={theme} onToggleTheme={onToggleTheme} />
      <main className="main-content">
        <div className="content-container">
            {children}
        </div>
      </main>
    </div>
  );
}