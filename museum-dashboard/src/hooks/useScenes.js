import { useState, useEffect, useCallback } from 'react';
import toast from 'react-hot-toast';
import { api } from '../services/api';

export function useScenes() {
    const [scenes, setScenes] = useState([]);
    const [loading, setLoading] = useState(true);

    const fetchScenes = useCallback(async () => {
        try {
            setLoading(true);
            const data = await api.getScenes();
            setScenes(data || []);
        } catch (e) {
            toast.error("Nepodarilo sa načítať scény");
            console.error(e);
        } finally {
            setLoading(false);
        }
    }, []);

    const saveSceneContent = async (filename, content) => {
        try {
            await api.saveScene(filename, content);
            toast.success("Scéna uložená");
            fetchScenes(); 
            return true;
        } catch (e) {
            toast.error("Chyba pri ukladaní: " + e.message);
            return false;
        }
    };

    const playScene = async (filename) => {
        try {
            await api.runScene(filename);
            toast.success(`Spúšťam scénu: ${filename}`);
        } catch (e) {
            toast.error("Chyba pri spustení: " + e.message);
        }
    };

    const loadSceneContent = async (filename) => {
        try {
            return await api.getSceneContent(filename);
        } catch (e) {
            toast.error("Nedá sa načítať obsah scény");
            throw e;
        }
    };

    useEffect(() => {
        fetchScenes();
    }, [fetchScenes]);

    return { 
        scenes, 
        loading, 
        fetchScenes, 
        saveSceneContent, 
        playScene,
        loadSceneContent
    };
}