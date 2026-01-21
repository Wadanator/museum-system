import { useState } from 'react';
import { Handle, Position } from 'reactflow';
import { 
    Play, Zap, ChevronDown, ChevronUp, 
    Music, Clapperboard, Flag, Clock,
    MessageSquare, Monitor, PauseCircle, FileText
} from 'lucide-react';

export default function CustomFlowNode({ data }) {
    const [expanded, setExpanded] = useState(false);
    
    const isEnd = data.type === 'end';
    const isStart = data.type === 'start';
    
    // Zistíme počet výstupov (ak nie sú definované, tak 0)
    // Ak je to END node, nemá výstupy. Ak je to START/STEP a nemá transitions, dáme aspoň 1 (pre manuálne spájanie)
    const handleCount = data.transitionCount > 0 ? data.transitionCount : (isEnd ? 0 : 1);
    // Vytvoríme pole indexov [0, 1, 2...] pre mapovanie
    const handleIndices = Array.from({ length: handleCount }, (_, i) => i);

    const getNodeIcon = () => {
        if (isStart) return <Play size={18} fill="currentColor" />;
        if (isEnd) return <Flag size={18} fill="currentColor" />;
        return <Zap size={18} />;
    };

    const getActionIcon = (type) => {
        switch (type) {
            case 'audio': return <Music size={14} />;
            case 'video': return <Clapperboard size={14} />;
            case 'mqtt': return <MessageSquare size={14} />;
            case 'delay': case 'clock': return <Clock size={14} />;
            default: return <Monitor size={14} />;
        }
    };

    const timelineActions = data.actions?.filter(a => a.type === 'clock') || [];
    const immediateActions = data.actions?.filter(a => a.type !== 'clock') || [];

    return (
        <div className={`custom-flow-node ${isEnd ? 'end-node' : ''} ${isStart ? 'start-node' : ''} ${expanded ? 'expanded' : ''}`}>
            
            {/* VSTUP (Target) - Ostáva jeden hore v strede */}
            <Handle type="target" position={Position.Top} className="node-handle target" />
            
            <div className="node-header" onClick={() => !isEnd && setExpanded(!expanded)}>
                <div className="node-title-group">
                    <div className="node-icon-box">
                        {getNodeIcon()}
                    </div>
                    <span className="node-label">{data.label}</span>
                </div>
                
                {!isEnd && (
                    <button className="expand-btn">
                        {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </button>
                )}
            </div>

            {/* DESCRIPTION ONLY (Collapsed) */}
            {!expanded && !isEnd && (
                <div className="node-preview-bar description-only">
                    <div className="preview-desc-row">
                        <FileText size={14} style={{ opacity: 0.5, flexShrink: 0 }} />
                        <span className="desc-text" title={data.description}>
                            {data.description || <span style={{ opacity: 0.5 }}>Bez popisu</span>}
                        </span>
                    </div>
                </div>
            )}

            {/* EXPANDED CONTENT */}
            {expanded && (
                <div className="node-content">
                    {data.description && (
                        <div className="node-description">{data.description}</div>
                    )}

                    {immediateActions.length > 0 && (
                        <div className="node-section">
                            <div className="section-label">On Enter</div>
                            {immediateActions.map((act, i) => (
                                <div key={i} className="action-row">
                                    <span className="action-icon">{getActionIcon(act.type)}</span>
                                    <span className="action-text">{act.val}</span>
                                </div>
                            ))}
                        </div>
                    )}

                    {timelineActions.length > 0 && (
                        <div className="node-section">
                            <div className="section-label" style={{ color: 'var(--warning)' }}>Timeline</div>
                            {timelineActions.map((act, i) => (
                                <div key={i} className="action-row timeline">
                                    <span className="action-icon"><Clock size={14} /></span>
                                    <span className="action-text">{act.val}</span>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* --- VÝSTUPY (Sources) - Generujeme ich dynamicky vedľa seba --- */}
            {!isEnd && (
                <div className="node-handles-container">
                    {handleIndices.map((idx) => (
                        <Handle 
                            key={`handle-${idx}`}
                            type="source" 
                            position={Position.Bottom} 
                            id={`handle-${idx}`} // Dôležité: Unikátne ID pre prepojenie
                            className="dynamic-source" 
                        />
                    ))}
                </div>
            )}
        </div>
    );
}