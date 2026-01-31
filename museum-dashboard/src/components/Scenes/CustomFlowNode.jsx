import React, { memo, useState } from 'react';
import { Handle, Position } from 'reactflow';
import { FiChevronDown, FiChevronUp, FiZap, FiClock, FiShare2, FiActivity, FiFlag, FiPlay, FiCode } from 'react-icons/fi';

const CustomFlowNode = ({ data, selected }) => {
    const [isExpanded, setIsExpanded] = useState(false);
    const isStart = data.type === 'start';
    const isEnd = data.type === 'end';
    const { onEnter, timeline, transitions } = data.sections || { onEnter: [], timeline: [], transitions: [] };
    
    const totalActions = onEnter.length + timeline.length;

    return (
        <div className={`custom-flow-node ${isStart ? 'start-node' : ''} ${isEnd ? 'end-node' : ''} ${selected ? 'selected' : ''}`}>
            {!isStart && <Handle type="target" position={Position.Top} className="node-handle target" />}

            <div className="node-header" onClick={() => !isEnd && setIsExpanded(!isExpanded)}>
                <div className="node-title-group">
                    <div className={`node-icon-box ${isStart ? 'start' : isEnd ? 'end' : 'state'}`}>
                        {isStart ? <FiPlay /> : isEnd ? <FiFlag /> : <FiActivity />}
                    </div>
                    <div className="node-title-content">
                        <div className="node-label">{data.label}</div>
                        {!isEnd && !isExpanded && (
                            <div className="node-meta">
                                {totalActions > 0 && <span className="meta-badge">{totalActions} actions</span>}
                                {transitions.length > 0 && <span className="meta-badge">{transitions.length} transitions</span>}
                            </div>
                        )}
                    </div>
                </div>
                {!isEnd && (
                    <button className="expand-btn" aria-label={isExpanded ? 'Collapse' : 'Expand'}>
                        {isExpanded ? <FiChevronUp /> : <FiChevronDown />}
                    </button>
                )}
            </div>

            {/* Náhľad, keď je uzol zavretý */}
            {!isExpanded && !isEnd && data.description && (
                <div className="node-preview">
                    <div className="preview-text">{data.description}</div>
                </div>
            )}

            {/* Obsah, keď je uzol otvorený */}
            {isExpanded && (
                <div className="node-content">
                    {data.description && (
                        <div className="node-description">
                            <FiCode className="desc-icon" />
                            <span>{data.description}</span>
                        </div>
                    )}

                    {/* PRIEČINOK: ON ENTER */}
                    {onEnter.length > 0 && (
                        <div className="node-section section-onenter">
                            <div className="section-header">
                                <FiZap className="section-icon" />
                                <span className="section-title">On Enter</span>
                                <span className="section-count">{onEnter.length}</span>
                            </div>
                            <div className="section-body">
                                {onEnter.map((text, i) => (
                                    <div key={i} className="action-item">
                                        <div className="action-index">{i + 1}</div>
                                        <code className="action-code">{text}</code>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* PRIEČINOK: TIMELINE */}
                    {timeline.length > 0 && (
                        <div className="node-section section-timeline">
                            <div className="section-header">
                                <FiClock className="section-icon" />
                                <span className="section-title">Timeline</span>
                                <span className="section-count">{timeline.length}</span>
                            </div>
                            <div className="section-body">
                                {timeline.map((item, i) => (
                                    <div key={i} className="action-item timeline-item">
                                        <div className="timeline-marker">
                                            <div className="timeline-dot"></div>
                                            <span className="timeline-time">+{item.time}s</span>
                                        </div>
                                        <code className="action-code">{item.text}</code>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* PRIEČINOK: TRANSITIONS */}
                    {transitions.length > 0 && (
                        <div className="node-section section-transitions">
                            <div className="section-header">
                                <FiShare2 className="section-icon" />
                                <span className="section-title">Transitions</span>
                                <span className="section-count">{transitions.length}</span>
                            </div>
                            <div className="section-body">
                                {transitions.map((text, i) => (
                                    <div key={i} className="action-item transition-item">
                                        <div className="transition-index">{i + 1}</div>
                                        <div className="transition-content">{text}</div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {!isEnd && data.transitionCount > 0 && (
                <div className="node-handles-container">
                    {Array.from({ length: data.transitionCount }).map((_, i) => (
                        <Handle 
                            key={i} 
                            type="source" 
                            position={Position.Bottom} 
                            id={`handle-${i}`} 
                            className="dynamic-source"
                            aria-label={`Transition ${i + 1}`}
                        />
                    ))}
                </div>
            )}
        </div>
    );
};

export default memo(CustomFlowNode);