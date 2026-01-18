import { Wifi, WifiOff } from 'lucide-react';

export default function StatsGrid({ status, deviceCount }) {
  return (
    <div className="status-overview">
        <div className="status-item good">
            <div className="status-header">Miestnosť</div>
            <div className="status-value">{status.room_id}</div>
        </div>
        
        <div className={`status-item ${status.mqtt_connected ? 'good' : 'error'}`}>
            <div className="status-header">Komunikácia</div>
            {/* Oprava: Použitie CSS triedy namiesto style={{...}} */}
            <div className="status-value status-value-row">
                {status.mqtt_connected ? <><Wifi size={20} /> Pripojené</> : <><WifiOff size={20} /> Odpojené</>}
            </div>
        </div>
        
        <div className={`status-item ${status.scene_running ? 'warning' : 'good'}`}>
            <div className="status-header">Scéna</div>
            <div className="status-value">
                {status.scene_running ? 'Prebieha' : 'Pripravená'}
            </div>
        </div>
        
        <div className={`status-item ${deviceCount === 0 ? 'error' : 'good'}`}>
            <div className="status-header">Zariadenia</div>
            <div className="status-value">{deviceCount} pripojených</div>
        </div>
    </div>
  );
}