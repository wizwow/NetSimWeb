import { useCallback } from 'react';
import { api } from '../services/api';
import { useTopologyStore } from '../store';
import { useSimulationStore } from '../store/simulation.slice';

/**
 * Provides fault-injection actions that can be called from any component.
 * Extracted from useTopology so non-canvas components (e.g. PropertyPanel)
 * can trigger faults without pulling in the full topology hook.
 */
export const useFault = () => {
  const currentTopologyId = useTopologyStore(s => s.currentTopologyId);
  const updateEdgeFault = useTopologyStore(s => s.updateEdgeFault);
  const addLog = useSimulationStore(s => s.addLog);

  const injectFault = useCallback(async (linkId: string) => {
    if (!currentTopologyId) {
      addLog('Save the topology before injecting a fault', 'warn', 'fault');
      return;
    }
    try {
      await api.injectFault(currentTopologyId, { linkId, faultType: 'link-down' });
      updateEdgeFault(linkId, {
        active: true,
        type: 'link-down',
        triggeredAt: new Date().toISOString(),
      });
      addLog(`Link fault injected on ${linkId}: link-down`, 'warn', 'fault');
    } catch (err) {
      addLog('Fault injection failed', 'error', 'fault');
    }
  }, [currentTopologyId, updateEdgeFault, addLog]);

  return { injectFault };
};
