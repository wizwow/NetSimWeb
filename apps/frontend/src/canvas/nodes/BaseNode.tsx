import React from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NetworkNode, LogicalInterface } from '@octet/shared-types';

/**
 * Handle positions cycle through these four sides in order.
 * Interface eth0 → Top, eth1 → Right, eth2 → Bottom, eth3 → Left,
 * eth4 → Top again, etc.
 */
const CYCLE: Position[] = [Position.Top, Position.Right, Position.Bottom, Position.Left];

interface BaseNodeProps {
  data: NetworkNode;
  icon: React.ReactNode;
}

/** Format the label shown beside a port handle. */
function portLabel(iface: LogicalInterface): string {
  const addr = iface.ip
    ? iface.subnet ? `${iface.ip}${iface.subnet}` : iface.ip
    : '';
  return addr ? `${iface.name}: ${addr}` : iface.name;
}

/**
 * Compute absolute-positioned style for a port label given:
 *  - which side of the node the handle is on
 *  - how many handles share that side (sideCount)
 *  - the 0-based index of this handle within that side (sideIdx)
 *
 * React Flow distributes N handles on a side evenly at positions
 * (1/(N+1), 2/(N+1), … N/(N+1)) as a fraction of the node edge length.
 * We reproduce that to align labels with handles.
 */
function labelStyle(
  position: Position,
  sideIdx: number,
  sideCount: number,
): React.CSSProperties {
  const fraction = (sideIdx + 1) / (sideCount + 1);
  const pct = `${fraction * 100}%`;
  const base: React.CSSProperties = {
    position: 'absolute',
    fontSize: '9px',
    fontFamily: 'monospace',
    color: 'var(--text-secondary)',
    whiteSpace: 'nowrap',
    pointerEvents: 'none',
    lineHeight: 1.2,
    zIndex: 1,
  };

  switch (position) {
    case Position.Top:
      return { ...base, bottom: '100%', left: pct, transform: 'translateX(-50%)', paddingBottom: '4px', textAlign: 'center' };
    case Position.Right:
      return { ...base, left: '100%', top: pct, transform: 'translateY(-50%)', paddingLeft: '6px' };
    case Position.Bottom:
      return { ...base, top: '100%', left: pct, transform: 'translateX(-50%)', paddingTop: '4px', textAlign: 'center' };
    case Position.Left:
      return { ...base, right: '100%', top: pct, transform: 'translateY(-50%)', paddingRight: '6px', textAlign: 'right' };
  }
}

export const BaseNode: React.FC<BaseNodeProps> = ({ data, icon }) => {
  const status = data.runtimeState?.status ?? 'stopped';
  const role = data.role ?? data.baseType;
  const interfaces = data.logicalConfig?.interfaces ?? [];

  // Count how many interfaces land on each side so labels can be distributed
  // along the edge at the same fractional positions React Flow uses.
  const sideCount: Record<Position, number> = {
    [Position.Top]: 0,
    [Position.Right]: 0,
    [Position.Bottom]: 0,
    [Position.Left]: 0,
  };
  for (let i = 0; i < interfaces.length; i++) {
    sideCount[CYCLE[i % CYCLE.length]]++;
  }
  const sideIdx: Record<Position, number> = {
    [Position.Top]: 0,
    [Position.Right]: 0,
    [Position.Bottom]: 0,
    [Position.Left]: 0,
  };

  return (
    <div className="netsim-node">
      {interfaces.map((iface, idx) => {
        const pos = CYCLE[idx % CYCLE.length];
        const thisIdx = sideIdx[pos]++;
        return (
          <React.Fragment key={iface.name}>
            <Handle
              type="source"
              position={pos}
              id={iface.name}
              className="netsim-handle"
            />
            <span style={labelStyle(pos, thisIdx, sideCount[pos])} aria-hidden="true">
              {portLabel(iface)}
            </span>
          </React.Fragment>
        );
      })}

      <div className="netsim-node-icon">{icon}</div>
      <div className="netsim-node-content">
        <span className="netsim-node-label">{data.label}</span>
        <span className="netsim-node-sub">{role.toUpperCase()}</span>
      </div>
      <div className={`status-dot ${status}`} title={`Status: ${status}`} />
    </div>
  );
};
