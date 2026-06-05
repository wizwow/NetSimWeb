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
