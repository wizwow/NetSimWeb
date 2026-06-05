# Spec: Minor UX Improvements — Launch Script, IP Controls, Delete, Smoothstep Edges

**Branch:** `feat/minor-ux-improvements`
**Spec file:** `specs/SPEC-minor-ux-improvements.md`
**Status:** ready-for-implementation

---

## Goal

Four self-contained improvements that make the app noticeably more usable:
1. A single `dev.ps1` script at the repo root that starts Docker, the backend,
   and the frontend in one command.
2. The IP field in the property inspector gets a real placeholder (`0.0.0.0`)
   and the Mask field becomes a CIDR dropdown instead of a free-text input.
3. Nodes and links can be deleted — via a Delete button in the inspector and
   via the `Delete`/`Backspace` keyboard shortcut on the canvas.
4. Edges render as smooth 90°-angle paths (`smoothstep`) instead of straight
   lines, which looks cleaner for network diagrams.

---

## Scope

**In scope:**
- `dev.ps1` at repo root — starts all three services
- `PropertyPanel.tsx` — IP placeholder, mask `<select>`, Delete buttons
- `PropertyPanel.css` — danger-button style
- `topology.slice.ts` — `removeEdge` action + interface cleanup in `removeNodes`
- `SimulatedEdge.tsx` — switch from `getStraightPath` to `getSmoothStepPath`

**Out of scope:**
- Drag-to-reattach edge endpoints on the canvas (separate spec)
- Obstacle-avoiding pathfinding (separate spec)
- Any backend changes
- Any shared-type changes

---

## Files to Read First

| File | Why |
|------|-----|
| `infra/docker-compose.dev.yml` | Service names and healthcheck details for the launch script |
| `apps/frontend/src/components/PropertyPanel.tsx` | Full current implementation — every line |
| `apps/frontend/src/components/PropertyPanel.css` | Existing button styles to match |
| `apps/frontend/src/store/topology.slice.ts` | `removeNodes` and action shape to extend |
| `apps/frontend/src/canvas/edges/SimulatedEdge.tsx` | Current path function to replace |
| `apps/frontend/src/canvas/TopologyCanvas.tsx` | ReactFlow props — confirm `onNodesChange`/`onEdgesChange` are wired |

---

## Implementation Steps

### Step 1 — Create `dev.ps1` at the repo root

**File:** `dev.ps1` *(create)*

```powershell
#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Start all Octet dev services: Docker infra, FastAPI backend, Vite frontend.
  Each service opens in its own PowerShell window so logs stay separate.
  Run from the repo root.
#>

$root = $PSScriptRoot

Write-Host "Starting Docker infrastructure (PostgreSQL + Redis)..." -ForegroundColor Cyan
docker compose -f "$root\infra\docker-compose.dev.yml" up -d

Write-Host "Waiting for containers to be healthy..." -ForegroundColor Cyan
$timeout = 30
$elapsed = 0
do {
    Start-Sleep -Seconds 2
    $elapsed += 2
    $status = docker compose -f "$root\infra\docker-compose.dev.yml" ps --format json 2>$null |
        ConvertFrom-Json -ErrorAction SilentlyContinue
    $allHealthy = $status | Where-Object { $_.Health -notin @('healthy', '') } | Measure-Object
    if ($allHealthy.Count -eq 0) { break }
} while ($elapsed -lt $timeout)

Write-Host "Starting FastAPI backend..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    '-NoExit',
    '-Command',
    "cd '$root\apps\api'; .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --reload --port 8000"
)

Write-Host "Starting Vite frontend..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    '-NoExit',
    '-Command',
    "cd '$root'; pnpm dev"
)

Write-Host ""
Write-Host "All services started." -ForegroundColor Green
Write-Host "  Frontend : http://localhost:5173" -ForegroundColor Green
Write-Host "  Backend  : http://localhost:8000" -ForegroundColor Green
Write-Host "  API docs : http://localhost:8000/docs" -ForegroundColor Green
```

