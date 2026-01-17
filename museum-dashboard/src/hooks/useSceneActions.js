// src/hooks/useSceneActions.js
import toast from 'react-hot-toast';
import { api } from '../services/api';
import { useConfirm } from '../context/ConfirmContext';

export function useSceneActions() {
    const { confirm } = useConfirm();

    const runScene = async () => {
        try {
            const res = await fetch('/api/config/main_scene');
            const config = await res.json();
            const sceneName = config.json_file_name || 'intro.json';

            toast.promise(
                api.runScene(sceneName),
                {
                    loading: 'Spúšťam hlavnú scénu...',
                    success: 'Predstavenie spustené!',
                    error: (err) => `Chyba: ${err.message}`
                }
            );
        } catch (e) {
            toast.error('Chyba konfigurácie: ' + e.message);
        }
    };

    const stopScene = async () => {
        if (await confirm({
            title: "Zastaviť scénu?",
            message: "Skutočne chcete zastaviť prebiehajúcu scénu?",
            confirmText: "Zastaviť",
            type: "danger"
        })) {
            toast.promise(
                api.stopScene(),
                {
                    loading: 'Zastavujem...',
                    success: 'Scéna zastavená',
                    error: (err) => `Chyba: ${err.message}`
                }
            );
        }
    };

    return { runScene, stopScene };
}