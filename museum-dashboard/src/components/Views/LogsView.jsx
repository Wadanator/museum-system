import { useState } from 'react';
import { Trash2, Filter, AlertCircle, Info, Bug } from 'lucide-react';
import { useLogs } from '../../hooks/useLogs';
import Card from '../ui/Card';
import Button from '../ui/Button';
import '../../styles/views/logs-view.css'; // Nezabudni importovať CSS!

export default function LogsView() {
    const { logs, clearLogs } = useLogs();
    const [filter, setFilter] = useState('ALL');

    // Filtrovanie logov
    const filteredLogs = logs.filter(log => {
        if (filter === 'ALL') return true;
        return log.level === filter;
    });

    // Pomocná funkcia pre ikonu podľa levelu
    const getLevelIcon = (level) => {
        switch (level) {
            case 'ERROR': return <AlertCircle size={14} />;
            case 'WARNING': return <AlertCircle size={14} />;
            case 'DEBUG': return <Bug size={14} />;
            default: return <Info size={14} />;
        }
    };

    return (
        <div className="view-container logs-view">
            {/* Header s ovládacími prvkami */}
            <div className="logs-header">
                <div className="filters">
                    <Filter size={18} className="filter-icon" />
                    <button 
                        className={`filter-btn ${filter === 'ALL' ? 'active' : ''}`} 
                        onClick={() => setFilter('ALL')}
                    >
                        Všetky
                    </button>
                    <button 
                        className={`filter-btn info ${filter === 'INFO' ? 'active' : ''}`} 
                        onClick={() => setFilter('INFO')}
                    >
                        Info
                    </button>
                    <button 
                        className={`filter-btn warning ${filter === 'WARNING' ? 'active' : ''}`} 
                        onClick={() => setFilter('WARNING')}
                    >
                        Warning
                    </button>
                    <button 
                        className={`filter-btn error ${filter === 'ERROR' ? 'active' : ''}`} 
                        onClick={() => setFilter('ERROR')}
                    >
                        Error
                    </button>
                </div>

                <Button onClick={clearLogs} variant="secondary" size="small" icon={Trash2}>
                    Vyčistiť
                </Button>
            </div>

            {/* Samotná konzola */}
            <Card className="logs-console-card">
                <div className="logs-console">
                    {filteredLogs.length === 0 ? (
                        <div className="empty-logs">
                            <span className="cursor">_</span> Žiadne záznamy pre zobrazenie
                        </div>
                    ) : (
                        filteredLogs.map((log, index) => (
                            <div key={index} className={`log-row ${log.level.toLowerCase()}`}>
                                <span className="log-time">[{log.timestamp?.split(' ')[1] || '00:00:00'}]</span>
                                <span className={`log-level ${log.level.toLowerCase()}`}>
                                    {getLevelIcon(log.level)} {log.level}
                                </span>
                                <span className="log-module">[{log.module}]</span>
                                <span className="log-message">{log.message}</span>
                            </div>
                        ))
                    )}
                </div>
            </Card>
        </div>
    );
}