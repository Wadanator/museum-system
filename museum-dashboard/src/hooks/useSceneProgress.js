import { useState, useEffect } from 'react';
import { socket } from '../services/socket';

export function useSceneProgress() {
    const [activeState, setActiveState] = useState(null);

    useEffect(() => {
        const handleProgress = (data) => {
            if (data?.activeState) {
                setActiveState(data.activeState);
            }
        };

        socket.on('scene_progress', handleProgress);
        return () => socket.off('scene_progress', handleProgress);
    }, []);

    const resetActiveState = () => setActiveState(null);

    return { activeState, resetActiveState };
}
