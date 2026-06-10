# Spec: Topology Objects Panel — Clickable Node/Edge Sidebar

**Branch:** `feat/topology-objects-panel`
**Spec file:** `specs/SPEC-topology-objects-panel.md`
**Status:** ready-for-implementation

---

## Goal

Add a collapsible sidebar panel on the left side of the canvas that lists every
node (and edge) in the current topology. Clicking an item in the list selects it
exactly as if it were clicked on the canvas — the property inspector opens and
that element is highlighted. This lets users work with topologies where nodes
are overlapping or hard to click, and gives a compact overview of the full
topology at a glance.

---

## Scope

**In scope:**
- `topologyPanelOpen` boolean + `toggleTopologyPanel` action added to `useUiStore`
- New `TopologyObjectsPanel.tsx` component in `apps/frontend/src/components/`
- New `TopologyObjectsPanel.css` in the same directory
- A "☰ Objects" toggle button added to the top-left toolbar in `TopologyCanvas.tsx`
- `<TopologyObjectsPanel />` rendered inside `TopologyCanvas`'s outer div (same
  level as `<PropertyPanel />` and `<LogConsole />`)
- Nodes listed with type icon, label, type badge, status dot
- Edges listed under a collapsible "Links" section with source→target labels
- Clicking any row calls `setSelectedElement` — identical to a canvas click

**Out of scope (do not implement):**
- Search/filter within the panel (can be added later)
- Drag-to-reorder nodes
- Inline renaming from the panel
- Integration with ping pick-mode (handled in SPEC-advanced-interactions.md)
- Any backend changes

---

## Files to Read First

| File | Why |
|------|-----|
| `apps/frontend/src/store/ui.slice.ts` | Full current state — add new fields here |
| `apps/frontend/src/components/PropertyPanel.tsx` | Pattern for a panel that reads from topology store |
| `apps/frontend/src/components/PropertyPanel.css` | CSS variables and patterns to reuse |
| `apps/frontend/src/canvas/TopologyCanvas.tsx` | Where to add the toggle button and render the panel |
| `apps/frontend/src/store/topology.slice.ts` | Confirm `nodes` and `edges` field shapes |
| `packages/shared-types/src/topology.ts` | `NetworkNode.baseType` values for icon mapping |

---

## Implementation Steps

### Step 1 — Add `topologyPanelOpen` and `toggleTopologyPanel` to `ui.slice.ts`

**File:** `apps/frontend/src/store/ui.slice.ts` *(modify)*

Before:
```typescript
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
```

After:
```typescript
interface UiState {
  theme: ThemeMode;
  toggleTheme: () => void;
  propertyPanelOpen: boolean;
  consoleOpen: boolean;
  topologyPanelOpen: boolean;
  selectedElementId: string | null;
  selectedElementType: 'node' | 'edge' | null;
  setSelectedElement: (id: string | null, type: 'node' | 'edge' | null) => void;
  closePropertyPanel: () => void;
  toggleConsole: () => void;
  toggleTopologyPanel: () => void;
}
```

Then add initial value and action in the `immer` block:

Before:
```typescript
    consoleOpen: false,
```

After:
```typescript
    consoleOpen: false,
    topologyPanelOpen: false,
```

Before:
```typescript
    toggleConsole: () => set((state) => {
      state.consoleOpen = !state.consoleOpen;
    })
```

After:
```typescript
    toggleConsole: () => set((state) => {
      state.consoleOpen = !state.consoleOpen;
    }),
    toggleTopologyPanel: () => set((state) => {
      state.topologyPanelOpen = !state.topologyPanelOpen;
    }),
```

---

### Step 2 — Create `TopologyObjectsPanel.tsx`

**File:** `apps/frontend/src/components/TopologyObjectsPanel.tsx` *(create)*

