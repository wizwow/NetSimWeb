import { useState, useEffect, useMemo } from 'react';
import { useTopologyStore, useUiStore } from '../store';
import type { NetworkNode, NetworkLink } from '@netsimflow/shared-types';
import './PropertyPanel.css';

export const PropertyPanel: React.FC = () => {
  const { propertyPanelOpen, selectedElementId, selectedElementType, closePropertyPanel } = useUiStore();
  const { nodes, edges, updateNode, updateNodeInterface } = useTopologyStore();

  const selectedNode = selectedElementType === 'node'
    ? nodes.find(n => n.id === selectedElementId) ?? null
    : null;
  const selectedEdge = selectedElementType === 'edge'
    ? edges.find(e => e.id === selectedElementId) ?? null
    : null;
  const edgeData = selectedEdge?.data as NetworkLink | undefined;

  // ── Node field local state ─────────────────────────────────────────────────
  const [label, setLabel] = useState('');
  const [loopback, setLoopback] = useState('');
  // Map of ifaceName → { ip, subnet } for all interfaces on the selected node
  const [ifaceEdits, setIfaceEdits] = useState<Record<string, { ip: string; subnet: string }>>({});

  // Re-initialise only when the selected element changes (not on every store update)
  useEffect(() => {
    if (selectedNode) {
      const data = selectedNode.data as NetworkNode;
      setLabel(data.label);
      setLoopback(data.logicalConfig?.loopback ?? '');
      const edits: Record<string, { ip: string; subnet: string }> = {};
      for (const iface of data.logicalConfig?.interfaces ?? []) {
        edits[iface.name] = { ip: iface.ip ?? '', subnet: iface.subnet ?? '' };
      }
      setIfaceEdits(edits);
    }
  }, [selectedElementId]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Interface peer lookup ──────────────────────────────────────────────────
  // Maps interface name → "PeerLabel:peerPort" for connected interfaces
  const peerByIface = useMemo(() => {
    if (!selectedNode) return {} as Record<string, string>;
    const map: Record<string, string> = {};
    for (const edge of edges) {
      const d = edge.data as NetworkLink | undefined;
      if (!d) continue;
      if (edge.source === selectedNode.id) {
        const peer = nodes.find(n => n.id === edge.target);
        const peerLabel = (peer?.data as NetworkNode | undefined)?.label ?? d.targetNodeId;
        map[d.sourcePort] = `${peerLabel} : ${d.targetPort}`;
      } else if (edge.target === selectedNode.id) {
        const peer = nodes.find(n => n.id === edge.source);
        const peerLabel = (peer?.data as NetworkNode | undefined)?.label ?? d.sourceNodeId;
        map[d.targetPort] = `${peerLabel} : ${d.sourcePort}`;
      }
    }
    return map;
  }, [selectedNode, edges, nodes]);

  // ── Save helpers ───────────────────────────────────────────────────────────
  const saveNodeMeta = () => {
    if (!selectedElementId || !selectedNode) return;
    const data = selectedNode.data as NetworkNode;
    updateNode(selectedElementId, {
      label,
      logicalConfig: {
        ...data.logicalConfig,
        interfaces: data.logicalConfig?.interfaces ?? [],
        loopback: loopback || undefined,
      },
    });
  };

  const saveIface = (ifaceName: string) => {
    if (!selectedElementId) return;
    const edits = ifaceEdits[ifaceName];
    if (!edits) return;
    updateNodeInterface(selectedElementId, ifaceName, { ip: edits.ip, subnet: edits.subnet });
  };

  if (!propertyPanelOpen) return null;

  const nodeData = selectedNode?.data as NetworkNode | undefined;
  const ifaces = nodeData?.logicalConfig?.interfaces ?? [];

  // Peer nodes for edge panel
  const sourceNode = edgeData ? nodes.find(n => n.id === edgeData.sourceNodeId) : null;
  const targetNode = edgeData ? nodes.find(n => n.id === edgeData.targetNodeId) : null;

  return (
    <div className={`property-panel ${propertyPanelOpen ? 'open' : ''}`}>
      <div className="property-panel-header">
        <h3>Properties</h3>
        <button onClick={closePropertyPanel} className="close-btn">×</button>
      </div>

      <div className="property-panel-content">

        {/* ── NODE PANEL ────────────────────────────────────────────────── */}
        {selectedNode && nodeData && (
          <>
            <div className="property-group">
              <label>Label</label>
              <input
                type="text"
                value={label}
                onChange={e => setLabel(e.target.value)}
                onBlur={saveNodeMeta}
              />

              <label>Type</label>
              <span className="badge">{nodeData.baseType}</span>

              <label>Loopback IP</label>
              <input
                type="text"
                value={loopback}
                onChange={e => setLoopback(e.target.value)}
                onBlur={saveNodeMeta}
                placeholder="e.g. 10.255.0.1"
              />
            </div>

            {/* ── Interface table ──────────────────────────────────────── */}
            {ifaces.length > 0 && (
              <div className="iface-section">
                <div className="iface-section-title">
                  Interfaces
                  <span className="iface-count">
                    {ifaces.filter(i => i.status === 'up').length}/{ifaces.length} connected
                  </span>
                </div>

                {ifaces.map(iface => {
                  const edits = ifaceEdits[iface.name] ?? { ip: '', subnet: '' };
                  const peer = peerByIface[iface.name];
                  return (
                    <div key={iface.name} className="iface-row">
                      <div className="iface-row-header">
                        <span className="iface-name">{iface.name}</span>
                        <span className={`iface-status ${iface.status}`}>
                          {iface.status}
                        </span>
                        {peer && (
                          <span className="iface-peer" title="Connected to">
                            → {peer}
                          </span>
                        )}
                      </div>
                      <div className="iface-ip-row">
                        <div className="iface-field">
                          <span className="iface-field-label">IP</span>
                          <input
                            type="text"
                            className="iface-input"
                            value={edits.ip}
                            placeholder="—"
                            onChange={e => setIfaceEdits(prev => ({
                              ...prev,
                              [iface.name]: { ...prev[iface.name], ip: e.target.value },
                            }))}
                            onBlur={() => saveIface(iface.name)}
                          />
                        </div>
                        <div className="iface-field">
                          <span className="iface-field-label">Mask</span>
                          <input
                            type="text"
                            className="iface-input iface-input--mask"
                            value={edits.subnet}
                            placeholder="/—"
                            onChange={e => setIfaceEdits(prev => ({
                              ...prev,
                              [iface.name]: { ...prev[iface.name], subnet: e.target.value },
                            }))}
                            onBlur={() => saveIface(iface.name)}
                          />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            <div className="status-section">
              <label>Node Status</label>
              <div className={`status-indicator ${nodeData.runtimeState?.status ?? 'stopped'}`}>
                {nodeData.runtimeState?.status ?? 'stopped'}
              </div>
            </div>
          </>
        )}

        {/* ── EDGE PANEL ────────────────────────────────────────────────── */}
        {edgeData && (
          <div className="property-group">
            <label>Link Type</label>
            <span className="badge">{edgeData.linkType}</span>

            <label>Source</label>
            <div className="link-info" title={`ID: ${edgeData.sourceNodeId}`}>
              <span>{(sourceNode?.data as NetworkNode | undefined)?.label ?? edgeData.sourceNodeId}</span>
              <span className="badge">{edgeData.sourcePort}</span>
            </div>

            <label>Target</label>
            <div className="link-info" title={`ID: ${edgeData.targetNodeId}`}>
              <span>{(targetNode?.data as NetworkNode | undefined)?.label ?? edgeData.targetNodeId}</span>
              <span className="badge">{edgeData.targetPort}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
