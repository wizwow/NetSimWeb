import { useEffect, useRef } from 'react';
import { useTopologyStore, useSimulationStore } from '../store';

export const useSimulationEvents = (topologyId: string | null) => {
  const updateNodeStatus = useTopologyStore(s => s.updateNodeStatus);
  const addLog = useSimulationStore(s => s.addLog);

  // Stable refs for the WS callback — avoids stale closures on hot-reload.
  const updateNodeStatusRef = useRef(updateNodeStatus);
  const addLogRef = useRef(addLog);

  useEffect(() => { updateNodeStatusRef.current = updateNodeStatus; }, [updateNodeStatus]);
  useEffect(() => { addLogRef.current = addLog; }, [addLog]);

  useEffect(() => {
    if (!topologyId) return;

    const wsUrl = `${import.meta.env.VITE_WS_URL}/events/${topologyId}`;
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      addLogRef.current('WebSocket connected', 'info', 'ws');
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as Record<string, unknown>;

        switch (data.type) {
          case 'NODE_STATUS_CHANGED': {
            const nodeId = data.nodeId as string;
            const status = data.status as Parameters<typeof updateNodeStatus>[1];
            updateNodeStatusRef.current(nodeId, status);
            addLogRef.current(
              `Node ${nodeId} → ${status}`,
              status === 'error' ? 'error' : 'info',
              'engine',
            );
            break;
          }
          case 'LINK_FAULT_INJECTED':
            addLogRef.current(
              `Fault injected on link ${data.linkId}: ${data.faultType}`,
              'warn',
              'engine',
            );
            break;
          case 'OSPF_ADJACENCY_CHANGED':
            addLogRef.current(
              `OSPF adj ${data.nodeId}↔${data.neighborId}: ${data.state}`,
              'info',
              'engine',
            );
            break;
          case 'PROBE_RESULT':
            addLogRef.current(
              `Probe ${data.probeId}: ${(data.result as any)?.output ?? ''}`,
              'info',
              'engine',
            );
            break;
          default:
            break;
        }
      } catch (err) {
        console.error('Error parsing WebSocket message', err);
      }
    };

    socket.onclose = () => {
      addLogRef.current('WebSocket disconnected', 'warn', 'ws');
    };

    socket.onerror = () => {
      addLogRef.current('WebSocket error', 'error', 'ws');
    };

    return () => {
      socket.close();
    };
  }, [topologyId]);
};
