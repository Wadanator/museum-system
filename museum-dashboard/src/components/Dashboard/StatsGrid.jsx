import { Wifi, WifiOff } from 'lucide-react';

export default function StatsGrid({ status, deviceCount }) {
  return (
    <div className="status-overview">

      <div className={`status-item ${status.room_id && status.room_id !== '-' && status.room_id !== 'Unknown' ? 'good' : 'error'}`}>
        <div className="status-header">Miestnosť</div>
        <div className="status-value">{status.room_id}</div>
      </div>

      <div className={`status-item ${status.mqtt_connected ? 'good' : 'error'}`}>
        <div className="status-header">Komunikácia</div>
        <div className="status-value status-value-row">
          {status.mqtt_connected
            ? <><Wifi size={20} /> Pripojené</>
            : <><WifiOff size={20} /> Odpojené</>}
        </div>
      </div>

      <div className={`status-item ${deviceCount === 0 ? 'error' : 'good'}`}>
        <div className="status-header">Zariadenia</div>
        <div className="status-value">{deviceCount} pripojených</div>
      </div>

    </div>
  );
}