```typescript
import React, { useState } from 'react';
import { useTopologyStore, useUiStore } from '../store';
import type { NetworkNode, NetworkLink } from '@octet/shared-types';
import './TopologyObjectsPanel.css';

const BASE_TYPE_ICON: Record<string, string> = {
  router:   '⌘',
  switch:   '⊟',
  host:     '□',
  cloud:    '☁',
  firewall: '⚡',
  site:     '◎',
};

const STATUS_COLOR: Record<string, string> = {
  running:  '#4caf50',
  stopped:  '#9e9e9e',
  booting:  '#ff9800',
  error:    '#f44336',
  degraded: '#ff5722',
};

export const TopologyObjectsPanel: React.FC = () => {
  const { topologyPanelOpen, toggleTopologyPanel, selectedElementId, setSelectedElement } = useUiStore();
  const { nodes, edges } = useTopologyStore();
  const [linksExpanded, setLinksExpanded] = useState(false);

  return (
    <div className={`topology-panel ${topologyPanelOpen ? 'open' : ''}`}>
      <div className="topology-panel-header">
        <h3>Objects</h3>
        <button className="close-btn" onClick={toggleTopologyPanel}>×</button>
      </div>

      <div className="topology-panel-content">

        {/* ── Nodes section ──────────────────────────────────────────── */}
        <div className="topo-section-title">
          Nodes
          <span className="topo-count">{nodes.length}</span>
        </div>

        {nodes.length === 0 && (
          <div className="topo-empty">No nodes yet. Add devices from the toolbar.</div>
        )}

        {nodes.map(node => {
          const data = node.data as NetworkNode;
          const status = data.runtimeState?.status ?? 'stopped';
          const isSelected = selectedElementId === node.id;
          return (
            <button
              key={node.id}
              className={`topo-row ${isSelected ? 'selected' : ''}`}
              onClick={() => setSelectedElement(node.id, 'node')}
              title={`${data.label} (${data.baseType})`}
            >
              <span className="topo-row-icon">{BASE_TYPE_ICON[data.baseType] ?? '□'}</span>
              <span className="topo-row-label">{data.label}</span>
              <span className="topo-row-badge">{data.baseType}</span>
              <span
                className="topo-row-status"
                style={{ background: STATUS_COLOR[status] ?? STATUS_COLOR.stopped }}
                title={`Status: ${status}`}
              />
            </button>
          );
        })}

        {/* ── Links section (collapsible) ────────────────────────────── */}
        {edges.length > 0 && (
          <>
            <button
              className="topo-section-title topo-section-toggle"
              onClick={() => setLinksExpanded(e => !e)}
            >
              Links
              <span className="topo-count">{edges.length}</span>
              <span className="topo-chevron">{linksExpanded ? '▴' : '▾'}</span>
            </button>

            {linksExpanded && edges.map(edge => {
              const d = edge.data as NetworkLink | undefined;
              if (!d) return null;
              const srcNode = nodes.find(n => n.id === edge.source);
              const tgtNode = nodes.find(n => n.id === edge.target);
              const srcLabel = (srcNode?.data as NetworkNode | undefined)?.label ?? edge.source;
              const tgtLabel = (tgtNode?.data as NetworkNode | undefined)?.label ?? edge.target;
              const isSelected = selectedElementId === edge.id;
              const faulted = Boolean(d.faultState?.active);
              return (
                <button
                  key={edge.id}
                  className={`topo-row ${isSelected ? 'selected' : ''} ${faulted ? 'faulted' : ''}`}
                  onClick={() => setSelectedElement(edge.id, 'edge')}
                  title={`${srcLabel}:${d.sourcePort} ↔ ${tgtLabel}:${d.targetPort}`}
                >
                  <span className="topo-row-icon">↔</span>
                  <span className="topo-row-label topo-row-label--link">
                    <span>{srcLabel}</span>
                    <span className="topo-row-port">{d.sourcePort}</span>
                    <span className="topo-row-arrow">→</span>
                    <span>{tgtLabel}</span>
                    <span className="topo-row-port">{d.targetPort}</span>
                  </span>
                  {faulted && <span className="topo-fault-badge">FAULT</span>}
                </button>
              );
            })}
          </>
        )}

      </div>
    </div>
  );
};
```

---

### Step 3 — Create `TopologyObjectsPanel.css`

**File:** `apps/frontend/src/components/TopologyObjectsPanel.css` *(create)*

```css
.topology-panel {
  position: absolute;
  left: -280px;
  top: 80px;
  bottom: 20px;
  width: 260px;
  background: var(--panel-bg);
  border: 1px solid var(--panel-border);
  backdrop-filter: var(--panel-backdrop);
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  transition: left 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 1000;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  color: var(--text-primary);
}

.topology-panel.open {
  left: 20px;
}

/* ── Header ──────────────────────────────────────────────────────────────── */

.topology-panel-header {
  padding: 16px;
  border-bottom: 1px solid var(--panel-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.topology-panel-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--accent-blue);
}

/* ── Content ─────────────────────────────────────────────────────────────── */

.topology-panel-content {
  padding: 8px;
  overflow-y: auto;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

/* ── Section titles ──────────────────────────────────────────────────────── */

.topo-section-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 8px 6px 4px;
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: default;
}

button.topo-section-toggle {
  background: none;
  border: none;
  width: 100%;
  text-align: left;
  cursor: pointer;
}

button.topo-section-toggle:hover {
  color: var(--text-primary);
}

.topo-count {
  background: var(--button-bg);
  padding: 1px 5px;
  border-radius: 8px;
  font-size: 10px;
  font-weight: 700;
  color: var(--text-secondary);
  margin-left: 2px;
}

.topo-chevron {
  margin-left: auto;
  font-size: 10px;
}

/* ── Row ─────────────────────────────────────────────────────────────────── */

.topo-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 6px;
  border: none;
  background: transparent;
  color: var(--text-primary);
  cursor: pointer;
  text-align: left;
  width: 100%;
  font-size: 13px;
  transition: background 0.15s;
  min-width: 0;
}

.topo-row:hover {
  background: var(--button-bg);
}

.topo-row.selected {
  background: rgba(var(--accent-blue-rgb, 33, 150, 243), 0.12);
  outline: 1px solid var(--accent-blue);
}

.topo-row.faulted .topo-row-label {
  color: #f44336;
}

.topo-row-icon {
  font-size: 14px;
  width: 18px;
  text-align: center;
  flex-shrink: 0;
  color: var(--text-secondary);
}

.topo-row-label {
  flex: 1;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.topo-row-label--link {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
}

.topo-row-port {
  font-family: monospace;
  font-size: 10px;
  color: var(--text-secondary);
  background: var(--button-bg);
  padding: 1px 4px;
  border-radius: 3px;
}

.topo-row-arrow {
  color: var(--text-secondary);
  font-size: 10px;
}

.topo-row-badge {
  font-size: 10px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  background: var(--button-bg);
  padding: 1px 5px;
  border-radius: 3px;
  flex-shrink: 0;
}

.topo-row-status {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}

.topo-fault-badge {
  font-size: 9px;
  font-weight: 700;
  color: #f44336;
  background: rgba(244, 67, 54, 0.12);
  border: 1px solid rgba(244, 67, 54, 0.3);
  padding: 1px 4px;
  border-radius: 3px;
  flex-shrink: 0;
  letter-spacing: 0.04em;
}

/* ── Empty state ─────────────────────────────────────────────────────────── */

.topo-empty {
  font-size: 12px;
  color: var(--text-secondary);
  font-style: italic;
  padding: 8px 6px;
  opacity: 0.7;
}
```

