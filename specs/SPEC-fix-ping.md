# Spec: Fix Ping — Interface-Centric Target Resolution

**Branch:** `fix/fix-ping`
**Spec file:** `specs/SPEC-fix-ping.md`
**Status:** ready-for-implementation

---

## Goal

The Ping button in the Test menu is permanently disabled for any topology built
after the Auto-IP removal. The root cause is that `probeTargetIp` in
`TopologyCanvas.tsx` still reads from `logicalConfig.loopback` and
`ipConfig.targetIp` / `ipConfig.sourceIp` — both of which were populated by
the deleted Auto-IP service and are now always `undefined`. This fix replaces
that broken lookup with the correct interface-centric model: the default ping
target is the **first configured IP on any directly-connected peer node's
interfaces**. It also adds a small override input so the user can type a
custom target IP, and fixes the log message to show the source node label
instead of a raw UUID.

---

## Scope

**In scope:**
- Fix `probeTargetIp` useMemo in `TopologyCanvas.tsx` to read from
  `NetworkNode.logicalConfig.interfaces[].ip`
- Add `pingTargetIp` state (user override) and `effectivePingTarget` derived
  value in `TopologyCanvas.tsx`
- Add a small `Panel` at `bottom-center` with a Target IP input and Ping
  button, visible only when a node is selected and a topology is saved
- Reset `pingTargetIp` when selection changes
- Update `canPing`, Ping `onClick`, and Ping button `title` to use
  `effectivePingTarget`
- Fix log message in `useTopology.ts` `runProbe` to show the source node label
  instead of the UUID
- Add one unit test verifying the log label fix

**Out of scope (do not implement):**
- Backend changes — the mock engine's `run_probe` already works correctly
- Traceroute support
- Multi-target ping
- Any changes to the property inspector / PropertyPanel
- Any shared-type changes

---

## Files to Read First

| File | Why |
|------|-----|
| `apps/frontend/src/canvas/TopologyCanvas.tsx` | Full current file — every line, especially the `probeTargetIp` memo and `canPing` logic |
| `apps/frontend/src/hooks/useTopology.ts` | `runProbe` callback and the `nodes` destructure at line 22 |
| `apps/frontend/src/hooks/useTopology.test.ts` | Existing test structure to copy the `runProbe` test pattern |
| `packages/shared-types/src/topology.ts` | `LogicalInterface.ip` field — confirm the field name |

---

## Implementation Steps

### Step 1 — Fix `probeTargetIp` and add ping state in `TopologyCanvas.tsx`

**File:** `apps/frontend/src/canvas/TopologyCanvas.tsx` *(modify)*

**1a.** Add `pingTargetIp` state next to the existing `selectedTemplateId` state.

Before:
```typescript
  const [selectedTemplateId, setSelectedTemplateId] = useState('ospf-3-sites');
  const importInputRef = useRef<HTMLInputElement>(null);
```

After:
```typescript
  const [selectedTemplateId, setSelectedTemplateId] = useState('ospf-3-sites');
  const [pingTargetIp, setPingTargetIp] = useState('');
  const importInputRef = useRef<HTMLInputElement>(null);
```

**1b.** Add a `useEffect` import to React if not already present. The import line
at the top of the file is:

Before:
```typescript
import React, { useMemo, useRef, useState } from 'react';
```

After:
```typescript
import React, { useEffect, useMemo, useRef, useState } from 'react';
```

**1c.** Replace the broken `probeTargetIp` memo entirely.

Before:
```typescript
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
    return peerEdge?.source === selectedNode.id
      ? edgeData.ipConfig.targetIp
      : edgeData.ipConfig.sourceIp;
  }, [edges, nodes, selectedElementId, selectedElementType]);
```

After:
```typescript
  // Default ping target: first IP on any directly-connected peer node's interface.
  const probeTargetIp = useMemo(() => {
    if (selectedElementType !== 'node' || !selectedElementId) return null;
    const peerEdge = edges.find(e => e.source === selectedElementId || e.target === selectedElementId);
    if (!peerEdge) return null;
    const peerId = peerEdge.source === selectedElementId ? peerEdge.target : peerEdge.source;
    const peerNode = nodes.find(n => n.id === peerId);
    return peerNode?.data.logicalConfig?.interfaces?.find(i => i.ip)?.ip ?? null;
  }, [edges, nodes, selectedElementId, selectedElementType]);

  // User-supplied override; resets whenever the node selection changes.
  useEffect(() => {
    setPingTargetIp('');
  }, [selectedElementId]);

  // Effective target: user override wins; falls back to auto-resolved peer IP.
  const effectivePingTarget = pingTargetIp.trim() || probeTargetIp;
```

