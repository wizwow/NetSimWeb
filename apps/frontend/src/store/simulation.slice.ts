import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import { v4 as uuidv4 } from 'uuid';

export interface LogEntry {
  id: string;
  timestamp: string;
  level: 'info' | 'warn' | 'error';
  message: string;
  source?: string;
}

interface SimulationState {
  status: 'idle' | 'running' | 'stopped' | 'error';
  logs: LogEntry[];
  activeProbes: string[];

  // Actions
  setStatus: (status: SimulationState['status']) => void;
  addLog: (message: string, level?: LogEntry['level'], source?: string) => void;
  clearLogs: () => void;
}

export const useSimulationStore = create<SimulationState>()(
  immer((set) => ({
    status: 'idle',
    logs: [],
    activeProbes: [],

    setStatus: (status) => set((state) => {
      state.status = status;
    }),

    addLog: (message, level = 'info', source) => set((state) => {
      state.logs.push({
        id: uuidv4(),
        timestamp: new Date().toLocaleTimeString(),
        level,
        message,
        source,
      });
      if (state.logs.length > 100) state.logs.shift();
    }),

    clearLogs: () => set((state) => {
      state.logs = [];
    }),
  })),
);
