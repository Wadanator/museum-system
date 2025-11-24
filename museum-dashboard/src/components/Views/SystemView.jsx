import { api } from '../../services/api';
import toast from 'react-hot-toast';
import { useConfirm } from '../../context/ConfirmContext';

export default function SystemView() {
  const { confirm } = useConfirm();

  const handleRestartSystem = async () => {
    if (await confirm({
        title: "Reštart systému",
        message: "Skutočne chcete vykonať tvrdý reštart? Toto reštartuje Raspberry Pi a preruší všetky operácie.",
        confirmText: "Reštartovať",
        type: "danger"
    })) {
        toast.promise(
            api.restartSystem(),
            {
                loading: 'Reštartujem systém...',
                success: 'Systém sa reštartuje. Počkajte na obnovenie pripojenia.',
                error: (err) => `Chyba: ${err.message}`
            }
        );
    }
  };

  const handleRestartService = async () => {
    if (await confirm({
        title: "Reštart služby",
        message: "Skutočne chcete reštartovať museum-system službu?",
        confirmText: "Reštartovať",
        type: "warning"
    })) {
        toast.promise(
            api.restartService(),
            {
                loading: 'Reštartujem službu...',
                success: 'Služba sa reštartuje...',
                error: (err) => `Chyba: ${err.message}`
            }
        );
    }
  };

  return (
    <div className="tab-content active">
      <h2>⚙️ Systémové ovládanie</h2>
      <div className="system-controls" style={{ maxWidth: '600px' }}>
        
        <div className="control-group">
            <h3>Reštart systému (Reboot)</h3>
            <p>Reštartuje celé Raspberry Pi. Použite v prípade vážnych problémov.</p>
            <button className="btn btn-danger" onClick={handleRestartSystem}>
                🔄 Reštartovať Raspberry Pi
            </button>
        </div>

        <div className="control-group">
            <h3>Reštart služby (Service)</h3>
            <p>Reštartuje iba Python aplikáciu. Rýchlejšie ako celý reštart.</p>
            <button className="btn btn-warning" style={{color: 'white'}} onClick={handleRestartService}>
                🔄 Reštartovať Službu
            </button>
        </div>

      </div>
    </div>
  );
}