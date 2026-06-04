import { beforeEach, describe, expect, it } from 'vitest';
import { useTopologyStore } from './topology.slice';
import { createNode } from '../canvas/nodes/nodeFactory';

function resetStore() {
  useTopologyStore.setState({
    currentTopologyId: null,
    currentTopologyName: 'Test',
    nodes: [],
    edges: [],
    selectedNodeIds: [],
    selectedEdgeIds: [],
  });
}

describe('topology store — updateNodeInterface', () => {
  beforeEach(resetStore);

  it('updates ip on a specific interface', () => {
    const node = createNode('router', 'R1', { x: 0, y: 0 });
    useTopologyStore.getState().addNode(node);

    useTopologyStore.getState().updateNodeInterface(node.id, 'eth0', { ip: '192.168.1.1' });

    const stored = useTopologyStore.getState().nodes.find(n => n.id === node.id);
    const iface = stored?.data.logicalConfig?.interfaces.find(i => i.name === 'eth0');
    expect(iface?.ip).toBe('192.168.1.1');
  });

  it('updates subnet independently', () => {
    const node = createNode('router', 'R1', { x: 0, y: 0 });
    useTopologyStore.getState().addNode(node);

    useTopologyStore.getState().updateNodeInterface(node.id, 'eth0', { subnet: '/30' });

    const stored = useTopologyStore.getState().nodes.find(n => n.id === node.id);
    const iface = stored?.data.logicalConfig?.interfaces.find(i => i.name === 'eth0');
    expect(iface?.subnet).toBe('/30');
    expect(iface?.ip).toBeUndefined();
  });

  it('updates both ip and subnet together', () => {
    const node = createNode('router', 'R1', { x: 0, y: 0 });
    useTopologyStore.getState().addNode(node);

    useTopologyStore.getState().updateNodeInterface(node.id, 'eth1', { ip: '10.0.0.1', subnet: '/24' });

    const stored = useTopologyStore.getState().nodes.find(n => n.id === node.id);
    const iface = stored?.data.logicalConfig?.interfaces.find(i => i.name === 'eth1');
    expect(iface?.ip).toBe('10.0.0.1');
    expect(iface?.subnet).toBe('/24');
  });

  it('does not affect sibling interfaces', () => {
    const node = createNode('router', 'R1', { x: 0, y: 0 });
    useTopologyStore.getState().addNode(node);

    useTopologyStore.getState().updateNodeInterface(node.id, 'eth0', { ip: '10.0.0.1' });

    const stored = useTopologyStore.getState().nodes.find(n => n.id === node.id);
    for (const iface of stored?.data.logicalConfig?.interfaces ?? []) {
      if (iface.name !== 'eth0') expect(iface.ip).toBeUndefined();
    }
  });

  it('stores empty string as undefined (clean model)', () => {
    const node = createNode('router', 'R1', { x: 0, y: 0 });
    useTopologyStore.getState().addNode(node);

    useTopologyStore.getState().updateNodeInterface(node.id, 'eth0', { ip: '10.0.0.1' });
    useTopologyStore.getState().updateNodeInterface(node.id, 'eth0', { ip: '' });

    const stored = useTopologyStore.getState().nodes.find(n => n.id === node.id);
    const iface = stored?.data.logicalConfig?.interfaces.find(i => i.name === 'eth0');
    expect(iface?.ip).toBeUndefined();
  });

  it('is a no-op for unknown node id', () => {
    const before = JSON.stringify(useTopologyStore.getState().nodes);
    useTopologyStore.getState().updateNodeInterface('non-existent', 'eth0', { ip: '1.2.3.4' });
    expect(JSON.stringify(useTopologyStore.getState().nodes)).toBe(before);
  });

  it('is a no-op for unknown interface name', () => {
    const node = createNode('host', 'H1', { x: 0, y: 0 });
    useTopologyStore.getState().addNode(node);

    useTopologyStore.getState().updateNodeInterface(node.id, 'eth9', { ip: '1.2.3.4' });

    const stored = useTopologyStore.getState().nodes.find(n => n.id === node.id);
    expect(stored?.data.logicalConfig?.interfaces.find(i => i.name === 'eth9')).toBeUndefined();
  });

  it('save/load round-trip preserves interface IPs', () => {
    const node = createNode('router', 'R1', { x: 0, y: 0 });
    useTopologyStore.getState().addNode(node);
    useTopologyStore.getState().updateNodeInterface(node.id, 'eth0', { ip: '10.1.1.1', subnet: '/24' });

    const stored = useTopologyStore.getState().nodes.find(n => n.id === node.id)!;
    const restored = JSON.parse(JSON.stringify(stored.data)) as typeof stored.data;
    const eth0 = restored.logicalConfig?.interfaces.find(i => i.name === 'eth0');
    expect(eth0?.ip).toBe('10.1.1.1');
    expect(eth0?.subnet).toBe('/24');
  });
});
