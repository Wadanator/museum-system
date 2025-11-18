import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Download, Upload, Plus, Eye, Settings, Trash2 } from 'lucide-react';
import Header from './components/Header';
import StateEditor from './components/StateEditor';
import GlobalEventsEditor from './components/GlobalEventsEditor';
import GraphicPreview from './components/GraphicPreview';
import { createEmptyState, generateSceneNode } from './utils/generators';
import { generateStateMachineJSON, formatJSON, downloadJSON, importJSON } from './utils/jsonExport';
import { DEFAULTS } from './utils/constants';

const STORAGE_KEY = 'railway_scene_editor_state';

function App() {
  const [sceneId, setSceneId] = useState(() => localStorage.getItem(`${STORAGE_KEY}_sceneId`) || DEFAULTS.SCENE_ID);
  const [description, setDescription] = useState(() => localStorage.getItem(`${STORAGE_KEY}_description`) || DEFAULTS.DESCRIPTION);
  const [version, setVersion] = useState(() => localStorage.getItem(`${STORAGE_KEY}_version`) || DEFAULTS.VERSION);
  const [initialState, setInitialState] = useState(() => localStorage.getItem(`${STORAGE_KEY}_initialState`) || '');
  const [globalPrefix, setGlobalPrefix] = useState(() => localStorage.getItem(`${STORAGE_KEY}_globalPrefix`) || DEFAULTS.GLOBAL_PREFIX);
  const [states, setStates] = useState(() => {
    try {
      const saved = localStorage.getItem(`${STORAGE_KEY}_states`);
      return saved ? JSON.parse(saved) : [createEmptyState('intro')];
    } catch (error) {
      console.error('Error parsing states from localStorage:', error);
      return [createEmptyState('intro')];
    }
  });
  const [globalEvents, setGlobalEvents] = useState(() => {
    try {
      const saved = localStorage.getItem(`${STORAGE_KEY}_globalEvents`);
      return saved ? JSON.parse(saved) : [];
    } catch (error) {
      console.error('Error parsing globalEvents from localStorage:', error);
      return [];
    }
  });
  const [jsonPreview, setJsonPreview] = useState('');
  const [showPreview, setShowPreview] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [activeTab, setActiveTab] = useState('editor');
  const [selectedStateId, setSelectedStateId] = useState(null); 
  
  const stateEditorRefs = useRef({}); 
  const SCROLL_DURATION = 200; 

  const handleAddStateFromPreview = useCallback(({ position }) => {
      const newState = createEmptyState(`state_${states.length + 1}`);
      setStates(prevStates => [...prevStates, newState]);
      if (states.length === 0) setInitialState(newState.name);
      setSelectedStateId(newState.id);
      setActiveTab('editor'); 
  }, [states]);

  const handleUpdateStateFromNode = useCallback((stateId, updates) => {
    setStates(prevStates => 
      prevStates.map(state => {
        if (state.id === stateId) {
          if (updates.name && updates.name !== state.name) {
            const oldName = state.name;
            const newName = updates.name;

            state = { ...state, name: newName };

            if (initialState === oldName) {
              setInitialState(newName);
            }
            
            prevStates = prevStates.map(s => {
                if (s.id !== stateId) {
                    const newTransitions = s.transitions.map(t => {
                        if (t.goto === oldName) {
                            return { ...t, goto: newName };
                        }
                        return t;
                    });
                    return { ...s, transitions: newTransitions };
                }
                return s;
            });
            return { ...state, ...updates };
          }
          
          return { ...state, ...updates };
        }
        
        return state;
      })
    );
  }, [initialState]);
  
  const handleEdgesDeleteInPreview = useCallback((deletedEdges) => {
      setStates(prevStates => {
          let updatedStates = [...prevStates];
          
          deletedEdges.forEach(edge => {
              const sourceStateId = edge.source;
              const stateIndex = updatedStates.findIndex(s => s.id === sourceStateId);
              
              if (stateIndex !== -1) {
                  const stateToUpdate = updatedStates[stateIndex];
                  
                  const targetNode = updatedStates.find(s => s.id === edge.target);
                  const targetStateName = targetNode?.name || 'END'; 
                  
                  let transitionRemoved = false;
                  const newTransitions = stateToUpdate.transitions.filter(t => {
                      if (!transitionRemoved && t.goto === targetStateName) {
                          transitionRemoved = true; 
                          return false;
                      }
                      return true;
                  });
                  
                  updatedStates[stateIndex] = { ...stateToUpdate, transitions: newTransitions };
              }
          });
          return updatedStates;
      });
  }, []);

  const handleNodeClickInPreview = useCallback((event, node) => {
      setSelectedStateId(node.id);
  }, []);
  
  const handleNodeDoubleClickInPreview = useCallback((event, node) => {
      setSelectedStateId(node.id);
      setActiveTab('editor'); 
      
      // Scrollovanie k stavu
      setTimeout(() => {
          const targetElement = stateEditorRefs.current[node.id];
          if (targetElement) {
              targetElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
      }, SCROLL_DURATION); 
  }, []);

  useEffect(() => {
    localStorage.setItem(`${STORAGE_KEY}_sceneId`, sceneId);
    localStorage.setItem(`${STORAGE_KEY}_description`, description);
    localStorage.setItem(`${STORAGE_KEY}_version`, version);
    localStorage.setItem(`${STORAGE_KEY}_initialState`, initialState);
    localStorage.setItem(`${STORAGE_KEY}_globalPrefix`, globalPrefix);
    localStorage.setItem(`${STORAGE_KEY}_states`, JSON.stringify(states));
    localStorage.setItem(`${STORAGE_KEY}_globalEvents`, JSON.stringify(globalEvents));
  }, [sceneId, description, version, initialState, globalPrefix, states, globalEvents]);

  const updateMetadata = (updates) => {
    if ('sceneId' in updates) setSceneId(updates.sceneId);
    if ('description' in updates) setDescription(updates.description);
    if ('version' in updates) setVersion(updates.version);
    if ('initialState' in updates) setInitialState(updates.initialState);
    if ('globalPrefix' in updates) setGlobalPrefix(updates.globalPrefix);
  };

  const addState = () => {
    const newState = createEmptyState(`state_${states.length + 1}`);
    setStates([...states, newState]);
  };

  const updateState = (index, updates) => {
    const newStates = [...states];
    
    if (updates.name && newStates[index].name !== updates.name) {
        const oldName = newStates[index].name;
        const newName = updates.name;
        
        if (initialState === oldName) {
            setInitialState(newName);
        }

        newStates.forEach(s => {
            s.transitions.forEach(t => {
                if (t.goto === oldName) {
                    t.goto = newName;
                }
            });
        });
    }

    newStates[index] = updates;
    setStates(newStates);
  };
  
  const deleteState = (index) => {
    if (states.length <= 1) {
      alert('Cannot delete the last state!');
      return;
    }
    const stateToDeleteName = states[index].name;
    let newStates = states.filter((_, i) => i !== index);
    
    newStates = newStates.map(state => ({
        ...state,
        transitions: state.transitions.filter(t => t.goto !== stateToDeleteName)
    }));

    setStates(newStates);
    
    if (initialState === stateToDeleteName) {
        setInitialState(newStates.length > 0 ? newStates[0].name : '');
    }
  };

  const handleGenerateJSON = () => {
    const json = generateStateMachineJSON(
      sceneId,
      description,
      version,
      initialState,
      states,
      globalEvents
    );
    const formatted = formatJSON(json);
    setJsonPreview(formatted);
    setShowPreview(true);
  };

  const handleDownloadJSON = () => {
    const json = generateStateMachineJSON(
      sceneId,
      description,
      version,
      initialState,
      states,
      globalEvents
    );
    downloadJSON(json, sceneId);
  };

  const handleImportJSON = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const imported = importJSON(e.target.result);
        setSceneId(imported.sceneId);
        setDescription(imported.description);
        setVersion(imported.version);
        setInitialState(imported.initialState);
        setGlobalPrefix(imported.globalPrefix || DEFAULTS.GLOBAL_PREFIX);
        setStates(imported.states.length > 0 ? imported.states : [createEmptyState()]);
        setGlobalEvents(imported.globalEvents || []);
        localStorage.setItem(`${STORAGE_KEY}_sceneId`, imported.sceneId);
        localStorage.setItem(`${STORAGE_KEY}_description`, imported.description);
        localStorage.setItem(`${STORAGE_KEY}_version`, imported.version);
        localStorage.setItem(`${STORAGE_KEY}_initialState`, imported.initialState);
        localStorage.setItem(`${STORAGE_KEY}_globalPrefix`, imported.globalPrefix || DEFAULTS.GLOBAL_PREFIX);
        localStorage.setItem(`${STORAGE_KEY}_states`, JSON.stringify(imported.states.length > 0 ? imported.states : [createEmptyState()]));
        localStorage.setItem(`${STORAGE_KEY}_globalEvents`, JSON.stringify(imported.globalEvents || []));
        alert('JSON imported successfully!');
      } catch (error) {
        alert('Error importing JSON: ' + error.message);
      }
    };
    reader.readAsText(file);
    event.target.value = '';
  };

  const resetStorage = () => {
    if (window.confirm('Are you sure you want to reset all data? This will clear all your current work.')) {
      localStorage.removeItem(`${STORAGE_KEY}_sceneId`);
      localStorage.removeItem(`${STORAGE_KEY}_description`);
      localStorage.removeItem(`${STORAGE_KEY}_version`);
      localStorage.removeItem(`${STORAGE_KEY}_initialState`);
      localStorage.removeItem(`${STORAGE_KEY}_globalPrefix`);
      localStorage.removeItem(`${STORAGE_KEY}_states`);
      localStorage.removeItem(`${STORAGE_KEY}_globalEvents`);
      setSceneId(DEFAULTS.SCENE_ID);
      setDescription(DEFAULTS.DESCRIPTION);
      setVersion(DEFAULTS.VERSION);
      setInitialState('');
      setGlobalPrefix(DEFAULTS.GLOBAL_PREFIX);
      setStates([createEmptyState('intro')]);
      setGlobalEvents([]);
      setJsonPreview('');
      setShowPreview(false);
      alert('Data reset successfully!');
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <div className="max-w-7xl mx-auto">
        <Header
          sceneId={sceneId}
          description={description}
          version={version}
          initialState={initialState}
          globalPrefix={globalPrefix}
          states={states}
          onChange={updateMetadata}
        />

        <div className="flex gap-2 mb-4 border-b border-gray-700">
          <button
            onClick={() => setActiveTab('editor')}
            className={`px-4 py-2 font-semibold transition ${
              activeTab === 'editor'
                ? 'bg-gray-700 text-white border-b-2 border-blue-500'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            ✏️ Editor
          </button>
          <button
            onClick={() => setActiveTab('graphic')}
            className={`px-4 py-2 font-semibold transition ${
              activeTab === 'graphic'
                ? 'bg-gray-700 text-white border-b-2 border-blue-500'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            🗺️ Graphic Preview
          </button>
        </div>

        <div className="flex flex-wrap gap-3 mb-6">
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded flex items-center gap-2 transition"
            title="Show settings"
          >
            <Settings size={18} /> Settings
          </button>
          <button
            onClick={addState}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded flex items-center gap-2 transition"
            title="Add new state"
          >
            <Plus size={18} /> Add State
          </button>
          <button
            onClick={handleGenerateJSON}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded flex items-center gap-2 transition"
            title="Preview JSON output"
          >
            <Eye size={18} /> Preview JSON
          </button>
          <button
            onClick={handleDownloadJSON}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded flex items-center gap-2 transition"
            title="Download JSON file"
          >
            <Download size={18} /> Export JSON
          </button>
          <label
            className="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 rounded flex items-center gap-2 cursor-pointer transition"
            title="Import JSON file"
          >
            <Upload size={18} /> Import JSON
            <input
              type="file"
              accept=".json"
              onChange={handleImportJSON}
              className="hidden"
            />
          </label>
          <button
            onClick={resetStorage}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded flex items-center gap-2 transition"
            title="Reset all data"
          >
            <Trash2 size={18} /> Reset Data
          </button>
        </div>

        {activeTab === 'editor' ? (
          <>
            {showSettings && (
              <div className="bg-gray-800 rounded-lg p-6 mb-6 border-2 border-indigo-600">
                <h2 className="text-xl font-bold mb-4 text-indigo-400">⚙️ Global Settings</h2>
                <div className="mb-4">
                  <label className="block text-sm mb-2 text-gray-300">
                    🌐 Global MQTT Prefix (používa sa vo všetkých MQTT topicoch)
                  </label>
                  <input
                    type="text"
                    value={globalPrefix}
                    onChange={(e) => setGlobalPrefix(e.target.value)}
                    className="w-full max-w-md px-3 py-2 bg-gray-700 rounded focus:ring-2 focus:ring-indigo-500"
                    placeholder="room1"
                  />
                  <div className="text-xs text-gray-400 mt-1">
                    💡 Príklad: "room1" → všetky topics budú "room1/motor1", "room1/light", atď.
                  </div>
                </div>
                <GlobalEventsEditor
                  globalEvents={globalEvents}
                  onChange={setGlobalEvents}
                  states={states}
                  globalPrefix={globalPrefix}
                />
              </div>
            )}

            <div className="mb-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-2xl font-bold">States ({states.length})</h2>
                <span className="text-sm text-gray-400">
                  Initial: {initialState || '(not set)'}
                </span>
              </div>
              {states.map((state, index) => (
                <div 
                    key={state.id}
                    // Správne pripojenie referencie k DIV elementu
                    ref={el => stateEditorRefs.current[state.id] = el}
                >
                    <StateEditor
                      state={state}
                      onChange={(updated) => updateState(index, updated)}
                      onDelete={() => deleteState(index)}
                      states={states}
                      globalPrefix={globalPrefix}
                      isSelected={selectedStateId === state.id} 
                    />
                </div>
              ))}
            </div>

            {showPreview && (
              <div className="bg-gray-800 rounded-lg p-6 mb-6">
                <div className="flex justify-between items-center mb-3">
                  <h2 className="text-xl font-bold">JSON Preview</h2>
                  <button
                    onClick={() => setShowPreview(false)}
                    className="px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded text-sm transition"
                  >
                    Hide
                  </button>
                </div>
                <pre className="bg-gray-900 p-4 rounded overflow-auto max-h-96 text-sm border border-gray-700">
                  {jsonPreview}
                </pre>
              </div>
            )}

            <div className="bg-gray-800 rounded-lg p-4 text-sm text-gray-400">
              <h3 className="font-bold mb-2">Quick Guide:</h3>
              <ul className="space-y-1 list-disc list-inside">
                <li><strong>Global Prefix:</strong> Nastaví sa raz v Settings a používa sa vo všetkých MQTT topicoch</li>
                <li><strong>States:</strong> Building blocks of your scene (intro, middle, finale, etc.)</li>
                <li><strong>onEnter:</strong> Actions executed when entering a state</li>
                <li><strong>Timeline:</strong> Timed actions during a state (e.g., "at 3.0 seconds, do X")</li>
                <li><strong>onExit:</strong> Actions executed when leaving a state</li>
                <li><strong>Transitions:</strong> timeout, mqttMessage, buttonPress, audioEnd, videoEnd</li>
                <li><strong>Global Events:</strong> Emergency stops a iné globálne udalosti</li>
              </ul>
            </div>
          </>
        ) : (
          <GraphicPreview
            states={states}
            initialState={initialState}
            globalEvents={globalEvents}
            onAddState={handleAddStateFromPreview}
            onUpdateState={handleUpdateStateFromNode}
            onEdgesDelete={handleEdgesDeleteInPreview} 
            onNodeClick={handleNodeClickInPreview} 
            onNodeDoubleClick={handleNodeDoubleClickInPreview}
          />
        )}
      </div>
    </div>
  );
}

export default App;