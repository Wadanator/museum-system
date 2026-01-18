import { useState } from 'react';
import { Plus, Loader2, RefreshCw, Drama } from 'lucide-react';
import { useScenes } from '../../hooks/useScenes';
import SceneCard from '../Scenes/SceneCard';
import SceneEditorModal from '../Scenes/SceneEditorModal';
import Button from '../ui/Button';
import PageHeader from '../ui/PageHeader';
import '../../styles/views/scenes-view.css';

export default function ScenesView() {
    const { scenes, loading, fetchScenes, playScene, loadSceneContent, saveSceneContent } = useScenes();

    // State pre Editor
    const [editorOpen, setEditorOpen] = useState(false);
    const [editingFile, setEditingFile] = useState(null);
    const [editorContent, setEditorContent] = useState(null);

    // Otvorenie editora
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

    // Uloženie
    const handleSave = async (filename, content) => {
        const success = await saveSceneContent(filename, content);
        if (success) {
            setEditorOpen(false);
        }
    };

    // Nová scéna
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
            {/* Nový Header */}
            <PageHeader 
                title="Scenáre" 
                subtitle="Správa a editácia show súborov"
                icon={Drama}
            >
                <Button variant="secondary" icon={RefreshCw} onClick={fetchScenes} disabled={loading} size="small">
                    Obnoviť
                </Button>
                <Button variant="primary" icon={Plus} onClick={handleCreate}>
                    Nová scéna
                </Button>
            </PageHeader>

            {/* Grid */}
            {loading ? (
                <div className="loading-state">
                    <Loader2 className="animate-spin" size={32} />
                    <span>Načítavam zoznam scén...</span>
                </div>
            ) : (
                <div className="scenes-grid">
                    {scenes.length === 0 ? (
                        <div className="empty-state">Žiadne scény sa nenašli.</div>
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

            {/* Editor Modal */}
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