# Spec: Update AGENTS.md and MANUAL_TESTING.md for green-v0

**Branch:** `chore/update-agent-docs-green-v0`
**Spec file:** `specs/SPEC-update-agent-docs-green-v0.md`
**Status:** ready-for-implementation

---

## Goal

The codebase just reached `green-v0`: Auto-IP was deleted, nodes now spawn with
correct interface sets, linking is reliable, and the property inspector exposes
editable IP/mask fields per interface. `AGENTS.md` and `MANUAL_TESTING.md` still
describe the old world (Auto-IP as a feature, old node recipes, stale roadmap).
This task brings both files in sync so that any future AI agent or human starts
with accurate context.

**This task is documentation-only. Do not modify any source code.**

---

## Scope

**In scope:**
- Remove all references to `autoip.py`, `assign_topology_ips()`, and the
  Auto-IP button/feature from `AGENTS.md`
- Update `AGENTS.md` Hard Stops, architecture rules, recipes, roadmap, and
  technical debt to match green-v0 reality
- Replace the Auto-IP step in `MANUAL_TESTING.md` with the new interface
  workflow
- Update the Ping step in `MANUAL_TESTING.md` to reference interface IPs
  instead of Auto-IP output
- Update the Import/Export steps to reflect that interface IPs now survive
  round-trips

**Out of scope (do not implement):**
- Any source code changes
- Adding new features to the checklist that don't exist yet (GNS3, DOCX, CLI)
- Changing architectural rules that are still valid

---

## Files to Read First

Before writing any changes, read these files in full to understand current
content and what is stale:

| File | Why |
|------|-----|
| `AGENTS.md` | The file to update — read every section |
| `MANUAL_TESTING.md` | The file to update — read every step |
| `apps/frontend/src/canvas/nodes/nodeFactory.ts` | New factory pattern to document |
| `apps/frontend/src/canvas/graphHelpers.ts` | `getNextFreePort` to document |
| `packages/shared-types/src/topology.ts` | `LogicalInterface` shape to reference |
| `apps/frontend/src/store/topology.slice.ts` | `updateNodeInterface` action to document |

---

## Implementation Steps

Complete these steps in order. Do not skip steps. Do not combine steps.

### Step 1 — Remove Auto-IP from AGENTS.md Hard Stops

**File:** `AGENTS.md` *(modify)*

Find the Hard Stops table (Section 1). Remove row #7 entirely:

Before:
```markdown
| 7 | Modify already-assigned IPs in `assign_topology_ips()` |
```

After:
*(row deleted — renumber subsequent rows so the table stays sequential from 1–9)*

---

### Step 2 — Replace Rule 6 (Auto-IP) with the Interface Addressing rule

**File:** `AGENTS.md` *(modify)*

Find Section 3, `### Rule 6 — Auto-IP is Idempotent`. Replace the entire rule
block with the new rule below.

Before:
```markdown
### Rule 6 — Auto-IP is Idempotent

`assign_topology_ips()` in `apps/api/app/services/autoip.py` must never modify
an IP that is already assigned. Same input always produces same output.
```

After:
```markdown
### Rule 6 — Interfaces Are the Source of Truth for Addressing

IP addresses live on **interfaces**, not on links. The correct data path is:

- A node's IPs are stored in `NetworkNode.logicalConfig.interfaces[]` as
  `LogicalInterface.ip` and `LogicalInterface.subnet`.
- Links store only connectivity (`sourcePort`, `targetPort`) — never IPs.
- `NetworkLink.ipConfig` is kept for backward-compat read but must not be
  written by new code.

When creating a new node, always use `createNode()` from
`apps/frontend/src/canvas/nodes/nodeFactory.ts`. Never construct a raw
`NetworkNode` object without calling this factory — it is the only place that
populates the correct `logicalConfig.interfaces` set for the node's type.

To update an interface's IP from the UI, call `updateNodeInterface(nodeId,
ifaceName, { ip, subnet })` on the topology store. Never mutate
`logicalConfig.interfaces` directly inside a component.

Auto-IP (`apps/api/app/services/autoip.py`) has been **deleted**. Do not
re-introduce it.
```

---

### Step 3 — Update the New Canvas Node Type recipe

**File:** `AGENTS.md` *(modify)*

Find Section 5, `### New Canvas Node Type`. Replace the 5-step recipe with
the updated version that includes the factory:

Before:
```markdown
### New Canvas Node Type

1. `apps/frontend/src/canvas/nodes/NameNode.tsx` — component wrapped in `React.memo`
2. `packages/shared-types/src/topology.ts` — add the new type literal to `NodeType`
3. `apps/frontend/src/canvas/nodeTypes.ts` — register the component
4. `apps/frontend/src/canvas/palette/PaletteItems.ts` — add icon + label metadata
5. Run `cd packages/shared-types && pnpm build`
```

