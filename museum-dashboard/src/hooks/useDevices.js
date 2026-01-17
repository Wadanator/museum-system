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
                
                // 1. Motory
                const motors = (response.motors || []).map(d => ({ ...d, type: 'motor' }));
                
                // 2. Relátka a Svetlá
                // Pre istotu skontrolujeme 'relays' AJ 'lights', keby to backend delil
                const relaysRaw = response.relays || [];
                const lightsRaw = response.lights || [];
                
                // Spojíme ich (aby sme nemali duplicity, ak by boli v oboch poliach, dá sa použiť Set, ale tu stačí concat)
                const allRelays = [...relaysRaw, ...lightsRaw].map(d => ({ ...d, type: 'relay' }));

                setData({
                    all: [...motors, ...allRelays],
                    motors: motors,
                    relays: allRelays
                });
                
            } catch (err) {
                console.error("Device fetch error:", err);
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchDevices();
    }, []);

    return { 
        devices: data.all, 
        motors: data.motors, 
        relays: data.relays, 
        loading, 
        error 
    };
}