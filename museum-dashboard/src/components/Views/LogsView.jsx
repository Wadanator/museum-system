import { useState, useEffect, useRef, useMemo } from 'react';
import { socket } from '../../services/socket';
import { api } from '../../services/api';
import toast from 'react-hot-toast';
import { useConfirm } from '../../context/ConfirmContext';
import { 
  ClipboardList, 
  ArrowDown, 
  Pause, 
  Trash2, 
  Download 
} from 'lucide-react';

// Import UI komponentov
import PageHeader from '../ui/PageHeader';
import Button from '../ui/Button';

export default function LogsView() {
  const [logs, setLogs] = useState([]);
  const logsEndRef = useRef(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const { confirm } = useConfirm();

  const [activeFilters, setActiveFilters] = useState(() => {
    const saved = localStorage.getItem('logFilters');
    return saved ? JSON.parse(saved) : ['info', 'warning', 'error', 'critical'];
  });

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
      if(await confirm({ 
          title: "Vymazať logy?", 
          message: "Naozaj chcete vymazať všetky systémové logy? Táto akcia je nevratná.",
          type: "warning"
      })) {
          await api.clearLogs();
      }
  };

  // Mapovanie farieb pre logy (pre vizuálne odlíšenie filtrov)
  const getVariantForFilter = (level, isActive) => {
      if (!isActive) return 'ghost';
      switch(level) {
          case 'error': return 'danger';
          case 'critical': return 'danger';
          case 'warning': return 'warning';
          default: return 'primary'; // info, debug
      }
  };

  return (
    <div className="tab-content active">
      <PageHeader title="Systémové logy" icon={ClipboardList}>
            <Button 
                variant={autoScroll ? 'primary' : 'secondary'} 
                size="small"
                onClick={() => setAutoScroll(!autoScroll)}
                icon={autoScroll ? ArrowDown : Pause}
            >
                {autoScroll ? 'Auto-scroll' : 'Pauza'}
            </Button>
            <Button 
                variant="secondary" 
                size="small"
                onClick={handleClearLogs}
                icon={Trash2}
            >
                Vymazať
            </Button>
            <Button 
                variant="secondary" 
                size="small"
                onClick={() => window.location.href = '/api/logs/export'}
                icon={Download}
            >
                Export
            </Button>
      </PageHeader>
      
      <div className="log-controls" style={{marginBottom: '15px'}}>
        <div className="filter-buttons" style={{ display: 'flex', gap: '8px' }}>
            {['debug', 'info', 'warning', 'error', 'critical'].map(level => {
                const isActive = activeFilters.includes(level);
                return (
                    <Button 
                        key={level}
                        size="small"
                        variant={getVariantForFilter(level, isActive)}
                        onClick={() => toggleFilter(level)}
                        style={{ 
                            textTransform: 'uppercase', 
                            fontWeight: 'bold',
                            opacity: isActive ? 1 : 0.6
                        }}
                    >
                        {level} <span style={{opacity: 0.7, marginLeft: 4}}>({logStats[level]})</span>
                    </Button>
                );
            })}
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