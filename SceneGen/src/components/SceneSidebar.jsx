import React from 'react';
import { Flag, Zap, Clock, ArrowRight } from 'lucide-react';

const SceneSidebar = ({ states, selectedStateId, onSelectState, globalEventsCount }) => {
  const scrollToTop = () => {
    onSelectState(null);
  };

  return (
    <div className="bg-gray-800 border border-gray-700 flex flex-col max-h-[calc(100vh-120px)] rounded-lg overflow-hidden shadow-xl sticky top-24">
      <div className="p-3 bg-gray-900 border-b border-gray-700 font-bold text-gray-400 uppercase text-xs tracking-wider flex justify-between items-center">
        <span>Navigácia</span>
        <span className="bg-gray-800 px-2 py-0.5 rounded text-[10px] text-gray-500">{states.length} stavov</span>
      </div>
      
      <div className="overflow-y-auto flex-1 p-2 space-y-1 custom-scrollbar">
        <button
          onClick={scrollToTop}
          className={`w-full text-left px-3 py-2.5 rounded flex items-center gap-2 transition text-sm mb-2 ${
            selectedStateId === null 
              ? 'bg-indigo-600 text-white shadow-md ring-1 ring-indigo-400' 
              : 'text-gray-300 hover:bg-gray-700 border border-transparent hover:border-gray-600'
          }`}
        >
          <Zap size={16} className={selectedStateId === null ? "text-yellow-300" : "text-gray-500"} />
          <span className="flex-1 font-semibold">Global & Nastavenia</span>
          {globalEventsCount > 0 && (
            <span className="bg-yellow-600 text-white text-[10px] px-1.5 py-0.5 rounded-full font-bold">
              {globalEventsCount}
            </span>
          )}
        </button>

        {states.map((state, index) => (
          <button
            key={state.id}
            onClick={() => onSelectState(state.id)}
            className={`w-full text-left px-3 py-2 rounded flex items-center gap-3 transition text-sm group border ${
              selectedStateId === state.id 
                ? 'bg-blue-600 text-white shadow-md border-blue-500 ring-1 ring-blue-400' 
                : 'text-gray-400 hover:bg-gray-750 hover:text-white border-transparent hover:border-gray-600'
            }`}
          >
            <div className={`min-w-[6px] h-6 rounded-full flex-shrink-0 ${
                index === 0 ? 'bg-green-500' : (selectedStateId === state.id ? 'bg-white' : 'bg-gray-600 group-hover:bg-gray-500')
            }`}></div>
            
            <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                    <span className="truncate font-mono font-medium">{state.name}</span>
                    {index === 0 && <Flag size={10} className="text-green-400 ml-1 flex-shrink-0" />}
                </div>
                
                <div className={`flex gap-2 text-[10px] mt-0.5 ${selectedStateId === state.id ? 'text-blue-200' : 'text-gray-600'}`}>
                    {(state.timeline?.length > 0) && <span className="flex items-center gap-0.5"><Clock size={8}/> TL</span>}
                    {(state.transitions?.length > 0) && <span className="flex items-center gap-0.5"><ArrowRight size={8}/> TR</span>}
                </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
};

export default SceneSidebar;