import { Handle, Position } from '@xyflow/react';
import type { NetworkNode } from '@netsimflow/shared-types';

/**
 * Handle positions cycle through these four sides in order.
 * Interface eth0 → Top, eth1 → Right, eth2 → Bottom, eth3 → Left,
 * eth4 → Top again, etc. This makes handle IDs match interface names
 * so edges survive a save/reload round-trip (toReactFlowEdge sets
 * sourceHandle = sourcePort, which must equal a real handle id).
 */
const CYCLE: Position[] = [Position.Top, Position.Right, Position.Bottom, Position.Left];

interface BaseNodeProps {
  data: NetworkNode;
  icon: React.ReactNode;
}

export const BaseNode: React.FC<BaseNodeProps> = ({ data, icon }) => {
  const status = data.runtimeState?.status ?? 'stopped';
  const role = data.role ?? data.baseType;
  const interfaces = data.logicalConfig?.interfaces ?? [];

  return (
    <div className="netsim-node">
      {interfaces.map((iface, idx) => (
        <Handle
          key={iface.name}
          type="source"
          position={CYCLE[idx % CYCLE.length]}
          id={iface.name}
          className="netsim-handle"
        />
      ))}

      <div className="netsim-node-icon">{icon}</div>
      <div className="netsim-node-content">
        <span className="netsim-node-label">{data.label}</span>
        <span className="netsim-node-sub">{role.toUpperCase()}</span>
      </div>
      <div className={`status-dot ${status}`} title={`Status: ${status}`} />
    </div>
  );
};
