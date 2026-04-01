import { useState, useEffect } from 'react';
import { socket } from '../services/socket';
import { api } from '../services/api';

export function useLogs() {
    const [logs, setLogs] = useState([]);
    const [isConnected, setIsConnected] = useState(socket.connected);

    useEffect(() => {
        const handleLogHistory = (history) => {
            if (Array.isArray(history)) {
                setLogs([...history].reverse());
            }
        };

        const handleNewLog = (logEntry) => {
            setLogs(prev => [logEntry, ...prev].slice(0, 200));
        };

        const handleLogsCleared = () => setLogs([]);

        const handleConnect = () => {
            setIsConnected(true);
            socket.emit('request_logs');
        };

        const handleDisconnect = () => setIsConnected(false);

        socket.on('log_history', handleLogHistory);
        socket.on('new_log', handleNewLog);
        socket.on('logs_cleared', handleLogsCleared);
        socket.on('connect', handleConnect);
        socket.on('disconnect', handleDisconnect);

        // Request logs on mount even if socket is already connected.
        socket.emit('request_logs');

        return () => {
            socket.off('log_history', handleLogHistory);
            socket.off('new_log', handleNewLog);
            socket.off('logs_cleared', handleLogsCleared);
            socket.off('connect', handleConnect);
            socket.off('disconnect', handleDisconnect);
        };
    }, []);

    const clearLogs = async () => {
        setLogs([]);
        try {
            await api.clearLogs();
        } catch (e) {
            console.error('Failed to clear logs on backend:', e);
        }
    };

    return { logs, isConnected, clearLogs };
}