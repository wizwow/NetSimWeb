import React, { useRef, useEffect } from 'react';
import { useTopologyStore, useUiStore } from '../store';
import './LogConsole.css';

export const LogConsole: React.FC = () => {
  const { logs, clearLogs } = useTopologyStore();
  const { consoleOpen, toggleConsole } = useUiStore();
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  if (!consoleOpen) {
    return (
      <button className="console-trigger" onClick={toggleConsole}>
        <span>Terminal</span>
      </button>
    );
  }

  return (
    <div className="log-console">
      <div className="log-console-header">
        <div className="log-console-tabs">
          <div className="tab active">Console</div>
          <div className="tab">Simulation Output</div>
        </div>
        <div className="log-console-actions">
          <button onClick={clearLogs} title="Clear Logs">🗑️</button>
          <button onClick={toggleConsole} title="Close Console">×</button>
        </div>
      </div>
      
      <div className="log-console-content" ref={scrollRef}>
        {logs.length === 0 && (
          <div className="log-empty">No simulation logs. Start the topology to see events.</div>
        )}
        {logs.map((log) => (
          <div key={log.id} className={`log-entry ${log.level}`}>
            <span className="log-time">[{log.timestamp}]</span>
            {log.source && <span className="log-source">[{log.source.toUpperCase()}]</span>}
            <span className="log-message">{log.message}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
