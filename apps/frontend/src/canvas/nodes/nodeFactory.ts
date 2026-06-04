import { v4 as uuidv4 } from 'uuid';
import type { NetworkNode, LogicalInterface } from '@netsimflow/shared-types';

/**
 * Default interface names per device type.
 * "Fixed now, configurable later" — the counts are sensible starting defaults;
 * dynamic add/remove can be layered on without changing this structure.
 */
export const INTERFACE_DEFAULTS: Record<NetworkNode['baseType'], string[]> = {
  router:   ['eth0', 'eth1', 'eth2', 'eth3'],
  switch:   ['eth0', 'eth1', 'eth2', 'eth3', 'eth4', 'eth5', 'eth6', 'eth7'],
  host:     ['eth0'],
  cloud:    ['eth0'],
  firewall: ['eth0', 'eth1'],
  site:     ['eth0', 'eth1'],
};

function makeInterfaces(ports: string[]): LogicalInterface[] {
  return ports.map(name => ({ name, status: 'down' as const }));
}

/**
 * Create a new NetworkNode with the correct default interface set for its type.
 * All interfaces start with status 'down' and no IP/subnet assigned.
 */
export function createNode(
  baseType: NetworkNode['baseType'],
  label: string,
  position: { x: number; y: number },
): NetworkNode {
  const ports = INTERFACE_DEFAULTS[baseType] ?? [];
  return {
    id: `node-${uuidv4()}`,
    label,
    position,
    baseType,
    tags: [],
    runtimeState: { status: 'stopped' },
    logicalConfig: {
      interfaces: makeInterfaces(ports),
    },
  };
}
