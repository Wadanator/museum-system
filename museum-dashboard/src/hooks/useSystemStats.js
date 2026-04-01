import { useState, useEffect, useMemo } from 'react';
import { socket } from '../services/socket';

export function useSystemStats() {
    const [stats, setStats] = useState({
        total_scenes_played: 0,
        total_uptime: 0,
        connected_devices: {},
        scene_play_counts: {}
    });

    useEffect(() => {
        const handleStats = (data) => setStats(data);
        
        const handleConnect = () => {
            // Re-request stats when socket reconnects
            socket.emit('request_stats');
        };

        socket.on('stats_update', handleStats);
        socket.on('connect', handleConnect);

        // Initial fetch
        if (socket.connected) {
            socket.emit('request_stats');
        }

        return () => {
            socket.off('stats_update', handleStats);
            socket.off('connect', handleConnect);
        };
    }, []);

    const formatTime = (s) => `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`;

    // Memoizácia triedenia pre výkon
    const sortedScenes = useMemo(() => 
        Object.entries(stats.scene_play_counts || {})
            .sort(([, a], [, b]) => b - a), 
    [stats.scene_play_counts]);

    const sortedDevices = useMemo(() => 
        Object.entries(stats.connected_devices || {})
            .sort(([, a]) => (a.status === 'online' ? -1 : 1)), 
    [stats.connected_devices]);

    return { 
        stats, 
        sortedScenes, 
        sortedDevices, 
        formatTime 
    };
}