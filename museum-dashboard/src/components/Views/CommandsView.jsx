import { useState, useEffect } from 'react';
import { api } from '../../services/api';
import toast from 'react-hot-toast';
import JsonEditor from '../Shared/JsonEditor';

// --- RELÉ KARTA ---
const RelayCard = ({ device }) => {
  const sendCommand = async (cmd) => {
    try {
        await api.sendMqtt(device.topic, cmd);
        
        // TOTO CHÝBALO: Vizuálna odozva
        const label = cmd === 'ON' ? 'ZAPNUTÉ' : 'VYPNUTÉ';
        toast.success(`${device.name}: ${label}`, {
            icon: cmd === 'ON' ? '🟢' : '⚫',
            duration: 2000
        });

    } catch (e) {
        toast.error("Chyba komunikácie");
    }
  };

  return (
    <div className="device-card">
        <div className="relay-header">
            <div className="relay-icon">{device.icon || '🔌'}</div>
            <div className="relay-name">{device.name}</div>
        </div>

        <div className="btn-group-dual">
            <button className="btn-dual off" onClick={() => sendCommand("OFF")}>
                Vypnúť
            </button>
            <button className="btn-dual on" onClick={() => sendCommand("ON")}>
                Zapnúť
            </button>
        </div>
    </div>
  );
};

// --- MOTOR KARTA ---
const MotorCard = ({ device }) => {
  const speed = device.speed || 100;

  const sendCmd = async (cmd, label) => {
      let payload;
      if (cmd === 'LEFT') payload = `ON:${speed}:L`;
      if (cmd === 'RIGHT') payload = `ON:${speed}:R`;
      if (cmd === 'STOP') payload = `OFF`;

      try {
        await api.sendMqtt(device.topic, payload);
        toast.success(`${device.name}: ${label}`);
      } catch (e) {
        toast.error("Chyba motora");
      }
  };

  return (
    <div className="device-card">
        <div className="motor-header">
            <span className="motor-title">{device.name}</span>
            <span className="motor-meta">{speed}% SPD</span>
        </div>
        
        <div className="motor-controls">
            <button className="btn-motor btn-motor-nav" onClick={() => sendCmd('LEFT', 'Vzad')}>
                ⏪ Vzad
            </button>
            <button className="btn-motor btn-stop" onClick={() => sendCmd('STOP', 'Stop')}>
                ⏹ STOP
            </button>
            <button className="btn-motor btn-motor-nav" onClick={() => sendCmd('RIGHT', 'Vpred')}>
                Vpred ⏩
            </button>
        </div>
    </div>
  );
};

export default function CommandsView() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [devices, setDevices] = useState({ relays: [], motors: [] });
  
  const [commands, setCommands] = useState([]);
  const [editorContent, setEditorContent] = useState('');
  const [selectedCommand, setSelectedCommand] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
        const [cmds, devs] = await Promise.all([
            api.getCommands(),
            api.getDevices()
        ]);
        setCommands(cmds);
        if (devs && !devs.error) {
            setDevices(devs);
        }
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
        toast('Nový príkaz vytvorený.', { icon: '⚡' });
    }
  };

  return (
    <div className="tab-content active">
      {/* Header Panelu */}
      <div className="header-row" style={{
          marginBottom: '30px', 
          borderBottom: '1px solid #2d3340', 
          paddingBottom: '20px', 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center'
      }}>
        <h2 style={{color: 'white', margin: 0, display:'flex', alignItems:'center', gap:'10px'}}>
            ⚡ Ovládací Panel
        </h2>
        <div style={{display: 'flex', gap: '10px', background: '#111318', padding: '4px', borderRadius: '8px'}}>
            <button 
                className={`btn ${activeTab === 'dashboard' ? 'btn-primary' : 'btn-ghost'}`}
                style={{borderRadius: '6px'}}
                onClick={() => setActiveTab('dashboard')}
            >
                🎛 Panel
            </button>
            <button 
                className={`btn ${activeTab === 'files' ? 'btn-primary' : 'btn-ghost'}`}
                style={{borderRadius: '6px'}}
                onClick={() => setActiveTab('files')}
            >
                📁 Súbory
            </button>
        </div>
      </div>

      {activeTab === 'dashboard' ? (
          <div className="animate-fade-in">
              {/* Sekcia RELÉ */}
              <h3 className="section-title">
                  💡 Zariadenia & Efekty ({devices.relays?.length || 0})
              </h3>
              <div className="devices-grid relays">
                  {devices.relays?.map((dev, i) => <RelayCard key={i} device={dev} />)}
              </div>

              {/* Sekcia MOTORY */}
              {devices.motors?.length > 0 && (
                  <>
                    <h3 className="section-title" style={{marginTop: '20px'}}>
                        ⚙️ Motorické Pohony ({devices.motors.length})
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
                    <button className="btn btn-success btn-small" style={{width: '100%'}} onClick={handleNew}>+ Nový Príkaz</button>
                </div>
                {commands.map(cmd => (
                    <div className={`sidebar-item ${selectedCommand === cmd.name ? 'active-command' : ''}`}
                         key={cmd.name} onClick={() => handleLoadCommand(cmd.name)}>
                        <div style={{overflow: 'hidden', textOverflow: 'ellipsis'}}>{cmd.name}</div>
                        <div className="sidebar-actions">
                             <button className="btn btn-warning btn-list" title="Spustiť" onClick={(e) => {e.stopPropagation(); handleRunFile(cmd.name)}}>⚡</button>
                        </div>
                    </div>
                ))}
            </div>
            <div className="editor-container">
                {selectedCommand ? (
                    <>
                        <div className="editor-header-bar">
                            <h3>{selectedCommand}</h3>
                            <button className="btn btn-primary btn-small" onClick={handleSave}>💾 Uložiť</button>
                        </div>
                        <JsonEditor value={editorContent} onChange={setEditorContent} />
                    </>
                ) : (
                    <div className="empty-state-container">
                        <p>Vyberte príkaz na úpravu</p>
                    </div>
                )}
            </div>
          </div>
      )}
    </div>
  );
}