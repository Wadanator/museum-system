import { useState, useEffect } from 'react';
import { socket } from '../services/socket';

export function useLogs() {
    const [logs, setLogs] = useState([]);
    const [isConnected, setIsConnected] = useState(socket.connected);

    useEffect(() => {
        // 1. Načítanie histórie po pripojení (backend posiela chronologicky, my otáčame)
        const handleLogHistory = (history) => {
            if (Array.isArray(history)) {
                setLogs([...history].reverse());
            }
        };

        // 2. Nový log pridáme na začiatok
        const handleNewLog = (logEntry) => {
            setLogs(prev => [logEntry, ...prev].slice(0, 200)); // Držíme max 200 riadkov
        };

        const handleConnect = () => setIsConnected(true);
        const handleDisconnect = () => setIsConnected(false);

        socket.on('log_history', handleLogHistory);
        socket.on('new_log', handleNewLog);
        socket.on('connect', handleConnect);
        socket.on('disconnect', handleDisconnect);
        
        // Vyžiadanie histórie ak sme už pripojení
        if (socket.connected) {
            socket.emit('request_logs');
        }

        return () => {
            socket.off('log_history', handleLogHistory);
            socket.off('new_log', handleNewLog);
            socket.off('connect', handleConnect);
            socket.off('disconnect', handleDisconnect);
        };
    }, []);

    const clearLogs = () => setLogs([]);

    return { logs, isConnected, clearLogs };
}