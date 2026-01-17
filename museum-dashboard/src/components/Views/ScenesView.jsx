import { useState, useEffect } from 'react';
import { api } from '../../services/api';
import toast from 'react-hot-toast';
import JsonEditor from '../Shared/JsonEditor';
import { 
  Plus, 
  Play, 
  Edit, 
  CheckCircle2, 
  Save, 
  ArrowLeft, 
  Drama 
} from 'lucide-react';

// Import UI komponentov
import PageHeader from '../ui/PageHeader';
import Button from '../ui/Button';

export default function ScenesView() {
  const [scenes, setScenes] = useState([]);
  const [editorContent, setEditorContent] = useState('');
  const [selectedScene, setSelectedScene] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadScenes();
  }, []);

  const loadScenes = async () => {
    try {
      const data = await api.getScenes();
      setScenes(data);
    } catch (error) {
      console.error(error);
      toast.error("Nepodarilo sa načítať zoznam scén");
    }
  };

  const handleLoadSceneContent = async (sceneName) => {
    if (!sceneName) return;
    if (sceneName === selectedScene && editorContent) return;

    setLoading(true);
    const loadingToast = toast.loading(`Načítavam ${sceneName}...`);

    try {
      const content = await api.getSceneContent(sceneName);
      if (content.error) throw new Error(content.error);

      setEditorContent(JSON.stringify(content, null, 2));
      setSelectedScene(sceneName);
      toast.success(`Scéna načítaná`, { id: loadingToast });
    } catch (error) {
      toast.error('Chyba: ' + error.message, { id: loadingToast });
      setSelectedScene('');
      setEditorContent('');
    } finally {
      setLoading(false);
    }
  };

  const validateSceneContent = (silent = false) => {
    try {
      const json = JSON.parse(editorContent);
      if (!silent) toast.success('JSON je platný');
      return json;
    } catch (e) {
      if (!silent) toast.error(`Neplatný JSON: ${e.message}`);
      return null;
    }
  };

  const handleSave = async () => {
    if (!selectedScene) return;
    const json = validateSceneContent(true);
    if (!json) return toast.error("Opravte chyby v JSONe pred uložením");

    const loadingToast = toast.loading('Ukladám scénu...');
    try {
      const res = await api.saveScene(selectedScene, json);
      if (res.success) {
        toast.success('Scéna úspešne uložená', { id: loadingToast });
        loadScenes();
      } else {
        toast.error('Chyba servera: ' + (res.error || 'Neznáma chyba'), { id: loadingToast });
      }
    } catch (e) {
      toast.error('Chyba komunikácie: ' + e.message, { id: loadingToast });
    }
  };

  const handleRun = async (sceneName) => {
    toast.promise(
      api.runScene(sceneName),
      {
        loading: `Spúšťam ${sceneName}...`,
        success: (res) => res.success ? `Scéna ${sceneName} spustená` : `Chyba: ${res.error}`,
        error: (err) => `Chyba komunikácie: ${err.message}`
      }
    );
  };

  const handleNewScene = () => {
    const name = prompt("Zadajte názov novej scény (bez .json):");
    if (name) {
      const fullName = name.endsWith('.json') ? name : name + '.json';
      const template = {
        sceneId: name.replace('.json', ''),
        version: "1.0",
        initialState: "start",
        states: {
            start: { 
                description: "Štart scény",
                onEnter: [{ action: "mqtt", topic: "room/light", message: "ON" }], 
                transitions: [{ type: "timeout", delay: 5, goto: "END" }] 
            }
        }
      };
      
      setSelectedScene(fullName);
      setEditorContent(JSON.stringify(template, null, 2));
      toast('Nová scéna vytvorená. Nezabudnite ju uložiť.', { icon: '🆕' });
    }
  };

  return (
    <div className="tab-content active">
      <PageHeader title="Správa scén" icon={Drama}>
        <Button variant="success" onClick={handleNewScene} icon={Plus}>
            Nová scéna
        </Button>
      </PageHeader>
      
      <div className="layout-grid">
        {/* ĽAVÝ PANEL: Zoznam */}
        <div className="sidebar-list">
            {scenes.length === 0 && (
                <div style={{padding: '20px', textAlign: 'center', color: '#6b7280'}}>
                    Žiadne scény.<br/>Skontrolujte pripojenie.
                </div>
            )}

            {scenes.map(scene => (
            <div 
                className={`sidebar-item ${selectedScene === scene.name ? 'active-scene' : ''}`}
                key={scene.name} 
                onClick={() => handleLoadSceneContent(scene.name)}
            >
                <div style={{marginBottom: '8px'}}>
                    <h4 className="sidebar-item-title">{scene.name}</h4>
                    <small className="sidebar-item-meta">
                        {new Date(scene.modified * 1000).toLocaleString()}
                    </small>
                </div>
                
                <div className="sidebar-actions">
                    <Button 
                        variant="primary" 
                        size="small"
                        icon={Play}
                        onClick={(e) => { e.stopPropagation(); handleRun(scene.name); }}
                        title="Spustiť scénu"
                    >
                        Spustiť
                    </Button>
                    <Button 
                        variant="secondary" 
                        size="small"
                        icon={Edit}
                        style={{ backgroundColor: '#6b7280', color: 'white' }}
                        onClick={(e) => { e.stopPropagation(); handleLoadSceneContent(scene.name); }}
                        title="Upraviť scénu"
                    >
                        Upraviť
                    </Button>
                </div>
            </div>
            ))}
        </div>

        {/* PRAVÝ PANEL: Editor */}
        <div className="editor-container">
            {selectedScene ? (
                <>
                    <div className="editor-header-bar">
                        <h3>Editujem: <span className="highlight-blue">{selectedScene}</span></h3>
                        <div className="editor-actions-group">
                            <Button variant="secondary" size="small" onClick={() => validateSceneContent()} icon={CheckCircle2}>
                                Overiť
                            </Button>
                            <Button variant="primary" size="small" onClick={handleSave} icon={Save}>
                                Uložiť
                            </Button>
                        </div>
                    </div>
                    
                    <div style={{flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column'}}>
                        <JsonEditor 
                            value={editorContent} 
                            onChange={setEditorContent} 
                            isLoading={loading} 
                        />
                    </div>
                </>
            ) : (
                <div className="empty-state-container">
                    <div className="empty-state-icon"><ArrowLeft size={48} /></div>
                    <p className="empty-state-text">Vyberte scénu zo zoznamu pre úpravu</p>
                </div>
            )}
        </div>
      </div>
    </div>
  );
}