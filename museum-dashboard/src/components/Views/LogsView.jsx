import { useState } from 'react';
import { Trash2, Filter, AlertCircle, Info, Bug, ClipboardList, Terminal } from 'lucide-react';
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
            case 'ERROR': return <AlertCircle size={12} />;
            case 'WARNING': return <AlertCircle size={12} />;
            case 'DEBUG': return <Bug size={12} />;
            default: return <Info size={12} />;
        }
    };

    return (
        <div className="view-container logs-view">
            <PageHeader 
                title="Logy systému" 
                subtitle="Živý výpis udalostí servera" 
                icon={ClipboardList}
            >
                {/* Filtre presunuté priamo do header akcií */}
                <div className="filters">
                    <button className={`filter-btn ${filter === 'ALL' ? 'active' : ''}`} onClick={() => setFilter('ALL')}>Všetky</button>
                    <button className={`filter-btn info ${filter === 'INFO' ? 'active' : ''}`} onClick={() => setFilter('INFO')}>Info</button>
                    <button className={`filter-btn warning ${filter === 'WARNING' ? 'active' : ''}`} onClick={() => setFilter('WARNING')}>Warning</button>
                    <button className={`filter-btn error ${filter === 'ERROR' ? 'active' : ''}`} onClick={() => setFilter('ERROR')}>Error</button>
                </div>

                <Button onClick={clearLogs} variant="secondary" size="small" icon={Trash2}>
                    Vyčistiť
                </Button>
            </PageHeader>

            <Card className="logs-console-card">
                <div className="logs-console">
                    {filteredLogs.length === 0 ? (
                        <div className="empty-logs">
                            <Terminal size={48} opacity={0.2} />
                            <span>Žiadne záznamy pre zobrazenie</span>
                        </div>
                    ) : (
                        filteredLogs.map((log, index) => (
                            <div key={index} className={`log-row ${log.level.toLowerCase()}`}>
                                <span className="log-time">{log.timestamp?.split(' ')[1] || '--:--:--'}</span>
                                <span className={`log-level ${log.level.toLowerCase()}`}>
                                    {getLevelIcon(log.level)} {log.level}
                                </span>
                                <span className="log-module">{log.module}</span>
                                <span className="log-message">{log.message}</span>
                            </div>
                        ))
                    )}
                </div>
            </Card>
        </div>
    );
}