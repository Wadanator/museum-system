import { Drama, CheckCircle2, AlertTriangle } from 'lucide-react';

export default function BigStatusCard({ status }) {
    const isRunning = status.scene_running;
    const isConnected = status.mqtt_connected;
    const isError = !isConnected && !isRunning;

    let icon, title, desc, className;

    if (isRunning) {
        icon = <Drama size={64} />;
        title = 'Scéna prebieha';
        desc = 'Predstavenie je v priebehu';
        className = 'running pulse';
    } else if (isConnected) {
        icon = <CheckCircle2 size={64} />;
        title = 'Systém pripravený';
        desc = 'Môžete spustiť predstavenie';
        className = 'ready';
    } else {
        icon = <AlertTriangle size={64} />;
        title = 'Systém nedostupný';
        desc = 'Skontrolujte MQTT pripojenie';
        className = 'error';
    }

    return (
        <div className="system-status-card">
            <div className={`main-status ${className}`}>
                <div className="status-icon">{icon}</div>
                <div className="status-text">{title}</div>
                <div className="status-description">{desc}</div>
            </div>
        </div>
    );
}