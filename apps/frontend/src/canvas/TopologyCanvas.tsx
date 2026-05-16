import React, { useEffect, useMemo, useState } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  ConnectionMode,
  Panel
} from '@xyflow/react';
import { v4 as uuidv4 } from 'uuid';
import type { NetworkNode } from '@netsimflow/shared-types';
import { useTopologyStore, useUiStore } from '../store';
import { nodeTypes } from './nodeTypes';
import { SimulatedEdge } from './edges/SimulatedEdge';
import { PropertyPanel } from '../components/PropertyPanel';
import { useSimulationEvents } from '../hooks/useSimulationEvents';
import { useTopology } from '../hooks/useTopology';
import { LogConsole } from '../components/LogConsole';
import { api, type TemplateSummary } from '../services/api';

const edgeTypes = { simulatedEdge: SimulatedEdge };

export const TopologyCanvas: React.FC = () => {
  const {
    nodes, edges, onNodesChange, onEdgesChange, onConnect,
    addNode, currentTopologyId,
  } = useTopologyStore();
  const { theme, selectedElementId, selectedElementType, setSelectedElement } = useUiStore();
  const [templates, setTemplates] = useState<TemplateSummary[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState('ospf-3-sites');

  // API side-effects live in hooks, not in the store
  const {
    saveTopology,
    loadLatestTopology,
    triggerAutoIp,
    loadTemplate,
    startSimulation,
    stopSimulation,
    runProbe,
    injectFault,
  } = useTopology();
  useSimulationEvents(currentTopologyId);

  useEffect(() => {
    api.getTemplates()
      .then((loadedTemplates) => {
        setTemplates(loadedTemplates);
        if (loadedTemplates.length > 0 && !loadedTemplates.some(t => t.id === selectedTemplateId)) {
          setSelectedTemplateId(loadedTemplates[0].id);
        }
      })
      .catch((err) => {
        console.error('Template list load failed', err);
      });
  }, [selectedTemplateId]);

  const probeTargetIp = useMemo(() => {
    const selectedNode = selectedElementType === 'node'
      ? nodes.find(node => node.id === selectedElementId)
      : null;
    if (!selectedNode) return null;

    const peerLoopback = nodes
      .find(node => node.id !== selectedNode.id && node.data.logicalConfig?.loopback)
      ?.data.logicalConfig?.loopback;
    if (peerLoopback) return peerLoopback;

    const peerEdge = edges.find(edge => edge.source === selectedNode.id || edge.target === selectedNode.id);
    const edgeData = peerEdge?.data;
    if (!edgeData?.ipConfig) return null;
    return peerEdge?.source === selectedNode.id
      ? edgeData.ipConfig.targetIp
      : edgeData.ipConfig.sourceIp;
  }, [edges, nodes, selectedElementId, selectedElementType]);

  const selectedFaultLinkId = useMemo(() => {
    if (selectedElementType !== 'edge') return null;
    const selectedEdge = edges.find(edge => edge.id === selectedElementId);
    return selectedEdge?.data?.id ?? selectedElementId;
  }, [edges, selectedElementId, selectedElementType]);

  const handleAddDevice = (type: NetworkNode['baseType']) => {
    const newNode: NetworkNode = {
      id: `node-${uuidv4()}`,
      label: `${type}-${nodes.length + 1}`,
      position: { x: Math.random() * 200 + 100, y: Math.random() * 200 + 100 },
      baseType: type,
      tags: [],
      runtimeState: { status: 'stopped' },
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
        edgeTypes={edgeTypes}
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

        <Panel position="top-center" style={{ display: 'flex', gap: '8px', background: 'var(--panel-bg)', padding: '8px', borderRadius: '8px', border: '1px solid var(--panel-border)', backdropFilter: 'var(--panel-backdrop)' }}>
          <select
            value={selectedTemplateId}
            onChange={(event) => setSelectedTemplateId(event.target.value)}
            style={selectStyle}
            title="Topology template"
          >
            {templates.map((template) => (
              <option key={template.id} value={template.id}>{template.name}</option>
            ))}
          </select>
          <button
            onClick={() => loadTemplate(selectedTemplateId)}
            style={buttonStyle}
            disabled={!selectedTemplateId}
          >
            Load Template
          </button>
          <button onClick={triggerAutoIp} style={buttonStyle}>Auto-IP</button>
        </Panel>

        <Panel position="top-right" style={{ display: 'flex', gap: '8px', background: 'var(--panel-bg)', padding: '8px', borderRadius: '8px', border: '1px solid var(--panel-border)', backdropFilter: 'var(--panel-backdrop)' }}>
          <button onClick={startSimulation} style={{ ...buttonStyle, background: 'var(--status-running)', color: 'white', border: 'none' }}>▶ Start</button>
          <button onClick={stopSimulation} style={{ ...buttonStyle, background: 'var(--status-stopped)', color: 'white', border: 'none' }}>■ Stop</button>
          <div style={{ width: '1px', background: 'var(--panel-border)', margin: '0 4px' }} />
          <button
            onClick={() => selectedElementId && probeTargetIp && runProbe(selectedElementId, probeTargetIp)}
            style={buttonStyle}
            disabled={selectedElementType !== 'node' || !probeTargetIp}
          >
            Ping
          </button>
          <button
            onClick={() => selectedFaultLinkId && injectFault(selectedFaultLinkId)}
            style={buttonStyle}
            disabled={!selectedFaultLinkId}
          >
            Fault
          </button>
          <button onClick={saveTopology} style={{ ...buttonStyle, background: 'var(--accent-blue)', color: 'white', border: 'none' }}>Save</button>
          <button onClick={loadLatestTopology} style={buttonStyle}>Load Latest</button>
        </Panel>
      </ReactFlow>
      <PropertyPanel />
      <LogConsole />
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

const selectStyle = {
  background: 'var(--button-bg)',
  border: '1px solid var(--button-border)',
  color: 'var(--text-primary)',
  padding: '6px 10px',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '13px',
  fontWeight: 500
};
