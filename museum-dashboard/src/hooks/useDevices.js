import { useState, useEffect } from 'react';
import { api } from '../services/api';

export function useDevices() {
    const [data, setData] = useState({ all: [], motors: [], relays: [] });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const loadDevices = async () => {
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
    };

    useEffect(() => {
        const fetchDevices = async () => {
            try {
                await loadDevices();
                setError(null);
            } catch (err) {
                setError(err.message || 'Failed to fetch devices');
            } finally {
                setLoading(false);
            }
        };

        fetchDevices();
    }, []);

    const refresh = async () => {
        setLoading(true);
        setError(null);
        try {
            await loadDevices();
        } catch (err) {
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