After:
```markdown
### New Canvas Node Type

1. `packages/shared-types/src/topology.ts` — add the new type literal to
   `NodeBaseType`.
2. `apps/frontend/src/canvas/nodes/nodeFactory.ts` — add the default interface
   list to `INTERFACE_DEFAULTS[newType]`.
3. `apps/frontend/src/canvas/nodes/NewTypeNode.tsx` — component using `BaseNode`
   wrapped in `React.memo`. `BaseNode` renders handles automatically from
   `data.logicalConfig.interfaces`; do **not** add hardcoded `<Handle>` elements.
4. `apps/frontend/src/canvas/nodeTypes.ts` — register the component.
5. Run `cd packages/shared-types && pnpm build`.

Key constraints:
- Node creation in the UI must always go through `createNode(baseType, label,
  position)` from `nodeFactory.ts`.
- Handle IDs are derived from interface names (`eth0`, `eth1`, …). This is
  required so that `toReactFlowEdge` can reconstruct edges after a save/reload.
  Never assign positional IDs (`'top'`, `'left'`, etc.) to handles.
```

---

### Step 4 — Update the Roadmap Quick Reference

**File:** `AGENTS.md` *(modify)*

Find Section 10, `## 10. Roadmap Quick Reference`. Replace the **Done** paragraph
and the **Partial** and **Not started** bullets so they match green-v0 reality.

Before:
```markdown
**Done (do not re-implement):** monorepo, React Flow canvas, Zustand stores, FastAPI CRUD, PostgreSQL schema, Alembic migration, Docker Compose dev infra, mock simulation engine, WebSocket events, Auto-IP, property panel, log console, topology templates (Blank/Hub-Spoke/OSPF 3 Sites), probe endpoint, link fault endpoint, Redis event bridge, export routes (JSON/MD/PDF/DOC), JWT auth v1 (register/login/me), frontend login screen.

**Partial (extend, do not rebuild):** auth hardening, GNS3 live provisioning, Redis multi-worker testing, frontend hook/canvas tests.

**Not started:** live GNS3 node/link provisioning, native DOCX export, CLI terminal.
```

After:
```markdown
**Done (do not re-implement):** monorepo, React Flow canvas, Zustand stores,
FastAPI CRUD, PostgreSQL schema, Alembic migration, Docker Compose dev infra,
mock simulation engine, WebSocket events, interface-centric node factory
(`nodeFactory.ts`), reliable bidirectional linking (`getNextFreePort`),
property inspector with per-interface IP/mask editing (`updateNodeInterface`),
edge save/reload (handle IDs match interface names), topology templates
(Blank/Hub-Spoke/OSPF 3 Sites — IPs baked in), probe endpoint, link fault
endpoint, Redis event bridge, export routes (JSON/MD/PDF/DOC), JWT auth v1
(register/login/me), frontend login screen.

**Explicitly removed (do not re-add without a spec):** Auto-IP service
(`autoip.py`), Auto-IP endpoint (`POST /topology/autoip`), Auto-IP UI button.
Addressing is now manual, via the interface inspector.

**Partial (extend, do not rebuild):** auth hardening (no password reset / OAuth
/ email verification), GNS3 live provisioning, Redis multi-worker testing,
frontend hook/canvas test coverage expansion.

**Not started:** correct ping UI (source = interface IP, target = another
interface IP), live GNS3 node/link provisioning, native DOCX export,
CLI terminal.
```

---

### Step 5 — Update Known Technical Debt table

**File:** `AGENTS.md` *(modify)*

Find Section 9, `## 9. Known Technical Debt`. Remove the Auto-IP row and update
the Simulation engine row:

Before:
```markdown
| Area | Issue | Priority |
|------|-------|----------|
| `events/manager.py` | Redis pub needs multi-worker smoke test before prod scaling claims | v1 hardening |
| `shared-types` index signatures | `[key: string]: unknown` weakens type checking | v2 |
| Simulation engine | Mock only; GNS3 live node/link provisioning pending | Sprint 2/3 |
| Auth | No password reset, no OAuth, no email verification, no billing | next hardening |
```

After:
```markdown
| Area | Issue | Priority |
|------|-------|----------|
| `events/manager.py` | Redis pub needs multi-worker smoke test before prod scaling claims | v1 hardening |
| `shared-types` index signatures | `[key: string]: unknown` weakens type checking | v2 |
| `NetworkLink.ipConfig` | Kept for backward-compat read; must not be written by new code. Remove in a future cleanup once all saved topologies are migrated. | v2 cleanup |
| Simulation engine | Mock only; GNS3 live node/link provisioning pending | Sprint 2/3 |
| Auth | No password reset, no OAuth, no email verification, no billing | next hardening |
| Ping UI | Ping button is wired to old Auto-IP output. Needs rework: source = a configured interface IP, target = user-selected target IP. | next slice |
```

