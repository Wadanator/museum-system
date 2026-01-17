import toast from 'react-hot-toast';
import { api } from '../services/api';

export function useDeviceControl(topic, deviceName) {
    
    const sendCommand = async (payload, successLabel = null) => {
        try {
            await api.sendMqtt(topic, payload);
            
            if (successLabel) {
                toast.success(`${deviceName}: ${successLabel}`);
            }
        } catch (e) {
            console.error(e);
            toast.error(`Chyba zariadenia ${deviceName}`);
        }
    };

    return { sendCommand };
}