import { useState, useEffect, useRef, useMemo } from 'react';
import { socket } from '../../services/socket';
import { api } from '../../services/api';
import toast from 'react-hot-toast';
import { useConfirm } from '../../context/ConfirmContext'; // <--- NOVÉ

export default function LogsView() {
  const [logs, setLogs] = useState([]);
  const logsEndRef = useRef(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const { confirm } = useConfirm(); // <--- NOVÉ

  // 1. NAČÍTANIE FILTROV Z LOCAL STORAGE (Aby si to pamätalo po refreshi)
  const [activeFilters, setActiveFilters] = useState(() => {
    const saved = localStorage.getItem('logFilters');
    return saved ? JSON.parse(saved) : ['info', 'warning', 'error', 'critical'];
  });

  // 2. UKLADANIE FILTROV PRI ZMENE
  useEffect(() => {
    localStorage.setItem('logFilters', JSON.stringify(activeFilters));
  }, [activeFilters]);

  // Socket Logic
  useEffect(() => {
    socket.emit('request_logs');

    const handleLogHistory = (history) => setLogs(history);
    const handleNewLog = (log) => {
        setLogs(prev => {
            const newLogs = [...prev, log];
            if (newLogs.length > 1000) return newLogs.slice(newLogs.length - 1000);
            return newLogs;
        });
    };
    const handleClear = () => {
        setLogs([]);
        toast.success('Logy boli vymazané');
    };

    socket.on('log_history', handleLogHistory);
    socket.on('new_log', handleNewLog);
    socket.on('logs_cleared', handleClear);

    return () => {
        socket.off('log_history', handleLogHistory);
        socket.off('new_log', handleNewLog);
        socket.off('logs_cleared', handleClear);
    };
  }, []);

  useEffect(() => {
    if (autoScroll) {
        logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs, autoScroll]);

  const logStats = useMemo(() => {
      const stats = { debug: 0, info: 0, warning: 0, error: 0, critical: 0 };
      logs.forEach(log => {
          const lvl = log.level?.toLowerCase() || 'info';
          if (stats[lvl] !== undefined) stats[lvl]++;
      });
      return stats;
  }, [logs]);

  const toggleFilter = (level) => {
    setActiveFilters(prev => 
      prev.includes(level) ? prev.filter(f => f !== level) : [...prev, level]
    );
  };

  const handleClearLogs = async () => {
      // POUŽITIE NOVÉHO CONFIRM OKNA
      if(await confirm({ 
          title: "Vymazať logy?", 
          message: "Naozaj chcete vymazať všetky systémové logy? Táto akcia je nevratná.",
          type: "warning"
      })) {
          await api.clearLogs();
      }
  };

  return (
    <div className="tab-content active">
      <div className="header-row" style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px'}}>
        <h2>📋 Systémové logy</h2>
        <div className="log-actions">
            <button className={`btn btn-small ${autoScroll ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setAutoScroll(!autoScroll)}>
                {autoScroll ? '⬇️ Auto-scroll ON' : '⏸️ Auto-scroll OFF'}
            </button>
            <button className="btn btn-secondary btn-small" onClick={handleClearLogs}>🗑️ Vymazať</button>
            <button className="btn btn-secondary btn-small" onClick={() => window.location.href = '/api/logs/export'}>📤 Export</button>
        </div>
      </div>
      
      <div className="log-controls" style={{marginBottom: '15px'}}>
        <div className="filter-buttons">
            {['debug', 'info', 'warning', 'error', 'critical'].map(level => (
                <button 
                    key={level}
                    className={`filter-btn ${level} ${activeFilters.includes(level) ? 'active' : ''}`}
                    onClick={() => toggleFilter(level)}
                >
                    {level.toUpperCase()} <span style={{opacity: 0.7, fontSize: '0.8em'}}>({logStats[level]})</span>
                </button>
            ))}
        </div>
      </div>

      <div className="log-container" style={{height: '600px'}}>
        {logs
            .filter(log => activeFilters.includes(log.level?.toLowerCase()))
            .map((log, i) => (
                <div key={i} className={`log-entry ${log.level?.toLowerCase()}`}>
                    <span className="log-timestamp">{log.timestamp}</span>
                    <span className={`log-level ${log.level?.toLowerCase()}`}>{log.level}</span>
                    <span className="log-module">{log.module}</span>
                    <span className="log-message">{log.message}</span>
                </div>
        ))}
        <div ref={logsEndRef} />
        
        {logs.length === 0 && (
            <div style={{padding: '20px', textAlign: 'center', color: '#9ca3af'}}>Žiadne logy na zobrazenie</div>
        )}
      </div>
    </div>
  );
}