import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Download, Upload, Plus, Eye, Settings, Trash2 } from 'lucide-react';
import Header from './components/Header';
import StateEditor from './components/StateEditor';
import GlobalEventsEditor from './components/GlobalEventsEditor';
import GraphicPreview from './components/GraphicPreview';
import { createEmptyState, generateSceneNode } from './utils/generators';
import { generateStateMachineJSON, formatJSON, downloadJSON, importJSON } from './utils/jsonExport';
import { DEFAULTS } from './utils/constants';

// Key for local storage persistence, updated for museum system clarity
const STORAGE_KEY = 'museum_scene_editor_state'; 

function App() {
  const [sceneId, setSceneId] = useState(() => localStorage.getItem(`${STORAGE_KEY}_sceneId`) || DEFAULTS.SCENE_ID);
  const [description, setDescription] = useState(() => localStorage.getItem(`${STORAGE_KEY}_description`) || DEFAULTS.DESCRIPTION);
  const [version, setVersion] = useState(() => localStorage.getItem(`${STORAGE_KEY}_version`) || DEFAULTS.VERSION);
  const [initialState, setInitialState] = useState(() => localStorage.getItem(`${STORAGE_KEY}_initialState`) || '');
  const [globalPrefix, setGlobalPrefix] = useState(() => localStorage.getItem(`${STORAGE_KEY}_globalPrefix`) || DEFAULTS.GLOBAL_PREFIX);
  const [states, setStates] = useState(() => {
    try {
      const saved = localStorage.getItem(`${STORAGE_KEY}_states`);
      // Ensure at least one state exists upon load
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
  // State ID of the currently selected state in the editor or graphical view
  const [selectedStateId, setSelectedStateId] = useState(null); 
  
  // New state for scene library (needs fetching from backend, simulated only for now)
  const [availableScenes, setAvailableScenes] = useState(['room1/intro.json', 'room1/TwoPaths.json', 'room2/test.json']); 

  // Ref map for scrolling to selected state editors
  const stateEditorRefs = useRef({}); 
  const SCROLL_DURATION = 200; 

  /**
   * Resets the entire editor state to a blank new scene (simpler than resetStorage).
   * Automatically creates 'intro' state and sets it as initial.
   */
  const handleNewScene = () => {
    if (window.confirm('Are you sure you want to start a new scene? All unsaved work will be lost.')) {
      const initialDefaultState = createEmptyState('intro');
      setSceneId(DEFAULTS.SCENE_ID);
      setDescription(DEFAULTS.DESCRIPTION);
      setVersion(DEFAULTS.VERSION);
      setInitialState(initialDefaultState.name); 
      setGlobalPrefix(DEFAULTS.GLOBAL_PREFIX);
      setStates([initialDefaultState]);
      setGlobalEvents([]);
      setJsonPreview('');
      setShowPreview(false);
      setShowSettings(false);
      
      // Clear local storage for a cleaner start
      localStorage.removeItem(`${STORAGE_KEY}_sceneId`);
      localStorage.removeItem(`${STORAGE_KEY}_description`);
      localStorage.removeItem(`${STORAGE_KEY}_version`);
      localStorage.removeItem(`${STORAGE_KEY}_initialState`);
      localStorage.removeItem(`${STORAGE_KEY}_states`);
      localStorage.removeItem(`${STORAGE_KEY}_globalEvents`);
      
      alert('New scene created.');
    }
  };

  /**
   * Handles loading an existing scene from the RPI backend via API.
   * NOTE: This is a placeholder for the necessary API call.
   * @param {string} sceneName - The name/path of the scene to load.
   */
  const handleSceneLoad = async (sceneName) => {
    if (!sceneName) return;
    if (!window.confirm(`Load scene "${sceneName}"? All unsaved work will be lost.`)) return;
    
    alert(`Conceptual load of scene "${sceneName}" started. You need to implement the RPI API call and file fetching here.`);
    
    // Placeholder for actual API call and state update:
    /*
    try {
      const response = await fetch(`/api/scenes/load?name=${sceneName}`);
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const sceneJson = await response.json();
      
      // The importJSON function handles conversion to the internal state format
      const imported = importJSON(JSON.stringify(sceneJson)); 
      
      setSceneId(imported.sceneId);
      setDescription(imported.description);
      setVersion(imported.version);
      setInitialState(imported.initialState);
      setGlobalPrefix(imported.globalPrefix || DEFAULTS.GLOBAL_PREFIX);
      const importedStates = imported.states.length > 0 ? imported.states : [createEmptyState('intro')];
      setStates(importedStates);
      setGlobalEvents(imported.globalEvents || []);
      
      // Update local storage automatically via useEffect, no manual update needed here
      
      alert(`Scene "${sceneName}" loaded successfully!`);
      
    } catch (error) {
      console.error('Loading scene failed:', error);
      alert(`Error loading scene "${sceneName}". Please check the RPI API endpoint.`);
    }
    */
  };
  
  /**
   * Handler for adding a new state from the graphical preview context.
   * @param {object} param0 - Contains position data.
   */
  const handleAddStateFromPreview = useCallback(({ position }) => {
      const newState = createEmptyState(`state_${states.length + 1}`);
      setStates(prevStates => {
        // Set initial state name if this is the first state being created
        if (prevStates.length === 0) setInitialState(newState.name);
        return [...prevStates, newState];
      });
      setSelectedStateId(newState.id);
      setActiveTab('editor'); 
  }, [states]);

  /**
   * Handler for updating state metadata (name/position) from the React Flow graph.
   * This handles renaming and propagation immutably (BUG FIX applied).
   * @param {string} stateId - The ID of the state to update.
   * @param {object} updates - The new properties (e.g., name, position).
   */
  const handleUpdateStateFromNode = useCallback((stateId, updates) => {
    setStates(prevStates => {
      const stateToUpdate = prevStates.find(s => s.id === stateId);
      
      // Handle state renaming and propagation (BUG FIX)
      if (stateToUpdate && updates.name && updates.name !== stateToUpdate.name) {
          const oldName = stateToUpdate.name;
          const newName = updates.name;

          if (initialState === oldName) {
              setInitialState(newName);
          }
          
          return prevStates.map(s => {
              let updatedS = { ...s };
              
              if (s.id === stateId) {
                  // Update the renamed state itself
                  updatedS = { ...s, ...updates };
              }
              
              // Propagate the name change to all transitions in all states
              updatedS.transitions = updatedS.transitions.map(t => {
                  if (t.goto === oldName) {
                      return { ...t, goto: newName };
                  }
                  return t;
              });
              
              return updatedS;
          });
      }
      
      // Standard update (mostly position change in the graph)
      return prevStates.map(s => 
          s.id === stateId ? { ...s, ...updates } : s
      );
    });
  }, [initialState]);
  
  /**
   * Handler for deleting edges in the graphical preview.
   * @param {Array<object>} deletedEdges - List of edges deleted in the graph.
   */
  const handleEdgesDeleteInPreview = useCallback((deletedEdges) => {
      setStates(prevStates => {
          // Use map for immutable update
          return prevStates.map(state => {
              let transitionsToKeep = [...state.transitions];
              
              deletedEdges.forEach(edge => {
                  // Only process edges that originate from the current state
                  if (edge.source === state.id) {
                      const targetNode = prevStates.find(s => s.id === edge.target);
                      // Default to 'END' if target node is not found
                      const targetStateName = targetNode?.name || 'END'; 
                      
                      // Remove the first transition that matches the target name 
                      // (to correctly handle multiple identical transitions)
                      let transitionRemoved = false;
                      transitionsToKeep = transitionsToKeep.filter(t => {
                          if (!transitionRemoved && t.goto === targetStateName) {
                              transitionRemoved = true; 
                              return false; // Remove this transition
                          }
                          return true; // Keep others
                      });
                  }
              });
              
              // Return a new state object with the updated transitions
              return { ...state, transitions: transitionsToKeep };
          });
      });
  }, []);

  /**
   * Handler for a single click on a node in the preview.
   */
  const handleNodeClickInPreview = useCallback((event, node) => {
      setSelectedStateId(node.id);
  }, []);
  
  /**
   * Handler for a double click on a node in the preview (scrolls to editor).
   */
  const handleNodeDoubleClickInPreview = useCallback((event, node) => {
      setSelectedStateId(node.id);
      setActiveTab('editor'); 
      
      // Scrolling to the state editor component
      setTimeout(() => {
          const targetElement = stateEditorRefs.current[node.id];
          if (targetElement) {
              targetElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
      }, SCROLL_DURATION); 
  }, []);

  // Effect to persist state to local storage
  useEffect(() => {
    localStorage.setItem(`${STORAGE_KEY}_sceneId`, sceneId);
    localStorage.setItem(`${STORAGE_KEY}_description`, description);
    localStorage.setItem(`${STORAGE_KEY}_version`, version);
    localStorage.setItem(`${STORAGE_KEY}_initialState`, initialState);
    localStorage.setItem(`${STORAGE_KEY}_globalPrefix`, globalPrefix);
    localStorage.setItem(`${STORAGE_KEY}_states`, JSON.stringify(states));
    localStorage.setItem(`${STORAGE_KEY}_globalEvents`, JSON.stringify(globalEvents));
  }, [sceneId, description, version, initialState, globalPrefix, states, globalEvents]);

  /**
   * Update scene metadata (ID, description, version, initial state, prefix).
   */
  const updateMetadata = (updates) => {
    if ('sceneId' in updates) setSceneId(updates.sceneId);
    if ('description' in updates) setDescription(updates.description);
    if ('version' in updates) setVersion(updates.version);
    if ('initialState' in updates) setInitialState(updates.initialState);
    if ('globalPrefix' in updates) setGlobalPrefix(updates.globalPrefix);
  };

  /**
   * Add a new state to the list.
   */
  const addState = () => {
    const newState = createEmptyState(`state_${states.length + 1}`);
    setStates([...states, newState]);
    // Optionally set the new state as initial state if none is set
    if (!initialState) {
        setInitialState(newState.name);
    }
  };

  /**
   * Update a specific state (including handling name changes and propagation) - BUG FIX APPLIED.
   * @param {number} index - Index of the state in the array.
   * @param {object} updates - The updated properties for the state.
   */
  const updateState = (index, updates) => {
    let newStates = [...states];
    const stateToUpdateId = newStates[index].id;
    
    // Check for state name change
    if (updates.name && newStates[index].name !== updates.name) {
        const oldName = newStates[index].name;
        const newName = updates.name;
        
        // Update initial state name if necessary
        if (initialState === oldName) {
            setInitialState(newName);
        }

        // Propagate the name change to all transitions in all states (Immutable map)
        newStates = newStates.map(s => {
            let updatedS = { ...s };
            
            // For other states, update the 'goto' property of their transitions
            updatedS.transitions = s.transitions.map(t => {
                if (t.goto === oldName) {
                    return { ...t, goto: newName };
                }
                return t;
            });

            // If this is the state being updated, merge the new properties
            if (s.id === stateToUpdateId) {
                updatedS = { ...updatedS, ...updates };
            }
            
            return updatedS;
        });
        
        setStates(newStates);
        return;
    }
    
    // Standard update (no name change)
    newStates[index] = updates;
    setStates(newStates);
  };
  
  /**
   * Delete a state and clean up all transitions referencing it.
   * @param {number} index - Index of the state to delete.
   */
  const deleteState = (index) => {
    if (states.length <= 1) {
      alert('Cannot delete the last state!');
      return;
    }
    const stateToDeleteName = states[index].name;
    let newStates = states.filter((_, i) => i !== index);
    
    // Remove transitions pointing to the deleted state (immutable update)
    newStates = newStates.map(state => ({
        ...state,
        transitions: state.transitions.filter(t => t.goto !== stateToDeleteName)
    }));

    setStates(newStates);
    
    // Set new initial state if the deleted state was the initial one
    if (initialState === stateToDeleteName) {
        setInitialState(newStates.length > 0 ? newStates[0].name : '');
    }
  };

  /**
   * Generate JSON output and display preview.
   */
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

  /**
   * Download the generated JSON file.
   */
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

  /**
   * Import scene data from a JSON file.
   * @param {object} event - File input change event.
   */
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
        // Ensure states array is not empty
        const importedStates = imported.states.length > 0 ? imported.states : [createEmptyState('intro')];
        setStates(importedStates);
        setGlobalEvents(imported.globalEvents || []);
        
        // Update local storage explicitly
        localStorage.setItem(`${STORAGE_KEY}_sceneId`, imported.sceneId);
        localStorage.setItem(`${STORAGE_KEY}_description`, imported.description);
        localStorage.setItem(`${STORAGE_KEY}_version`, imported.version);
        localStorage.setItem(`${STORAGE_KEY}_initialState`, imported.initialState);
        localStorage.setItem(`${STORAGE_KEY}_globalPrefix`, imported.globalPrefix || DEFAULTS.GLOBAL_PREFIX);
        localStorage.setItem(`${STORAGE_KEY}_states`, JSON.stringify(importedStates));
        localStorage.setItem(`${STORAGE_KEY}_globalEvents`, JSON.stringify(imported.globalEvents || []));
        
        alert('JSON imported successfully!');
      } catch (error) {
        alert('Error importing JSON: ' + error.message);
      }
    };
    reader.readAsText(file);
    event.target.value = '';
  };

  /**
   * Reset all data stored in local storage and the application state.
   */
  const resetStorage = () => {
    if (window.confirm('Are you sure you want to reset all data? This will clear all your current work.')) {
      // Clear all related keys from local storage
      localStorage.removeItem(`${STORAGE_KEY}_sceneId`);
      localStorage.removeItem(`${STORAGE_KEY}_description`);
      localStorage.removeItem(`${STORAGE_KEY}_version`);
      localStorage.removeItem(`${STORAGE_KEY}_initialState`);
      localStorage.removeItem(`${STORAGE_KEY}_globalPrefix`);
      localStorage.removeItem(`${STORAGE_KEY}_states`);
      localStorage.removeItem(`${STORAGE_KEY}_globalEvents`);
      
      // Reset state to defaults
      const initialDefaultState = createEmptyState('intro');
      setSceneId(DEFAULTS.SCENE_ID);
      setDescription(DEFAULTS.DESCRIPTION);
      setVersion(DEFAULTS.VERSION);
      // Set initial state to 'intro' after creating the state object
      setInitialState(initialDefaultState.name); 
      setGlobalPrefix(DEFAULTS.GLOBAL_PREFIX);
      setStates([initialDefaultState]);
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
          // --- New Props for Intuitive Scene Selection ---
          availableScenes={availableScenes}
          onSceneLoad={handleSceneLoad}
          onNewScene={handleNewScene}
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
            title="Add new state to the current scene"
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
            <Upload size={18} /> Import JSON (File)
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
            <Trash2 size={18} /> Reset Data (Local Storage)
          </button>
        </div>

        {activeTab === 'editor' ? (
          <>
            {showSettings && (
              <div className="bg-gray-800 rounded-lg p-6 mb-6 border-2 border-indigo-600">
                <h2 className="text-xl font-bold mb-4 text-indigo-400">⚙️ Global Settings</h2>
                <div className="mb-4">
                  <label className="block text-sm mb-2 text-gray-300">
                    🌐 Global MQTT Prefix (Used in all MQTT topics)
                  </label>
                  <input
                    type="text"
                    value={globalPrefix}
                    onChange={(e) => setGlobalPrefix(e.target.value)}
                    className="w-full max-w-md px-3 py-2 bg-gray-700 rounded focus:ring-2 focus:ring-indigo-500"
                    placeholder="room1"
                  />
                  <div className="text-xs text-gray-400 mt-1">
                    💡 Example: "room1" → all topics will be "room1/motor1", "room1/light", etc.
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
                    // Correctly connecting the ref to the DIV element
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
                <li><strong>Global Prefix:</strong> Set once in Settings and used in all MQTT topics.</li>
                <li><strong>States:</strong> Building blocks of your scene (intro, middle, finale, etc.).</li>
                <li><strong>onEnter:</strong> Actions executed when entering a state.</li>
                <li><strong>Timeline:</strong> Timed actions during a state (e.g., "at 3.0 seconds, do X").</li>
                <li><strong>onExit:</strong> Actions executed when leaving a state.</li>
                <li><strong>Transitions:</strong> timeout, buttonPress, mqttMessage, audioEnd, videoEnd.</li>
                <li><strong>Global Events:</strong> Emergency stops and other global triggers.</li>
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