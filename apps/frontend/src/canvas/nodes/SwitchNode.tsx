import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import type { NetworkNode } from '@octet/shared-types';
import { Network } from 'lucide-react';
import './SwitchNode.css';

/**
 * Switch node rendered as a patch-panel: a horizontal strip of numbered port
 * slots, each with its own React Flow Handle at the bottom edge.
 *
 * Both the visual slot and the Handle share the formula
 *   left = (idx + 1) / (count + 1) * 100%
 * so they align horizontally regardless of how many interfaces exist.
 */
export const SwitchNode = memo(({ data }: NodeProps) => {
  const nodeData = data as NetworkNode;
  const status = nodeData.runtimeState?.status ?? 'stopped';
  const interfaces = nodeData.logicalConfig?.interfaces ?? [];
  const count = interfaces.length;

  return (
    <div className="switch-node">

      {/* React Flow connection handles — one per interface at the bottom edge */}
      {interfaces.map((iface, idx) => (
        <Handle
          key={iface.name}
          type="source"
          position={Position.Bottom}
          id={iface.name}
          className={`switch-port-handle ${iface.status}`}
          style={{ left: `${(idx + 1) / (count + 1) * 100}%` }}
          title={
            iface.ip
              ? `${iface.name}: ${iface.ip}${iface.subnet ?? ''}`
              : iface.name
          }
        />
      ))}

      {/* Header */}
      <div className="switch-node-header">
        <Network size={14} color="var(--node-switch)" />
        <span className="switch-node-label">{nodeData.label}</span>
        <div className={`status-dot ${status}`} title={`Status: ${status}`} />
      </div>

      {/* Port strip */}
      <div className="switch-port-row">
        {interfaces.map((iface, idx) => (
          <div
            key={iface.name}
            className={`switch-port-slot ${iface.status}`}
            style={{ left: `${(idx + 1) / (count + 1) * 100}%` }}
            title={
              iface.ip
                ? `${iface.name}: ${iface.ip}${iface.subnet ?? ''}`
                : iface.name
            }
          >
            <span className="switch-port-num">{idx + 1}</span>
          </div>
        ))}
      </div>

    </div>
  );
});

SwitchNode.displayName = 'SwitchNode';
