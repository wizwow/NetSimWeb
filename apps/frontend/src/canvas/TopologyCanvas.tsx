import React, { useMemo, useRef, useState, useCallback, useEffect } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  ConnectionMode,
  useReactFlow,
} from '@xyflow/react';
import type { Connection } from '@xyflow/react';
import { v4 as uuidv4 } from 'uuid';
import type { NetworkNode, NetworkLink } from '@netsimflow/shared-types';
import {
  Router, Network, Cloud, Monitor, Shield,
  Sun, Moon, LogOut, Save, Zap, Play, Square,
  ChevronDown, X, Trash2, Copy, Search,
  MousePointer, Hand, Maximize2,
  TerminalSquare,
} from 'lucide-react';
import { useTopologyStore, useUiStore, useSimulationStore } from '../store';
import type { ReactFlowNode, ReactFlowEdge } from './graphHelpers';
import type { LogEntry } from '../store/simulation.slice';
import type { TemplateSummary } from '../services/api';
import type { CurrentUser } from '../services/api';
import { nodeTypes } from './nodeTypes';
import { SimulatedEdge } from './edges/SimulatedEdge';
import { useSimulationEvents } from '../hooks/useSimulationEvents';
import { useTopology } from '../hooks/useTopology';
import './TopologyCanvas.css';

const edgeTypes = { simulatedEdge: SimulatedEdge };

// ─── Helper: node color by kind ───────────────────────────────────────────────
function devColor(kind: string): string {
  switch (kind) {
    case 'router': return 'var(--dev-router)';
    case 'switch': return 'var(--dev-switch)';
    case 'cloud':  return 'var(--dev-cloud)';
    case 'host':   return 'var(--dev-host)';
    case 'firewall': return 'var(--dev-firewall)';
    default: return 'var(--text-3)';
  }
}

function devBg(kind: string): string {
  switch (kind) {
    case 'router': return 'var(--dev-router-bg)';
    case 'switch': return 'var(--dev-switch-bg)';
    case 'cloud':  return 'var(--dev-cloud-bg)';
    case 'host':   return 'var(--dev-host-bg)';
    case 'firewall': return 'var(--dev-firewall-bg)';
    default: return 'var(--surface-3)';
  }
}

function DevIcon({ kind, size = 18 }: { kind: string; size?: number }) {
  const color = devColor(kind);
  switch (kind) {
    case 'router':   return <Router size={size} color={color} />;
    case 'switch':   return <Network size={size} color={color} />;
    case 'cloud':    return <Cloud size={size} color={color} />;
    case 'host':     return <Monitor size={size} color={color} />;
    case 'firewall': return <Shield size={size} color={color} />;
    default:         return <Router size={size} color={color} />;
  }
}

// ─── BrandMark ────────────────────────────────────────────────────────────────
const BrandMark: React.FC = () => (
  <div className="brand-mark" aria-hidden="true">
    <span></span>
    <span className="accent"></span>
    <span></span>
    <span></span>
  </div>
);

// ─── TopBar ───────────────────────────────────────────────────────────────────
interface TopBarProps {
  user: CurrentUser;
  onLogout: () => void;
  currentTopologyName: string;
  setCurrentTopologyName: (n: string) => void;
  simStatus: 'idle' | 'running' | 'stopped' | 'error';
  canStartStop: boolean;
  canExport: boolean;
  canRunAutoIp: boolean;
  onSave: () => void;
  onStart: () => void;
  onStop: () => void;
  onAutoIp: () => void;
  onImportClick: () => void;
  onLoadLatest: () => void;
  onExportJson: () => void;
  onExportReport: () => void;
  onExportPdf: () => void;
  onExportDoc: () => void;
  theme: string;
  onToggleTheme: () => void;
}

