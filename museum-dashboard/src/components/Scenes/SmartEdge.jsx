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
  const [edgePath] = getBezierPath({
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
            className="smart-edge-label-wrapper"
            style={{
              transform: `translate(-50%, -50%) translate(${customLabelX}px,${customLabelY}px)`,
            }}
          >
            <div 
                className="smart-edge-label"
                style={{
                backgroundColor: labelBgStyle?.fill || 'var(--bg-card)',
                    borderColor: labelBgStyle?.stroke || 'var(--border-color)',
                color: labelStyle?.fill || 'var(--text-primary)',
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