import { useState, useEffect } from 'react';
import { Save, X, AlertTriangle, Code, Workflow } from 'lucide-react';
import Button from '../ui/Button';
import JsonEditor from '../Shared/JsonEditor'; 
import SceneVisualizer from './SceneVisualizer';

/* DÔLEŽITÉ: Uistite sa, že cesta k CSS je správna */
import '../../styles/views/scene-editor.css';
import '../../styles/views/scene-flow.css'; 

export default function SceneEditorModal({ isOpen, onClose, filename, initialContent, onSave }) {
    // ... (state premenné ostávajú rovnaké: jsonString, jsonObj, isValid, activeTab) ...
    const [jsonString, setJsonString] = useState('');
    const [jsonObj, setJsonObj] = useState([]);
    const [isValid, setIsValid] = useState(true);
    const [activeTab, setActiveTab] = useState('code');

    useEffect(() => {
        if (isOpen && initialContent) {
            setJsonString(JSON.stringify(initialContent, null, 2));
            setJsonObj(initialContent);
            setIsValid(true);
            setActiveTab('code');
        }
    }, [isOpen, initialContent]);

    const handleCodeChange = (value) => {
        setJsonString(value);
        try {
            const parsed = JSON.parse(value);
            setJsonObj(parsed);
            setIsValid(true);
        } catch (e) {
            setIsValid(false);
        }
    };

    const handleSave = () => {
        if (!isValid) return;
        try {
            const parsed = JSON.parse(jsonString);
            onSave(filename, parsed);
        } catch (e) {
            console.error(e);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="modal-overlay">
            <div className="modal-content large-editor">
                {/* Header */}
                <div className="modal-header">
                    <div className="modal-title-group">
                        <h3>Úprava scény</h3>
                        <span className="file-badge">{filename}</span>
                    </div>
                    <button className="close-btn" onClick={onClose}><X size={20} /></button>
                </div>

                {/* Tabs */}
                <div className="editor-tabs">
                    <button 
                        className={`editor-tab-btn ${activeTab === 'code' ? 'active' : ''}`}
                        onClick={() => setActiveTab('code')}
                    >
                        <Code size={16} /> JSON Editor
                    </button>
                    <button 
                        className={`editor-tab-btn ${activeTab === 'visual' ? 'active' : ''}`}
                        onClick={() => setActiveTab('visual')}
                        disabled={!isValid}
                    >
                        <Workflow size={16} /> Vizualizácia
                    </button>
                </div>

                {/* Body - TU BOLA CHYBA VÝŠKY */}
                {/* Pridali sme style={{ flex: 1, overflow: 'hidden' }} aby sa to roztiahlo */}
                <div className="modal-body-editor" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                    
                    {activeTab === 'code' ? (
                        <JsonEditor 
                            value={jsonString} 
                            onChange={handleCodeChange} 
                        />
                    ) : (
                        /* Obalíme Visualizer do wrapperu s height: 100% */
                        <div className="flow-wrapper">
                             <SceneVisualizer data={jsonObj} />
                        </div>
                    )}

                </div>

                {/* Footer */}
                <div className="modal-footer">
                    <div className="validation-status">
                        {!isValid && (
                            <span className="error-text">
                                <AlertTriangle size={16} /> Neplatný JSON
                            </span>
                        )}
                    </div>
                    <div className="footer-buttons">
                        <Button variant="secondary" onClick={onClose}>Zrušiť</Button>
                        <Button variant="primary" onClick={handleSave} disabled={!isValid} icon={Save}>
                            Uložiť zmeny
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    );
}