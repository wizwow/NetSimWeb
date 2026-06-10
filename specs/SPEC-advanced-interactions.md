# Spec: Advanced Canvas Interactions — Switch Patch Panel + Click-to-Ping

**Branch:** `feat/advanced-interactions`
**Spec file:** `specs/SPEC-advanced-interactions.md`
**Status:** ready-for-implementation

---

## Goal

Two focused UX improvements:

1. **Switch patch panel** (#2): The switch node currently renders handles using the
   same four-sided CYCLE layout as routers. With 8 interfaces (2 per side), cables
   visually crowd the node sides and it is not obvious each port is a dedicated
   physical slot. Replace the SwitchNode renderer with a custom "patch panel" layout —
   a wide box with a row of numbered rectangular port slots along the bottom edge, each
   with its own React Flow Handle. This mirrors how a real managed switch looks.

2. **Click-to-ping target selection** (#13): When the ping bar is visible the user has
   to manually type a target IP. Add a "Pick" button that activates a temporary pick
   mode; while active, clicking any canvas node (or its row in the Topology Objects
   Panel) copies that node's first configured interface IP into the ping target field,
   without changing the current node selection.

---

## Scope

**In scope:**
- New `SwitchNode.css` (create)
- `SwitchNode.tsx` rewritten to custom patch-panel renderer (no longer wraps `BaseNode`)
- `TopologyCanvas.tsx` — `pingPickMode` state, updated `onNodeClick`, updated
  `onPaneClick`, Escape-to-cancel effect, "Pick" button in the ping bar, pick mode
  overlay hint
- No backend changes, no shared-types changes, no `nodeFactory.ts` / `nodeTypes.ts`
  changes (SwitchNode is already registered)

**Out of scope (do not implement):**
- Visual traceroute animation (item #8 — deferred to Phase 5)
- Draggable port handles (item #11 — deferred to Phase 5)
- Integration with TopologyObjectsPanel click-to-ping (handled when that panel is
  implemented — the pick mode state is already wired to `setPingTargetIp`)
- Any changes to `BaseNode.tsx`, `RouterNode.tsx`, `HostNode.tsx`

---

## Files to Read First

| File | Why |
|------|-----|
| `apps/frontend/src/canvas/nodes/SwitchNode.tsx` | Current (thin) implementation to replace |
| `apps/frontend/src/canvas/nodes/BaseNode.tsx` | Handle+label pattern to understand, NOT copy |
| `apps/frontend/src/canvas/TopologyCanvas.tsx` | Current ping bar + onNodeClick exact code |
| `packages/shared-types/src/topology.ts` | `LogicalInterface` shape — `name`, `ip`, `subnet`, `status` |
| `apps/frontend/src/store/topology.slice.ts` | Confirm `nodes` shape for the pick handler |

---

## Implementation Steps

### Step 1 — Create `SwitchNode.css`

**File:** `apps/frontend/src/canvas/nodes/SwitchNode.css` *(create)*

```css
/* ─── Switch node outer shell ─────────────────────────────────────────────── */
.switch-node {
  position: relative;
  background: var(--panel-bg);
  border: 1px solid var(--panel-border);
  border-radius: 8px;
  padding: 8px 12px 30px;   /* large bottom padding reserves space for port row */
  min-width: 210px;
  backdrop-filter: var(--panel-backdrop);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  transition: box-shadow 0.2s, border-color 0.2s;
  cursor: grab;
  user-select: none;
}

/* ─── Header ──────────────────────────────────────────────────────────────── */
.switch-node-header {
  display: flex;
  align-items: center;
  gap: 6px;
}

.switch-node-label {
  flex: 1;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ─── Port strip ──────────────────────────────────────────────────────────── */
/* Absolutely positioned inside the node, above the bottom border.             */
/* Individual slots are positioned using the same (idx+1)/(count+1) formula    */
/* that the Handles use, so slots and handles align horizontally.              */
.switch-port-row {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 6px;
  height: 18px;
}

.switch-port-slot {
  position: absolute;
  transform: translateX(-50%);
  width: 20px;
  height: 14px;
  border-radius: 2px;
  border: 1px solid var(--button-border);
  background: var(--input-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s, border-color 0.2s;
  top: 2px;           /* centered in .switch-port-row */
}

.switch-port-slot.up {
  background: rgba(76, 175, 80, 0.22);
  border-color: #4caf50;
}

.switch-port-num {
  font-size: 7px;
  font-family: monospace;
  font-weight: 700;
  color: var(--text-secondary);
  line-height: 1;
}

/* ─── Handles ─────────────────────────────────────────────────────────────── */
/* React Flow places Position.Bottom handles at the bottom edge.               */
/* We override only the width / height / colour; left is set via inline style. */
.switch-port-handle {
  width: 8px !important;
  height: 8px !important;
  border: 2px solid var(--panel-border) !important;
  background: var(--bg-canvas, var(--panel-bg)) !important;
  transition: border-color 0.2s, background 0.2s, box-shadow 0.2s;
}

.switch-port-handle.up {
  border-color: rgba(76, 175, 80, 0.5) !important;
}

.switch-port-handle:hover {
  border-color: var(--accent-blue) !important;
  background: var(--accent-blue) !important;
  box-shadow: 0 0 0 3px var(--accent-blue-glow), 0 0 8px var(--accent-blue);
}
```

---

### Step 2 — Rewrite `SwitchNode.tsx`

**File:** `apps/frontend/src/canvas/nodes/SwitchNode.tsx` *(modify)*

Replace the entire file with:

```typescript
import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import type { NetworkNode } from '@octet/shared-types';
import { Network } from 'lucide-react';
import './SwitchNode.css';

/**
 * Switch node rendered as a patch-panel: a horizontal strip of numbered port
 * slots, each with its own React Flow Handle at the bottom edge.
 *
 * Both the visual slot and the Handle share the formula
 *   left = (idx + 1) / (count + 1) * 100%
 * so they align horizontally regardless of how many interfaces exist.
 */
export const SwitchNode = memo(({ data }: NodeProps) => {
  const nodeData = data as NetworkNode;
  const status = nodeData.runtimeState?.status ?? 'stopped';
  const interfaces = nodeData.logicalConfig?.interfaces ?? [];
  const count = interfaces.length;

  return (
    <div className="switch-node">

      {/* React Flow connection handles — one per interface at the bottom edge */}
      {interfaces.map((iface, idx) => (
        <Handle
          key={iface.name}
          type="source"
          position={Position.Bottom}
          id={iface.name}
          className={`switch-port-handle ${iface.status}`}
          style={{ left: `${(idx + 1) / (count + 1) * 100}%` }}
          title={
            iface.ip
              ? `${iface.name}: ${iface.ip}${iface.subnet ?? ''}`
              : iface.name
          }
        />
      ))}

      {/* Header */}
      <div className="switch-node-header">
        <Network size={14} color="var(--node-switch)" />
        <span className="switch-node-label">{nodeData.label}</span>
        <div className={`status-dot ${status}`} title={`Status: ${status}`} />
      </div>

      {/* Port strip */}
      <div className="switch-port-row">
        {interfaces.map((iface, idx) => (
          <div
            key={iface.name}
            className={`switch-port-slot ${iface.status}`}
            style={{ left: `${(idx + 1) / (count + 1) * 100}%` }}
            title={
              iface.ip
                ? `${iface.name}: ${iface.ip}${iface.subnet ?? ''}`
                : iface.name
            }
          >
            <span className="switch-port-num">{idx + 1}</span>
          </div>
        ))}
      </div>

    </div>
  );
});

SwitchNode.displayName = 'SwitchNode';
```

---

### Step 3 — Add `pingPickMode` state and Escape handler to `TopologyCanvas.tsx`

**File:** `apps/frontend/src/canvas/TopologyCanvas.tsx` *(modify)*

**3a.** Add `pingPickMode` to the existing state declarations (after `activeMenu`):

Before:
```typescript
  const [activeMenu, setActiveMenu] = useState<string | null>(null);
  const toggleMenu = (label: string) => setActiveMenu(prev => prev === label ? null : label);
```

After:
```typescript
  const [activeMenu, setActiveMenu] = useState<string | null>(null);
  const toggleMenu = (label: string) => setActiveMenu(prev => prev === label ? null : label);
  const [pingPickMode, setPingPickMode] = useState(false);
```

**3b.** Add a `useEffect` that cancels pick mode whenever the selection changes (place
it directly after the existing `useEffect` that resets `pingTargetIp`):

Before:
```typescript
  // User-supplied override; resets whenever the node selection changes.
  useEffect(() => {
    setPingTargetIp('');
  }, [selectedElementId]);
```

After:
```typescript
  // User-supplied override; resets whenever the node selection changes.
  useEffect(() => {
    setPingTargetIp('');
    setPingPickMode(false);
  }, [selectedElementId]);
```

**3c.** Add an `Escape` key handler `useEffect` — place it after Step 3b's effect:

```typescript
  // Cancel pick mode on Escape.
  useEffect(() => {
    if (!pingPickMode) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setPingPickMode(false);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [pingPickMode]);
```

---

### Step 4 — Update `onNodeClick` and `onPaneClick` in the ReactFlow component

**File:** `apps/frontend/src/canvas/TopologyCanvas.tsx` *(modify)*

**4a.** Replace the inline `onNodeClick` prop:

Before:
```typescript
        onNodeClick={(_, node) => setSelectedElement(node.id, 'node')}
```

After:
```typescript
        onNodeClick={(_, node) => {
          if (pingPickMode) {
            const d = node.data as NetworkNode;
            const firstIp = d.logicalConfig?.interfaces?.find(i => i.ip)?.ip;
            if (firstIp) setPingTargetIp(firstIp);
            setPingPickMode(false);
            return; // do NOT change selection
          }
          setSelectedElement(node.id, 'node');
        }}
```

**4b.** Replace the inline `onPaneClick` prop so that clicking empty canvas also cancels
pick mode:

Before:
```typescript
        onPaneClick={() => setSelectedElement(null, null)}
```

After:
```typescript
        onPaneClick={() => {
          if (pingPickMode) { setPingPickMode(false); return; }
          setSelectedElement(null, null);
        }}
```

**4c.** Add pick mode cursor to ReactFlow. Add a `style` prop to `<ReactFlow>`:

Before:
```typescript
        connectionMode={ConnectionMode.Loose}
        colorMode={theme}
        fitView
```

After:
```typescript
        connectionMode={ConnectionMode.Loose}
        colorMode={theme}
        fitView
        style={{ cursor: pingPickMode ? 'crosshair' : undefined }}
```

---

### Step 5 — Add "Pick" button and pick mode overlay to `TopologyCanvas.tsx`

**File:** `apps/frontend/src/canvas/TopologyCanvas.tsx` *(modify)*

**5a.** Extend the ping bar with a "Pick" button. The ping bar section currently ends
with the `Ping ▶` button inside the absolute div. Add the Pick button BEFORE the Ping
button:

Before:
```typescript
          <button
            style={{
              ...buttonStyle,
              opacity: canPing ? 1 : 0.45,
              cursor: canPing ? 'pointer' : 'not-allowed',
            }}
            disabled={!canPing}
            onClick={() => selectedElementId && effectivePingTarget && runProbe(selectedElementId, effectivePingTarget)}
            title={canPing ? `Ping ${effectivePingTarget}` : 'No target IP configured'}
          >
            Ping ▶
          </button>
```

After:
```typescript
          <button
            style={{
              ...buttonStyle,
              background: pingPickMode ? 'var(--accent-blue)' : (buttonStyle as React.CSSProperties).background,
              color: pingPickMode ? '#fff' : (buttonStyle as React.CSSProperties).color,
            }}
            onClick={() => setPingPickMode(p => !p)}
            title="Click a node on the canvas to use its IP as the ping target"
          >
            {pingPickMode ? '✕ Cancel' : '⊕ Pick'}
          </button>
          <button
            style={{
              ...buttonStyle,
              opacity: canPing ? 1 : 0.45,
              cursor: canPing ? 'pointer' : 'not-allowed',
            }}
            disabled={!canPing}
            onClick={() => selectedElementId && effectivePingTarget && runProbe(selectedElementId, effectivePingTarget)}
            title={canPing ? `Ping ${effectivePingTarget}` : 'No target IP configured'}
          >
            Ping ▶
          </button>
```

**5b.** Add the pick mode overlay hint. Place it inside the outer wrapper `<div>`
(which already has `position: 'relative'`), just BEFORE `<PropertyPanel />`:

Before:
```typescript
      <PropertyPanel />
```

After:
```typescript
      {pingPickMode && (
        <div style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          pointerEvents: 'none',
          zIndex: 1200,
          background: 'rgba(33, 150, 243, 0.12)',
          border: '2px dashed var(--accent-blue)',
          color: 'var(--accent-blue)',
          padding: '10px 20px',
          borderRadius: '10px',
          fontSize: '14px',
          fontWeight: 600,
          whiteSpace: 'nowrap',
          backdropFilter: 'blur(4px)',
        }}>
          Click a node to set it as ping target · Esc to cancel
        </div>
      )}
      <PropertyPanel />
```

---

## Tests to Add or Update

No new automated tests required for these purely visual/interaction changes.

If snapshot tests exist for `TopologyCanvas` or `SwitchNode`, regenerate them after
implementation (`pnpm vitest run --update-snapshot`).

---

## Validation Commands

```powershell
# 1. Type check
cd apps/frontend
pnpm tsc --noEmit

# 2. Frontend tests
cd apps/frontend
pnpm vitest run

# 3. Backend tests (unchanged — quick sanity)
cd apps/api
.\.venv\Scripts\python.exe -m pytest --tb=short -q

# 4. Build
cd apps/frontend
pnpm build

# ── Switch patch panel manual checks ─────────────────────────────────────────
# 5. Load a template (e.g. ospf-3-sites) that has switches.
#    Switch nodes should display as a wide patch-panel rectangle with a row of
#    numbered grey slot rectangles along the bottom.
#
# 6. Hover over a port slot → tooltip shows interface name and IP (if configured).
#
# 7. Hover over a handle (small circle at bottom edge) → it glows blue.
#
# 8. Drag a cable FROM a switch port → it snaps to the numbered slot's handle.
#    Two cables attached to different ports should connect to visually distinct
#    slot positions — no two cables share the same visual attachment point.
#
# 9. After simulation starts, the slot for a connected interface changes to
#    green background (status 'up'). Faulted link → slot stays grey (status
#    is not 'up').

# ── Click-to-ping manual checks ───────────────────────────────────────────────
# 10. Click a router (R1) → ping bar appears at bottom.
#
# 11. Click "⊕ Pick" → button turns blue / label changes to "✕ Cancel".
#     A dashed blue hint overlay appears in the centre of the canvas:
#     "Click a node to set it as ping target · Esc to cancel"
#     The canvas cursor becomes a crosshair.
#
# 12. Click R2 on the canvas → R1 remains selected (property panel stays on R1),
#     the hint disappears, the pick button reverts, and the ping target input
#     now shows R2's first configured IP.
#
# 13. Click "⊕ Pick" then press Escape → pick mode is cancelled with no change
#     to the ping target.
#
# 14. Click "⊕ Pick" then click empty canvas → pick mode is cancelled, selection
#     is NOT cleared (R1 remains selected).
```

---

## Architectural Checklist

- [ ] No `@xyflow/react` imports outside `apps/frontend/src/canvas/`
- [ ] No API calls in `SwitchNode.tsx` — reads `data` prop only
- [ ] Pick mode logic stays inside `TopologyCanvas.tsx` — no new store state required
- [ ] `onNodeClick` guard: when `pingPickMode` is true, selection is NOT changed
- [ ] SwitchNode renders handle `id` equal to `iface.name` (matches save/reload contract)
- [ ] `SwitchNode.displayName` is set (aids React DevTools debugging)
- [ ] No `console.log` or `print()` debug statements
- [ ] All frontend type checks pass
- [ ] Production build is clean (`pnpm build` exits 0)
