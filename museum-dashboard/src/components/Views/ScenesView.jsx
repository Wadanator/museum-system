import { useState } from 'react';
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
    const { scenes, loading, fetchScenes, playScene, loadSceneContent, saveSceneContent } = useScenes();

    const [editorOpen, setEditorOpen] = useState(false);
    const [editingFile, setEditingFile] = useState(null);
    const [editorContent, setEditorContent] = useState(null);

    const [liveSceneName, setLiveSceneName] = useState(null);
    const [liveSceneData, setLiveSceneData] = useState(null);

    const [newSceneModal, setNewSceneModal] = useState({ isOpen: false, name: '' });

    const handleEdit = async (filename) => {
        try {
            const content = await loadSceneContent(filename);
            setEditingFile(filename);
            setEditorContent(content);
            setEditorOpen(true);
        } catch (error) {
            console.error(error);
        }
    };

    const handleSave = async (filename, content) => {
        const success = await saveSceneContent(filename, content);
        if (success) {
            setEditorOpen(false);
        }
    };

    const handleCreate = () => {
        setNewSceneModal({ isOpen: true, name: '' });
    };

    const handleCreateConfirm = async () => {
        const name = newSceneModal.name.trim();
        if (!name) return;
        const filename = name.endsWith('.json') ? name : `${name}.json`;
        const template = [
            { type: 'log', message: `Začiatok scény ${name}` },
            { type: 'delay', value: 1 },
        ];
        await saveSceneContent(filename, template);
        setNewSceneModal({ isOpen: false, name: '' });
    };

    const handlePlayFromCard = async (filename) => {
        try {
            const content = await loadSceneContent(filename);
            setLiveSceneName(filename);
            setLiveSceneData(content);
            playScene(filename);
        } catch (error) {
            console.error(error);
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
                key={`${editingFile ?? 'new'}-${editorOpen ? 'open' : 'closed'}`}
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
