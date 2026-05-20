import { BaseEdge, getStraightPath } from '@xyflow/react';
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