---

### Step 6 — Update Project State description

**File:** `AGENTS.md` *(modify)*

Find this line near the top of Section 0:

Before:
```markdown
**Project state: late Sprint 1 / early Sprint 2.** Core CRUD, auth, mock simulation, and export are working. You are likely implementing incremental features or tests, not building foundations.
```

After:
```markdown
**Project state: green-v0 baseline (tagged `green-v0` on `main`).**
The topology editor has a correct domain model: nodes carry explicit interface
sets, linking is reliable (interfaces auto-assigned on connect), and the
inspector exposes per-interface IP/mask editing. Mock simulation, auth, and
export are working. Auto-IP has been removed. You are implementing incremental
slices on top of a stable base — do not rebuild what is already there.
```

---

### Step 7 — Rewrite MANUAL_TESTING.md

**File:** `MANUAL_TESTING.md` *(modify)*

Replace the **entire file** with the content below. Preserve the preamble
(startup commands, auth note, GNS3 note) and steps 0, 1, 3–12 with minor
updates. Replace step 2 (Auto-IP) with the new Interface steps. Update step 5
(Ping) to reference interface IPs.

```markdown
# Octet Manual Testing Checklist

Use this checklist after each feature batch. Keep Docker, the backend, and the
frontend running:

```powershell
docker compose -f infra/docker-compose.dev.yml up -d

cd apps/api
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000

# separate terminal, repo root
pnpm dev
```

Auth note: local dev uses `DEV_AUTH_EMAIL=dev@octet.local` when no
`Authorization` header is sent only if `DEV_AUTH_ENABLED=true`. Normal testing
should use the login/register UI, which sends JWT-backed
`Authorization: Bearer <token>` requests.

GNS3 note: normal manual testing still uses `SIMULATION_ENGINE=mock`.

Open the app at `http://localhost:5173`.

---

## 0. Login

**Action:** register or log in with a local account.

**Expected:** the canvas loads and the header shows the authenticated email and
account tier.

**Problem signs:** login succeeds without a token, authenticated API calls return
401, or logout does not return to the login screen.

---

## 1. Load Template

**Action:** choose `OSPF 3 Sites` and click `Load Template`.

**Expected:** four nodes appear on the canvas with four links. Each link
visually connects two nodes from specific handle points. The console logs that
the template loaded.

**Problem signs:** the canvas stays empty, the template dropdown is empty,
links are missing, or console says templates could not load.

---

## 2. Verify Interfaces

**Action:** click any router node to open the property inspector.

**Expected:**
- The inspector shows an **Interfaces** section listing `eth0`–`eth3`.
- Interfaces that are connected to another node show status **UP** and a
  peer label (e.g. `→ Branch A Router : eth0`).
- Interfaces with no link show status **DOWN** and empty IP/mask fields.

**Problem signs:** no Interfaces section appears, all interfaces show DOWN even
when links exist, or peer labels are missing/wrong.

---

## 3. Assign IPs Manually

**Action:** with a router node selected, type `192.168.1.1` into the IP field
of `eth0` and `/30` into its Mask field. Click elsewhere (blur the field).

**Expected:** the values remain in the fields — they are not reset.

Then save (see step 4) and reload the topology (see step 5). The IP and mask
must reappear in the inspector after reload.

**Problem signs:** fields reset on blur, IPs disappear after save/reload, or
the wrong interface is updated.

---

## 4. Save

**Action:** set a recognizable topology name, then click `Save`.

**Expected:** the console logs a successful save. The `Simulation`, `Test`,
`Project`, and `Export` menus expose the actions valid for the current selection.

**Problem signs:** save logs an error, or refreshing then `Load Latest` cannot
recover the topology.

---

## 5. Reload and Verify

**Action:** refresh the browser, then use `Load Latest`.

**Expected:**
- All nodes reappear at their saved positions.
- All links reappear **graphically** connecting the correct handle points.
- Clicking a node shows the interface IPs assigned in step 3.

**Problem signs:** nodes load but links are invisible, IPs are missing after
reload, or interface status shows DOWN for links that were connected before
saving.

---

## 6. Start Simulation

**Action:** open the `Simulation` menu and click `Start`.

**Expected:** node status dots turn running/green and the console logs
simulation events.

**Problem signs:** nodes remain stopped, the backend returns an error, or
WebSocket errors appear repeatedly.

---

## 7. Ping

**Action:** select a router node that has at least one connected interface with
an IP assigned. Open the `Test` menu and click `Ping`.

**Expected:** the console logs a ping result.