**1d.** Update `canPing` to use `effectivePingTarget`.

Before:
```typescript
  const canPing = selectedElementType === 'node' && Boolean(selectedElementId) && Boolean(probeTargetIp) && canStartStop;
```

After:
```typescript
  const canPing = selectedElementType === 'node' && Boolean(selectedElementId) && Boolean(effectivePingTarget) && canStartStop;
```

**1e.** Update the `workflowHint` line that mentions `probeTargetIp`.

Before:
```typescript
    if (selectedElementType === 'node' && !probeTargetIp) return 'Selected node has no IP configured on its interfaces yet.';
```

After:
```typescript
    if (selectedElementType === 'node' && !effectivePingTarget) return 'No connected node has an IP configured yet — or type a target IP in the ping bar below.';
```

**1f.** Update the Ping menu item in `ToolbarMenu` to use `effectivePingTarget`.

Before:
```typescript
              {
                label: 'Ping',
                onClick: () => selectedElementId && probeTargetIp && runProbe(selectedElementId, probeTargetIp),
                disabled: !canPing,
                title: !currentTopologyId
                  ? 'Save the topology before running a ping'
                  : selectedElementType !== 'node'
                    ? 'Select a node to run a ping'
                    : probeTargetIp
                      ? `Ping ${probeTargetIp} from the selected node`
                      : 'Select a node with an IP configured on its interfaces',
              },
```

After:
```typescript
              {
                label: 'Ping',
                onClick: () => selectedElementId && effectivePingTarget && runProbe(selectedElementId, effectivePingTarget),
                disabled: !canPing,
                title: !currentTopologyId
                  ? 'Save the topology before running a ping'
                  : selectedElementType !== 'node'
                    ? 'Select a node to run a ping'
                    : effectivePingTarget
                      ? `Ping ${effectivePingTarget} from the selected node`
                      : 'No target IP — connect a node with a configured IP or type one below',
              },
```

**1g.** Add the ping controls panel. Place it just **before** the closing `</ReactFlow>` tag (currently at line 302, just after the `workflowHint` Panel block).

Before:
```typescript
        {workflowHint && (
          <Panel position="bottom-left" style={hintStyle}>
            {workflowHint}
          </Panel>
        )}
      </ReactFlow>
```

After:
```typescript
        {workflowHint && (
          <Panel position="bottom-left" style={hintStyle}>
            {workflowHint}
          </Panel>
        )}

        {selectedElementType === 'node' && currentTopologyId && (
          <Panel position="bottom-center" style={pingBarStyle}>
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
              Ping target:
            </span>
            <input
              type="text"
              value={pingTargetIp}
              onChange={e => setPingTargetIp(e.target.value)}
              placeholder={probeTargetIp ?? '0.0.0.0'}
              style={pingInputStyle}
              aria-label="Ping target IP"
              onKeyDown={e => {
                if (e.key === 'Enter' && canPing && selectedElementId && effectivePingTarget) {
                  void runProbe(selectedElementId, effectivePingTarget);
                }
              }}
            />
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
          </Panel>
        )}
      </ReactFlow>
```

**1h.** Add the two new style objects at the bottom of the file alongside the other
style constants:

```typescript
const pingBarStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  background: 'var(--panel-bg)',
  padding: '8px 12px',
  borderRadius: '8px',
  border: '1px solid var(--panel-border)',
  backdropFilter: 'var(--panel-backdrop)',
};

const pingInputStyle = {
  ...inputStyle,
  width: '140px',
  fontFamily: 'monospace',
};
```

---

### Step 2 — Fix log message in `useTopology.ts`

**File:** `apps/frontend/src/hooks/useTopology.ts` *(modify)*

The `nodes` array is already destructured at the top of the hook (line 22). Just
update the `runProbe` callback body and its dependency array.

Before:
```typescript
  const runProbe = useCallback(async (sourceNodeId: string, targetIp: string) => {
    if (!currentTopologyId) {
      addLog('Save the topology before running a probe', 'warn', 'probe');
      return;
    }
    try {
      const result = await api.runProbe(currentTopologyId, {
        sourceNodeId,
        targetIp,
        probeType: 'ping',
      });
      addLog(`Ping ${sourceNodeId} → ${targetIp}: ${result.output}`, result.success ? 'info' : 'error', 'probe');
    } catch (err) {
      console.error('Probe failed', err);
      addLog('Probe failed', 'error', 'probe');
    }
  }, [currentTopologyId, addLog]);
```

