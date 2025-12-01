import React from 'react';
import { FilePlus, FolderOpen, Save } from 'lucide-react';

const Header = ({ onNewScene, onSceneLoad, availableScenes }) => {
  return (
    <header className="bg-gray-900 border-b border-gray-800 py-4 mb-6">
      <div className="flex flex-col md:flex-row justify-between items-center gap-4">
        
        {/* LOGO & TITLE */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center shadow-lg shadow-blue-900/20">
            <span className="text-xl">🏛️</span>
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">Museum Scene Editor</h1>
            <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Wadanator Systems</p>
          </div>
        </div>

        {/* APP ACTIONS */}
        <div className="flex items-center gap-3 bg-gray-800/50 p-1.5 rounded-lg border border-gray-700/50">
          <select 
            className="bg-gray-900 border-none text-sm text-gray-300 rounded px-3 py-1.5 focus:ring-1 focus:ring-blue-500 outline-none"
            onChange={(e) => onSceneLoad(e.target.value)}
            defaultValue=""
          >
            <option value="" disabled>📂 Načítať scénu...</option>
            {availableScenes.map(s => <option key={s} value={s}>{s}</option>)}
          </select>

          <div className="w-px h-6 bg-gray-700 mx-1"></div>

          <button 
            onClick={onNewScene}
            className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-gray-300 hover:text-white hover:bg-gray-700 rounded transition"
          >
            <FilePlus size={16} className="text-green-400"/>
            Nová
          </button>
        </div>
      </div>
    </header>
  );
};

export default Header;