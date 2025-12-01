import React, { useState, useCallback, useRef } from 'react';
import { Plus } from 'lucide-react'; 
import Header from './components/Header';
import StateEditor from './components/StateEditor';
import GlobalEventsEditor from './components/GlobalEventsEditor';
import GraphicPreview from './components/GraphicPreview';
import EditorToolbar from './components/EditorToolbar';
import SettingsPanel from './components/SettingsPanel';
import SceneSidebar from './components/SceneSidebar';
import { useSceneManager } from './hooks/useSceneManager';

function App() {
  const { metadata, states, globalEvents, ui, actions } = useSceneManager();
  
  const [activeTab, setActiveTab] = useState('editor');
  const [selectedStateId, setSelectedStateId] = useState(null); 
  const [availableScenes] = useState(['room1/intro.json', 'room1/TwoPaths.json', 'room2/test.json']); 

  const stateEditorRefs = useRef({}); 
  const topRef = useRef(null);

  // --- NAVIGÁCIA ---

  const handleSelectState = (id) => {
      setSelectedStateId(id);
      
      if (id === null) {
          if (topRef.current) {
              topRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
      } else {
          setTimeout(() => {
              const el = stateEditorRefs.current[id];
              if (el) {
                  el.scrollIntoView({ behavior: 'smooth', block: 'start' });
              }
          }, 100); 
      }
  };

  // --- NOVÉ: Handler pre prepínanie (Accordion logic) ---
  const handleToggleState = (id) => {
      if (selectedStateId === id) {
          // Ak kliknem na ten istý, zatvorím ho (a idem hore na settings)
          handleSelectState(null);
      } else {
          // Ak kliknem na iný, otvorím ho (a ostatné sa zatvoria, lebo selectedStateId je len jedno)
          handleSelectState(id);
      }
  };

  const handleSceneLoad = (sceneName) => {
    alert(`Načítanie scény "${sceneName}" nie je implementované.`);
  };

  const handleAddStateAndScroll = () => {
      const newId = actions.addState();
      setTimeout(() => handleSelectState(newId), 100);
  };
  
  const handleAddStateFromPreview = useCallback(({ position }) => {
      const newId = actions.handleAddStateFromPreview(); 
      setActiveTab('editor'); 
      setTimeout(() => handleSelectState(newId), 100);
  }, [actions]);

  const handleUpdateStateFromNode = actions.handleUpdateStateFromNode;
  const handleEdgesDeleteInPreview = actions.handleEdgesDeleteInPreview;
  const handleNodeClickInPreview = useCallback((event, node) => setSelectedStateId(node.id), []);
  const handleNodeDoubleClickInPreview = useCallback((event, node) => {
      setActiveTab('editor'); 
      handleSelectState(node.id);
  }, []);

  return (
    <div className="min-h-screen bg-gray-900 text-white p-4 lg:p-8 pb-20 font-sans">
      <div className="max-w-[1600px] mx-auto">
        
        {/* 1. HLAVIČKA */}
        <Header
            onSceneLoad={handleSceneLoad}
            onNewScene={actions.handleNewScene}
            availableScenes={availableScenes}
        />

        {/* 2. TOOLBAR & TABS */}
        <div className="sticky top-0 z-50 bg-gray-900/95 backdrop-blur-md border-b border-gray-700 py-3 mb-8 transition-all shadow-lg -mx-4 px-4 lg:-mx-8 lg:px-8">
            <div className="flex flex-col sm:flex-row justify-between items-center max-w-[1600px] mx-auto gap-4">
                
                <div className="bg-gray-800 p-1 rounded-lg flex gap-1 shadow-inner">
                    <button 
                        onClick={() => setActiveTab('editor')} 
                        className={`px-4 py-1.5 text-sm font-medium rounded-md transition ${activeTab === 'editor' ? 'bg-gray-700 text-white shadow' : 'text-gray-400 hover:text-white'}`}
                    >
                        Editor
                    </button>
                    <button 
                        onClick={() => setActiveTab('graphic')} 
                        className={`px-4 py-1.5 text-sm font-medium rounded-md transition ${activeTab === 'graphic' ? 'bg-gray-700 text-white shadow' : 'text-gray-400 hover:text-white'}`}
                    >
                        Grafika
                    </button>
                </div>
                
                <EditorToolbar 
                    onAddState={handleAddStateAndScroll}
                    onGenerateJSON={actions.handleGenerateJSON}
                    onDownloadJSON={actions.handleDownloadJSON}
                    onImportJSON={actions.handleImportJSON}
                    onReset={actions.handleNewScene}
                />
            </div>
        </div>

        {/* --- HLAVNÝ OBSAH --- */}
        {activeTab === 'editor' ? (
          <div className="flex gap-8 items-start relative">
            
            {/* SIDEBAR */}
            <div className="hidden lg:block sticky top-28 w-72 flex-shrink-0">
                <SceneSidebar 
                    states={states} 
                    selectedStateId={selectedStateId} 
                    onSelectState={handleSelectState}
                    globalEventsCount={globalEvents.length}
                />
            </div>

            {/* MAIN EDITOR AREA */}
            <div className="flex-1 min-w-0 space-y-8">
                
                {/* SECTION: Global Configuration */}
                <div ref={topRef} style={{ scrollMarginTop: '100px' }} className="space-y-6 animate-fadeIn">
                    <SettingsPanel 
                        {...metadata}
                        states={states}
                        onChange={actions.updateMetadata}
                    />
                    
                    <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
                        <div className="bg-gray-900/30 px-6 py-4 border-b border-gray-700">
                            <h2 className="text-lg font-bold text-yellow-400 flex items-center gap-2">
                                🚨 Globálne Udalosti
                            </h2>
                            <p className="text-xs text-gray-400 mt-1">
                                Pravidlá, ktoré platia neustále (Emergency Stop, Timeouty).
                            </p>
                        </div>
                        <div className="p-6">
                            <GlobalEventsEditor
                                globalEvents={globalEvents}
                                onChange={actions.setGlobalEvents}
                                states={states}
                                globalPrefix={metadata.globalPrefix}
                            />
                        </div>
                    </div>
                    
                    <div className="flex items-center gap-4 text-gray-600">
                        <div className="h-px bg-gray-700 flex-1"></div>
                        <span className="text-xs font-bold uppercase tracking-widest">Stavy Scény</span>
                        <div className="h-px bg-gray-700 flex-1"></div>
                    </div>
                </div>

                {/* SECTION: States List */}
                <div className="space-y-6">
                    {states.map((state, index) => (
                        <div 
                            key={state.id} 
                            ref={el => stateEditorRefs.current[state.id] = el}
                            style={{ scrollMarginTop: '90px' }} 
                        >
                            <StateEditor
                                state={state}
                                onChange={(updated) => actions.updateState(index, updated)}
                                onDelete={() => actions.deleteState(index)}
                                states={states}
                                globalPrefix={metadata.globalPrefix}
                                isSelected={selectedStateId === state.id}
                                // Tu posielame funkciu pre prepínanie
                                onToggle={handleToggleState} 
                            />
                        </div>
                    ))}
                </div>
                
                {/* Big Add Button at Bottom */}
                <button 
                    onClick={handleAddStateAndScroll}
                    className="w-full py-8 border-2 border-dashed border-gray-700 rounded-xl text-gray-500 hover:text-white hover:border-blue-500 hover:bg-gray-800/50 transition flex flex-col items-center justify-center gap-2 group"
                >
                    <div className="p-3 bg-gray-800 rounded-full group-hover:bg-blue-600 transition shadow-lg">
                        <Plus size={24} />
                    </div>
                    <span className="font-medium">Pridať ďalší stav</span>
                </button>

            </div>
          </div>
        ) : (
          <div className="bg-gray-800 rounded-xl border border-gray-700 h-[800px] shadow-2xl overflow-hidden">
            <GraphicPreview
                states={states}
                initialState={metadata.initialState}
                globalEvents={globalEvents}
                onAddState={handleAddStateFromPreview}
                onUpdateState={handleUpdateStateFromNode}
                onEdgesDelete={handleEdgesDeleteInPreview} 
                onNodeClick={handleNodeClickInPreview} 
                onNodeDoubleClick={handleNodeDoubleClickInPreview}
            />
          </div>
        )}

        {/* JSON Modal */}
        {ui.showPreview && (
            <div className="fixed inset-0 bg-black/90 flex items-center justify-center z-[100] p-4 lg:p-10 backdrop-blur-sm animate-fadeIn">
                <div className="bg-gray-800 rounded-xl w-full max-w-5xl h-[85vh] flex flex-col shadow-2xl border border-gray-700 overflow-hidden">
                    <div className="flex justify-between items-center px-6 py-4 border-b border-gray-700 bg-gray-900">
                        <h2 className="text-lg font-bold text-white flex items-center gap-2">📄 JSON Výstup</h2>
                        <button onClick={() => ui.setShowPreview(false)} className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm transition">Zavrieť</button>
                    </div>
                    <div className="flex-1 bg-[#1e1e1e] p-6 overflow-auto custom-scrollbar">
                        <pre className="text-sm font-mono text-green-400 whitespace-pre-wrap">
                            {ui.jsonPreview}
                        </pre>
                    </div>
                </div>
            </div>
        )}
      </div>
    </div>
  );
}

export default App;