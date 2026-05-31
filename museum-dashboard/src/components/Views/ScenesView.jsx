import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Loader2, RefreshCw, Drama } from 'lucide-react';
import { useScenes } from '../../hooks/useScenes';
import SceneCard from '../Scenes/SceneCard';
import SceneEditorModal from '../Scenes/SceneEditorModal';
import Button from '../ui/Button';
import PageHeader from '../ui/PageHeader';
import Modal from '../ui/Modal';
import StateNotice from '../ui/StateNotice';
import '../../styles/views/scenes-view.css';

export default function ScenesView() {
    const navigate = useNavigate();
    const { scenes, loading, fetchScenes, playScene, loadSceneContent, saveSceneContent } = useScenes();

    // JSON editor modal (gear button)
    const [editorOpen, setEditorOpen] = useState(false);
    const [editingFile, setEditingFile] = useState(null);
    const [editorContent, setEditorContent] = useState(null);

    const [newSceneModal, setNewSceneModal] = useState({ isOpen: false, name: '' });

    // Open scene in JSON editor modal (gear button)
    const handleEdit = async (filename) => {
        try {
            const content = await loadSceneContent(filename);
            setEditingFile(filename);
            setEditorContent(content);
            setEditorOpen(true);
        } catch {
            // fall through — modal won't open
        }
    };

    const handleSave = async (filename, content) => {
        return saveSceneContent(filename, content);
    };

    const handleCreate = () => {
        setNewSceneModal({ isOpen: true, name: '' });
    };

    const handleCreateConfirm = async () => {
        const name = newSceneModal.name.trim();
        if (!name) return;
        const filename = name.endsWith('.json') ? name : `${name}.json`;
        const sceneId = filename.replace('.json', '');

        // Minimal V2 state-machine template
        const template = {
            sceneId,
            version: '2.0',
            initialState: 'INTRO',
            states: {
                INTRO: { transitions: [{ type: 'always', goto: 'END' }] },
            },
        };

        const saved = await saveSceneContent(filename, template);
        if (!saved) return;
        setNewSceneModal({ isOpen: false, name: '' });
        navigate(`/scene-editor/${filename}`);
    };

    const handlePlayFromCard = async (filename) => {
        const started = await playScene(filename);
        if (started) {
            navigate('/live');
        }
    };

    return (
        <div className="view-container scenes-view">
            <PageHeader
                title="Knižnica scén"
                subtitle="Dostupné show súbory"
                icon={Drama}
            >
                <Button variant="toolbar" icon={RefreshCw} onClick={fetchScenes} disabled={loading} size="small">
                    Obnoviť
                </Button>
            </PageHeader>

            {loading ? (
                <StateNotice
                    icon={Loader2}
                    title="Načítavam scény"
                    message="Zoznam dostupných scenárov sa obnovuje zo servera."
                    isLoading
                />
            ) : (
                <div className="scenes-grid">
                    {scenes.map((scene) => (
                        <SceneCard
                            key={scene.name}
                            scene={scene}
                            onPlay={handlePlayFromCard}
                            onEdit={handleEdit}
                        />
                    ))}
                    <button
                        type="button"
                        className="create-scene-card"
                        onClick={handleCreate}
                    >
                        <span className="create-scene-card__icon">
                            <Plus size={28} />
                        </span>
                        <span className="create-scene-card__title">Vytvoriť scénu</span>
                        <span className="create-scene-card__meta">Nový JSON scenár</span>
                    </button>
                </div>
            )}

            <SceneEditorModal
                key={editingFile}
                isOpen={editorOpen}
                onClose={() => setEditorOpen(false)}
                filename={editingFile}
                initialContent={editorContent}
                onSave={handleSave}
            />

            <Modal
                isOpen={newSceneModal.isOpen}
                title="Vytvoriť scénu"
                onClose={() => setNewSceneModal({ isOpen: false, name: '' })}
                footer={
                    <>
                        <Button variant="secondary" onClick={() => setNewSceneModal({ isOpen: false, name: '' })}>
                            Zrušiť
                        </Button>
                        <Button
                            variant="primary"
                            onClick={handleCreateConfirm}
                            disabled={!newSceneModal.name.trim()}
                        >
                            Vytvoriť
                        </Button>
                    </>
                }
            >
                <p className="modal-body-text">Zadajte názov novej scény (bez .json):</p>
                <input
                    type="text"
                    className="modal-input"
                    value={newSceneModal.name}
                    onChange={(e) => setNewSceneModal(prev => ({ ...prev, name: e.target.value }))}
                    onKeyDown={(e) => e.key === 'Enter' && handleCreateConfirm()}
                    autoFocus
                    placeholder="napr. uvod_show"
                />
            </Modal>
        </div>
    );
}
