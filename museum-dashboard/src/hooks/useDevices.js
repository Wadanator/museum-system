import { useState, useEffect } from 'react';
import { api } from '../services/api';

export function useDevices() {
    const [data, setData] = useState({ all: [], motors: [], relays: [] });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchDevices = async () => {
            try {
                const response = await api.getDevices();
                
                // Motors
                const motors = (response.motors || []).map(d => ({ ...d, type: 'motor' }));
                
                const relaysRaw = response.relays || [];
                const lightsRaw = response.lights || [];
                
                // Combine them (concat is fine here to avoid duplicates)
                const allRelays = [...relaysRaw, ...lightsRaw].map(d => ({ ...d, type: 'relay' }));

                setData({
                    all: [...motors, ...allRelays],
                    motors,
                    relays: allRelays
                });
                
                setError(null);
                
            } catch (err) {
                console.error("Device fetch error:", err);
                setError(err.message || 'Failed to fetch devices');
            } finally {
                setLoading(false);
            }
        };

        fetchDevices();
    }, []);

    // Refresh function that other components can use
    const refresh = async () => {
        setLoading(true);
        setError(null);
        
        try {
            const response = await api.getDevices();
            const motors = (response.motors || []).map(d => ({ ...d, type: 'motor' }));
            const relaysRaw = response.relays || [];
            const lightsRaw = response.lights || [];
            const allRelays = [...relaysRaw, ...lightsRaw].map(d => ({ ...d, type: 'relay' }));

            setData({
                all: [...motors, ...allRelays],
                motors,
                relays: allRelays
            });
        } catch (err) {
            console.error("Device refresh error:", err);
            setError(err.message || 'Failed to refresh devices');
        } finally {
            setLoading(false);
        }
    };

    return { 
        devices: data.all, 
        motors: data.motors, 
        relays: data.relays, 
        loading, 
        error,
        refresh
    };
}