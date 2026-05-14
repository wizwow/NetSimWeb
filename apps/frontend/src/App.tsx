import React, { useEffect } from 'react';
import { TopologyCanvas } from './canvas/TopologyCanvas';
import { ReactFlowProvider } from '@xyflow/react';
import { useUiStore } from './store';
import { Sun, Moon } from 'lucide-react';

function App() {
  const { theme, toggleTheme } = useUiStore();

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  return (
    <div style={{ width: '100vw', height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <div style={{ height: '50px', background: 'var(--bg-canvas)', borderBottom: '1px solid var(--panel-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 20px', fontWeight: 600 }}>
        <span>NetSim-Flow</span>
        <button 
          onClick={toggleTheme}
          style={{ 
            background: 'var(--button-bg)', 
            border: '1px solid var(--button-border)', 
            color: 'var(--text-primary)', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            padding: '6px', 
            borderRadius: '6px', 
            cursor: 'pointer' 
          }}
        >
          {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
        </button>
      </div>
      <div style={{ flex: 1, position: 'relative' }}>
        <ReactFlowProvider>
          <TopologyCanvas />
        </ReactFlowProvider>
      </div>
    </div>
  );
}

export default App;