---

### Step 2 — Add `removeEdge` action and fix `removeNodes` cleanup in the store

**File:** `apps/frontend/src/store/topology.slice.ts` *(modify)*

**2a.** Add `removeEdge` to the state interface. Find the line:

```typescript
  removeNodes: (nodeIds: string[]) => void;
```

Add after it:

```typescript
  removeEdge: (edgeId: string) => void;
```

**2b.** Replace the `removeNodes` implementation to also free peer interfaces
when a node is deleted. Find the block:

```typescript
    removeNodes: (nodeIds) => set((state) => {
      state.nodes = state.nodes.filter(n => !nodeIds.includes(n.id));
      state.edges = state.edges.filter(e => !nodeIds.includes(e.source) && !nodeIds.includes(e.target));
    }),
```

Replace with:

```typescript
    removeNodes: (nodeIds) => set((state) => {
      // Free interfaces on peer nodes before removing edges
      for (const nodeId of nodeIds) {
        for (const edge of state.edges.filter(e => e.source === nodeId || e.target === nodeId)) {
          if (!edge.data) continue;
          if (edge.source === nodeId) {
            const tgt = state.nodes.find(n => n.id === edge.target);
            const iface = tgt?.data.logicalConfig?.interfaces.find(i => i.name === edge.data!.targetPort);
            if (iface) iface.status = 'down';
          } else {
            const src = state.nodes.find(n => n.id === edge.source);
            const iface = src?.data.logicalConfig?.interfaces.find(i => i.name === edge.data!.sourcePort);
            if (iface) iface.status = 'down';
          }
        }
      }
      state.nodes = state.nodes.filter(n => !nodeIds.includes(n.id));
      state.edges = state.edges.filter(e => !nodeIds.includes(e.source) && !nodeIds.includes(e.target));
    }),
```

**2c.** Add the `removeEdge` implementation directly after `removeNodes`:

```typescript
    removeEdge: (edgeId) => set((state) => {
      const edge = state.edges.find(e => e.id === edgeId);
      if (edge?.data) {
        const src = state.nodes.find(n => n.id === edge.source);
        const srcIface = src?.data.logicalConfig?.interfaces.find(i => i.name === edge.data!.sourcePort);
        if (srcIface) srcIface.status = 'down';
        const tgt = state.nodes.find(n => n.id === edge.target);
        const tgtIface = tgt?.data.logicalConfig?.interfaces.find(i => i.name === edge.data!.targetPort);
        if (tgtIface) tgtIface.status = 'down';
      }
      state.edges = state.edges.filter(e => e.id !== edgeId);
    }),
```

---

### Step 3 — Add Delete buttons to `PropertyPanel.tsx`

**File:** `apps/frontend/src/components/PropertyPanel.tsx` *(modify)*

**3a.** Add `removeNodes` and `removeEdge` to the destructured store call. Find:

```typescript
  const { nodes, edges, updateNode, updateNodeInterface } = useTopologyStore();
```

Replace with:

```typescript
  const { nodes, edges, updateNode, updateNodeInterface, removeNodes, removeEdge } = useTopologyStore();
```

**3b.** Add delete handlers after the `saveIface` function (before the early
`if (!propertyPanelOpen) return null;` return):

```typescript
  const handleDeleteNode = () => {
    if (!selectedElementId) return;
    removeNodes([selectedElementId]);
    closePropertyPanel();
  };

  const handleDeleteEdge = () => {
    if (!selectedElementId) return;
    removeEdge(selectedElementId);
    closePropertyPanel();
  };
```

**3c.** Add the Delete button at the bottom of the **node panel** section.
Find the closing of the node panel (just before the edge panel comment):

```typescript
            <div className="status-section">
              <label>Node Status</label>
              <div className={`status-indicator ${nodeData.runtimeState?.status ?? 'stopped'}`}>
                {nodeData.runtimeState?.status ?? 'stopped'}
              </div>
            </div>
          </>
        )}
```

