import { useState } from 'react';
import { Handle, Position } from 'reactflow';
import { 
    Play, Clock, Terminal, Zap, ChevronDown, ChevronUp, 
    Music, Clapperboard, Flag 
} from 'lucide-react';

const getIcon = (type) => {
    switch (type) {
        case 'start': return <Play size={16} fill="currentColor" />;
        case 'end': return <Flag size={16} fill="currentColor" />;
        default: return <Zap size={16} />;
    }
};

const getActionIcon = (actionType) => {
    switch (actionType) {
        case 'audio': return <Music size={12} />;
        case 'video': return <Clapperboard size={12} />;
        case 'mqtt': return <Zap size={12} />;
        default: return <Terminal size={12} />;
    }
};

export default function CustomFlowNode({ data }) {
    const [expanded, setExpanded] = useState(false);
    
    // Špeciálny štýl pre END node
    const isEnd = data.type === 'end';
    const isStart = data.type === 'start';

    return (
        <div className={`custom-flow-node ${isEnd ? 'end-node' : ''} ${isStart ? 'start-node' : ''} ${expanded ? 'expanded' : ''}`}>
            {/* Vstupný bod (hore) - END node nemá výstup, START nemá vstup (ale pre istotu nechávame) */}
            <Handle type="target" position={Position.Top} className="node-handle target" />
            
            {/* Hlavička */}
            <div 
                className="node-header" 
                onClick={() => !isEnd && setExpanded(!expanded)}
                style={{ cursor: isEnd ? 'default' : 'pointer' }}
            >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span className={`node-icon ${data.type}`}>
                        {getIcon(data.type)}
                    </span>
                    <span>{data.label}</span>
                </div>
                
                {/* Šípka na rozbalenie (len ak to nie je END) */}
                {!isEnd && (
                    <button className="expand-btn">
                        {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                    </button>
                )}
            </div>
            
            {/* Telo (zobrazí sa len ak je expanded alebo ak je tam description) */}
            <div className="node-content">
                {/* Popis zobrazíme vždy ak je krátky, alebo v detaile */}
                {data.description && (
                    <div className="node-description">
                        {data.description}
                    </div>
                )}

                {/* Detailné akcie - len keď je rozbalené */}
                {expanded && data.actions && data.actions.length > 0 && (
                    <div className="node-actions-list">
                        <div className="list-label">Akcie:</div>
                        {data.actions.map((act, i) => (
                            <div key={i} className="action-item">
                                {getActionIcon(act.type)}
                                <span title={act.val}>{act.val}</span>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Výstupný bod (dole) - END node už nikam nevedie */}
            {!isEnd && (
                <Handle type="source" position={Position.Bottom} className="node-handle source" />
            )}
        </div>
    );
}