**Note:** the Ping feature is partially implemented. The button should be
enabled when a valid target IP can be derived from the selected node's peer
connections. If it remains disabled, verify the node has a saved IP on a
connected interface.

**Problem signs:** Ping stays permanently disabled after saving and selecting a
configured router, or the backend returns a 500 error.

---

## 8. Fault

**Action:** select a link, open the `Test` menu, and click `Fault`.

**Expected:** the selected link becomes red/dashed and the console logs a
link-down fault.

**Problem signs:** the link does not change visually, or the fault button is
enabled without a link selected.

---

## 9. Export JSON

**Action:** open the `Export` menu and click `JSON`.

**Expected:** a `.octet.json` file downloads. Open it and verify it contains
`exportFormat`, topology metadata, nodes with `logicalConfig.interfaces` (each
interface should carry any manually assigned `ip`/`subnet`), and edges with
`sourcePort`/`targetPort` set to interface names (e.g. `"eth0"`).

**Problem signs:** the file is empty, missing interfaces, or `sourcePort` still
shows a positional ID like `"right"`.

---

## 10. Import JSON

**Action:** load another template, then import the previously exported
`.octet.json`.

**Expected:** the original topology reappears with positions, nodes, links,
interface IPs, and fault state preserved. Links must render graphically
immediately on import (no reload required).

**Problem signs:** node positions reset, links are invisible, interface IPs are
missing, or the imported topology cannot be saved/started/pinged/faulted.

---

## 11. Export Report

**Action:** open the `Export` menu and click `Markdown Report`.

**Expected:** a `.octet.md` file downloads. It contains metadata, topology
overview SVG, node inventory, interface/IP table, link table, and routing
summary. If IPs were assigned in step 3, they should appear in the interface
table.

**Problem signs:** the file is empty, interface IPs are missing from the table,
or exporting the report breaks JSON export/import.

---

## 12. Export PDF/DOC

**Action:** open the `Export` menu, click `PDF Report`, then `DOC Report`.

**Expected:** `.octet.pdf` and `.octet.doc` files download and open correctly,
containing the topology diagram and IP/link tables.

**Problem signs:** either file is empty, cannot be opened, or lacks the
topology diagram.

---

## 13. Final Smoke

**Action:** after importing, use the grouped menus to save, start, ping, fault,
export JSON, Markdown, PDF, and DOC again.

**Expected:** the imported topology behaves identically to a topology built
from scratch.

**Problem signs:** imported data looks correct visually but fails on any action.

---

## 14. Ownership Smoke

**Action:** log out, create or log into a second account, then use
`Load Latest`.

**Expected:** the second account does not see the first account's saved
topology.

**Problem signs:** topologies leak between accounts, or simulation/probe/fault
endpoints can access another account's topology ID.
```

*(Note: the triple-backtick code fence inside the file should be preserved as-is
for the startup commands block — do not escape it in the actual file.)*

---

## Tests to Add or Update

This task is documentation-only. No tests to add. No code to change.

---

## Validation Commands

Run these after making the changes to confirm nothing is broken:

```powershell
# 1. Backend tests must still pass (no code changed, just confirm)
cd apps/api
.\.venv\Scripts\python.exe -m pytest --tb=short -q

# 2. Frontend tests must still pass
cd apps/frontend
pnpm vitest run

# 3. Manual: open AGENTS.md and verify:
#    - No mention of autoip.py
#    - No mention of assign_topology_ips()
#    - Rule 6 describes interface addressing, not Auto-IP
#    - Roadmap Done list includes interface factory and reliable linking
#    - New Canvas Node Type recipe includes nodeFactory.ts step

# 4. Manual: open MANUAL_TESTING.md and verify:
#    - Step 2 describes interface verification, not Auto-IP
#    - Step 3 describes manual IP assignment
#    - Step 5 (Reload) explicitly checks that links appear graphically
#    - Step 7 (Ping) references interface IPs
#    - Step 9 (Export JSON) checks for logicalConfig.interfaces in output
```

---

## Architectural Checklist

- [ ] No source code was modified — documentation only
- [ ] `AGENTS.md` contains zero references to `autoip`, `Auto-IP`, or
      `assign_topology_ips`
- [ ] `AGENTS.md` Rule 6 describes `nodeFactory.ts` and `updateNodeInterface`
- [ ] `AGENTS.md` roadmap Done list includes `green-v0` items
- [ ] `MANUAL_TESTING.md` step 2 is "Verify Interfaces" (not "Auto-IP")
- [ ] `MANUAL_TESTING.md` has a step for "Reload and Verify" that explicitly
      checks graphical edge rendering after reload
- [ ] All 49 backend tests still pass
- [ ] All 46 frontend tests still pass
