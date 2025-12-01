import React from 'react';
import { Download, Upload, Plus, Eye, Trash2 } from 'lucide-react';

const EditorToolbar = ({ 
    onAddState, 
    onGenerateJSON, 
    onDownloadJSON, 
    onImportJSON, 
    onReset 
}) => {
  return (
    <div className="flex flex-wrap gap-2 items-center">
        {/* Hlavná Akcia */}
        <button 
            onClick={onAddState} 
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg flex items-center gap-2 transition shadow-lg shadow-blue-900/30 font-medium"
        >
            <Plus size={18} /> Pridať Stav
        </button>

        <div className="w-px h-8 bg-gray-700 mx-2"></div>

        {/* JSON Nástroje */}
        <button 
            onClick={onGenerateJSON} 
            className="p-2 text-gray-300 hover:text-white hover:bg-gray-800 rounded-lg transition" 
            title="Náhľad JSON"
        >
            <Eye size={20} />
        </button>
        
        <button 
            onClick={onDownloadJSON} 
            className="p-2 text-purple-400 hover:text-purple-300 hover:bg-gray-800 rounded-lg transition" 
            title="Stiahnuť JSON"
        >
            <Download size={20} />
        </button>
        
        <label 
            className="p-2 text-yellow-500 hover:text-yellow-400 hover:bg-gray-800 rounded-lg transition cursor-pointer" 
            title="Importovať JSON"
        >
            <Upload size={20} />
            <input type="file" accept=".json" onChange={onImportJSON} className="hidden" />
        </label>

        <div className="w-px h-8 bg-gray-700 mx-2"></div>

        {/* Deštruktívne akcie */}
        <button 
            onClick={onReset} 
            className="p-2 text-red-500 hover:text-red-400 hover:bg-red-900/20 rounded-lg transition" 
            title="Resetovať Editor"
        >
            <Trash2 size={20} />
        </button>
    </div>
  );
};

export default EditorToolbar;