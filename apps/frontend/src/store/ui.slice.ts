import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';

export type ThemeMode = 'light' | 'dark';

interface UiState {
  theme: ThemeMode;
  toggleTheme: () => void;
  propertyPanelOpen: boolean;
  consoleOpen: boolean;
  selectedElementId: string | null;
  selectedElementType: 'node' | 'edge' | null;
  setSelectedElement: (id: string | null, type: 'node' | 'edge' | null) => void;
  closePropertyPanel: () => void;
  toggleConsole: () => void;
}

export const useUiStore = create<UiState>()(
  immer((set) => ({
    theme: 'dark',
    toggleTheme: () => set((state) => {
      state.theme = state.theme === 'dark' ? 'light' : 'dark';
    }),
    propertyPanelOpen: false,
    consoleOpen: false,
    selectedElementId: null,
    selectedElementType: null,
    setSelectedElement: (id, type) => set((state) => {
      state.selectedElementId = id;
      state.selectedElementType = type;
      state.propertyPanelOpen = !!id;
    }),
    closePropertyPanel: () => set((state) => {
      state.propertyPanelOpen = false;
      state.selectedElementId = null;
      state.selectedElementType = null;
    }),
    toggleConsole: () => set((state) => {
      state.consoleOpen = !state.consoleOpen;
    })
  }))
);
