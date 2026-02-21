import { useState } from 'react';
import { Plus, Loader2, RefreshCw, Sparkles, Activity } from 'lucide-react';
import { useScenes } from '../../hooks/useScenes';
import SceneCard from '../Scenes/SceneCard';
import SceneEditorModal from '../Scenes/SceneEditorModal';
import Button from '../ui/Button';
import PageHeader from '../ui/PageHeader';
import LiveView from './LiveView';
import Card from '../ui/Card';
import '../../styles/views/scenes-view.css';

export default function ScenesView() {
    const { scenes, loading, fetchScenes, playScene, loadSceneContent, saveSceneContent } = useScenes();

    const [editorOpen, setEditorOpen] = useState(false);
    const [editingFile, setEditingFile] = useState(null);
    const [editorContent, setEditorContent] = useState(null);

    const handleEdit = async (filename) => {
        try {
            const content = await loadSceneContent(filename);
            setEditingFile(filename);
            setEditorContent(content);
            setEditorOpen(true);
        } catch (e) {
            console.error(e);
        }
    };

    const handleSave = async (filename, content) => {
        const success = await saveSceneContent(filename, content);
        if (success) {
            setEditorOpen(false);
        }
    };

    const handleCreate = () => {
        const name = prompt("Zadajte názov novej scény (bez .json):");
        if (name) {
            const filename = name.endsWith('.json') ? name : `${name}.json`;
            const template = [
                { type: "log", message: `Začiatok scény ${name}` },
                { type: "delay", value: 1 }
            ];
            saveSceneContent(filename, template);
        }
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
                    {/* Oprava: Odstránený inline style, parent .loading-state má gap: 16px v CSS */}
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
                                onPlay={playScene}
                                onEdit={handleEdit}
                            />
                        ))
                    )}
                </div>
            )}



            <Card
                title="Live Monitor"
                icon={Activity}
                className="scenes-live-card"
            >
                <LiveView embedded />
            </Card>

            <SceneEditorModal 
                isOpen={editorOpen}
                onClose={() => setEditorOpen(false)}
                filename={editingFile}
                initialContent={editorContent}
                onSave={handleSave}
            />
        </div>
    );
}