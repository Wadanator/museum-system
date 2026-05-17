import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Loader2, RefreshCw, Sparkles, Activity } from 'lucide-react';
import { useScenes } from '../../hooks/useScenes';
import SceneCard from '../Scenes/SceneCard';
import SceneEditorModal from '../Scenes/SceneEditorModal';
import Button from '../ui/Button';
import PageHeader from '../ui/PageHeader';
import Modal from '../ui/Modal';
import LiveView from './LiveView';
import Card from '../ui/Card';
import '../../styles/views/scenes-view.css';

export default function ScenesView() {
    const navigate = useNavigate();
    const { scenes, loading, fetchScenes, playScene, loadSceneContent, saveSceneContent } = useScenes();

    const [liveSceneName, setLiveSceneName] = useState(null);
    const [liveSceneData, setLiveSceneData] = useState(null);

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
        } catch (_err) {
            // fall through — modal won't open
        }
    };

    const handleSave = async (filename, content) => {
        await saveSceneContent(filename, content);
        setEditorOpen(false);
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

        await saveSceneContent(filename, template);
        setNewSceneModal({ isOpen: false, name: '' });
        navigate(`/scene-editor/${filename}`);
    };

    const handlePlayFromCard = async (filename) => {
        try {
            const content = await loadSceneContent(filename);
            setLiveSceneName(filename);
            setLiveSceneData(content);
            playScene(filename);
        } catch (_err) {
            // play failure is visible in LiveView
        }
    };

    const handleLiveSceneDataLoaded = (filename, content) => {
        setLiveSceneName(filename);
        setLiveSceneData(content);
    };

    return (
        <div className="view-container scenes-view">
            <PageHeader
                title="Knižnica Scén"
                subtitle="Dostupné show súbory"
                icon={Sparkles}
            >
                <Button variant="secondary" icon={RefreshCw} onClick={fetchScenes} disabled={loading} size="small">
                    Obnoviť
                </Button>
                <Button variant="primary" icon={Plus} onClick={handleCreate}>
                    Nová scéna
                </Button>
            </PageHeader>

            {loading ? (
                <div className="loading-state">
                    <Loader2 className="animate-spin" size={40} strokeWidth={1.5} />
                    <span>Načítavam scenáre...</span>
                </div>
            ) : (
                <div className="scenes-grid">
                    {scenes.length === 0 ? (
                        <div className="empty-state">
                            <Sparkles size={48} opacity={0.2} />
                            Žiadne scény sa nenašli. Vytvorte novú.
                        </div>
                    ) : (
                        scenes.map((scene) => (
                            <SceneCard
                                key={scene.name}
                                scene={scene}
                                onPlay={handlePlayFromCard}
                                onEdit={handleEdit}
                            />
                        ))
                    )}
                </div>
            )}

            {liveSceneName && (
                <Card
                    title="Live Monitor"
                    icon={Activity}
                    className="scenes-live-card"
                >
                    <LiveView
                        embedded
                        showSceneSelector={false}
                        selectedScene={liveSceneName}
                        sceneData={liveSceneData}
                        onSceneDataLoaded={handleLiveSceneDataLoaded}
                    />
                </Card>
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
                title="Nová scéna"
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
