import { useState } from 'react';
import { Trash2, Filter, AlertCircle, Info, Bug, ClipboardList } from 'lucide-react';
import { useLogs } from '../../hooks/useLogs';
import Card from '../ui/Card';
import Button from '../ui/Button';
import PageHeader from '../ui/PageHeader';
import '../../styles/views/logs-view.css';

export default function LogsView() {
    const { logs, clearLogs } = useLogs();
    const [filter, setFilter] = useState('ALL');

    const filteredLogs = logs.filter(log => {
        if (filter === 'ALL') return true;
        return log.level === filter;
    });

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
            {/* Nový Header s filtrami v pravej časti */}
            <PageHeader 
                title="Logy" 
                subtitle="História udalostí" 
                icon={ClipboardList}
            >
                <div className="filters" style={{ display: 'flex', alignItems: 'center', gap: '8px', marginRight: '10px' }}>
                    <Filter size={18} className="filter-icon" />
                    <button className={`filter-btn ${filter === 'ALL' ? 'active' : ''}`} onClick={() => setFilter('ALL')}>Všetky</button>
                    <button className={`filter-btn info ${filter === 'INFO' ? 'active' : ''}`} onClick={() => setFilter('INFO')}>Info</button>
                    <button className={`filter-btn warning ${filter === 'WARNING' ? 'active' : ''}`} onClick={() => setFilter('WARNING')}>Warning</button>
                    <button className={`filter-btn error ${filter === 'ERROR' ? 'active' : ''}`} onClick={() => setFilter('ERROR')}>Error</button>
                </div>

                <Button onClick={clearLogs} variant="secondary" size="small" icon={Trash2}>
                    Vyčistiť
                </Button>
            </PageHeader>

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