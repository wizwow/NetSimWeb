import { describe, it, expect } from 'vitest';
import { createNode, INTERFACE_DEFAULTS } from './nodeFactory';
import type { NetworkNode } from '@octet/shared-types';

describe('createNode — interface factory', () => {
  it('router gets 4 interfaces named eth0–eth3', () => {
    const node = createNode('router', 'R1', { x: 0, y: 0 });
    expect(node.logicalConfig?.interfaces.map(i => i.name)).toEqual(['eth0', 'eth1', 'eth2', 'eth3']);
  });

  it('switch gets 8 interfaces', () => {
    const node = createNode('switch', 'SW1', { x: 0, y: 0 });
    expect(node.logicalConfig?.interfaces).toHaveLength(8);
  });

  it('host gets exactly 1 interface — eth0', () => {
    const node = createNode('host', 'H1', { x: 0, y: 0 });
    expect(node.logicalConfig?.interfaces).toHaveLength(1);
    expect(node.logicalConfig?.interfaces[0].name).toBe('eth0');
  });

  it('cloud gets exactly 1 interface — eth0', () => {
    const node = createNode('cloud', 'Cloud1', { x: 0, y: 0 });
    expect(node.logicalConfig?.interfaces).toHaveLength(1);
    expect(node.logicalConfig?.interfaces[0].name).toBe('eth0');
  });

  it('firewall gets 2 interfaces', () => {
    const node = createNode('firewall', 'FW1', { x: 0, y: 0 });
    expect(node.logicalConfig?.interfaces).toHaveLength(2);
  });

  it('all interfaces start with status down and no IP or subnet', () => {
    const node = createNode('router', 'R1', { x: 0, y: 0 });
    for (const iface of node.logicalConfig!.interfaces) {
      expect(iface.status).toBe('down');
      expect(iface.ip).toBeUndefined();
      expect(iface.subnet).toBeUndefined();
    }
  });

  it('generates a unique id for every node', () => {
    const a = createNode('router', 'R1', { x: 0, y: 0 });
    const b = createNode('router', 'R2', { x: 100, y: 0 });
    expect(a.id).not.toBe(b.id);
    expect(a.id).toMatch(/^node-/);
  });

  it('preserves label and position', () => {
    const node = createNode('router', 'Core-R1', { x: 42, y: 99 });
    expect(node.label).toBe('Core-R1');
    expect(node.position).toEqual({ x: 42, y: 99 });
    expect(node.baseType).toBe('router');
  });

  it('save/load round-trip preserves interfaces', () => {
    const node = createNode('router', 'R1', { x: 0, y: 0 });
    const restored = JSON.parse(JSON.stringify(node)) as NetworkNode;
    expect(restored.logicalConfig?.interfaces).toEqual(node.logicalConfig?.interfaces);
  });

  it('INTERFACE_DEFAULTS covers all baseTypes used in the UI palette', () => {
    const paletteTypes: NetworkNode['baseType'][] = ['router', 'switch', 'host', 'cloud'];
    for (const type of paletteTypes) {
      expect(INTERFACE_DEFAULTS[type].length).toBeGreaterThan(0);
    }
  });
});
