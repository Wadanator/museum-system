import { useState, useEffect, useCallback } from 'react';
import toast from 'react-hot-toast';
import { api } from '../services/api';

const HIDDEN_SCENE_FILES = new Set(['devices.json', 'sc_preview.json', 'sc_preview']);

export function useScenes() {
    const [scenes, setScenes] = useState([]);
    const [loading, setLoading] = useState(true);

    const fetchScenes = useCallback(async () => {
        try {
            setLoading(true);
            const data = await api.getScenes();
            const safeScenes = (data || []).filter(
                (scene) => !HIDDEN_SCENE_FILES.has(scene?.name)
            );
            setScenes(safeScenes);
        } catch (e) {
            toast.error("Nepodarilo sa načítať scény");
            console.error(e);
        } finally {
            setLoading(false);
        }
    }, []);

    const saveSceneContent = useCallback(async (filename, content) => {
        try {
            await api.saveScene(filename, content);
            toast.success("Scéna uložená");
            fetchScenes(); 
            return true;
        } catch (e) {
            toast.error("Chyba pri ukladaní: " + e.message);
            return false;
        }
    }, [fetchScenes]);

    const playScene = useCallback(async (filename) => {
        try {
            await api.runScene(filename);
            const started = true;
            toast.success(`Spúšťam scénu: ${filename}`);
            return started;
        } catch (e) {
            toast.error("Chyba pri spustení: " + e.message);
            return false;
        }
    }, []);

    const loadSceneContent = useCallback(async (filename) => {
        try {
            return await api.getSceneContent(filename);
        } catch (e) {
            toast.error("Nedá sa načítať obsah scény");
            throw e;
        }
    }, []);

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
