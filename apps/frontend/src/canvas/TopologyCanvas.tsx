import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  ConnectionMode,
  Panel
} from '@xyflow/react';
import type { NetworkNode } from '@octet/shared-types';
import { useTopologyStore, useUiStore } from '../store';
import { createNode } from './nodes/nodeFactory';
import { nodeTypes } from './nodeTypes';
import { SimulatedEdge } from './edges/SimulatedEdge';
import { PropertyPanel } from '../components/PropertyPanel';
import { useSimulationEvents } from '../hooks/useSimulationEvents';
import { useTopology } from '../hooks/useTopology';
import { LogConsole } from '../components/LogConsole';

const edgeTypes = { simulatedEdge: SimulatedEdge };

type ToolbarMenuItem = {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  title: string;
  variant?: 'primary' | 'running' | 'stopped';
};

export const TopologyCanvas: React.FC = () => {
  const {
    nodes, edges, onNodesChange, onEdgesChange, onConnect,
    addNode, currentTopologyId,
  } = useTopologyStore();
  const { theme, selectedElementId, selectedElementType, setSelectedElement } = useUiStore();
  const [selectedTemplateId, setSelectedTemplateId] = useState('ospf-3-sites');
  const [pingTargetIp, setPingTargetIp] = useState('');
  const importInputRef = useRef<HTMLInputElement>(null);

  // API side-effects live in hooks, not in the store
  const {
    templates,
    templatesLoading,
    templatesError,
    currentTopologyName,
    setCurrentTopologyName,
    saveTopology,
    loadLatestTopology,
    loadTemplate,
    startSimulation,
    stopSimulation,
    runProbe,
    injectFault,
    exportTopology,
    exportReport,
    exportPdfReport,
    exportDocReport,
    importTopology,
  } = useTopology();
  useSimulationEvents(currentTopologyId);

  const activeTemplateId = useMemo(() => {
    if (templates.some(t => t.id === selectedTemplateId)) return selectedTemplateId;
    return templates[0]?.id ?? selectedTemplateId;
  }, [selectedTemplateId, templates]);

  // Default ping target: first IP on any directly-connected peer node's interface.
  const probeTargetIp = useMemo(() => {
    if (selectedElementType !== 'node' || !selectedElementId) return null;
    const peerEdge = edges.find(e => e.source === selectedElementId || e.target === selectedElementId);
    if (!peerEdge) return null;
    const peerId = peerEdge.source === selectedElementId ? peerEdge.target : peerEdge.source;
    const peerNode = nodes.find(n => n.id === peerId);
    return peerNode?.data.logicalConfig?.interfaces?.find(i => i.ip)?.ip ?? null;
  }, [edges, nodes, selectedElementId, selectedElementType]);

  // User-supplied override; resets whenever the node selection changes.
  useEffect(() => {
    setPingTargetIp('');
  }, [selectedElementId]);

  // Effective target: user override wins; falls back to auto-resolved peer IP.
  const effectivePingTarget = pingTargetIp.trim() || probeTargetIp;

  const selectedFaultLinkId = useMemo(() => {
    if (selectedElementType !== 'edge') return null;
    const selectedEdge = edges.find(edge => edge.id === selectedElementId);
    return selectedEdge?.data?.id ?? selectedElementId;
  }, [edges, selectedElementId, selectedElementType]);

  const canLoadTemplate = Boolean(activeTemplateId) && !templatesLoading && !templatesError;
  const canStartStop = Boolean(currentTopologyId);
  const canExport = Boolean(currentTopologyId);
  const canPing = selectedElementType === 'node' && Boolean(selectedElementId) && Boolean(effectivePingTarget) && canStartStop;
  const canInjectFault = Boolean(selectedFaultLinkId) && canStartStop;

  const workflowHint = (() => {
    if (templatesError) return templatesError;
    if (nodes.length === 0 && edges.length === 0) return 'Load a template or add devices to begin.';
    if (!currentTopologyId) return 'Save the topology before starting simulation, ping, or fault tests.';
    if (selectedElementType !== 'node' && selectedElementType !== 'edge') return 'Select a node to ping or a link to inject a fault.';
    if (selectedElementType === 'node' && !effectivePingTarget) return 'No connected node has an IP configured yet — or type a target IP in the ping bar below.';
    return null;
  })();

  const handleAddDevice = (type: NetworkNode['baseType']) => {
    const newNode = createNode(
      type,
      `${type}-${nodes.length + 1}`,
      { x: Math.random() * 200 + 100, y: Math.random() * 200 + 100 },
    );
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
          <input
            value={currentTopologyName}
            onChange={(event) => setCurrentTopologyName(event.target.value)}
            style={inputStyle}
            title="Topology name used for save and export"
            aria-label="Topology name"
          />
          <button onClick={() => handleAddDevice('router')} style={buttonStyle}>+ Router</button>
          <button onClick={() => handleAddDevice('switch')} style={buttonStyle}>+ Switch</button>
          <button onClick={() => handleAddDevice('cloud')} style={buttonStyle}>+ Cloud</button>
          <button onClick={() => handleAddDevice('host')} style={buttonStyle}>+ Host</button>
        </Panel>

        <Panel position="top-center" style={{ display: 'flex', gap: '8px', background: 'var(--panel-bg)', padding: '8px', borderRadius: '8px', border: '1px solid var(--panel-border)', backdropFilter: 'var(--panel-backdrop)' }}>
          <select
            value={activeTemplateId}
            onChange={(event) => setSelectedTemplateId(event.target.value)}
            style={selectStyle}
            title="Topology template"
          >
            {templates.map((template) => (
              <option key={template.id} value={template.id}>{template.name}</option>
            ))}
          </select>
          <button
            onClick={() => loadTemplate(activeTemplateId)}
            style={buttonStyle}
            disabled={!canLoadTemplate}
            title={
              templatesLoading
                ? 'Loading templates...'
                : templatesError ?? 'Load the selected topology template'
            }
          >
            {templatesLoading ? 'Loading...' : 'Load Template'}
          </button>
        </Panel>

        <Panel position="top-right" style={toolbarPanelStyle}>
          <ToolbarMenu
            label="Simulation"
            items={[
              {
                label: 'Start',
                onClick: startSimulation,
                disabled: !canStartStop,
                title: canStartStop ? 'Start the saved topology simulation' : 'Save the topology before starting simulation',
                variant: 'running',
              },
              {
                label: 'Stop',
                onClick: stopSimulation,
                disabled: !canStartStop,
                title: canStartStop ? 'Stop the saved topology simulation' : 'Save the topology before stopping simulation',
                variant: 'stopped',
              },
            ]}
          />
          <ToolbarMenu
            label="Test"
            items={[
              {
                label: 'Ping',
                onClick: () => selectedElementId && effectivePingTarget && runProbe(selectedElementId, effectivePingTarget),
                disabled: !canPing,
                title: !currentTopologyId
                  ? 'Save the topology before running a ping'
                  : selectedElementType !== 'node'
                    ? 'Select a node to run a ping'
                    : effectivePingTarget
                      ? `Ping ${effectivePingTarget} from the selected node`
                      : 'No target IP — connect a node with a configured IP or type one below',
              },
              {
                label: 'Fault',
                onClick: () => selectedFaultLinkId && injectFault(selectedFaultLinkId),
                disabled: !canInjectFault,
                title: !currentTopologyId
                  ? 'Save the topology before injecting a fault'
                  : selectedFaultLinkId
                    ? 'Inject a link-down fault on the selected edge'
                    : 'Select a link to inject a fault',
              },
            ]}
          />
          <ToolbarMenu
            label="Project"
            items={[
              {
                label: 'Save',
                onClick: saveTopology,
                title: 'Save the current topology',
                variant: 'primary',
              },
              {
                label: 'Load Latest',
                onClick: loadLatestTopology,
                title: 'Load the most recently saved topology',
              },
              {
                label: 'Import JSON',
                onClick: () => importInputRef.current?.click(),
                title: 'Import a .octet.json topology file',
              },
            ]}
          />
          <ToolbarMenu
            label="Export"
            items={[
              {
                label: 'JSON',
                onClick: exportTopology,
                disabled: !canExport,
                title: canExport ? 'Download this topology as .octet.json' : 'Save the topology before exporting JSON',
              },
              {
                label: 'Markdown Report',
                onClick: exportReport,
                disabled: !canExport,
                title: canExport ? 'Download this topology report as Markdown' : 'Save the topology before exporting a report',
              },
              {
                label: 'PDF Report',
                onClick: exportPdfReport,
                disabled: !canExport,
                title: canExport ? 'Download this topology report as PDF' : 'Save the topology before exporting a PDF report',
              },
              {
                label: 'DOC Report',
                onClick: exportDocReport,
                disabled: !canExport,
                title: canExport ? 'Download this topology report as DOC' : 'Save the topology before exporting a DOC report',
              },
            ]}
          />
          <input
            ref={importInputRef}
            type="file"
            accept=".json,.octet.json,application/json"
            style={{ display: 'none' }}
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void importTopology(file);
              event.target.value = '';
            }}
          />
        </Panel>

        {workflowHint && (
          <Panel position="bottom-left" style={hintStyle}>
            {workflowHint}
          </Panel>
        )}

        {selectedElementType === 'node' && currentTopologyId && (
          <Panel position="bottom-center" style={pingBarStyle}>
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
              Ping target:
            </span>
            <input
              type="text"
              value={pingTargetIp}
              onChange={e => setPingTargetIp(e.target.value.replace(/[^0-9.]/g, ''))}
              placeholder={probeTargetIp ?? '0.0.0.0'}
              style={pingInputStyle}
              aria-label="Ping target IP"
              onKeyDown={e => {
                if (e.key === 'Enter' && canPing && selectedElementId && effectivePingTarget) {
                  void runProbe(selectedElementId, effectivePingTarget);
                }
              }}
            />
            <button
              style={{
                ...buttonStyle,
                opacity: canPing ? 1 : 0.45,
                cursor: canPing ? 'pointer' : 'not-allowed',
              }}
              disabled={!canPing}
              onClick={() => selectedElementId && effectivePingTarget && runProbe(selectedElementId, effectivePingTarget)}
              title={canPing ? `Ping ${effectivePingTarget}` : 'No target IP configured'}
            >
              Ping ▶
            </button>
          </Panel>
        )}
      </ReactFlow>
      <PropertyPanel />
      <LogConsole />
    </div>
  );
};