const TopBar: React.FC<TopBarProps> = ({
  user, onLogout,
  currentTopologyName, setCurrentTopologyName,
  simStatus, canStartStop, canExport, canRunAutoIp,
  onSave, onStart, onStop, onAutoIp, onImportClick, onLoadLatest,
  onExportJson, onExportReport, onExportPdf, onExportDoc,
  theme, onToggleTheme,
}) => {
  const [exportOpen, setExportOpen] = useState(false);
  const [projectOpen, setProjectOpen] = useState(false);
  const exportRef = useRef<HTMLDivElement>(null);
  const projectRef = useRef<HTMLDivElement>(null);

  // Close dropdowns on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (exportRef.current && !exportRef.current.contains(e.target as Node)) setExportOpen(false);
      if (projectRef.current && !projectRef.current.contains(e.target as Node)) setProjectOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const isRunning = simStatus === 'running';

  return (
    <header className="topbar">
      <div className="topbar-brand">
        <BrandMark />
        <span className="brand-name">octet.</span>
      </div>
      <div className="topbar-sep" />

      {/* Topology name */}
      <input
        className="crumb-input"
        value={currentTopologyName}
        onChange={e => setCurrentTopologyName(e.target.value)}
        aria-label="Topology name"
        title="Topology name"
      />

      {/* Sim pill */}
      <div className={`sim-pill ${isRunning ? 'running' : ''}`}>
        <span className="sim-pill-dot" />
        {isRunning ? 'Simulation running' : 'Simulation idle'}
      </div>

      <div className="topbar-sep" />

      {/* Start / Stop */}
      {isRunning ? (
        <button
          className="btn btn-danger"
          onClick={onStop}
          disabled={!canStartStop}
          title="Stop the running simulation"
        >
          <Square size={13} />
          Stop
        </button>
      ) : (
        <button
          className="btn btn-primary"
          onClick={onStart}
          disabled={!canStartStop}
          title={canStartStop ? 'Start the saved topology simulation' : 'Save the topology first'}
        >
          <Play size={13} />
          Start
        </button>
      )}

      {/* Auto-IP */}
      <button
        className="btn"
        onClick={onAutoIp}
        disabled={!canRunAutoIp}
        title={canRunAutoIp ? 'Assign missing loopbacks and link subnets' : 'Add devices first'}
      >
        <Zap size={13} />
        Auto-IP
      </button>

      {/* Project dropdown */}
      <div className="dropdown-wrap" ref={projectRef}>
        <button
          className="btn"
          onClick={() => setProjectOpen(o => !o)}
          aria-haspopup="menu"
          aria-expanded={projectOpen}
        >
          Project <ChevronDown size={12} />
        </button>
        {projectOpen && (
          <div className="dropdown-menu" role="menu">
            <button className="dropdown-item" onClick={() => { setProjectOpen(false); onSave(); }}>
              Save topology
            </button>
            <button className="dropdown-item" onClick={() => { setProjectOpen(false); onLoadLatest(); }}>
              Load latest
            </button>
            <button className="dropdown-item" onClick={() => { setProjectOpen(false); onImportClick(); }}>
              Import JSON…
            </button>
          </div>
        )}
      </div>

      {/* Export dropdown */}
      <div className="dropdown-wrap" ref={exportRef}>
        <button
          className="btn"
          onClick={() => setExportOpen(o => !o)}
          disabled={!canExport}
          aria-haspopup="menu"
          aria-expanded={exportOpen}
          title={canExport ? 'Export options' : 'Save the topology before exporting'}
        >
          Export <ChevronDown size={12} />
        </button>
        {exportOpen && (
          <div className="dropdown-menu" role="menu">
            <button className="dropdown-item" onClick={() => { setExportOpen(false); onExportJson(); }}>
              JSON (.netsimflow.json)
            </button>
            <button className="dropdown-item" onClick={() => { setExportOpen(false); onExportReport(); }}>
              Markdown report
            </button>
            <button className="dropdown-item" onClick={() => { setExportOpen(false); onExportPdf(); }}>
              PDF report
            </button>
            <button className="dropdown-item" onClick={() => { setExportOpen(false); onExportDoc(); }}>
              DOC report
            </button>
          </div>
        )}
      </div>

      {/* Save */}
      <button className="btn btn-primary" onClick={onSave} title="Save (⌘S)">
        <Save size={13} />
        Save
      </button>

      <div className="topbar-spacer" />

      {/* User + theme + logout */}
      <span style={{ fontSize: 11, color: 'var(--text-dim)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 160 }}>
        {user.email}
      </span>

      <button className="btn btn-icon" onClick={onToggleTheme} aria-label="Toggle theme" title="Toggle theme">
        {theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
      </button>

      <button className="btn btn-icon btn-danger" onClick={onLogout} aria-label="Logout" title="Logout">
        <LogOut size={14} />
      </button>
    </header>
  );
};

// ─── LeftRail ─────────────────────────────────────────────────────────────────
interface LeftRailProps {
  nodes: ReactFlowNode[];
  templates: TemplateSummary[];
  templatesLoading: boolean;
  activeTemplateId: string;
  selectedElementId: string | null;
  onAddDevice: (type: NetworkNode['baseType']) => void;
  onLoadTemplate: (id: string) => void;
  onSelectNode: (id: string) => void;
}

const PALETTE_ITEMS: { type: NetworkNode['baseType']; label: string }[] = [
  { type: 'router', label: 'Router' },
  { type: 'switch', label: 'Switch' },
  { type: 'host', label: 'Host' },
  { type: 'cloud', label: 'Cloud' },
];

const LeftRail: React.FC<LeftRailProps> = ({
  nodes, templates, templatesLoading, activeTemplateId,
  selectedElementId, onAddDevice, onLoadTemplate, onSelectNode,
}) => {
  const [search, setSearch] = useState('');

  // Group nodes by kind
  const groups: Record<string, typeof nodes> = {};
  for (const n of nodes) {
    const kind = (n.data as NetworkNode).baseType || 'unknown';
    if (!groups[kind]) groups[kind] = [];
    groups[kind].push(n);
  }

  const filteredGroups = Object.entries(groups).map(([kind, ns]) => ({
    kind,
    nodes: ns.filter(n => {
      if (!search) return true;
      const label = ((n.data as NetworkNode).label || '').toLowerCase();
      return label.includes(search.toLowerCase());
    }),
  })).filter(g => g.nodes.length > 0);

  return (
    <aside className="rail">
      {/* Devices palette */}
      <div className="rail-section">
        <div className="rail-section-header">Devices</div>
        <div className="palette-grid">
          {PALETTE_ITEMS.map(item => (
            <button
              key={item.type}
              className="palette-tile"
              onClick={() => onAddDevice(item.type)}
              title={`Add ${item.label}`}
            >
              <div className="palette-tile-icon" style={{ background: devBg(item.type) }}>
                <DevIcon kind={item.type} size={16} />
              </div>
              <span className="palette-tile-label">{item.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Templates */}
      <div className="rail-section">
        <div className="rail-section-header">Templates</div>
        <div className="template-list">
          {templatesLoading && (
            <span style={{ fontSize: 12, color: 'var(--text-dim)', padding: '4px 8px' }}>Loading…</span>
          )}
          {templates.map(t => (
            <button
              key={t.id}
              className={`template-item ${t.id === activeTemplateId ? 'active' : ''}`}
              onClick={() => onLoadTemplate(t.id)}
              title={`Load template: ${t.name}`}
            >
              <span className="template-item-name">{t.name}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Outline */}
      <div className="rail-section" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div className="rail-section-header">Topology</div>
        <div className="outline-search">
          <input
            placeholder="Search nodes…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            aria-label="Search nodes"
          />
        </div>
        <div className="outline-list">
          {filteredGroups.map(({ kind, nodes: ns }) => (
            <div key={kind}>
              <div className="outline-group-label">{kind.charAt(0).toUpperCase() + kind.slice(1)}s</div>
              {ns.map(n => {
                const nd = n.data as NetworkNode;
                const status = nd.runtimeState?.status || 'stopped';
                return (
                  <button
                    key={n.id}
                    className={`outline-row ${n.id === selectedElementId ? 'active' : ''}`}
                    onClick={() => onSelectNode(n.id)}
                    title={nd.label}
                  >
                    <span className={`outline-status-dot ${status}`} />
                    <span className="outline-label">{nd.label}</span>
                  </button>
                );
              })}
            </div>
          ))}
          {nodes.length === 0 && (
            <div style={{ fontSize: 12, color: 'var(--text-dim)', padding: '8px 6px' }}>
              No devices yet.
            </div>
          )}
        </div>
      </div>
    </aside>
  );
};

// ─── Inspector ────────────────────────────────────────────────────────────────
interface InspectorProps {
  nodes: ReactFlowNode[];
  edges: ReactFlowEdge[];
  selectedElementId: string | null;
  selectedElementType: 'node' | 'edge' | null;
  updateNode: (id: string, updates: Partial<NetworkNode>) => void;
  updateEdge: (id: string, updates: Partial<NetworkLink>) => void;
  removeNodes: (ids: string[]) => void;
  onClose: () => void;
  canStartStop: boolean;
  probeTargetIp: string | null;
  selectedFaultLinkId: string | null;
  onRunProbe: (srcId: string, targetIp: string) => void;
  onInjectFault: (linkId: string) => void;
}

const Inspector: React.FC<InspectorProps> = ({
  nodes, edges, selectedElementId, selectedElementType,
  updateNode, updateEdge, removeNodes, onClose,
  canStartStop, probeTargetIp, selectedFaultLinkId,
  onRunProbe, onInjectFault,
}) => {
  const [tab, setTab] = useState<'config' | 'routing' | 'interfaces' | 'events'>('config');

  const selectedNode = selectedElementType === 'node' ? nodes.find(n => n.id === selectedElementId) : null;
  const selectedEdge = selectedElementType === 'edge' ? edges.find(e => e.id === selectedElementId) : null;
  const edgeData = selectedEdge?.data as NetworkLink | undefined;
  const sourceNode = edgeData ? nodes.find(n => n.id === edgeData.sourceNodeId) : null;
  const targetNode = edgeData ? nodes.find(n => n.id === edgeData.targetNodeId) : null;

  const [label, setLabel] = useState('');
  const [loopback, setLoopback] = useState('');
  const [subnet, setSubnet] = useState('');
  const [vendor, setVendor] = useState('generic');

  useEffect(() => {
    if (selectedNode) {
      const nd = selectedNode.data as NetworkNode;
      setLabel(nd.label || '');
      setLoopback(nd.logicalConfig?.loopback || '');
      setVendor((nd.logicalConfig as Record<string, unknown> | undefined)?.vendor as string || 'generic');
    } else if (edgeData) {
      setSubnet(edgeData.ipConfig?.subnet || '');
    }
  }, [selectedNode, edgeData]);

  const handleSaveNode = () => {
    if (selectedElementId && selectedNode) {
      const nd = selectedNode.data as NetworkNode;
      updateNode(selectedElementId, {
        label,
        logicalConfig: {
          ...nd.logicalConfig,
          interfaces: nd.logicalConfig?.interfaces ?? [],
          loopback,
          vendor,
        } as NetworkNode['logicalConfig'],
      });
    }
  };

  const handleSaveEdge = () => {
    if (selectedElementId && edgeData) {
      updateEdge(selectedElementId, {
        ipConfig: { ...edgeData.ipConfig, subnet },
      } as Partial<NetworkLink>);
    }
  };

  if (!selectedElementId) {
    return (
      <aside className="inspect">
        <div className="inspect-empty">
          <MousePointer size={28} color="var(--text-dim)" />
          <span>Nothing selected</span>
          <span style={{ fontSize: 11 }}>Click a node or edge on the canvas</span>
        </div>
      </aside>
    );
  }

  if (selectedNode) {
    const nd = selectedNode.data as NetworkNode;
    const status = nd.runtimeState?.status || 'stopped';
    const kind = nd.baseType || 'router';
    const faultEdge = edges.find(e => (e.source === selectedNode.id || e.target === selectedNode.id) && e.data?.faultState?.active);

    return (
      <aside className="inspect">
        <div className="inspect-header">
          <div className="inspect-icon-plate" style={{ background: devBg(kind) }}>
            <DevIcon kind={kind} size={18} />
          </div>
          <div className="inspect-header-text">
            <div className="inspect-title">{nd.label}</div>
            <div className="inspect-subtitle">{nd.id} · {kind}</div>
          </div>
          <button className="inspect-close-btn" onClick={onClose} title="Close inspector">×</button>
        </div>

        <div className="inspect-tabs">
          {(['config', 'routing', 'interfaces', 'events'] as const).map(t => (
            <button
              key={t}
              className={`inspect-tab ${tab === t ? 'active' : ''}`}
              onClick={() => setTab(t)}
            >
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>

        <div className="inspect-body">
          {tab === 'config' && (
            <>
              <div className="inspect-field">
                <label className="inspect-label">Label</label>
                <input
                  className="inspect-input"
                  value={label}
                  onChange={e => setLabel(e.target.value)}
                  onBlur={handleSaveNode}
                />
              </div>
              <div className="inspect-field">
                <label className="inspect-label">Loopback IP</label>
                <input
                  className="inspect-input"
                  value={loopback}
                  onChange={e => setLoopback(e.target.value)}
                  onBlur={handleSaveNode}
                  placeholder="e.g. 10.255.0.1"
                />
              </div>
              <div className="inspect-field">
                <label className="inspect-label">Vendor</label>
                <select
                  className="inspect-select"
                  value={vendor}
                  onChange={e => { setVendor(e.target.value); }}
                  onBlur={handleSaveNode}
                >
                  <option value="cisco">Cisco</option>
                  <option value="juniper">Juniper</option>
                  <option value="arista">Arista</option>
                  <option value="frr">FRR</option>
                  <option value="generic">Generic</option>
                </select>
              </div>

              <div className="inspect-kv-section">
                <div className="inspect-kv-section-label">Runtime</div>
                <div className="inspect-kv-row">
                  <span className="inspect-kv-key">Status</span>
                  <span className={`status-chip ${status}`}>{status}</span>
                </div>
                {faultEdge && (
                  <div className="inspect-kv-row">
                    <span className="inspect-kv-key">Link fault</span>
                    <span className="status-chip fault">active</span>
                  </div>
                )}
                <div className="inspect-kv-row">
                  <span className="inspect-kv-key">Node ID</span>
                  <span className="inspect-kv-val">{nd.id.slice(0, 14)}…</span>
                </div>
              </div>

              <div className="inspect-actions">
                <button
                  className="btn"
                  disabled={!canStartStop || !probeTargetIp}
                  onClick={() => selectedElementId && probeTargetIp && onRunProbe(selectedElementId, probeTargetIp)}
                  title={probeTargetIp ? `Ping ${probeTargetIp}` : 'No peer IP available'}
                >
                  Ping peer
                </button>
                <button
                  className="btn"
                  onClick={() => navigator.clipboard.writeText(nd.id)}
                  title="Copy node ID"
                >
                  <Copy size={12} />
                </button>
                <button
                  className="btn btn-danger"
                  onClick={() => { removeNodes([selectedNode.id]); onClose(); }}
                  title="Delete node"
                >
                  <Trash2 size={12} />
                </button>
              </div>
            </>
          )}
          {tab !== 'config' && (
            <div className="inspect-placeholder">
              {tab.charAt(0).toUpperCase() + tab.slice(1)} tab — coming soon.
            </div>
          )}
        </div>
      </aside>
    );
  }

  if (edgeData) {
    const srcName = (sourceNode?.data as NetworkNode | undefined)?.label || edgeData.sourceNodeId;
    const tgtName = (targetNode?.data as NetworkNode | undefined)?.label || edgeData.targetNodeId;
    const faultActive = edgeData.faultState?.active ?? false;

    return (
      <aside className="inspect">
        <div className="inspect-header">
          <div className="inspect-icon-plate" style={{ background: 'var(--surface-3)' }}>
            <Network size={18} color="var(--text-3)" />
          </div>
          <div className="inspect-header-text">
            <div className="inspect-title">{srcName} ↔ {tgtName}</div>
            <div className="inspect-subtitle">{selectedEdge?.id} · link</div>
          </div>
          <button className="inspect-close-btn" onClick={onClose} title="Close inspector">×</button>
        </div>

        <div className="inspect-body">
          <div className="inspect-field">
            <label className="inspect-label">Subnet</label>
            <input
              className="inspect-input"
              value={subnet}
              onChange={e => setSubnet(e.target.value)}
              onBlur={handleSaveEdge}
              placeholder="e.g. 10.0.0.0/30"
            />
          </div>

          <div className="inspect-kv-section">
            <div className="inspect-kv-section-label">Link</div>
            <div className="inspect-kv-row">
              <span className="inspect-kv-key">Type</span>
              <span className="inspect-kv-val">{edgeData.linkType || 'ethernet'}</span>
            </div>
            <div className="inspect-kv-row">
              <span className="inspect-kv-key">State</span>
              <span className={`status-chip ${faultActive ? 'fault' : 'running'}`}>
                {faultActive ? 'fault' : 'up'}
              </span>
            </div>
          </div>

          <div className="inspect-kv-section">
            <div className="inspect-kv-section-label">Endpoints</div>
            <div className="inspect-kv-row">
              <span className="inspect-kv-key">Source</span>
              <span className="inspect-kv-val">{srcName} / {edgeData.sourcePort}</span>
            </div>
            {edgeData.ipConfig?.sourceIp && (
              <div className="inspect-kv-row">
                <span className="inspect-kv-key">Src IP</span>
                <span className="inspect-kv-val">{edgeData.ipConfig.sourceIp}</span>
              </div>
            )}
            <div className="inspect-kv-row">
              <span className="inspect-kv-key">Target</span>
              <span className="inspect-kv-val">{tgtName} / {edgeData.targetPort}</span>
            </div>
            {edgeData.ipConfig?.targetIp && (
              <div className="inspect-kv-row">
                <span className="inspect-kv-key">Tgt IP</span>
                <span className="inspect-kv-val">{edgeData.ipConfig.targetIp}</span>
              </div>
            )}
          </div>

          <div className="inspect-actions">
            <button
              className={`btn ${faultActive ? 'btn-danger' : ''}`}
              disabled={!canStartStop || !selectedFaultLinkId}
              onClick={() => selectedFaultLinkId && onInjectFault(selectedFaultLinkId)}
              title={faultActive ? 'Fault already active' : 'Inject link-down fault'}
            >
              {faultActive ? 'Clear fault' : 'Inject fault'}
            </button>
            <button
              className="btn"
              onClick={() => navigator.clipboard.writeText(selectedEdge?.id || '')}
              title="Copy edge ID"
            >
              <Copy size={12} />
            </button>
          </div>
        </div>
      </aside>
    );
  }

  return null;
};

// ─── Dock ─────────────────────────────────────────────────────────────────────
interface DockProps {
  logs: LogEntry[];
  onClearLogs: () => void;
  onClose: () => void;
}

const Dock: React.FC<DockProps> = ({ logs, onClearLogs, onClose }) => {
  const [tab, setTab] = useState<'console' | 'probes' | 'faults' | 'config'>('console');
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  const probeLogs = logs.filter(l => l.source === 'probe');
  const faultLogs = logs.filter(l => l.source === 'fault');

  const tabData: Record<typeof tab, { label: string; count: number; logs: typeof logs }> = {
    console: { label: 'Console', count: logs.length, logs },
    probes: { label: 'Probes', count: probeLogs.length, logs: probeLogs },
    faults: { label: 'Faults', count: faultLogs.length, logs: faultLogs },
    config: { label: 'Config', count: 0, logs: [] },
  };

  const currentLogs = tabData[tab].logs;

  return (
    <div className="dock">
      <div className="dock-header">
        <div className="dock-tabs">
          {(Object.entries(tabData) as [typeof tab, { label: string; count: number }][]).map(([key, { label, count }]) => (
            <button
              key={key}
              className={`dock-tab ${tab === key ? 'active' : ''}`}
              onClick={() => setTab(key)}
            >
              {label}
              {count > 0 && <span className="dock-tab-badge">{count}</span>}
            </button>
          ))}
        </div>
        <div className="dock-actions">
          <button className="btn btn-icon" onClick={onClearLogs} title="Clear logs">
            <Trash2 size={12} />
          </button>
          <button className="btn btn-icon" onClick={onClose} title="Close dock">
            <X size={12} />
          </button>
        </div>
      </div>
      <div className="dock-body" ref={scrollRef}>
        {tab === 'config' ? (
          <div className="dock-empty">
            <pre style={{ margin: 0, fontSize: 11, color: 'var(--text-dim)' }}>
              Config generation not yet implemented.
            </pre>
          </div>
        ) : currentLogs.length === 0 ? (
          <div className="dock-empty">No entries yet.</div>
        ) : (
          <div className="dock-log-lines">
            {currentLogs.map(log => (
              <div key={log.id} className={`log-line ${log.level}`}>
                <span className="log-ts">{log.timestamp}</span>
                <span className="log-src">{log.source ? `[${log.source}]` : ''}</span>
                <span className="log-msg">{log.message}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// ─── StatusBar ────────────────────────────────────────────────────────────────
interface StatusBarProps {
  topologyName: string;
  simStatus: 'idle' | 'running' | 'stopped' | 'error';
  nodeCount: number;
  edgeCount: number;
  faultCount: number;
  dockOpen: boolean;
  onToggleDock: () => void;
}

const StatusBar: React.FC<StatusBarProps> = ({
  topologyName, simStatus, nodeCount, edgeCount, faultCount, dockOpen, onToggleDock,
}) => (
  <footer className="statusbar">
    <span className={`statusbar-dot ${simStatus === 'running' ? 'running' : ''}`} />
    <span>{topologyName}</span>
    <span className="statusbar-sep" />
    <span>{nodeCount} nodes · {edgeCount} links</span>
    <div className="statusbar-spacer" />
    {faultCount > 0 && (
      <>
        <span className="statusbar-fault">{faultCount} fault{faultCount !== 1 ? 's' : ''}</span>
        <span className="statusbar-sep" />
      </>
    )}
    <button className="statusbar-dock-btn" onClick={onToggleDock} title="Toggle dock">
      <TerminalSquare size={11} />
      {dockOpen ? 'Hide console' : 'Console'}
    </button>
  </footer>
);

// ─── Canvas Toolbar ───────────────────────────────────────────────────────────
const CanvasToolbar: React.FC = () => {
  const { fitView } = useReactFlow();
  const [tool, setTool] = useState<'select' | 'pan'>('select');

  return (
    <div className="canvas-toolbar">
      <button
        className={`canvas-toolbar-btn ${tool === 'select' ? 'active' : ''}`}
        onClick={() => setTool('select')}
        title="Select (V)"
      >
        <MousePointer size={14} />
      </button>
      <button
        className={`canvas-toolbar-btn ${tool === 'pan' ? 'active' : ''}`}
        onClick={() => setTool('pan')}
        title="Pan (H)"
      >
        <Hand size={14} />
      </button>
      <div className="canvas-toolbar-sep" />
      <button
        className="canvas-toolbar-btn"
        onClick={() => fitView({ padding: 0.15, duration: 300 })}
        title="Fit view"
      >
        <Maximize2 size={14} />
      </button>
      <button
        className="canvas-toolbar-btn"
        onClick={() => void navigator.clipboard.writeText(window.location.href)}
        title="Copy share link"
      >
        <Search size={14} />
      </button>
    </div>
  );
};

// ─── Main component ───────────────────────────────────────────────────────────
interface TopologyCanvasProps {
  user: CurrentUser;
  onLogout: () => void;
}

export const TopologyCanvas: React.FC<TopologyCanvasProps> = ({ user, onLogout }) => {
  const {
    nodes, edges, onNodesChange, onEdgesChange, onConnect,
    addNode, currentTopologyId, removeNodes, updateNode, updateEdge,
  } = useTopologyStore();
  const { theme, toggleTheme, selectedElementId, selectedElementType, setSelectedElement, consoleOpen, toggleConsole } = useUiStore();
  const { logs, clearLogs, status: simStatus } = useSimulationStore();
  const [selectedTemplateId, setSelectedTemplateId] = useState('ospf-3-sites');
  const [toastError, setToastError] = useState<string | null>(null);
  const importInputRef = useRef<HTMLInputElement>(null);

  const {
    templates, templatesLoading, templatesError,
    currentTopologyName, setCurrentTopologyName,
    saveTopology, loadLatestTopology, triggerAutoIp, loadTemplate,
    startSimulation, stopSimulation, runProbe, injectFault,
    exportTopology, exportReport, exportPdfReport, exportDocReport, importTopology,
  } = useTopology();

  useSimulationEvents(currentTopologyId);

  const activeTemplateId = useMemo(() => {
    if (templates.some(t => t.id === selectedTemplateId)) return selectedTemplateId;
    return templates[0]?.id ?? selectedTemplateId;
  }, [selectedTemplateId, templates]);

  const probeTargetIp = useMemo(() => {
    const selectedNode = selectedElementType === 'node'
      ? nodes.find(node => node.id === selectedElementId)
      : null;
    if (!selectedNode) return null;
    const peerLoopback = nodes
      .find(node => node.id !== selectedNode.id && node.data.logicalConfig?.loopback)
      ?.data.logicalConfig?.loopback;
    if (peerLoopback) return peerLoopback;
    const peerEdge = edges.find(edge => edge.source === selectedNode.id || edge.target === selectedNode.id);
    const edgeData = peerEdge?.data;
    if (!edgeData?.ipConfig) return null;
    return peerEdge?.source === selectedNode.id ? edgeData.ipConfig.targetIp : edgeData.ipConfig.sourceIp;
  }, [edges, nodes, selectedElementId, selectedElementType]);

  const selectedFaultLinkId = useMemo(() => {
    if (selectedElementType !== 'edge') return null;
    const selectedEdge = edges.find(edge => edge.id === selectedElementId);
    return selectedEdge?.data?.id ?? selectedElementId;
  }, [edges, selectedElementId, selectedElementType]);

  const canRunAutoIp = nodes.length > 0 || edges.length > 0;
  const canStartStop = Boolean(currentTopologyId);
  const canExport = Boolean(currentTopologyId);
  const canPing = selectedElementType === 'node' && Boolean(selectedElementId) && Boolean(probeTargetIp) && canStartStop;
  const canInjectFault = Boolean(selectedFaultLinkId) && canStartStop;
  const faultCount = edges.filter(e => e.data?.faultState?.active).length;

  const handleAddDevice = (type: NetworkNode['baseType']) => {
    const newNode: NetworkNode = {
      id: `node-${uuidv4()}`,
      label: `${type}-${nodes.length + 1}`,
      position: { x: Math.random() * 300 + 100, y: Math.random() * 200 + 100 },
      baseType: type,
      tags: [],
      runtimeState: { status: 'stopped' },
    };
    addNode(newNode);
  };

  const isValidConnection = useCallback((connection: Connection | ReactFlowEdge) => {
    const sourceUsed = edges.some(e => e.source === connection.source && e.sourceHandle === (connection.sourceHandle ?? null));
    const targetUsed = edges.some(e => e.target === connection.target && e.targetHandle === (connection.targetHandle ?? null));
    if (sourceUsed || targetUsed) {
      setToastError(`Connection Failed: The ${sourceUsed ? 'source' : 'target'} port is already in use.`);
      setTimeout(() => setToastError(null), 3000);
      return false;
    }
    return true;
  }, [edges]);

  const hasInspect = Boolean(selectedElementId);

  return (
    <div className={`shell ${consoleOpen ? 'dock-open' : ''} ${hasInspect ? 'has-inspect' : ''}`}>
      {/* Top bar */}
      <TopBar
        user={user}
        onLogout={onLogout}
        currentTopologyName={currentTopologyName}
        setCurrentTopologyName={setCurrentTopologyName}
        simStatus={simStatus}
        canStartStop={canStartStop}
        canExport={canExport}
        canRunAutoIp={canRunAutoIp}
        onSave={saveTopology}
        onStart={startSimulation}
        onStop={stopSimulation}
        onAutoIp={triggerAutoIp}
        onImportClick={() => importInputRef.current?.click()}
        onLoadLatest={loadLatestTopology}
        onExportJson={exportTopology}
        onExportReport={exportReport}
        onExportPdf={exportPdfReport}
        onExportDoc={exportDocReport}
        theme={theme}
        onToggleTheme={toggleTheme}
      />

      {/* Left rail */}
      <LeftRail
        nodes={nodes}
        templates={templates}
        templatesLoading={templatesLoading}
        activeTemplateId={activeTemplateId}
        selectedElementId={selectedElementId}
        onAddDevice={handleAddDevice}
        onLoadTemplate={(id) => { setSelectedTemplateId(id); void loadTemplate(id); }}
        onSelectNode={(id) => setSelectedElement(id, 'node')}
      />

      {/* Canvas */}
      <div className="canvas-wrap">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          isValidConnection={isValidConnection}
          onNodeClick={(_, node) => setSelectedElement(node.id, 'node')}
          onEdgeClick={(_, edge) => setSelectedElement(edge.id, 'edge')}
          onPaneClick={() => setSelectedElement(null, null)}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          connectionMode={ConnectionMode.Loose}
          colorMode={theme}
          fitView
        >
          <Background color="var(--canvas-grid)" gap={24} size={1} />
          <Controls position="bottom-right" />
          <MiniMap
            nodeColor={(node) => {
              switch (node.type) {
                case 'router': return 'var(--dev-router)';
                case 'switch': return 'var(--dev-switch)';
                case 'cloud':  return 'var(--dev-cloud)';
                case 'host':   return 'var(--dev-host)';
                default: return 'var(--text-dim)';
              }
            }}
            style={{ bottom: 10, right: 46 }}
          />
        </ReactFlow>
        <CanvasToolbar />

        {/* Toast */}
        {toastError && (
          <div className="canvas-toast error">{toastError}</div>
        )}
        {!toastError && templatesError && (
          <div className="canvas-toast error">{templatesError}</div>
        )}
      </div>

      {/* Inspector (shown when something is selected) */}
      {hasInspect && (
        <Inspector
          nodes={nodes}
          edges={edges}
          selectedElementId={selectedElementId}
          selectedElementType={selectedElementType}
          updateNode={updateNode}
          updateEdge={updateEdge}
          removeNodes={removeNodes}
          onClose={() => setSelectedElement(null, null)}
          canStartStop={canStartStop}
          probeTargetIp={canPing ? (probeTargetIp ?? null) : null}
          selectedFaultLinkId={canInjectFault ? selectedFaultLinkId : null}
          onRunProbe={runProbe}
          onInjectFault={injectFault}
        />
      )}

      {/* Dock */}
      {consoleOpen && (
        <Dock
          logs={logs}
          onClearLogs={clearLogs}
          onClose={toggleConsole}
        />
      )}

      {/* Status bar */}
      <StatusBar
        topologyName={currentTopologyName}
        simStatus={simStatus}
        nodeCount={nodes.length}
        edgeCount={edges.length}
        faultCount={faultCount}
        dockOpen={consoleOpen}
        onToggleDock={toggleConsole}
      />

      {/* Hidden import input */}
      <input
        ref={importInputRef}
        type="file"
        accept=".json,.netsimflow.json,application/json"
        style={{ display: 'none' }}
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) void importTopology(file);
          event.target.value = '';
        }}
      />
    </div>
  );
};
