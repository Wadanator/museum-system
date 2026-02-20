import React from 'react';
import { Trash2, Clock, LogIn, LogOut, ArrowRight, Hash } from 'lucide-react';
import ActionListEditor from './ActionListEditor';
import TransitionEditor from './TransitionEditor';
import TimelineEditor from './TimelineEditor';

const StateEditor = ({ state, onChange, onDelete, states, globalPrefix, isSelected, onFocus }) => {
  
  // ZMENA: Žiadny accordion, obsah je vždy viditeľný.
  // isSelected slúži už len na vizuálne zvýraznenie (modrý rámik).

  return (
    <div 
        // Kliknutie kdekoľvek v editore ho označí ako aktívny (pre Sidebar)
        onClick={() => onFocus(state.id)}
        className={`rounded-lg mb-4 transition-all duration-300 border ${
            isSelected 
                ? 'bg-gray-800 border-blue-500 shadow-lg shadow-blue-900/20 ring-1 ring-blue-500/50' 
                : 'bg-gray-800 border-gray-700 hover:border-gray-600'
        }`}
    >
      {/* HEADER */}
      <div className="flex items-center justify-between p-4 cursor-pointer select-none border-b border-gray-700/50 bg-gray-900/20">
        <div className="flex items-center gap-3">
            {/* Odstránené šípky (Chevron) */}
            
            <div className="flex flex-col">
                <span className={`font-mono text-lg font-bold ${isSelected ? 'text-blue-400' : 'text-gray-200'}`}>
                    {state.name}
                </span>
                <span className="text-xs text-gray-500 truncate max-w-md">
                    {state.description || "Bez popisu..."}
                </span>
            </div>
        </div>

        <div className="flex items-center gap-3">
            {/* Odstránené sumárne info (LogIn, Clock...) keďže sú viditeľné dole */}
            
            <button
                onClick={(e) => { e.stopPropagation(); onDelete(); }}
                className="p-2 text-gray-500 hover:text-red-400 hover:bg-red-900/30 rounded transition"
                title="Vymazať stav"
            >
                <Trash2 size={18} />
            </button>
        </div>
      </div>

      {/* BODY - VŽDY VIDITEĽNÉ */}
      <div className="p-4 space-y-6 bg-gray-800/50">
            {/* Metadata */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-gray-900/50 p-4 rounded-lg border border-gray-700">
                <div>
                    <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">Názov stavu (ID)</label>
                    <div className="flex items-center gap-2">
                        <Hash size={16} className="text-gray-500"/>
                        <input
                            type="text"
                            value={state.name}
                            onChange={(e) => onChange({ ...state, name: e.target.value })}
                            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white font-mono focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition"
                        />
                    </div>
                </div>
                <div>
                    <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">Popis</label>
                    <input
                        type="text"
                        value={state.description || ''}
                        onChange={(e) => onChange({ ...state, description: e.target.value })}
                        className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white placeholder-gray-500 focus:border-blue-500 outline-none transition"
                        placeholder="Čo sa deje v tomto stave?"
                    />
                </div>
            </div>

            {/* 1. ON ENTER */}
            <div className="border-l-2 border-green-500 pl-4 ml-1">
                <h4 className="text-sm font-bold text-green-400 flex items-center gap-2 mb-3 uppercase tracking-wider">
                    <LogIn size={16} /> Pri Vstupe (onEnter)
                </h4>
                <ActionListEditor 
                    actions={state.onEnter || []}
                    onChange={(newActions) => onChange({ ...state, onEnter: newActions })}
                    globalPrefix={globalPrefix}
                />
            </div>

            {/* 2. TIMELINE */}
            <div className="border-l-2 border-blue-500 pl-4 ml-1">
                <h4 className="text-sm font-bold text-blue-400 flex items-center gap-2 mb-3 uppercase tracking-wider">
                    <Clock size={16} /> Časová os (Timeline)
                </h4>
                <TimelineEditor
                    timeline={state.timeline || []}
                    onChange={(newTimeline) => onChange({ ...state, timeline: newTimeline })}
                    globalPrefix={globalPrefix}
                />
            </div>

            {/* 3. ON EXIT */}
            <div className="border-l-2 border-red-500 pl-4 ml-1">
                <h4 className="text-sm font-bold text-red-400 flex items-center gap-2 mb-3 uppercase tracking-wider">
                    <LogOut size={16} /> Pri Odchode (onExit)
                </h4>
                <ActionListEditor
                    actions={state.onExit || []}
                    onChange={(newActions) => onChange({ ...state, onExit: newActions })}
                    globalPrefix={globalPrefix}
                />
            </div>

            {/* 4. TRANSITIONS */}
            <div className="bg-gray-900/30 p-4 rounded-lg border border-gray-700">
                <h4 className="text-sm font-bold text-yellow-400 flex items-center gap-2 mb-3 uppercase tracking-wider">
                    <ArrowRight size={16} /> Prechody (Transitions)
                </h4>
                <TransitionEditor
                    transitions={state.transitions || []}
                    onChange={(newTransitions) => onChange({ ...state, transitions: newTransitions })}
                    states={states}
                    globalPrefix={globalPrefix}
                />
            </div>
      </div>
    </div>
  );
};

export default StateEditor;