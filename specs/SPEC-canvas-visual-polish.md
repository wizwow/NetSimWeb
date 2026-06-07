# Spec: Canvas Visual Polish — Handle Animation, Port Labels, Link Colors, Console Filter

**Branch:** `feat/canvas-visual-polish`
**Spec file:** `specs/SPEC-canvas-visual-polish.md`
**Status:** ready-for-implementation

---

## Goal

Four focused visual improvements that make the canvas feel more professional and
informative. Handle hover no longer jumps off-center. Each port shows its
interface name and IP address as a small permanent label on the node. Links turn
green during simulation and red-dashed when faulted. The log console gets a
filter bar so engineers can quickly find specific events.

---

## Scope

**In scope:**
- Fix handle hover animation (`index.css`) — replace `transform: scale` with a
  glow/outline so the handle doesn't appear to jump
- Port labels in `BaseNode.tsx` — small permanent labels next to each handle
  showing `ifaceName` and `ip/mask` when configured
- Link state colours in `SimulatedEdge.tsx` — grey → green when simulation
  running; red/dashed when faulted (already done for fault, needs running state)
- Console filter bar in `LogConsole.tsx` — text input that filters the log list
  live; clear button resets the filter

**Out of scope:**
- Draggable/repositionable handles (separate spec)
- Animated packet traceroute (Phase 5)
- Switch port visual uniqueness (next spec)
- Any backend changes
- Any shared-type changes

---

## Files to Read First

| File | Why |
|------|-----|
| `apps/frontend/src/index.css` | Full `.netsim-handle` and `.netsim-node` CSS — every line |
| `apps/frontend/src/canvas/nodes/BaseNode.tsx` | Full current implementation — understand CYCLE, handle rendering |
| `apps/frontend/src/canvas/edges/SimulatedEdge.tsx` | Current path + fault colour logic to extend |
| `apps/frontend/src/components/LogConsole.tsx` | Full current implementation |
| `apps/frontend/src/components/LogConsole.css` | Existing styles to match |
| `apps/frontend/src/store/topology.slice.ts` | Confirm `nodes` array and `runtimeState.status` field |

---

## Implementation Steps

### Step 1 — Fix handle hover animation in `index.css`

**File:** `apps/frontend/src/index.css` *(modify)*

The current `transform: scale(1.5)` causes the handle to jump off-center
because the transform origin is the handle center, which is exactly on the node
border — half inside, half outside. Replace the scale with a box-shadow glow.

Find:
```css
.netsim-handle:hover {
  transform: scale(1.5);
  border-color: var(--accent-blue) !important;
  background-color: var(--accent-blue) !important;
}
```

Replace with:
```css
.netsim-handle:hover {
  border-color: var(--accent-blue) !important;
  background-color: var(--accent-blue) !important;
  box-shadow: 0 0 0 3px var(--accent-blue-glow), 0 0 8px var(--accent-blue);
}
```

---

### Step 2 — Add port labels to `BaseNode.tsx`

**File:** `apps/frontend/src/canvas/nodes/BaseNode.tsx` *(modify)*

Each handle needs a small label positioned just outside the node boundary on
the corresponding side. The label shows `ifaceName` plus `ip/mask` when
configured.

**2a.** Add a helper that computes how many interfaces share a given side and
the within-side index for each interface. This is needed to distribute labels
along the edge without overlap (React Flow auto-distributes handles, and the
labels must follow the same logic).

Replace the entire file with:

