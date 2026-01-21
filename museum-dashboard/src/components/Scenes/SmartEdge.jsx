import React from 'react';
import { BaseEdge, EdgeLabelRenderer, getBezierPath } from 'reactflow';

// Pomocná funkcia na výpočet bodu na Bézierovej krivke
// t = 0 (začiatok), t = 1 (koniec), t = 0.5 (stred)
function getCubicBezierPoint(t, sx, sy, c1x, c1y, c2x, c2y, tx, ty) {
  const k = 1 - t;
  const x =
    k * k * k * sx +
    3 * k * k * t * c1x +
    3 * k * t * t * c2x +
    t * t * t * tx;
  const y =
    k * k * k * sy +
    3 * k * k * t * c1y +
    3 * k * t * t * c2y +
    t * t * t * ty;
  return [x, y];
}

export default function SmartEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  markerEnd,
  label,
  labelStyle,
  labelBgStyle,
}) {
  // 1. Získame parametre cesty, ktoré React Flow generuje
  const [edgePath, labelCenterX, labelCenterY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  // 2. Vypočítame vlastnú pozíciu pre Label
  // Defaultne používa React Flow "curvature" cca 0.25 dĺžky. 
  // Pre vertikálny layout (Top-Bottom) sú kontrolné body takto:
  const distY = Math.abs(targetY - sourceY);
  const curvature = Math.min(distY * 0.5, 100); // Obmedzenie zakrivenia
  
  const c1x = sourceX;
  const c1y = sourceY + curvature;
  const c2x = targetX;
  const c2y = targetY - curvature;

  // KĽÚČOVÉ: Posunieme label na 25% cesty (bližšie k zdroju, kde sú čiary oddelené)
  // Experimentujte s hodnotou 0.2 (bližšie) až 0.4 (ďalej)
  const [customLabelX, customLabelY] = getCubicBezierPoint(
    0.25, 
    sourceX, sourceY, 
    c1x, c1y, 
    c2x, c2y, 
    targetX, targetY
  );

  return (
    <>
      <BaseEdge path={edgePath} markerEnd={markerEnd} style={style} />
      
      {label && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${customLabelX}px,${customLabelY}px)`,
              pointerEvents: 'all',
              zIndex: 10, // Zabezpečí, že text bude nad čiarami
            }}
          >
            <div 
                style={{
                    backgroundColor: labelBgStyle?.fill || '#ffffff',
                    padding: '4px 8px',
                    borderRadius: '6px',
                    border: `1px solid ${labelBgStyle?.stroke || '#ccc'}`,
                    fontSize: '11px',
                    fontWeight: 600,
                    color: labelStyle?.fill || '#000',
                    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                    whiteSpace: 'nowrap',
                    ...labelStyle
                }}
            >
                {label}
            </div>
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}