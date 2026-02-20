import { useDashboardData } from '../../hooks/useDashboardData';
import { useSceneActions } from '../../hooks/useSceneActions';
import '../../styles/views/main-dashboard.css';

import BigStatusCard from '../Dashboard/BigStatusCard';
import StatsGrid from '../Dashboard/StatsGrid';
import DashboardControls from '../Dashboard/DashboardControls';

export default function MainDashboard() {
  const { status, deviceCount } = useDashboardData();
  const { runScene, stopScene, isLoading } = useSceneActions();

  return (
    <div className="main-dashboard">
      <BigStatusCard status={status} />
      <StatsGrid status={status} deviceCount={deviceCount} />
      <DashboardControls 
          status={status} 
          onRun={runScene} 
          onStop={stopScene} 
          isLoading={isLoading}
      />
    </div>
  );
}