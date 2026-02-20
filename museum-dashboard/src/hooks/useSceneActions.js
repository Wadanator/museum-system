// src/hooks/useSceneActions.js
import { useState, useRef, useCallback } from 'react';
import toast from 'react-hot-toast';
import { api } from '../services/api';
import { useConfirm } from '../context/ConfirmContext';

export function useSceneActions() {
    const { confirm } = useConfirm();
    const [isLoading, setIsLoading] = useState(false);
    
    // Použijeme Ref, aby sme mali okamžitý prístup k stavu bez čakania na re-render
    const lockedRef = useRef(false);

    // Pomocná funkcia: Čakaj minimálne X sekúnd
    const waitMinTime = (ms) => new Promise(resolve => setTimeout(resolve, ms));

    const withSafetyLock = useCallback(async (actionFn) => {
        if (lockedRef.current) return;
        
        // 2. Zamknutie
        lockedRef.current = true;
        setIsLoading(true);

        try {

            await Promise.all([
                actionFn(),
                waitMinTime(5000) // 2 sekundy bezpečnostný zámok
            ]);
        } finally {
            // 4. Odomknutie až po uplynutí bezpečného času
            lockedRef.current = false;
            setIsLoading(false);
        }
    }, []);

    const runScene = async () => {
        await withSafetyLock(async () => {
            try {
                const res = await fetch('/api/config/main_scene');
                const config = await res.json();
                const sceneName = config.json_file_name || 'intro.json';

                // Potom voláme hlavnú API
                await toast.promise(
                    api.runScene(sceneName),
                    {
                        loading: 'Spúšťam hlavnú scénu...',
                        success: 'Predstavenie spustené!',
                        error: (err) => `Chyba: ${err.message}`
                    }
                );
            } catch (e) {
                toast.error('Chyba konfigurácie: ' + e.message);
                throw e;
            }
        });
    };

    const stopScene = async () => {
        const shouldStop = await confirm({
            title: "Zastaviť scénu?",
            message: "Skutočne chcete zastaviť prebiehajúcu scénu?",
            confirmText: "Zastaviť",
            type: "danger"
        });

        if (shouldStop) {
            await withSafetyLock(async () => {
                try {
                    await toast.promise(
                        api.stopScene(),
                        {
                            loading: 'Zastavujem...',
                            success: 'Scéna zastavená',
                            error: (err) => `Chyba: ${err.message}`
                        }
                    );
                } catch (e) {
                    throw e;
                }
            });
        }
    };

    return { runScene, stopScene, isLoading };
}