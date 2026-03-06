import { useDashboardData } from '../../hooks/useDashboardData';
import { useSceneActions } from '../../hooks/useSceneActions';
import '../../styles/views/main-dashboard.css';

import HeroCard from '../Dashboard/HeroCard';
import StatsGrid from '../Dashboard/StatsGrid';

export default function MainDashboard() {
  const { status, deviceCount } = useDashboardData();
  const { runScene, stopScene, isLoading } = useSceneActions();

  return (
    <div className="main-dashboard">
      <HeroCard
        status={status}
        onRun={runScene}
        onStop={stopScene}
        isLoading={isLoading}
      />
      <StatsGrid status={status} deviceCount={deviceCount} />
    </div>
  );
}