---

### Step 4 — Add the toggle button and render the panel in `TopologyCanvas.tsx`

**File:** `apps/frontend/src/canvas/TopologyCanvas.tsx` *(modify)*

**4a.** Add `toggleTopologyPanel` to the `useUiStore` destructure.

Before:
```typescript
  const { theme, selectedElementId, selectedElementType, setSelectedElement, consoleOpen, toggleConsole } = useUiStore();
```

After:
```typescript
  const { theme, selectedElementId, selectedElementType, setSelectedElement, consoleOpen, toggleConsole, topologyPanelOpen, toggleTopologyPanel } = useUiStore();
```

**4b.** Import `TopologyObjectsPanel`.

Before:
```typescript
import { LogConsole } from '../components/LogConsole';
```

After:
```typescript
import { LogConsole } from '../components/LogConsole';
import { TopologyObjectsPanel } from '../components/TopologyObjectsPanel';
```

**4c.** Add the "☰ Objects" button to the top-left toolbar `Panel`. Append it after the existing device buttons:

Before:
```typescript
          <button onClick={() => handleAddDevice('host')} style={buttonStyle}>+ Host</button>
        </Panel>
```

After:
```typescript
          <button onClick={() => handleAddDevice('host')} style={buttonStyle}>+ Host</button>
          <button
            onClick={toggleTopologyPanel}
            style={{
              ...buttonStyle,
              background: topologyPanelOpen ? 'var(--accent-blue)' : buttonStyle.background,
              color: topologyPanelOpen ? 'white' : buttonStyle.color,
            }}
            title="Toggle topology objects panel"
          >
            ☰ Objects
          </button>
        </Panel>
```

**4d.** Render `<TopologyObjectsPanel />` alongside the other overlay components.

Before:
```typescript
      <PropertyPanel />
      <LogConsole />
```

After:
```typescript
      <TopologyObjectsPanel />
      <PropertyPanel />
      <LogConsole />
```

---

## Tests to Add or Update

No new automated tests required — this is a pure UI component with no business
logic. It reads from stores that already have tests.

If a snapshot test exists for `TopologyCanvas`, update it to include the new button and panel.

---

## Validation Commands

```powershell
# 1. Type check
cd apps/frontend
pnpm tsc --noEmit

# 2. Frontend tests
cd apps/frontend
pnpm vitest run

# 3. Backend tests (unchanged)
cd apps/api
.\.venv\Scripts\python.exe -m pytest --tb=short -q

# 4. Build
cd apps/frontend
pnpm build

# 5. Manual — open/close
#    Click "☰ Objects" in the top-left toolbar.
#    The panel slides in from the left. The button turns blue.
#    Click the × or click "☰ Objects" again → panel slides out.

# 6. Manual — selection sync
#    Open the panel. Click "R1" in the list.
#    R1 highlights on the canvas AND the property inspector opens for R1.
#    Click a different node on the canvas — the Objects panel highlight
#    moves to that node.

# 7. Manual — edge list
#    Connect two nodes. Open Objects panel.
#    The "Links" section appears. Expand it → see the link row.
#    Click the link row → edge is selected, inspector shows edge properties.
#    Inject a fault on the link → link row shows "FAULT" badge.

# 8. Manual — empty state
#    Load a blank topology. Open Objects panel.
#    "No nodes yet." message appears in the Nodes section.
```

---

## Architectural Checklist

- [ ] No `@xyflow/react` imports outside `apps/frontend/src/canvas/`
- [ ] No API calls in `TopologyObjectsPanel` — reads from Zustand stores only
- [ ] `topologyPanelOpen` state is in `useUiStore`, not local component state
- [ ] Clicking a row calls `setSelectedElement` — no direct store mutation in the component
- [ ] No `console.log` or `print()` debug statements
- [ ] All frontend tests pass
- [ ] Production build is clean (`pnpm build` exits 0)
