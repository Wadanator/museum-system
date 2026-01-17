import { useDashboardData } from '../../hooks/useDashboardData';
import { useSceneActions } from '../../hooks/useSceneActions';

// Import komponentov
import BigStatusCard from '../Dashboard/BigStatusCard';
import StatsGrid from '../Dashboard/StatsGrid';
import SceneProgressBar from '../Dashboard/SceneProgressBar';
import DashboardControls from '../Dashboard/DashboardControls';

export default function MainDashboard() {
  // 1. Data Hook (získava stav zo socketu)
  const { status, deviceCount, progressData } = useDashboardData();
  
  // 2. Actions Hook (obsahuje logiku tlačidiel)
  const { runScene, stopScene } = useSceneActions();

  // 3. Render
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