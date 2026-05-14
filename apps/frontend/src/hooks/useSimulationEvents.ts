import { useEffect } from 'react';
import { useTopologyStore } from '../store';

export const useSimulationEvents = (topologyId: string | null) => {
  const { updateNodeStatus, addLog } = useTopologyStore();

  useEffect(() => {
    if (!topologyId) return;

    const wsUrl = `${import.meta.env.VITE_WS_URL}/events/${topologyId}`;
    
    console.log(`Connecting to WebSocket: ${wsUrl}`);
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      console.log('WebSocket Connected');
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("WebSocket event received:", data);
        
        // Gestione eventi di cambio stato nodi
        if (data.type === 'NODE_STATUS_CHANGED') {
          updateNodeStatus(data.node_id, data.status);
          addLog(`Node ${data.node_id} is now ${data.status}`, data.status === 'error' ? 'error' : 'info', 'system');
        }
        
        // Gestione avvio/stop globale
        if (data.type === 'SIMULATION_STARTED') {
          addLog('Simulation started successfully', 'info', 'engine');
        }

        if (data.type === 'SIMULATION_STOPPED') {
          addLog('Simulation stopped', 'warn', 'engine');
        }

        // Gestione log generici dall'engine
        if (data.type === 'SIMULATION_LOG') {
          addLog(data.message, data.level || 'info', data.source || 'node');
        }
      } catch (err) {
        console.error("Error parsing WebSocket message", err);
      }
    };

    socket.onclose = () => {
      console.log('WebSocket Disconnected');
    };

    socket.onerror = (error) => {
      console.error('WebSocket Error:', error);
    };

    return () => {
      socket.close();
    };
  }, [topologyId, updateNodeStatus]);
};