const ToolbarMenu: React.FC<{ label: string; items: ToolbarMenuItem[] }> = ({ label, items }) => {
  const [open, setOpen] = useState(false);

  return (
    <div style={menuContainerStyle}>
      <button
        type="button"
        onClick={() => setOpen(isOpen => !isOpen)}
        style={buttonStyle}
        title={`${label} actions`}
        aria-haspopup="menu"
        aria-expanded={open}
      >
        {label} ▾
      </button>
      {open && (
        <div role="menu" style={menuStyle}>
          {items.map(item => (
            <button
              key={item.label}
              type="button"
              role="menuitem"
              onClick={() => {
                setOpen(false);
                item.onClick();
              }}
              disabled={item.disabled}
              title={item.title}
              style={{
                ...menuItemStyle,
                ...(item.variant === 'primary' ? primaryMenuItemStyle : {}),
                ...(item.variant === 'running' ? runningMenuItemStyle : {}),
                ...(item.variant === 'stopped' ? stoppedMenuItemStyle : {}),
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

const toolbarPanelStyle = {
  display: 'flex',
  gap: '8px',
  background: 'var(--panel-bg)',
  padding: '8px',
  borderRadius: '8px',
  border: '1px solid var(--panel-border)',
  backdropFilter: 'var(--panel-backdrop)',
  flexWrap: 'wrap' as const,
  justifyContent: 'flex-end'
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

const menuContainerStyle = {
  position: 'relative' as const
};

const menuStyle = {
  position: 'absolute' as const,
  right: 0,
  top: 'calc(100% + 6px)',
  display: 'flex',
  flexDirection: 'column' as const,
  gap: '4px',
  minWidth: '180px',
  background: 'var(--panel-bg)',
  border: '1px solid var(--panel-border)',
  borderRadius: '6px',
  padding: '6px',
  boxShadow: '0 12px 32px rgba(0, 0, 0, 0.22)',
  backdropFilter: 'var(--panel-backdrop)',
  zIndex: 20
};

const menuItemStyle = {
  ...buttonStyle,
  width: '100%',
  textAlign: 'left' as const,
  border: 'none',
  borderRadius: '4px'
};

const primaryMenuItemStyle = {
  background: 'var(--accent-blue)',
  color: 'white'
};

const runningMenuItemStyle = {
  background: 'var(--status-running)',
  color: 'white'
};

const stoppedMenuItemStyle = {
  background: 'var(--status-stopped)',
  color: 'white'
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

const inputStyle = {
  background: 'var(--input-bg)',
  border: '1px solid var(--button-border)',
  color: 'var(--text-primary)',
  padding: '6px 10px',
  borderRadius: '4px',
  fontSize: '13px',
  fontWeight: 500,
  width: '160px'
};

const hintStyle = {
  background: 'var(--panel-bg)',
  border: '1px solid var(--panel-border)',
  color: 'var(--text-secondary)',
  padding: '8px 10px',
  borderRadius: '6px',
  fontSize: '12px',
  backdropFilter: 'var(--panel-backdrop)'
};

const pingBarStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  background: 'var(--panel-bg)',
  padding: '8px 12px',
  borderRadius: '8px',
  border: '1px solid var(--panel-border)',
  backdropFilter: 'var(--panel-backdrop)',
};

const pingInputStyle = {
  ...inputStyle,
  width: '140px',
  fontFamily: 'monospace',
};
