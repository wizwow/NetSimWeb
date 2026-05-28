import React from 'react';
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

  const subnet = data?.ipConfig?.subnet;

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          stroke: faultActive ? 'var(--err)' : 'var(--line-strong)',
          strokeWidth: faultActive ? 2.5 : 1.5,
          strokeDasharray: faultActive ? '8 5' : undefined,
          ...style,
        }}
        markerEnd={markerEnd}
      />
      {subnet && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${midX}px,${midY}px)`,
              background: 'var(--surface)',
              padding: '2px 6px',
              borderRadius: 'var(--r-xs)',
              fontSize: 10,
              fontFamily: 'var(--font-mono)',
              color: 'var(--text-3)',
              border: '1px solid var(--line)',
              pointerEvents: 'all',
              zIndex: 10,
            }}
            className="nodrag nopan"
          >
            {subnet}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
};