```typescript
import React from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NetworkNode, LogicalInterface } from '@octet/shared-types';

/**
 * Handle positions cycle through these four sides in order.
 * Interface eth0 → Top, eth1 → Right, eth2 → Bottom, eth3 → Left,
 * eth4 → Top again, etc.
 */
const CYCLE: Position[] = [Position.Top, Position.Right, Position.Bottom, Position.Left];

interface BaseNodeProps {
  data: NetworkNode;
  icon: React.ReactNode;
}

/** Format the label shown beside a port handle. */
function portLabel(iface: LogicalInterface): string {
  const addr = iface.ip
    ? iface.subnet ? `${iface.ip}${iface.subnet}` : iface.ip
    : '';
  return addr ? `${iface.name}: ${addr}` : iface.name;
}

/**
 * Compute absolute-positioned style for a port label given:
 *  - which side of the node the handle is on
 *  - how many handles share that side (sideCount)
 *  - the 0-based index of this handle within that side (sideIdx)
 *
 * React Flow distributes N handles on a side evenly at positions
 * (1/(N+1), 2/(N+1), … N/(N+1)) as a fraction of the node edge length.
 * We reproduce that to align labels with handles.
 */
function labelStyle(
  position: Position,
  sideIdx: number,
  sideCount: number,
): React.CSSProperties {
  const fraction = (sideIdx + 1) / (sideCount + 1);
  const pct = `${fraction * 100}%`;
  const base: React.CSSProperties = {
    position: 'absolute',
    fontSize: '9px',
    fontFamily: 'monospace',
    color: 'var(--text-secondary)',
    whiteSpace: 'nowrap',
    pointerEvents: 'none',
    lineHeight: 1.2,
    zIndex: 1,
  };

  switch (position) {
    case Position.Top:
      return { ...base, bottom: '100%', left: pct, transform: 'translateX(-50%)', paddingBottom: '4px', textAlign: 'center' };
    case Position.Right:
      return { ...base, left: '100%', top: pct, transform: 'translateY(-50%)', paddingLeft: '6px' };
    case Position.Bottom:
      return { ...base, top: '100%', left: pct, transform: 'translateX(-50%)', paddingTop: '4px', textAlign: 'center' };
    case Position.Left:
      return { ...base, right: '100%', top: pct, transform: 'translateY(-50%)', paddingRight: '6px', textAlign: 'right' };
  }
}

export const BaseNode: React.FC<BaseNodeProps> = ({ data, icon }) => {
  const status = data.runtimeState?.status ?? 'stopped';
  const role = data.role ?? data.baseType;
  const interfaces = data.logicalConfig?.interfaces ?? [];

  // Count how many interfaces land on each side so labels can be distributed
  // along the edge at the same fractional positions React Flow uses.
  const sideCount: Record<Position, number> = {
    [Position.Top]: 0,
    [Position.Right]: 0,
    [Position.Bottom]: 0,
    [Position.Left]: 0,
  };
  for (let i = 0; i < interfaces.length; i++) {
    sideCount[CYCLE[i % CYCLE.length]]++;
  }
  const sideIdx: Record<Position, number> = {
    [Position.Top]: 0,
    [Position.Right]: 0,
    [Position.Bottom]: 0,
    [Position.Left]: 0,
  };

  return (
    <div className="netsim-node">
      {interfaces.map((iface, idx) => {
        const pos = CYCLE[idx % CYCLE.length];
        const thisIdx = sideIdx[pos]++;
        return (
          <React.Fragment key={iface.name}>
            <Handle
              type="source"
              position={pos}
              id={iface.name}
              className="netsim-handle"
            />
            <span style={labelStyle(pos, thisIdx, sideCount[pos])} aria-hidden="true">
              {portLabel(iface)}
            </span>
          </React.Fragment>
        );
      })}

      <div className="netsim-node-icon">{icon}</div>
      <div className="netsim-node-content">
        <span className="netsim-node-label">{data.label}</span>
        <span className="netsim-node-sub">{role.toUpperCase()}</span>
      </div>
      <div className={`status-dot ${status}`} title={`Status: ${status}`} />
    </div>
  );
};
```

**2b.** Ensure `.netsim-node` allows overflow so labels outside the boundary
are visible. In `index.css`, find the `.netsim-node` block and confirm or add
`overflow: visible`. If `overflow` is not set, the default is `visible` and
no change is needed. If it is set to `hidden`, change it:

```css
/* Find and fix if present: */
.netsim-node {
  overflow: visible; /* must NOT be hidden — port labels extend beyond the border */
  …
}
```

---

### Step 3 — Add simulation-running colour to `SimulatedEdge.tsx`

**File:** `apps/frontend/src/canvas/edges/SimulatedEdge.tsx` *(modify)*

Currently edges are always grey unless faulted. When the simulation is running
they should turn green. Read the running state directly from the topology store
inside the edge component — this is allowed since edge components live inside
`apps/frontend/src/canvas/`.

Replace the entire file:

```typescript
import { BaseEdge, getSmoothStepPath } from '@xyflow/react';
import type { EdgeProps, Position } from '@xyflow/react';
import type { NetworkNode } from '@octet/shared-types';
import { useTopologyStore } from '../../store';
import type { ReactFlowEdge } from '../graphHelpers';

export const SimulatedEdge: React.FC<EdgeProps<ReactFlowEdge>> = ({
  id,
  sourceX,
  sourceY,
  sourcePosition,
  targetX,
  targetY,
  targetPosition,
  data,
  style,
  markerEnd,
}) => {
  const [edgePath] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition: sourcePosition as Position,
    targetX,
    targetY,
    targetPosition: targetPosition as Position,
    borderRadius: 6,
  });

  const faultActive = Boolean(data?.faultState?.active);

  // Green when any node is running (simulation is live).
  const isRunning = useTopologyStore(s =>
    s.nodes.some(n => (n.data as NetworkNode).runtimeState?.status === 'running'),
  );

  const stroke = faultActive
    ? 'var(--status-stopped)'       // red — faulted
    : isRunning
      ? '#4caf50'                   // green — simulation live
      : 'var(--text-secondary)';    // grey — idle/stopped

  return (
    <BaseEdge
      id={id}
      path={edgePath}
      style={{
        stroke,
        strokeWidth: faultActive ? 3 : 2,
        strokeDasharray: faultActive ? '8 6' : undefined,
        transition: 'stroke 0.4s ease',
        ...style,
      }}
      markerEnd={markerEnd}
    />
  );
};
```

