import { BaseEdge, getSmoothStepPath } from '@xyflow/react';
import type { EdgeProps, Position } from '@xyflow/react';
import type { NetworkNode } from '@octet/shared-types';
import { useTopologyStore } from '../../store';
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

  // Green when any node is running (simulation is live).
  const isRunning = useTopologyStore(s =>
    s.nodes.some(n => (n.data as NetworkNode).runtimeState?.status === 'running'),
  );

  const stroke = faultActive
    ? 'var(--status-stopped)'       // red — faulted
    : isRunning
      ? '#4caf50'                   // green — simulation live
      : 'var(--text-secondary)';    // grey — idle/stopped

  return (
    <BaseEdge
      id={id}
      path={edgePath}
      style={{
        stroke,
        strokeWidth: faultActive ? 3 : 2,
        strokeDasharray: faultActive ? '8 6' : undefined,
        transition: 'stroke 0.4s ease',
        ...style,
      }}
      markerEnd={markerEnd}
    />
  );
};
