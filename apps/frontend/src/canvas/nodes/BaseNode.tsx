import React from 'react';
import { useReactFlow } from '@xyflow/react';
import type { NetworkNode } from '@netsimflow/shared-types';

// Node card dimensions (visual area including padding)
const NODE_W = 108;
const NODE_H = 104;

interface BaseNodeProps {
  data: NetworkNode;
  icon: React.ReactNode;
  handles: React.ReactNode;
  iconBg: string;
  nodeId: string;
}

// Geometry helper: compute the point on the node border closest to the peer
function getBorderPoint(
  nx: number, ny: number,
  px: number, py: number,
): { x: number; y: number } {
  const hw = NODE_W / 2;
  const hh = NODE_H / 2;
  const dx = px - nx;
  const dy = py - ny;
  if (Math.abs(dx) < 0.1 && Math.abs(dy) < 0.1) return { x: nx, y: ny };
  const tx = Math.abs(dx) > 0.1 ? hw / Math.abs(dx) : Infinity;
  const ty = Math.abs(dy) > 0.1 ? hh / Math.abs(dy) : Infinity;
  const t = Math.min(tx, ty);
  return { x: nx + dx * t, y: ny + dy * t };
}

// Compute NIC port indicators for this node
const NicPorts: React.FC<{ nodeId: string }> = ({ nodeId }) => {
  const { getEdges, getNode } = useReactFlow();
  const edges = getEdges();
  const thisNode = getNode(nodeId);
  if (!thisNode) return null;

  // Center of this node
  const nx = thisNode.position.x + NODE_W / 2;
  const ny = thisNode.position.y + NODE_H / 2;

  const ports: Array<{ bx: number; by: number; faultActive: boolean; stopped: boolean; key: string }> = [];

  for (const edge of edges) {
    let peerId: string | null = null;
    if (edge.source === nodeId) peerId = edge.target;
    else if (edge.target === nodeId) peerId = edge.source;
    if (!peerId) continue;

    const peer = getNode(peerId);
    if (!peer) continue;

    const px = peer.position.x + NODE_W / 2;
    const py = peer.position.y + NODE_H / 2;
    const bp = getBorderPoint(nx, ny, px, py);

    // relative to node top-left
    const bx = bp.x - (thisNode.position.x);
    const by = bp.y - (thisNode.position.y);

    const faultActive = Boolean((edge.data as { faultState?: { active?: boolean } })?.faultState?.active);
    const stopped = false; // node status is in data, not edge

    ports.push({ bx, by, faultActive, stopped, key: edge.id });
  }

  return (
    <>
      {ports.map(({ bx, by, faultActive, key }) => {
        const color = faultActive ? 'var(--err)' : 'var(--ok)';
        // Determine orientation based on which edge we're on
        const onLeft = bx < 8;
        const onRight = bx > NODE_W - 8;
        const isHoriz = onLeft || onRight;
        const w = isHoriz ? 6 : 9;
        const h = isHoriz ? 9 : 6;
        return (
          <div
            key={key}
            style={{
              position: 'absolute',
              left: bx - w / 2,
              top: by - h / 2,
              width: w,
              height: h,
              background: color,
              borderRadius: 1,
              pointerEvents: 'none',
              zIndex: 5,
              opacity: 0.9,
            }}
          />
        );
      })}
    </>
  );
};

export const BaseNode: React.FC<BaseNodeProps> = ({ data, icon, handles, iconBg, nodeId }) => {
  const status = data.runtimeState?.status || 'stopped';
  const loopback = data.logicalConfig?.loopback || '';

  let statusColor = 'var(--text-dim)';
  if (status === 'running') statusColor = 'var(--ok)';
  else if (status === 'error') statusColor = 'var(--err)';
  else if (status === 'booting') statusColor = 'var(--warn)';

  return (
    <div
      className="tnode"
      style={{
        position: 'relative',
        width: NODE_W,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 5,
        padding: '8px 4px 7px',
        background: 'var(--surface)',
        border: '1px solid var(--line)',
        borderRadius: 'var(--r-md)',
        boxShadow: 'var(--shadow-node)',
        userSelect: 'none',
      }}
    >
      {/* Icon plate */}
      <div
        className="tnode-icon"
        style={{
          width: 50,
          height: 44,
          borderRadius: 'var(--r-sm)',
          background: iconBg,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          position: 'relative',
        }}
      >
        {icon}
        {/* Status dot */}
        <span
          className="tnode-status"
          style={{
            position: 'absolute',
            top: 4,
            right: 4,
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: statusColor,
            ...(status === 'running' ? { boxShadow: `0 0 0 2px color-mix(in oklab, ${statusColor} 25%, transparent)` } : {}),
          }}
          title={`Status: ${status}`}
        />
      </div>

      {/* Label */}
      <span
        className="tnode-name"
        style={{
          fontSize: 12.5,
          fontWeight: 600,
          color: 'var(--text)',
          maxWidth: 96,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          textAlign: 'center',
        }}
      >
        {data.label}
      </span>

      {/* Loopback IP */}
      {loopback && (
        <span
          className="tnode-ip"
          style={{
            fontSize: 10,
            fontFamily: 'var(--font-mono)',
            color: 'var(--text-3)',
            maxWidth: 96,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            textAlign: 'center',
            marginTop: -2,
          }}
        >
          {loopback}
        </span>
      )}

      {/* NIC port indicators */}
      <NicPorts nodeId={nodeId} />

      {/* React Flow handles */}
      {handles}
    </div>
  );
};
