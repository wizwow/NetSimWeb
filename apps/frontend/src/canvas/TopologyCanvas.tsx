import React, { useCallback, useMemo } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  ConnectionMode,
  Panel
} from '@xyflow/react';
import { useTopologyStore, useUiStore } from '../store';
import { nodeTypes } from './nodeTypes';
import { v4 as uuidv4 } from 'uuid';
import type { NetworkNode } from '@netsimflow/shared-types';
import { PropertyPanel } from '../components/PropertyPanel';

export const TopologyCanvas: React.FC = () => {
  const { nodes, edges, onNodesChange, onEdgesChange, onConnect, addNode, saveTopology, loadLatestTopology } = useTopologyStore();
  const { theme, setSelectedElement } = useUiStore();

  const handleAddDevice = (type: NetworkNode['baseType']) => {
    const newNode: NetworkNode = {
      id: `node-${uuidv4()}`,
      label: `${type}-${nodes.length + 1}`,
      position: { x: Math.random() * 200 + 100, y: Math.random() * 200 + 100 },
      baseType: type,
      tags: [],
      runtimeState: { status: 'stopped' }
    };
    addNode(newNode);
  };

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={(_, node) => setSelectedElement(node.id, 'node')}
        onEdgeClick={(_, edge) => setSelectedElement(edge.id, 'edge')}
        onPaneClick={() => setSelectedElement(null, null)}
        nodeTypes={nodeTypes}
        connectionMode={ConnectionMode.Loose}
        colorMode={theme}
        fitView
      >
        <Background color="var(--text-secondary)" gap={20} size={1} />
        <Controls />
        <MiniMap 
          nodeColor={(node) => {
            switch (node.type) {
              case 'router': return 'var(--node-router)';
              case 'switch': return 'var(--node-switch)';
              case 'cloud': return 'var(--node-cloud)';
              case 'host': return 'var(--node-host)';
              default: return '#eee';
            }
          }}
          maskColor="var(--minimap-mask)"
          style={{ backgroundColor: 'var(--panel-bg)' }}
        />
        
        <Panel position="top-left" style={{ display: 'flex', gap: '8px', background: 'var(--panel-bg)', padding: '8px', borderRadius: '8px', border: '1px solid var(--panel-border)', backdropFilter: 'var(--panel-backdrop)' }}>
          <button onClick={() => handleAddDevice('router')} style={buttonStyle}>+ Router</button>
          <button onClick={() => handleAddDevice('switch')} style={buttonStyle}>+ Switch</button>
          <button onClick={() => handleAddDevice('cloud')} style={buttonStyle}>+ Cloud</button>
          <button onClick={() => handleAddDevice('host')} style={buttonStyle}>+ Host</button>
        </Panel>

        <Panel position="top-right" style={{ display: 'flex', gap: '8px', background: 'var(--panel-bg)', padding: '8px', borderRadius: '8px', border: '1px solid var(--panel-border)', backdropFilter: 'var(--panel-backdrop)' }}>
          <button onClick={saveTopology} style={{ ...buttonStyle, background: 'var(--accent-blue)', color: 'white', border: 'none' }}>Save</button>
          <button onClick={loadLatestTopology} style={buttonStyle}>Load Latest</button>
        </Panel>
      </ReactFlow>
      <PropertyPanel />
    </div>
  );
};

const buttonStyle = {
  background: 'var(--button-bg)',
  border: '1px solid var(--button-border)',
  color: 'var(--text-primary)',
  padding: '6px 12px',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '13px',
  fontWeight: 500
};
