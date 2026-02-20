import toast from 'react-hot-toast';
import { api } from '../services/api';
import { useConfirm } from '../context/ConfirmContext';

export function useSystemActions() {
    const { confirm } = useConfirm();

    // Univerzálna funkcia pre systémové príkazy
    const performAction = async (actionFn, title, message, successText) => {
        if (await confirm({
            title: title,
            message: message,
            confirmText: "Vykonať",
            type: "danger"
        })) {
            toast.promise(
                actionFn(),
                {
                    loading: 'Vykonávam...',
                    success: successText,
                    error: (err) => `Chyba: ${err.message}`
                }
            );
        }
    };

    const restartService = () => performAction(
        api.restartService, // Predpokladám, že máš túto metódu v api.js, ak nie, doplň ju
        "Reštartovať službu?",
        "Múzejný systém sa reštartuje. Výpadok potrvá pár sekúnd.",
        "Služba sa reštartuje..."
    );

    const rebootSystem = () => performAction(
        api.rebootSystem,
        "Reštartovať Raspberry Pi?",
        "Celý systém sa reštartuje. Toto potrvá cca 1-2 minúty.",
        "Systém sa reštartuje..."
    );

    const shutdownSystem = () => performAction(
        api.shutdownSystem,
        "Vypnúť Raspberry Pi?",
        "Systém sa úplne vypne. Na zapnutie bude potrebné odpojiť a pripojiť napájanie.",
        "Systém sa vypína..."
    );

    return { restartService, rebootSystem, shutdownSystem };
}