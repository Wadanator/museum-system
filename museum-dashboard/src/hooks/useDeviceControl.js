import toast from 'react-hot-toast';
import { api } from '../services/api';

export function useDeviceControl(topic, deviceName) {
    
    const sendCommand = async (payload, successLabel = null) => {
        try {
            await api.sendMqtt(topic, payload);
            
            if (successLabel) {
                toast.success(`${deviceName}: ${successLabel}`);
            }
            
            return { success: true };
        } catch (e) {
            console.error(`Device command error for ${deviceName}:`, e);
            toast.error(`Chyba zariadenia ${deviceName}`);
            return { success: false, error: e };
        }
    };

    return { sendCommand };
}