import React, { useRef, useEffect, useState } from 'react';
import { useSimulationStore, useUiStore } from '../store';
import './LogConsole.css';

export const LogConsole: React.FC = () => {
  const { logs, clearLogs } = useSimulationStore();
  const { consoleOpen, toggleConsole } = useUiStore();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [filterText, setFilterText] = useState('');

  // Auto-scroll to bottom when new logs arrive (only when no filter active)
  useEffect(() => {
    if (!filterText && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, filterText]);

  if (!consoleOpen) {
    return (
      <button className="console-trigger" onClick={toggleConsole}>
        <span>Terminal</span>
      </button>
    );
  }

  const needle = filterText.toLowerCase();
  const visibleLogs = filterText
    ? logs.filter(l =>
        l.message.toLowerCase().includes(needle) ||
        (l.source ?? '').toLowerCase().includes(needle),
      )
    : logs;

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

      <div className="log-console-filter">
        <input
          className="log-filter-input"
          type="text"
          placeholder="Filter logs…"
          value={filterText}
          onChange={e => setFilterText(e.target.value)}
          aria-label="Filter log messages"
        />
        {filterText && (
          <button
            className="log-filter-clear"
            onClick={() => setFilterText('')}
            title="Clear filter"
          >
            ×
          </button>
        )}
        {filterText && (
          <span className="log-filter-count">
            {visibleLogs.length}/{logs.length}
          </span>
        )}
      </div>

      <div className="log-console-content" ref={scrollRef}>
        {visibleLogs.length === 0 && (
          <div className="log-empty">
            {filterText ? `No logs matching "${filterText}".` : 'No simulation logs. Start the topology to see events.'}
          </div>
        )}
        {visibleLogs.map((log) => (
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
