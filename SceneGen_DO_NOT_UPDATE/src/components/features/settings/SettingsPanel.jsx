import React from 'react';
import { Tag, Hash, GitBranch, MapPin, AlignLeft, Globe } from 'lucide-react';

const SettingsPanel = ({ 
    sceneId, description, version, initialState, globalPrefix, 
    states, onChange 
}) => {
  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden shadow-sm">
        {/* Header panela */}
        <div className="bg-gray-900/50 px-6 py-4 border-b border-gray-700 flex items-center gap-2">
            <div className="p-1.5 bg-indigo-500/10 rounded">
                <Globe size={18} className="text-indigo-400"/>
            </div>
            <h2 className="text-lg font-bold text-white">Nastavenia Scény</h2>
        </div>

        <div className="p-6 grid grid-cols-1 gap-6">
            
            {/* 1. Riadok: Scene ID & Version */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="md:col-span-2">
                    <label className="flex items-center gap-2 text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">
                        <Tag size={14} /> ID Scény (Názov súboru)
                    </label>
                    <input
                        type="text"
                        value={sceneId}
                        onChange={(e) => onChange({ sceneId: e.target.value })}
                        className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2.5 text-white font-mono focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none transition"
                        placeholder="napr. room1_intro"
                    />
                </div>
                <div>
                    <label className="flex items-center gap-2 text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">
                        <GitBranch size={14} /> Verzia
                    </label>
                    <input
                        type="text"
                        value={version}
                        onChange={(e) => onChange({ version: e.target.value })}
                        className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2.5 text-white font-mono text-center focus:border-indigo-500 outline-none transition"
                        placeholder="1.0"
                    />
                </div>
            </div>

            {/* 2. Riadok: Initial State & Global Prefix */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                    <label className="flex items-center gap-2 text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">
                        <MapPin size={14} /> Počiatočný Stav (Start)
                    </label>
                    <select
                        value={initialState}
                        onChange={(e) => onChange({ initialState: e.target.value })}
                        className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2.5 text-white focus:border-indigo-500 outline-none transition appearance-none cursor-pointer"
                    >
                        {states.map(s => <option key={s.id} value={s.name}>{s.name}</option>)}
                    </select>
                </div>
                <div>
                    <label className="flex items-center gap-2 text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">
                        <Hash size={14} /> MQTT Prefix (Miestnosť)
                    </label>
                    <div className="relative">
                        <input
                            type="text"
                            value={globalPrefix}
                            onChange={(e) => onChange({ globalPrefix: e.target.value })}
                            className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2.5 text-white font-mono focus:border-indigo-500 outline-none transition"
                            placeholder="room1"
                        />
                        <div className="absolute right-3 top-3 text-xs text-gray-500 pointer-events-none">/topic...</div>
                    </div>
                </div>
            </div>

            {/* 3. Riadok: Description */}
            <div>
                <label className="flex items-center gap-2 text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">
                    <AlignLeft size={14} /> Popis Scény
                </label>
                <textarea
                    value={description}
                    onChange={(e) => onChange({ description: e.target.value })}
                    rows={2}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 focus:border-indigo-500 outline-none transition resize-none"
                    placeholder="Stručný popis toho, čo táto scéna robí..."
                />
            </div>
        </div>
    </div>
  );
};

export default SettingsPanel;