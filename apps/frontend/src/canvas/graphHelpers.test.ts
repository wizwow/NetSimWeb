import { describe, it, expect } from 'vitest';
import { getNextFreePort } from './graphHelpers';
import type { ReactFlowEdge } from './graphHelpers';
import type { LogicalInterface } from '@netsimflow/shared-types';

const ifaces = (names: string[]): LogicalInterface[] =>
  names.map(name => ({ name, status: 'down' as const }));

const sourceEdge = (sourceNodeId: string, sourcePort: string): ReactFlowEdge =>
  ({
    id: `e-${sourceNodeId}-${sourcePort}`,
    source: sourceNodeId,
    target: 'other',
    type: 'simulatedEdge',
    data: { id: 'lnk', sourceNodeId, targetNodeId: 'other', sourcePort, targetPort: 'eth0', linkType: 'ethernet' },
  } as ReactFlowEdge);

const targetEdge = (targetNodeId: string, targetPort: string): ReactFlowEdge =>
  ({
    id: `e-other-${targetPort}`,
    source: 'other',
    target: targetNodeId,
    type: 'simulatedEdge',
    data: { id: 'lnk', sourceNodeId: 'other', targetNodeId, sourcePort: 'eth0', targetPort, linkType: 'ethernet' },
  } as ReactFlowEdge);

describe('getNextFreePort', () => {
  it('returns eth0 when no edges exist', () => {
    expect(getNextFreePort('r1', ifaces(['eth0', 'eth1', 'eth2']), [])).toBe('eth0');
  });

  it('skips eth0 when it is already used as sourcePort', () => {
    const edges = [sourceEdge('r1', 'eth0')];
    expect(getNextFreePort('r1', ifaces(['eth0', 'eth1', 'eth2']), edges)).toBe('eth1');
  });

  it('skips eth0 when it is already used as targetPort', () => {
    const edges = [targetEdge('r1', 'eth0')];
    expect(getNextFreePort('r1', ifaces(['eth0', 'eth1']), edges)).toBe('eth1');
  });

  it('skips both source and target used ports', () => {
    const edges = [sourceEdge('r1', 'eth0'), targetEdge('r1', 'eth1')];
    expect(getNextFreePort('r1', ifaces(['eth0', 'eth1', 'eth2', 'eth3']), edges)).toBe('eth2');
  });

  it('returns null when all interfaces are occupied', () => {
    const edges = [sourceEdge('h1', 'eth0')];
    expect(getNextFreePort('h1', ifaces(['eth0']), edges)).toBeNull();
  });

  it('ignores edges belonging to other nodes', () => {
    const edges = [sourceEdge('r2', 'eth0')]; // r2, not r1
    expect(getNextFreePort('r1', ifaces(['eth0', 'eth1']), edges)).toBe('eth0');
  });

  it('returns null for a node with no interfaces', () => {
    expect(getNextFreePort('r1', [], [])).toBeNull();
  });

  it('works correctly for a host with a single interface', () => {
    expect(getNextFreePort('h1', ifaces(['eth0']), [])).toBe('eth0');
    const edges = [targetEdge('h1', 'eth0')];
    expect(getNextFreePort('h1', ifaces(['eth0']), edges)).toBeNull();
  });
});
