import { useState, useEffect } from 'react';
import { useTopologyStore, useUiStore } from '../store';
import type { NetworkNode, NetworkLink } from '@netsimflow/shared-types';
import './PropertyPanel.css';

export const PropertyPanel: React.FC = () => {
  const { propertyPanelOpen, selectedElementId, selectedElementType, closePropertyPanel } = useUiStore();
  const { nodes, edges, updateNode, updateEdge } = useTopologyStore();

  const [label, setLabel] = useState('');
  const [loopback, setLoopback] = useState('');
  const [subnet, setSubnet] = useState('');

  const selectedNode = selectedElementType === 'node' ? nodes.find(n => n.id === selectedElementId) : null;
  const selectedEdge = selectedElementType === 'edge' ? edges.find(e => e.id === selectedElementId) : null;

  const edgeData = selectedEdge?.data as NetworkLink | undefined;
  const sourceNode = edgeData ? nodes.find(n => n.id === edgeData.sourceNodeId) : null;
  const targetNode = edgeData ? nodes.find(n => n.id === edgeData.targetNodeId) : null;

  useEffect(() => {
    let active = true;
    queueMicrotask(() => {
      if (!active) return;
      if (selectedNode) {
        setLabel(selectedNode.data.label);
        setLoopback((selectedNode.data as NetworkNode).logicalConfig?.loopback || '');
      } else if (edgeData) {
        setSubnet(edgeData.ipConfig?.subnet || '');
      }
    });
    return () => {
      active = false;
    };
  }, [selectedNode, edgeData]);

  if (!propertyPanelOpen) return null;

  const handleSaveNode = () => {
    if (selectedElementId && selectedNode) {
      const nodeData = selectedNode.data as NetworkNode;
      updateNode(selectedElementId, {
        label,
        logicalConfig: {
          ...nodeData.logicalConfig,
          interfaces: nodeData.logicalConfig?.interfaces ?? [],
          loopback,
        },
      });
    }
  };

  const handleSaveEdge = () => {
    if (selectedElementId && edgeData) {
      updateEdge(selectedElementId, {
        ipConfig: {
          ...edgeData.ipConfig,
          subnet,
        },
      } as Partial<NetworkLink>);
    }
  };

  return (
    <div className={`property-panel ${propertyPanelOpen ? 'open' : ''}`}>
      <div className="property-panel-header">
        <h3>Properties</h3>
        <button onClick={closePropertyPanel} className="close-btn">×</button>
      </div>

      <div className="property-panel-content">
        {selectedNode && (
          <div className="property-group">
            <label>Node ID</label>
            <input type="text" value={selectedNode.id} disabled />

            <label>Label</label>
            <input
              type="text"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              onBlur={handleSaveNode}
            />

            <label>Type</label>
            <span className="badge">{(selectedNode.data as NetworkNode).baseType}</span>

            <label>Loopback IP</label>
            <input
              type="text"
              value={loopback}
              onChange={(e) => setLoopback(e.target.value)}
              onBlur={handleSaveNode}
              placeholder="e.g. 10.255.0.1"
            />

            <div className="status-section">
              <label>Status</label>
              <div className={`status-indicator ${(selectedNode.data as NetworkNode).runtimeState?.status || 'stopped'}`}>
                {(selectedNode.data as NetworkNode).runtimeState?.status || 'stopped'}
              </div>
            </div>
          </div>
        )}

        {edgeData && (
          <div className="property-group">
            <label>Link ID</label>
            <input type="text" value={selectedEdge!.id} disabled />

            <label>Subnet</label>
            <input
              type="text"
              value={subnet}
              onChange={(e) => setSubnet(e.target.value)}
              onBlur={handleSaveEdge}
              placeholder="e.g. 10.0.0.0/30"
            />

            <label>Source</label>
            <div className="link-info" title={`ID: ${edgeData.sourceNodeId}`}>
              <span>{(sourceNode?.data as NetworkNode | undefined)?.label || edgeData.sourceNodeId}</span>
              <span className="badge">{edgeData.sourcePort}</span>
            </div>

            <label>Target</label>
            <div className="link-info" title={`ID: ${edgeData.targetNodeId}`}>
              <span>{(targetNode?.data as NetworkNode | undefined)?.label || edgeData.targetNodeId}</span>
              <span className="badge">{edgeData.targetPort}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
