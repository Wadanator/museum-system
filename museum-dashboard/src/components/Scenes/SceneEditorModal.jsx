import { useState, useEffect } from 'react';
import { Save, X, AlertTriangle } from 'lucide-react';
import Button from '../ui/Button';
import JsonEditor from '../Shared/JsonEditor'; // Import tvojho existujúceho editora

export default function SceneEditorModal({ isOpen, onClose, filename, initialContent, onSave }) {
    const [jsonString, setJsonString] = useState('');
    const [isValid, setIsValid] = useState(true);

    // Inicializácia editora
    useEffect(() => {
        if (isOpen && initialContent) {
            // Prevedieme objekt na pekne formátovaný string pre editor
            setJsonString(JSON.stringify(initialContent, null, 2));
            setIsValid(true);
        }
    }, [isOpen, initialContent]);

    // Validácia pri zmene
    const handleChange = (value) => {
        setJsonString(value);
        try {
            JSON.parse(value);
            setIsValid(true);
        } catch (e) {
            setIsValid(false);
        }
    };

    const handleSave = () => {
        if (!isValid) return;
        try {
            // Pred uložením parse-neme string späť na objekt
            const parsed = JSON.parse(jsonString);
            onSave(filename, parsed);
        } catch (e) {
            console.error("Save error", e);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="modal-overlay">
            <div className="modal-content large-editor">
                {/* Hlavička */}
                <div className="modal-header">
                    <div className="modal-title-group">
                        <h3>Úprava scény</h3>
                        <span className="file-badge">{filename}</span>
                    </div>
                    <button className="close-btn" onClick={onClose}><X size={20} /></button>
                </div>

                {/* Telo s editorom */}
                <div className="modal-body-editor">
                    <JsonEditor 
                        value={jsonString} 
                        onChange={handleChange} 
                    />
                </div>

                {/* Footer */}
                <div className="modal-footer">
                    <div className="validation-status">
                        {!isValid && (
                            <span className="error-text">
                                <AlertTriangle size={16} /> Neplatný JSON formát
                            </span>
                        )}
                    </div>
                    <div className="footer-buttons">
                        <Button variant="secondary" onClick={onClose}>Zrušiť</Button>
                        <Button 
                            variant="primary" 
                            onClick={handleSave} 
                            disabled={!isValid}
                            icon={Save}
                        >
                            Uložiť zmeny
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    );
}