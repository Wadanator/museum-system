import { useState, useEffect, useCallback } from 'react';
import { createEmptyState } from '../utils/generators';
import { generateStateMachineJSON, formatJSON, downloadJSON, importJSON } from '../utils/jsonExport';
import { DEFAULTS } from '../utils/constants';

const STORAGE_KEY = 'museum_scene_editor_state';

export const useSceneManager = () => {
  // --- STATE ---
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
      console.error('Error parsing states:', error);
      return [createEmptyState('intro')];
    }
  });

  const [globalEvents, setGlobalEvents] = useState(() => {
    try {
      const saved = localStorage.getItem(`${STORAGE_KEY}_globalEvents`);
      return saved ? JSON.parse(saved) : [];
    } catch (error) {
      return [];
    }
  });

  const [jsonPreview, setJsonPreview] = useState('');
  const [showPreview, setShowPreview] = useState(false);

  // --- PERSISTENCE ---
  useEffect(() => {
    localStorage.setItem(`${STORAGE_KEY}_sceneId`, sceneId);
    localStorage.setItem(`${STORAGE_KEY}_description`, description);
    localStorage.setItem(`${STORAGE_KEY}_version`, version);
    localStorage.setItem(`${STORAGE_KEY}_initialState`, initialState);
    localStorage.setItem(`${STORAGE_KEY}_globalPrefix`, globalPrefix);
    localStorage.setItem(`${STORAGE_KEY}_states`, JSON.stringify(states));
    localStorage.setItem(`${STORAGE_KEY}_globalEvents`, JSON.stringify(globalEvents));
  }, [sceneId, description, version, initialState, globalPrefix, states, globalEvents]);

  // --- ACTIONS ---

  const updateMetadata = (updates) => {
    if ('sceneId' in updates) setSceneId(updates.sceneId);
    if ('description' in updates) setDescription(updates.description);
    if ('version' in updates) setVersion(updates.version);
    if ('initialState' in updates) setInitialState(updates.initialState);
    if ('globalPrefix' in updates) setGlobalPrefix(updates.globalPrefix);
  };

  const addState = useCallback(() => {
    const newState = createEmptyState(`state_${states.length + 1}`);
    setStates(prev => {
        const newStates = [...prev, newState];
        if (!initialState) setInitialState(newState.name);
        return newStates;
    });
    return newState.id;
  }, [states, initialState]);

  const updateState = useCallback((index, updates) => {
    setStates(prevStates => {
        let newStates = [...prevStates];
        const stateToUpdateId = newStates[index].id;
        
        if (updates.name && newStates[index].name !== updates.name) {
            const oldName = newStates[index].name;
            const newName = updates.name;
            
            if (initialState === oldName) setInitialState(newName);

            return newStates.map(s => {
                let updatedS = { ...s };
                updatedS.transitions = s.transitions.map(t => {
                    if (t.goto === oldName) return { ...t, goto: newName };
                    return t;
                });
                if (s.id === stateToUpdateId) updatedS = { ...updatedS, ...updates };
                return updatedS;
            });
        }
        
        newStates[index] = updates;
        return newStates;
    });
  }, [initialState]);

  const handleUpdateStateFromNode = useCallback((stateId, updates) => {
    const index = states.findIndex(s => s.id === stateId);
    if (index !== -1) {
        updateState(index, updates);
    }
  }, [states, updateState]);

  const deleteState = (index) => {
    if (states.length <= 1) {
      alert('Nemôžete vymazať posledný stav!');
      return;
    }
    const stateToDeleteName = states[index].name;
    
    setStates(prevStates => {
        let newStates = prevStates.filter((_, i) => i !== index);
        
        newStates = newStates.map(state => ({
            ...state,
            transitions: state.transitions.filter(t => t.goto !== stateToDeleteName)
        }));
        
        if (initialState === stateToDeleteName) {
            setInitialState(newStates.length > 0 ? newStates[0].name : '');
        }
        return newStates;
    });
  };

  const handleEdgesDeleteInPreview = useCallback((deletedEdges) => {
    setStates(prevStates => {
        return prevStates.map(state => {
            let transitionsToKeep = [...state.transitions];
            deletedEdges.forEach(edge => {
                if (edge.source === state.id) {
                    const targetNode = prevStates.find(s => s.id === edge.target);
                    const targetStateName = targetNode?.name || 'END'; 
                    let transitionRemoved = false;
                    transitionsToKeep = transitionsToKeep.filter(t => {
                        if (!transitionRemoved && t.goto === targetStateName) {
                            transitionRemoved = true; 
                            return false; 
                        }
                        return true; 
                    });
                }
            });
            return { ...state, transitions: transitionsToKeep };
        });
    });
  }, []);

  const handleGenerateJSON = () => {
    const json = generateStateMachineJSON(sceneId, description, version, initialState, states, globalEvents);
    setJsonPreview(formatJSON(json));
    setShowPreview(true);
  };

  const handleDownloadJSON = () => {
    const json = generateStateMachineJSON(sceneId, description, version, initialState, states, globalEvents);
    downloadJSON(json, sceneId);
  };

  const handleImportJSON = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const imported = importJSON(e.target.result);
        updateMetadata(imported);
        
        const importedStates = imported.states.length > 0 ? imported.states : [createEmptyState('intro')];
        setStates(importedStates);
        setGlobalEvents(imported.globalEvents || []);
        
        alert('JSON importovaný úspešne!');
      } catch (error) {
        alert('Chyba pri importe: ' + error.message);
      }
    };
    reader.readAsText(file);
    event.target.value = '';
  };

  const handleNewScene = () => {
    if (window.confirm('Naozaj chcete začať novú scénu? Neuložené zmeny budú stratené.')) {
      localStorage.clear();
      
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
    }
  };

  const handleAddStateFromPreview = useCallback(() => {
      return addState();
  }, [addState]);

  return {
    metadata: { sceneId, description, version, initialState, globalPrefix },
    states,
    globalEvents,
    ui: { jsonPreview, showPreview, setShowPreview },
    actions: {
        updateMetadata,
        addState,
        updateState,
        deleteState,
        setGlobalEvents,
        handleUpdateStateFromNode,
        handleEdgesDeleteInPreview,
        handleGenerateJSON,
        handleDownloadJSON,
        handleImportJSON,
        handleNewScene,
        handleAddStateFromPreview
    }
  };
};