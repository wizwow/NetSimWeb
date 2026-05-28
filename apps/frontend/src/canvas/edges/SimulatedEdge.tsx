import { BaseEdge, EdgeLabelRenderer, getStraightPath } from '@xyflow/react';
import type { EdgeProps } from '@xyflow/react';
import type { ReactFlowEdge } from '../graphHelpers';

export const SimulatedEdge: React.FC<EdgeProps<ReactFlowEdge>> = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  data,
  style,
  markerEnd,
}) => {
  const [edgePath] = getStraightPath({ sourceX, sourceY, targetX, targetY });
  const faultActive = Boolean(data?.faultState?.active);

  const midX = (sourceX + targetX) / 2;
  const midY = (sourceY + targetY) / 2;
  const srcLabelX = sourceX + (targetX - sourceX) * 0.25;
  const srcLabelY = sourceY + (targetY - sourceY) * 0.25;
  const tgtLabelX = sourceX + (targetX - sourceX) * 0.75;
  const tgtLabelY = sourceY + (targetY - sourceY) * 0.75;

  const subnet = data?.ipConfig?.subnet;
  const srcLabel = data?.ipConfig?.sourceIp ? `${data?.sourcePort || ''} - ${data.ipConfig.sourceIp}` : '';
  const tgtLabel = data?.ipConfig?.targetIp ? `${data?.targetPort || ''} - ${data.ipConfig.targetIp}` : '';

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          stroke: faultActive ? 'var(--status-stopped)' : 'var(--text-secondary)',
          strokeWidth: faultActive ? 3 : 2,
          strokeDasharray: faultActive ? '8 6' : undefined,
          ...style,
        }}
        markerEnd={markerEnd}
      />
      <EdgeLabelRenderer>
        {subnet && (
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${midX}px,${midY}px)`,
              background: 'var(--panel-bg)',
              padding: '2px 6px',
              borderRadius: '4px',
              fontSize: '10px',
              color: 'var(--text-primary)',
              border: '1px solid var(--panel-border)',
              pointerEvents: 'all',
              zIndex: 10,
            }}
            className="nodrag nopan"
          >
            {subnet}
          </div>
        )}
        {srcLabel && (
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${srcLabelX}px,${srcLabelY}px)`,
              background: 'var(--bg-primary)',
              padding: '2px 4px',
              borderRadius: '2px',
              fontSize: '9px',
              color: 'var(--text-secondary)',
              pointerEvents: 'none',
              zIndex: 5,
            }}
          >
            {srcLabel}
          </div>
        )}
        {tgtLabel && (
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${tgtLabelX}px,${tgtLabelY}px)`,
              background: 'var(--bg-primary)',
              padding: '2px 4px',
              borderRadius: '2px',
              fontSize: '9px',
              color: 'var(--text-secondary)',
              pointerEvents: 'none',
              zIndex: 5,
            }}
          >
            {tgtLabel}
          </div>
        )}
      </EdgeLabelRenderer>
    </>
  );
};
