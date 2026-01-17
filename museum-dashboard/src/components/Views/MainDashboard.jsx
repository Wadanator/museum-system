import toast from 'react-hot-toast';
import { api } from '../../services/api';
import { useConfirm } from '../../context/ConfirmContext';
import { useDashboardData } from '../../hooks/useDashboardData';

// Import našich nových komponentov
import BigStatusCard from '../Dashboard/BigStatusCard';
import StatsGrid from '../Dashboard/StatsGrid';
import SceneProgressBar from '../Dashboard/SceneProgressBar';
import DashboardControls from '../Dashboard/DashboardControls';

export default function MainDashboard() {
  // 1. Hook pre dáta
  const { status, deviceCount, progressData } = useDashboardData();
  const { confirm } = useConfirm();

  // 2. Handlere akcií
  const handleRunScene = async () => {
    try {
      const res = await fetch('/api/config/main_scene');
      const config = await res.json();
      const sceneName = config.json_file_name || 'intro.json';

      toast.promise(
        api.runScene(sceneName),
        {
            loading: 'Spúšťam hlavnú scénu...',
            success: 'Predstavenie spustené!',
            error: (err) => `Chyba: ${err.message}`
        }
      );
    } catch (e) {
      toast.error('Chyba pri načítaní konfigurácie: ' + e.message);
    }
  };

  const handleStopScene = async () => {
    if (await confirm({
        title: "Zastaviť scénu?",
        message: "Skutočne chcete zastaviť prebiehajúcu scénu? Toto okamžite preruší predstavenie.",
        confirmText: "Zastaviť",
        type: "danger"
    })) {
        toast.promise(
            api.stopScene(),
            {
                loading: 'Zastavujem...',
                success: 'Scéna zastavená (STOPALL)',
                error: (err) => `Chyba: ${err.message}`
            }
        );
    }
  };

  // 3. Render (čistý a prehľadný layout)
  return (
    <div className="main-dashboard">
      <BigStatusCard status={status} />
      
      <StatsGrid status={status} deviceCount={deviceCount} />

      <SceneProgressBar data={progressData} />

      <DashboardControls 
          status={status} 
          onRun={handleRunScene} 
          onStop={handleStopScene} 
      />
    </div>
  );
}