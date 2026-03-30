import { useState } from 'react';
import { Save, X, AlertTriangle, Code, Workflow } from 'lucide-react';
import Button from '../ui/Button';
import JsonEditor from '../Shared/JsonEditor';
import SceneVisualizer from './SceneVisualizer';

import '../../styles/views/scene-editor.css';
import '../../styles/views/scene-flow.css';

export default function SceneEditorModal({ isOpen, onClose, filename, initialContent, onSave }) {
    const [jsonString, setJsonString] = useState(() => (
        initialContent ? JSON.stringify(initialContent, null, 2) : ''
    ));
    const [jsonObj, setJsonObj] = useState(() => (initialContent ?? []));
    const [isValid, setIsValid] = useState(true);
    const [activeTab, setActiveTab] = useState('code');

    const handleCodeChange = (value) => {
        setJsonString(value);
        try {
            const parsed = JSON.parse(value);
            setJsonObj(parsed);
            setIsValid(true);
        } catch {
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
            {/* KEY FIX: large-editor uses display:flex + flex-direction:column.
                Every child in the chain needs min-height:0 so ReactFlow
                can correctly fill the remaining space. */}
            <div className="modal-content large-editor">

                {/* ── Header ─────────────────────────────────────────── */}
                <div className="modal-header">
                    <div className="modal-title-group">
                        <h3>Úprava scény</h3>
                        <span className="file-badge">{filename}</span>
                    </div>
                    <button className="close-btn" onClick={onClose}>
                        <X size={20} />
                    </button>
                </div>

                {/* ── Tabs ───────────────────────────────────────────── */}
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

                {/* ── Body — this is the flex-grow area ─────────────── */}
                {/* min-height: 0 is the critical fix for flex children   */}
                <div className="modal-body-editor">
                    {activeTab === 'code' ? (
                        <JsonEditor value={jsonString} onChange={handleCodeChange} />
                    ) : (
                        // SceneVisualizer already renders .flow-wrapper with height:100%
                        <SceneVisualizer data={jsonObj} />
                    )}
                </div>

                {/* ── Footer ─────────────────────────────────────────── */}
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