import { useRuntime } from '../context/useRuntime';

/**
 * Compatibility hook for components that only need actuator endpoint states.
 * The actual subscription/snapshot logic lives in RuntimeProvider so it
 * survives navigation between dashboard pages.
 */
export function useDeviceRuntimeState() {
    const {
        deviceStates,
        getStateForDevice,
        getDisplayStateForDevice,
        isLoading,
    } = useRuntime();

    return { deviceStates, getStateForDevice, getDisplayStateForDevice, isLoading };
}
