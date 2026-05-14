import React, { useState, useEffect } from 'react';
import { useTopologyStore, useUiStore } from '../store';
import './PropertyPanel.css';

export const PropertyPanel: React.FC = () => {
  const { propertyPanelOpen, selectedElementId, selectedElementType, setSelectedElement, closePropertyPanel } = useUiStore();
  const { nodes, edges, updateNode, updateEdge } = useTopologyStore();

  const [label, setLabel] = useState('');
  const [loopback, setLoopback] = useState('');
  const [subnet, setSubnet] = useState('');

  const selectedNode = selectedElementType === 'node' ? nodes.find(n => n.id === selectedElementId) : null;
  const selectedEdge = selectedElementType === 'edge' ? edges.find(e => e.id === selectedElementId) : null;

  const sourceNode = selectedEdge ? nodes.find(n => n.id === selectedEdge.data.sourceNodeId) : null;
  const targetNode = selectedEdge ? nodes.find(n => n.id === selectedEdge.data.targetNodeId) : null;

  useEffect(() => {
    if (selectedNode) {
      setLabel(selectedNode.data.label);
      setLoopback(selectedNode.data.logicalConfig?.loopback || '');
    } else if (selectedEdge) {
      setSubnet(selectedEdge.data.ipConfig?.subnet || '');
    }
  }, [selectedNode, selectedEdge]);

  if (!propertyPanelOpen) return null;

  const handleSaveNode = () => {
    if (selectedElementId) {
      updateNode(selectedElementId, {
        label,
        logicalConfig: {
          ...selectedNode?.data.logicalConfig,
          loopback
        }
      });
    }
  };

  const handleSaveEdge = () => {
    if (selectedElementId) {
      updateEdge(selectedElementId, {
        ipConfig: {
          ...selectedEdge?.data.ipConfig,
          subnet
        }
      });
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
            <span className="badge">{selectedNode.data.baseType}</span>

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
              <div className={`status-indicator ${selectedNode.data.runtimeState?.status || 'stopped'}`}>
                {selectedNode.data.runtimeState?.status || 'stopped'}
              </div>
            </div>
          </div>
        )}

        {selectedEdge && (
          <div className="property-group">
            <label>Link ID</label>
            <input type="text" value={selectedEdge.id} disabled />

            <label>Subnet</label>
            <input 
              type="text" 
              value={subnet} 
              onChange={(e) => setSubnet(e.target.value)} 
              onBlur={handleSaveEdge}
              placeholder="e.g. 10.0.0.0/30"
            />

            <label>Source</label>
            <div className="link-info" title={`ID: ${selectedEdge.data.sourceNodeId}`}>
              <span>{sourceNode?.data.label || selectedEdge.data.sourceNodeId}</span>
              <span className="badge">{selectedEdge.data.sourcePort}</span>
            </div>

            <label>Target</label>
            <div className="link-info" title={`ID: ${selectedEdge.data.targetNodeId}`}>
              <span>{targetNode?.data.label || selectedEdge.data.targetNodeId}</span>
              <span className="badge">{selectedEdge.data.targetPort}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