After:
```typescript
  const runProbe = useCallback(async (sourceNodeId: string, targetIp: string) => {
    if (!currentTopologyId) {
      addLog('Save the topology before running a probe', 'warn', 'probe');
      return;
    }
    try {
      const result = await api.runProbe(currentTopologyId, {
        sourceNodeId,
        targetIp,
        probeType: 'ping',
      });
      const sourceLabel = nodes.find(n => n.id === sourceNodeId)?.data.label ?? sourceNodeId;
      addLog(`Ping ${sourceLabel} → ${targetIp}: ${result.output}`, result.success ? 'info' : 'error', 'probe');
    } catch (err) {
      addLog('Probe failed', 'error', 'probe');
    }
  }, [currentTopologyId, nodes, addLog]);
```

> **Note:** The `console.error` on the catch is removed per AGENTS.md Rule 8
> (no debug statements in committed code).

---

## Tests to Add or Update

### `apps/frontend/src/hooks/useTopology.test.ts`

**Test name:** `runProbe logs source node label instead of node ID`

**What it asserts:** When `runProbe` is called with a `sourceNodeId` that
matches a node in the store, the log entry contains the node's `label`
(not the raw UUID).

**Pattern to follow:** Look at the existing `runProbe` test in the file (search
for `runProbe` or `probe`) and copy its setup. The only difference is asserting
that the logged string contains the node label.

Concretely:
1. Seed the store with a node: `{ id: 'r1', label: 'R1', ... }`
2. Set `currentTopologyId` to a valid ID
3. Mock `api.runProbe` to resolve `{ success: true, output: 'Reply from 10.0.0.1: 3ms', rttMs: 3 }`
4. Call `runProbe('r1', '10.0.0.1')` via `act`
5. Assert that `useSimulationStore.getState().logs` contains an entry whose
   `message` includes `'R1'` and `'10.0.0.1'` — not `'r1'`.

---

## Validation Commands

```powershell
# 1. Type check
cd apps/frontend
pnpm tsc --noEmit

# 2. Frontend tests
cd apps/frontend
pnpm vitest run

# 3. Backend tests (unchanged — should still pass)
cd apps/api
.\.venv\Scripts\python.exe -m pytest --tb=short -q

# 4. Build
cd apps/frontend
pnpm build

# 5. Manual — ping with auto-target
#    Load the Hub-Spoke or OSPF 3-Sites template (IPs are baked in).
#    Save it. Select a router. The ping bar appears at bottom-center.
#    Input is pre-filled with the placeholder (peer's first interface IP).
#    Click "Ping ▶". Log console shows: "Ping R1 → 10.x.x.x: Reply from ..."

# 6. Manual — ping with manual override
#    Select a node with no peer IPs configured (e.g. a fresh node).
#    Ping bar shows empty input (placeholder "0.0.0.0").
#    Type "192.168.1.1" in the input. Ping button becomes enabled.
#    Click "Ping ▶". Log shows: "Ping [NodeLabel] → 192.168.1.1: Reply from ..."

# 7. Manual — selection change resets override
#    Type an IP in the ping bar for node A. Click node B.
#    The ping bar input clears (shows placeholder again).

# 8. Manual — Enter key triggers ping
#    Select a node, type a target IP, press Enter.
#    Same log entry appears as clicking the button.
```

---

## Architectural Checklist

- [ ] No `@xyflow/react` imports outside `apps/frontend/src/canvas/`
- [ ] No API calls directly in React components — ping still calls `runProbe` from the hook
- [ ] No `console.log` or `print()` debug statements (the `console.error` catch was removed)
- [ ] `probeTargetIp` reads from `logicalConfig.interfaces[].ip`, not from `loopback` or `ipConfig`
- [ ] `effectivePingTarget` = user override (if non-empty) else auto-resolved peer IP
- [ ] `pingTargetIp` state resets on `selectedElementId` change via `useEffect`
- [ ] Log message shows node label, not raw UUID
- [ ] `nodes` added to `runProbe` useCallback dependency array
- [ ] All frontend tests pass
- [ ] All backend tests pass
- [ ] Production build is clean (`pnpm build` exits 0)
