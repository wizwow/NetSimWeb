import React, { useState } from 'react';
import { useTopologyStore, useUiStore } from '../store';
import type { NetworkNode, NetworkLink } from '@octet/shared-types';
import './TopologyObjectsPanel.css';

const BASE_TYPE_ICON: Record<string, string> = {
  router:   '⌘',
  switch:   '⊟',
  host:     '□',
  cloud:    '☁',
  firewall: '⚡',
  site:     '◎',
};

const STATUS_COLOR: Record<string, string> = {
  running:  '#4caf50',
  stopped:  '#9e9e9e',
  booting:  '#ff9800',
  error:    '#f44336',
  degraded: '#ff5722',
};

export const TopologyObjectsPanel: React.FC = () => {
  const { topologyPanelOpen, toggleTopologyPanel, selectedElementId, setSelectedElement } = useUiStore();
  const { nodes, edges } = useTopologyStore();
  const [linksExpanded, setLinksExpanded] = useState(false);

  return (
    <div className={`topology-panel ${topologyPanelOpen ? 'open' : ''}`}>
      <div className="topology-panel-header">
        <h3>Objects</h3>
        <button className="close-btn" onClick={toggleTopologyPanel}>×</button>
      </div>

      <div className="topology-panel-content">

        {/* ── Nodes section ──────────────────────────────────────────── */}
        <div className="topo-section-title">
          Nodes
          <span className="topo-count">{nodes.length}</span>
        </div>

        {nodes.length === 0 && (
          <div className="topo-empty">No nodes yet. Add devices from the toolbar.</div>
        )}

        {nodes.map(node => {
          const data = node.data as NetworkNode;
          const status = data.runtimeState?.status ?? 'stopped';
          const isSelected = selectedElementId === node.id;
          return (
            <button
              key={node.id}
              className={`topo-row ${isSelected ? 'selected' : ''}`}
              onClick={() => setSelectedElement(node.id, 'node')}
              title={`${data.label} (${data.baseType})`}
            >
              <span className="topo-row-icon">{BASE_TYPE_ICON[data.baseType] ?? '□'}</span>
              <span className="topo-row-label">{data.label}</span>
              <span className="topo-row-badge">{data.baseType}</span>
              <span
                className="topo-row-status"
                style={{ background: STATUS_COLOR[status] ?? STATUS_COLOR.stopped }}
                title={`Status: ${status}`}
              />
            </button>
          );
        })}

        {/* ── Links section (collapsible) ────────────────────────────── */}
        {edges.length > 0 && (
          <>
            <button
              className="topo-section-title topo-section-toggle"
              onClick={() => setLinksExpanded(e => !e)}
            >
              Links
              <span className="topo-count">{edges.length}</span>
              <span className="topo-chevron">{linksExpanded ? '▴' : '▾'}</span>
            </button>

            {linksExpanded && edges.map(edge => {
              const d = edge.data as NetworkLink | undefined;
              if (!d) return null;
              const srcNode = nodes.find(n => n.id === edge.source);
              const tgtNode = nodes.find(n => n.id === edge.target);
              const srcLabel = (srcNode?.data as NetworkNode | undefined)?.label ?? edge.source;
              const tgtLabel = (tgtNode?.data as NetworkNode | undefined)?.label ?? edge.target;
              const isSelected = selectedElementId === edge.id;
              const faulted = Boolean(d.faultState?.active);
              return (
                <button
                  key={edge.id}
                  className={`topo-row ${isSelected ? 'selected' : ''} ${faulted ? 'faulted' : ''}`}
                  onClick={() => setSelectedElement(edge.id, 'edge')}
                  title={`${srcLabel}:${d.sourcePort} ↔ ${tgtLabel}:${d.targetPort}`}
                >
                  <span className="topo-row-icon">↔</span>
                  <span className="topo-row-label topo-row-label--link">
                    <span>{srcLabel}</span>
                    <span className="topo-row-port">{d.sourcePort}</span>
                    <span className="topo-row-arrow">→</span>
                    <span>{tgtLabel}</span>
                    <span className="topo-row-port">{d.targetPort}</span>
                  </span>
                  {faulted && <span className="topo-fault-badge">FAULT</span>}
                </button>
              );
            })}
          </>
        )}

      </div>
    </div>
  );
};
