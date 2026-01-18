import { useDashboardData } from '../../hooks/useDashboardData';
import { useSceneActions } from '../../hooks/useSceneActions';
import '../../styles/views/main-dashboard.css';

// Import komponentov
import BigStatusCard from '../Dashboard/BigStatusCard';
import StatsGrid from '../Dashboard/StatsGrid';
import SceneProgressBar from '../Dashboard/SceneProgressBar';
import DashboardControls from '../Dashboard/DashboardControls';

export default function MainDashboard() {
  const { status, deviceCount, progressData } = useDashboardData();
  const { runScene, stopScene } = useSceneActions();

  return (
    <div className="main-dashboard">
      <BigStatusCard status={status} />
      <StatsGrid status={status} deviceCount={deviceCount} />
      <SceneProgressBar data={progressData} />
      <DashboardControls 
          status={status} 
          onRun={runScene} 
          onStop={stopScene} 
      />
    </div>
  );
}