import { useState, useEffect } from 'react';
import { api } from '../../services/api';
import toast from 'react-hot-toast';
import JsonEditor from '../Shared/JsonEditor';
import { 
    Zap, LayoutGrid, FileJson, Play, Save, Plus, 
    Lightbulb, Settings, Cpu // Pridané ikony
} from 'lucide-react';

import PageHeader from '../ui/PageHeader';
import Button from '../ui/Button';
import RelayCard from '../Devices/RelayCard';
import MotorCard from '../Devices/MotorCard';

export default function CommandsView() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [devices, setDevices] = useState({ relays: [], motors: [] });
  const [commands, setCommands] = useState([]);
  const [editorContent, setEditorContent] = useState('');
  const [selectedCommand, setSelectedCommand] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
        const [cmds, devs] = await Promise.all([
            api.getCommands(),
            api.getDevices()
        ]);
        setCommands(cmds);
        if (devs && !devs.error) setDevices(devs);
    } catch (e) {
        console.error(e);
        toast.error("Chyba načítania dát");
    }
  };

  const handleLoadCommand = async (cmdName) => {
    if (!cmdName) return;
    setLoading(true);
    try {
      const content = await api.getCommandContent(cmdName);
      setEditorContent(JSON.stringify(content, null, 2));
      setSelectedCommand(cmdName);
    } catch (e) { toast.error(e.message); }
    finally { setLoading(false); }
  };

  const handleRunFile = async (cmdName) => {
      toast.promise(api.runCommand(cmdName), {
          loading: 'Odosielam...',
          success: 'Vykonané',
          error: 'Chyba'
      });
  };

  const handleSave = async () => {
    try {
        const json = JSON.parse(editorContent);
        await api.saveCommand(selectedCommand, json);
        toast.success("Uložené");
        loadData();
    } catch(e) { toast.error("Chyba ukladania: " + e.message); }
  };

  const handleNew = () => {
    const name = prompt("Názov nového príkazu (bez .json):");
    if(name) {
        const cleanName = name.replace('.json', '');
        setSelectedCommand(cleanName);
        setEditorContent('[\n  {\n    "topic": "room/device",\n    "message": "ON"\n  }\n]');
        // Opravené: Žiadne emoji v toaste
        toast.success('Nový príkaz vytvorený');
    }
  };

  // Štýl pre nadpisy sekcií
  const sectionTitleStyle = {
      display: 'flex', 
      alignItems: 'center', 
      gap: '10px', 
      fontSize: '1.2rem', 
      color: '#374151',
      marginBottom: '20px',
      marginTop: '10px'
  };

  return (
    <div className="tab-content active">
      <PageHeader title="Ovládací Panel" icon={Zap}>
        <div style={{ display: 'flex', gap: '8px', background: '#e5e7eb', padding: '4px', borderRadius: '8px' }}>
            <Button 
                variant={activeTab === 'dashboard' ? 'primary' : 'ghost'}
                size="small"
                onClick={() => setActiveTab('dashboard')}
                icon={LayoutGrid}
            >
                Panel
            </Button>
            <Button 
                variant={activeTab === 'files' ? 'primary' : 'ghost'}
                size="small"
                onClick={() => setActiveTab('files')}
                icon={FileJson}
            >
                Súbory
            </Button>
        </div>
      </PageHeader>

      {activeTab === 'dashboard' ? (
          <div className="animate-fade-in">
              {/* Sekcia RELÉ - Opravený nadpis */}
              <h3 style={sectionTitleStyle}>
                  <Lightbulb size={24} color="#f59e0b" /> 
                  Zariadenia & Efekty
              </h3>
              
              <div className="devices-grid relays">
                  {devices.relays?.map((dev, i) => <RelayCard key={i} device={dev} />)}
              </div>

              {/* Sekcia MOTORY - Opravený nadpis */}
              {devices.motors?.length > 0 && (
                  <>
                    <h3 style={{...sectionTitleStyle, marginTop: '40px'}}>
                        <Settings size={24} color="#4b5563" /> 
                        Motorické Pohony
                    </h3>
                    <div className="devices-grid motors">
                        {devices.motors.map((dev, i) => <MotorCard key={i} device={dev} />)}
                    </div>
                  </>
              )}
          </div>
      ) : (
          /* Editor súborov */
          <div className="layout-grid">
            <div className="sidebar-list">
                <div style={{padding: '10px'}}>
                    <Button variant="success" size="small" onClick={handleNew} icon={Plus} style={{width: '100%'}}>
                        Nový Príkaz
                    </Button>
                </div>
                {commands.map(cmd => (
                    <div className={`sidebar-item ${selectedCommand === cmd.name ? 'active-command' : ''}`}
                         key={cmd.name} onClick={() => handleLoadCommand(cmd.name)}>
                        <div style={{overflow: 'hidden', textOverflow: 'ellipsis'}}>{cmd.name}</div>
                        <div className="sidebar-actions">
                             <Button 
                                variant="warning" 
                                size="small" 
                                icon={Play}
                                onClick={(e) => {e.stopPropagation(); handleRunFile(cmd.name)}} 
                                title="Spustiť"
                             />
                        </div>
                    </div>
                ))}
            </div>
            
            <div className="editor-container">
                {selectedCommand ? (
                    <>
                        <div className="editor-header-bar">
                            <h3>{selectedCommand}</h3>
                            <Button size="small" onClick={handleSave} icon={Save}>Uložiť</Button>
                        </div>
                        <JsonEditor value={editorContent} onChange={setEditorContent} isLoading={loading} />
                    </>
                ) : (
                    <div className="empty-state-container">
                        <Cpu size={48} color="#9ca3af" />
                        <p style={{marginTop: 10, color: '#6b7280'}}>Vyberte príkaz na úpravu</p>
                    </div>
                )}
            </div>
          </div>
      )}
    </div>
  );
}