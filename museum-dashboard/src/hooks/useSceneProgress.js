import { useRuntime } from '../context/useRuntime';

export function useSceneProgress() {
    const { activeState, resetActiveState } = useRuntime();
    return { activeState, resetActiveState };
}
