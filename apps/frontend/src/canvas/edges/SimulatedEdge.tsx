import { BaseEdge, getSmoothStepPath } from '@xyflow/react';
import type { EdgeProps, Position } from '@xyflow/react';
import type { ReactFlowEdge } from '../graphHelpers';

export const SimulatedEdge: React.FC<EdgeProps<ReactFlowEdge>> = ({
  id,
  sourceX,
  sourceY,
  sourcePosition,
  targetX,
  targetY,
  targetPosition,
  data,
  style,
  markerEnd,
}) => {
  const [edgePath] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition: sourcePosition as Position,
    targetX,
    targetY,
    targetPosition: targetPosition as Position,
    borderRadius: 6,
  });

  const faultActive = Boolean(data?.faultState?.active);

  return (
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
  );
};