Replace with:

```typescript
            <div className="status-section">
              <label>Node Status</label>
              <div className={`status-indicator ${nodeData.runtimeState?.status ?? 'stopped'}`}>
                {nodeData.runtimeState?.status ?? 'stopped'}
              </div>
            </div>

            <button className="delete-btn" onClick={handleDeleteNode}>
              Delete Node
            </button>
          </>
        )}
```

**3d.** Add the Delete button at the bottom of the **edge panel** section.
Find the closing of the edge panel:

```typescript
          </div>
        )}
      </div>
    </div>
```

The edge panel ends with the Target `<div className="link-info">` block. After that
closing `</div>` of `property-group` and before the outer closing tags, add:

```typescript
          <button className="delete-btn" onClick={handleDeleteEdge}>
            Delete Link
          </button>
        )}
```

So the full closing sequence of the edge panel becomes:

```typescript
            <label>Target</label>
            <div className="link-info" title={`ID: ${edgeData.targetNodeId}`}>
              <span>{(targetNode?.data as NetworkNode | undefined)?.label ?? edgeData.targetNodeId}</span>
              <span className="badge">{edgeData.targetPort}</span>
            </div>

            <button className="delete-btn" onClick={handleDeleteEdge}>
              Delete Link
            </button>
          </div>
        )}
      </div>
    </div>
  );
```

---

### Step 4 — Add the `delete-btn` style to `PropertyPanel.css`

**File:** `apps/frontend/src/components/PropertyPanel.css` *(modify)*

Append at the end of the file:

```css
/* ── Delete button ───────────────────────────────────────────────────────── */

.delete-btn {
  margin-top: 20px;
  padding: 8px 12px;
  width: 100%;
  background: rgba(244, 67, 54, 0.08);
  border: 1px solid rgba(244, 67, 54, 0.3);
  color: #f44336;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.delete-btn:hover {
  background: rgba(244, 67, 54, 0.18);
  border-color: rgba(244, 67, 54, 0.6);
}
```

---

### Step 5 — Update IP placeholder and replace Mask input with dropdown

**File:** `apps/frontend/src/components/PropertyPanel.tsx` *(modify)*

Find the IP input inside the interface map:

```typescript
                          <input
                            type="text"
                            className="iface-input"
                            value={edits.ip}
                            placeholder="—"
```

Replace `placeholder="—"` with `placeholder="0.0.0.0"`:

```typescript
                          <input
                            type="text"
                            className="iface-input"
                            value={edits.ip}
                            placeholder="0.0.0.0"
```

Find the Mask `<input>` block inside the interface map:

```typescript
                        <div className="iface-field">
                          <span className="iface-field-label">Mask</span>
                          <input
                            type="text"
                            className="iface-input iface-input--mask"
                            value={edits.subnet}
                            placeholder="/—"
                            onChange={e => setIfaceEdits(prev => ({
                              ...prev,
                              [iface.name]: { ...prev[iface.name], subnet: e.target.value },
                            }))}
                            onBlur={() => saveIface(iface.name)}
                          />
                        </div>
```

Replace the entire `<div className="iface-field">` block for Mask with:

```typescript
                        <div className="iface-field">
                          <span className="iface-field-label">Mask</span>
                          <select
                            className="iface-input iface-input--mask"
                            value={edits.subnet}
                            onChange={e => {
                              const val = e.target.value;
                              setIfaceEdits(prev => ({
                                ...prev,
                                [iface.name]: { ...prev[iface.name], subnet: val },
                              }));
                              updateNodeInterface(selectedElementId!, iface.name, {
                                ip: ifaceEdits[iface.name]?.ip,
                                subnet: val,
                              });
                            }}
                          >
                            <option value="">—</option>
                            <option value="/8">/8</option>
                            <option value="/16">/16</option>
                            <option value="/24">/24</option>
                            <option value="/25">/25</option>
                            <option value="/28">/28</option>
                            <option value="/29">/29</option>
                            <option value="/30">/30</option>
                            <option value="/31">/31</option>
                            <option value="/32">/32</option>
                          </select>
                        </div>
```

