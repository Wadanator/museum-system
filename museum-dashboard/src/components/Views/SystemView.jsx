import { api } from '../../services/api';
import toast from 'react-hot-toast';
import { useConfirm } from '../../context/ConfirmContext';
import { Settings, RefreshCw } from 'lucide-react';
import PageHeader from '../ui/PageHeader';
import Button from '../ui/Button';
import Card from '../ui/Card';

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

  return (
    <div className="tab-content active">
      <PageHeader title="Systémové ovládanie" icon={Settings} />
      <div className="system-controls" style={{ maxWidth: '600px' }}>
        <Card title="Správa napájania" icon={Settings}>
            <p style={{marginBottom: 20, color: '#4b5563'}}>
                Reštartuje celé Raspberry Pi. Použite v prípade vážnych problémov s OS alebo hardvérom.
            </p>
            <Button variant="danger" onClick={handleRestartSystem} icon={RefreshCw} style={{width: '100%'}}>
                Reštartovať Raspberry Pi
            </Button>
        </Card>
      </div>
    </div>
  );
}