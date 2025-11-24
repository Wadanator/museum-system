import { useState, useEffect } from 'react';
import { api } from '../../services/api';
import toast from 'react-hot-toast';
import JsonEditor from '../Shared/JsonEditor';

export default function CommandsView() {
  const [commands, setCommands] = useState([]);
  const [editorContent, setEditorContent] = useState('');
  const [selectedCommand, setSelectedCommand] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadCommands();
  }, []);

  const loadCommands = async () => {
    try {
      const data = await api.getCommands();
      setCommands(data);
    } catch (error) {
      console.error("Chyba:", error);
      toast.error("Nepodarilo sa načítať príkazy");
    }
  };

  const handleLoadCommand = async (cmdName) => {
    if (!cmdName) return;
    if (cmdName === selectedCommand && editorContent) return;

    setLoading(true);
    const loadingToast = toast.loading(`Načítavam ${cmdName}...`);

    try {
      const content = await api.getCommandContent(cmdName);
      if (content.error) throw new Error(content.error);

      setEditorContent(JSON.stringify(content, null, 2));
      setSelectedCommand(cmdName);
      toast.success(`Príkaz načítaný`, { id: loadingToast });
    } catch (error) {
      toast.error('Chyba: ' + error.message, { id: loadingToast });
      setSelectedCommand('');
      setEditorContent('');
    } finally {
      setLoading(false);
    }
  };

  const handleRun = async (cmdName) => {
    toast.promise(
        api.runCommand(cmdName),
        {
            loading: 'Odosielam príkaz...',
            success: `Príkaz ${cmdName} odoslaný`,
            error: (err) => `Chyba: ${err.message}`
        }
    );
  };

  const handleSave = async () => {
    if (!selectedCommand) return;
    
    let json;
    try {
        json = JSON.parse(editorContent);
    } catch (e) {
        return toast.error(`Neplatný JSON: ${e.message}`);
    }

    const loadingToast = toast.loading('Ukladám...');
    try {
        const res = await api.saveCommand(selectedCommand, json);
        if (res.success) {
            toast.success('Príkaz uložený', { id: loadingToast });
            loadCommands();
        } else {
            toast.error('Chyba: ' + res.error, { id: loadingToast });
        }
    } catch (e) {
        toast.error('Chyba komunikácie: ' + e.message, { id: loadingToast });
    }
  };

  const handleNew = () => {
      const name = prompt("Názov nového príkazu (bez .json):");
      if(name) {
          const cleanName = name.endsWith('.json') ? name.replace('.json', '') : name;
          
          setSelectedCommand(cleanName);
          setEditorContent(JSON.stringify([
            { 
              "timestamp": 0, 
              "topic": "room/device", 
              "message": "ON" 
            }
          ], null, 2));
          
          toast('Nový príkaz vytvorený. Uložte ho.', { icon: '⚡' });
      }
  };

  return (
    <div className="tab-content active">
      <div className="header-row" style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px'}}>
        <h2>⚡ Rýchle príkazy</h2>
        <div className="actions" style={{display: 'flex', gap: '10px'}}>
            <button className="btn btn-success btn-small" onClick={handleNew}>➕ Nový</button>
            <button className="btn btn-secondary btn-small" onClick={loadCommands}>🔄 Obnoviť</button>
        </div>
      </div>

      <div className="layout-grid">
        
        {/* ĽAVÝ PANEL: ZOZNAM */}
        <div className="sidebar-list">
            {commands.length === 0 && (
                <div style={{padding: '20px', textAlign: 'center', color: '#6b7280'}}>
                    Žiadne príkazy.
                </div>
            )}

            {commands.map(cmd => (
            <div 
                className={`sidebar-item ${selectedCommand === cmd.name ? 'active-command' : ''}`}
                key={cmd.name} 
                onClick={() => handleLoadCommand(cmd.name)}
            >
                <div style={{marginBottom: '8px'}}>
                    <h4 className="sidebar-item-title">{cmd.name}</h4>
                    <small className="sidebar-item-meta">
                        {new Date(cmd.modified * 1000).toLocaleString()}
                    </small>
                </div>
                
                <div className="sidebar-actions">
                    <button 
                        className="btn btn-warning btn-list" 
                        style={{ color: '#fff' }} 
                        onClick={(e) => { e.stopPropagation(); handleRun(cmd.name); }}
                        title="Vykonať príkaz"
                    >
                        ⚡ Spustiť
                    </button>
                    <button 
                        className="btn btn-secondary btn-list" 
                        style={{ backgroundColor: '#6b7280', color: 'white' }} 
                        onClick={(e) => { e.stopPropagation(); handleLoadCommand(cmd.name); }}
                        title="Upraviť kód"
                    >
                        ✏️ Upraviť
                    </button>
                </div>
            </div>
            ))}
        </div>
        
        {/* PRAVÝ PANEL: EDITOR */}
        <div className="editor-container">
            {selectedCommand ? (
                <>
                    <div className="editor-header-bar">
                        <h3>Úprava: <span className="highlight-orange">{selectedCommand}</span></h3>
                        <button className="btn btn-primary btn-small" onClick={handleSave}>💾 Uložiť zmeny</button>
                    </div>

                    <JsonEditor 
                        value={editorContent} 
                        onChange={setEditorContent} 
                        isLoading={loading} 
                    />
                </>
            ) : (
                <div className="empty-state-container">
                    <div className="empty-state-icon">⚡</div>
                    <p className="empty-state-text">Vyberte príkaz na úpravu</p>
                </div>
            )}
        </div>
      </div>
    </div>
  );
}