> **Note:** The `<select>` saves immediately on change (no blur needed) since the
> value is always a valid option. Remove the `onBlur` — it is replaced by `onChange`.

---

### Step 6 — Switch edges to smoothstep routing

**File:** `apps/frontend/src/canvas/edges/SimulatedEdge.tsx` *(modify)*

Replace the entire file content with:

```typescript
import { BaseEdge, getSmoothStepPath } from '@xyflow/react';
import type { EdgeProps, Position } from '@xyflow/react';
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

  return (
    <BaseEdge
      id={id}
      path={edgePath}
      style={{
        stroke: faultActive ? 'var(--status-stopped)' : 'var(--text-secondary)',
        strokeWidth: faultActive ? 3 : 2,
        strokeDasharray: faultActive ? '8 6' : undefined,
        ...style,
      }}
      markerEnd={markerEnd}
    />
  );
};
```

---

## Tests to Add or Update

### `apps/frontend/src/store/topology.slice.test.ts` — add two tests

**Test 1**
- **Name:** `removeEdge frees both interface slots`
- **What it asserts:** after adding two nodes, connecting them (via `onConnect`
  with a mock connection), then calling `removeEdge(edgeId)`, both nodes'
  interfaces involved return to status `'down'`.

**Test 2**
- **Name:** `removeNodes frees peer interface when a node is deleted`
- **What it asserts:** after adding two nodes and connecting them, calling
  `removeNodes([sourceNodeId])` sets the target node's connected interface
  back to `'down'`.

---

## Validation Commands

```powershell
# 1. Frontend tests
cd apps/frontend
pnpm vitest run

# 2. Backend tests (unchanged — should still pass)
cd apps/api
.\.venv\Scripts\python.exe -m pytest --tb=short -q

# 3. Type check
cd apps/frontend
pnpm tsc --noEmit

# 4. Build
cd apps/frontend
pnpm build

# 5. Manual — launch script
#    Run: .\dev.ps1
#    Expected: two new PowerShell windows open (backend + frontend),
#    docker containers are running, app loads at http://localhost:5173

# 6. Manual — delete
#    Place two nodes, draw a link. Click the source node → inspector shows
#    "Delete Node" button. Click it → node and its link both disappear,
#    inspector closes. The peer node's interface that was connected should
#    show status DOWN.
#    Select a link → "Delete Link" button → link disappears, both endpoints'
#    interfaces revert to DOWN.
#    Select a node and press Delete/Backspace on keyboard → same result.

# 7. Manual — IP controls
#    Click a node. In the Interfaces section: IP field shows "0.0.0.0"
#    placeholder. Mask field is a dropdown with /8…/32 options.
#    Select /30 → value saves immediately (no blur needed).
#    Type an IP, blur → IP saves. Reload topology → both persist.

# 8. Manual — edges
#    Load any template or draw two connected nodes.
#    Edges should render as right-angle paths (not straight lines).
#    Fault a link → dashed red right-angle path.
```

---

## Architectural Checklist

- [ ] No `@xyflow/react` imports outside `apps/frontend/src/canvas/`
- [ ] No API calls in React components — delete actions go through the store
- [ ] No `console.log` or `print()` debug statements
- [ ] `removeEdge` frees both interface statuses before removing the edge
- [ ] `removeNodes` frees peer interface statuses before removing edges
- [ ] The mask `<select>` saves on `onChange` (not `onBlur`) — no stale value
- [ ] `dev.ps1` uses `$PSScriptRoot` so it works regardless of the caller's CWD
- [ ] All frontend tests pass
- [ ] All backend tests pass
- [ ] Production build is clean (`pnpm build` exits 0)
