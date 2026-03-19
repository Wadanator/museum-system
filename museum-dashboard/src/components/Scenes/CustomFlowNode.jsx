import React, { memo, useState, useCallback } from 'react';
import { Handle, Position } from 'reactflow';
import { FiChevronDown, FiChevronUp, FiZap, FiClock, FiShare2, FiActivity, FiFlag, FiPlay, FiCode, FiLogOut } from 'react-icons/fi';

// ─── ReactFlow magic class names ─────────────────────────────────────────────
// nowheel  → wheel events on this element do NOT zoom/pan the canvas
// nodrag   → this element cannot initiate a node drag
// nopan    → this element cannot initiate canvas panning
//
// Rule of thumb:
//   • Any scrollable content area  → nowheel
//   • Any clickable button/control → nodrag nopan
//   • Both                         → nowheel nodrag nopan
// ─────────────────────────────────────────────────────────────────────────────

const CustomFlowNode = ({ data, selected }) => {
    const [isExpanded, setIsExpanded] = useState(false);
    const isStart = data.type === 'start';
    const isEnd = data.type === 'end';

    const { onEnter, onExit, timeline, transitions } = data.sections || {
        onEnter: [], onExit: [], timeline: [], transitions: []
    };

    const totalActions = data.totalActions ?? (onEnter.length + (onExit?.length || 0) + timeline.length);

    // stopPropagation prevents ReactFlow from starting a node-drag
    // when the user clicks the expand/collapse button
    const handleExpandClick = useCallback((e) => {
        e.stopPropagation();
        if (!isEnd) setIsExpanded(prev => !prev);
    }, [isEnd]);

    return (
        <div className={`custom-flow-node ${isStart ? 'start-node' : ''} ${isEnd ? 'end-node' : ''} ${selected ? 'selected' : ''}`}>
            {!isStart && <Handle type="target" position={Position.Top} className="node-handle target" />}

            {/* ── Header — draggable area ──────────────────────────── */}
            <div className="node-header" onClick={handleExpandClick}>
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
                    // nodrag nopan → click on chevron never starts a drag
                    <button
                        className="expand-btn nodrag nopan"
                        onClick={handleExpandClick}
                        aria-label={isExpanded ? 'Collapse' : 'Expand'}
                    >
                        {isExpanded ? <FiChevronUp /> : <FiChevronDown />}
                    </button>
                )}
            </div>

            {/* ── Collapsed preview ────────────────────────────────── */}
            {!isExpanded && !isEnd && data.description && (
                // nowheel → scrolling over description text won't zoom canvas
                <div className="node-preview nowheel">
                    <div className="preview-text">{data.description}</div>
                </div>
            )}

            {/* ── Expanded content ─────────────────────────────────── */}
            {isExpanded && (
                // nowheel nodrag → user can scroll content without zooming canvas
                //                  and can't accidentally start a drag from content
                <div className="node-content nowheel nodrag">
                    {data.description && (
                        <div className="node-description">
                            <FiCode className="desc-icon" />
                            <span>{data.description}</span>
                        </div>
                    )}

                    {/* ON ENTER */}
                    {onEnter.length > 0 && (
                        <div className="node-section section-onenter">
                            <div className="section-header">
                                <FiZap className="section-icon" />
                                <span className="section-title">On Enter</span>
                                <span className="section-count">{onEnter.length}</span>
                            </div>
                            {/* nowheel on section-body so scrolling the list
                                doesn't propagate to the ReactFlow zoom handler */}
                            <div className="section-body nowheel">
                                {onEnter.map((text, i) => (
                                    <div key={i} className="action-item">
                                        <div className="action-index">{i + 1}</div>
                                        <code className="action-code">{text}</code>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* TIMELINE */}
                    {timeline.length > 0 && (
                        <div className="node-section section-timeline">
                            <div className="section-header">
                                <FiClock className="section-icon" />
                                <span className="section-title">Timeline</span>
                                <span className="section-count">{timeline.length}</span>
                            </div>
                            <div className="section-body nowheel">
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

                    {/* ON EXIT */}
                    {onExit.length > 0 && (
                        <div className="node-section section-onexit">
                            <div className="section-header">
                                <FiLogOut className="section-icon" />
                                <span className="section-title">On Exit</span>
                                <span className="section-count">{onExit.length}</span>
                            </div>
                            <div className="section-body nowheel">
                                {onExit.map((text, i) => (
                                    <div key={i} className="action-item onexit-item">
                                        <div className="action-index">{i + 1}</div>
                                        <code className="action-code">{text}</code>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* TRANSITIONS */}
                    {transitions.length > 0 && (
                        <div className="node-section section-transitions">
                            <div className="section-header">
                                <FiShare2 className="section-icon" />
                                <span className="section-title">Transitions</span>
                                <span className="section-count">{transitions.length}</span>
                            </div>
                            <div className="section-body nowheel">
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