> **Note:** `useTopologyStore` is already used inside `apps/frontend/src/canvas/`
> (e.g. `topology.slice.ts` re-exports it). Importing it here is allowed per
> AGENTS.md Rule 5 (canvas isolation only applies to `@xyflow/react` imports,
> not Zustand stores).

---

### Step 4 — Add filter bar to `LogConsole.tsx`

**File:** `apps/frontend/src/components/LogConsole.tsx` *(modify)*

Add a `filterText` state. Filter the `logs` array before rendering — only show
entries whose `message` or `source` includes the filter string
(case-insensitive). Show a small `×` button to clear the filter.

Replace the entire file:

```typescript
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
```

**File:** `apps/frontend/src/components/LogConsole.css` *(modify)*

Add styles for the filter bar after the existing `.log-console-actions button:hover` block:

```css
/* ── Filter bar ──────────────────────────────────────────────────────────── */

.log-console-filter {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 16px;
  border-bottom: 1px solid var(--panel-border);
  background: rgba(0, 0, 0, 0.1);
}

.log-filter-input {
  flex: 1;
  background: var(--input-bg);
  border: 1px solid var(--button-border);
  color: var(--text-primary);
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  outline: none;
}

.log-filter-input:focus {
  border-color: var(--accent-blue);
}

.log-filter-clear {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 16px;
  padding: 0 4px;
  line-height: 1;
}

.log-filter-clear:hover {
  color: var(--text-primary);
}

.log-filter-count {
  font-size: 11px;
  color: var(--text-secondary);
  white-space: nowrap;
  font-family: monospace;
}
```

---

## Tests to Add or Update

No automated tests are required for these changes — they are pure UI rendering
with no business logic. Verify manually per the checklist below.

If a test already exists that snapshots `LogConsole` or `BaseNode`, update it
to account for the new DOM structure (filter bar, label spans).

---

## Validation Commands

```powershell
# 1. Type check
cd apps/frontend
pnpm tsc --noEmit

# 2. Frontend tests (confirm nothing broken)
cd apps/frontend
pnpm vitest run

# 3. Backend tests (unchanged)
cd apps/api
.\.venv\Scripts\python.exe -m pytest --tb=short -q

# 4. Build
cd apps/frontend
pnpm build

# 5. Manual — handle animation
#    Hover over any port handle on a node. The handle should glow blue
#    (box-shadow) WITHOUT jumping or scaling. The center stays fixed.

# 6. Manual — port labels
#    Place a router. All four handles should show a small grey label
#    ("eth0", "eth1", etc.) just outside the node border.
#    Open the inspector, set 10.0.0.1/30 on eth0.
#    The label next to eth0's handle should update to "eth0: 10.0.0.1/30".

# 7. Manual — link colours
#    Connect two nodes, save, then Start simulation.
#    The link should turn green while simulation is running.
#    From the Test menu or the edge inspector, inject a fault.
#    The link should turn red/dashed. Stop the simulation → link returns to grey.

# 8. Manual — console filter
#    Open the log console. Type "probe" in the filter bar.
#    Only probe-related log entries are shown; count shows "N/total".
#    Click × or clear the input → all logs reappear.
#    Auto-scroll to bottom works normally when no filter is active.
```

---

## Architectural Checklist

- [ ] No `@xyflow/react` imports outside `apps/frontend/src/canvas/`
- [ ] No API calls in components — `SimulatedEdge` only reads from the store
- [ ] No `console.log` or `print()` debug statements
- [ ] `BaseNode.tsx` `sideIdx` counter is reset per render (not module-level state)
- [ ] Port labels have `pointerEvents: 'none'` so they don't interfere with canvas interactions
- [ ] `.netsim-node` has `overflow: visible` (check, don't blindly add)
- [ ] `SimulatedEdge` imports `useTopologyStore` from `../../store`, not from `@xyflow/react`
- [ ] Console filter is client-side only — no backend call, no store change
- [ ] All frontend tests pass
- [ ] Production build is clean (`pnpm build` exits 0)
