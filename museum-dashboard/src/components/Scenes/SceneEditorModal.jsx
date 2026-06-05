import { useState } from 'react';
import { Save, X, AlertTriangle, Code, Workflow } from 'lucide-react';
import Button from '../ui/Button';
import JsonEditor from '../Shared/JsonEditor';
import SceneVisualizer from './SceneVisualizer';
import { api } from '../../services/api';

import '../../styles/views/scene-editor.css';
import '../../styles/views/scene-flow.css';

export default function SceneEditorModal({ isOpen, onClose, filename, initialContent, onSave }) {
    const [jsonString, setJsonString] = useState(() => (
        initialContent ? JSON.stringify(initialContent, null, 2) : ''
    ));
    const [jsonObj, setJsonObj] = useState(() => (initialContent ?? []));
    const [isValid, setIsValid] = useState(true);
    const [isValidating, setIsValidating] = useState(false);
    const [validationErrors, setValidationErrors] = useState([]);
    const [activeTab, setActiveTab] = useState('code');

    const handleCodeChange = (value) => {
        setJsonString(value);
        try {
            const parsed = JSON.parse(value);
            setJsonObj(parsed);
            setIsValid(true);
            setValidationErrors([]);
        } catch {
            setIsValid(false);
            setValidationErrors([]);
        }
    };

    const formatValidationError = (error) => {
        if (!error) return 'Scena nie je validna';
        return `${error.path}: ${error.message}`;
    };

    const handleSave = async () => {
        if (!isValid) return;
        let shouldClose = false;
        try {
            const parsed = JSON.parse(jsonString);
            setIsValidating(true);
            const validation = await api.validateScene(parsed);
            if (!validation.valid) {
                setValidationErrors(validation.errors || []);
                return;
            }
            const saved = await onSave(filename, parsed);
            if (saved === false) {
                return;
            }
            shouldClose = true;
        } catch (e) {
            console.error(e);
            setValidationErrors([{
                path: '<root>',
                message: e.message || 'Validacia zlyhala',
            }]);
        } finally {
            setIsValidating(false);
            if (shouldClose) onClose();
        }
    };

    if (!isOpen) return null;

    return (
        <div className="modal-overlay">
            {/* KEY FIX: large-editor uses display:flex + flex-direction:column.
                Every child in the chain needs min-height:0 so ReactFlow
                can correctly fill the remaining space. */}
            <div className="modal-content large-editor">

                {/* -- Header ------------------------------------------- */}
                <div className="modal-header">
                    <div className="modal-title-group">
                        <h3>Úprava scény</h3>
                        <span className="file-badge">{filename}</span>
                    </div>
                    <Button
                        variant="ghost"
                        size="small"
                        className="close-btn"
                        onClick={onClose}
                        icon={X}
                        aria-label="Zatvoriť"
                        title="Zatvoriť"
                        cooldown={0}
                    />
                </div>

                {/* -- Tabs --------------------------------------------- */}
                <div className="editor-tabs">
                    <Button
                        variant="ghost"
                        size="small"
                        className={`editor-tab-btn ${activeTab === 'code' ? 'active' : ''}`}
                        onClick={() => setActiveTab('code')}
                        cooldown={0}
                    >
                        <Code size={16} /> JSON Editor
                    </Button>
                    <Button
                        variant="ghost"
                        size="small"
                        className={`editor-tab-btn ${activeTab === 'visual' ? 'active' : ''}`}
                        onClick={() => setActiveTab('visual')}
                        disabled={!isValid}
                        cooldown={0}
                    >
                        <Workflow size={16} /> Vizualizácia
                    </Button>
                </div>

                {/* -- Body - this is the flex-grow area --------------- */}
                {/* min-height: 0 is the critical fix for flex children   */}
                <div className="modal-body-editor">
                    {activeTab === 'code' ? (
                        <JsonEditor value={jsonString} onChange={handleCodeChange} />
                    ) : (
                        // SceneVisualizer already renders .flow-wrapper with height:100%
                        <SceneVisualizer data={jsonObj} />
                    )}
                </div>

                {/* -- Footer ------------------------------------------- */}
                <div className="modal-footer">
                    <div className="validation-status">
                        {!isValid && (
                            <span className="error-text">
                                <AlertTriangle size={16} /> Neplatný JSON
                            </span>
                        )}
                        {isValid && validationErrors.length > 0 && (
                            <span
                                className="error-text"
                                title={validationErrors.map(formatValidationError).join('\n')}
                            >
                                <AlertTriangle size={16} />
                                {formatValidationError(validationErrors[0])}
                            </span>
                        )}
                    </div>
                    <div className="footer-buttons">
                        <Button variant="secondary" onClick={onClose}>Zrušiť</Button>
                        <Button
                            variant="primary"
                            onClick={handleSave}
                            disabled={!isValid || isValidating}
                            icon={Save}
                            loading={isValidating}
                        >
                            Uložiť zmeny
                        </Button>
                    </div>
                </div>

            </div>
        </div>
    );
}
