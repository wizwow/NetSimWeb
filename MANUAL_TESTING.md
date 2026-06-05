# Octet Manual Testing Checklist

Use this checklist after each feature batch. Keep Docker, the backend, and the frontend running:

```powershell
docker compose -f infra/docker-compose.dev.yml up -d

cd apps/api
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000

# separate terminal, repo root
pnpm dev
```

Auth note: local dev uses `DEV_AUTH_EMAIL=dev@octet.local` when no `Authorization`
header is sent only if `DEV_AUTH_ENABLED=true`. Normal testing should use the login/register UI,
which sends JWT-backed `Authorization: Bearer <token>` requests. API-only multi-user bypass checks
can send `Authorization: Bearer dev:user@example.com` only with `DEV_AUTH_ENABLED=true`.

GNS3 note: normal manual testing still uses `SIMULATION_ENGINE=mock`. To check whether a
local GNS3 server is ready later, run:

```powershell
cd apps/api
.\.venv\Scripts\python.exe scripts\gns3_readiness_check.py
```

Open the app at `http://localhost:5173`.

## 0. Login

Action: register or log in with a local account.

Expected: the canvas loads and the header shows the authenticated email and account tier.

Problem signs: login succeeds without a token, authenticated API calls return 401, or logout does
not return to the login screen.

## 1. Load Template

Action: choose `OSPF 3 Sites` and click `Load Template`.

Expected: four nodes appear on the canvas with four links. The console logs that the template loaded.

Problem signs: the canvas stays empty, the template dropdown is empty, or the console says templates could not load.

## 2. Auto-IP

Action: click `Auto-IP`.

Expected: links receive `/30` subnet labels and routers receive loopbacks in their properties.

Problem signs: links stay unlabeled, Auto-IP logs an error, or existing manual IP values are overwritten unexpectedly.

## 3. Save

Action: set a recognizable topology name, then click `Save`.

Expected: the console logs a successful save, and the `Simulation`, `Test`, `Project`, and `Export` menus expose the actions that are valid for the current selection.

Problem signs: save logs an error, start remains disabled after saving, or refreshing then `Load Latest` cannot recover the topology.

## 4. Start Simulation

Action: open the `Simulation` menu and click `Start`.

Expected: node status dots turn running/green and the console logs simulation events.

Problem signs: nodes remain stopped, the backend returns an error, or WebSocket errors appear repeatedly.

## 5. Ping

Action: select a router node, open the `Test` menu, and click `Ping`.

Expected: the console logs a successful ping result such as `Reply from ...`.

Problem signs: the Ping button stays disabled after saving and selecting a router, or the target IP is missing after Auto-IP.

## 6. Fault

Action: select a link, open the `Test` menu, and click `Fault`.

Expected: the selected link becomes red/dashed and the console logs a link-down fault.

Problem signs: the link does not visually change, the fault button is enabled without selecting a link, or the topology cannot be saved after the fault.

## 7. Export JSON

Action: open the `Export` menu and click `JSON`.

Expected: a `.octet.json` file downloads. It contains `exportFormat`, topology metadata, nodes, and edges.

Problem signs: the file is empty, invalid JSON, missing links/IPs, or has no format metadata.

## 8. Import JSON

Action: load another template, then import the previously exported `.octet.json`.

Expected: the original topology reappears with positions, nodes, links, IPs, and fault state preserved.

Problem signs: node positions reset, links disappear, IP data is missing, or the imported topology cannot be saved/start/ping/faulted.

## 9. Export Report

Action: open the `Export` menu and click `Markdown Report`.

Expected: a `.octet.md` file downloads. It contains metadata, topology overview SVG, topology summary, node inventory, interface/IP table, link table, routing summary, and validation checklist.

Problem signs: the file is empty, missing IPs or links, missing routing information for OSPF templates, or exporting the report breaks JSON export/import.

## 10. Export PDF/DOC

Action: open the `Export` menu, click `PDF Report`, then open it again and click `DOC Report`.

Expected: `.octet.pdf` and `.octet.doc` files download. They contain styled, rendered report content and a visible topology diagram.

Problem signs: either file is empty, cannot be opened by a normal PDF/Word-compatible viewer, shows raw Markdown syntax, lacks the topology diagram, or does not contain the topology name and IP/link tables.

## 11. Final Smoke

Action: after importing, use the grouped menus to save, start, ping, fault, then export JSON, Markdown, PDF, and DOC files again.

Expected: the imported topology behaves like a normal saved topology.

Problem signs: imported data looks correct visually but fails on save, simulation, ping, fault, JSON export, or any report export.

## 12. Ownership Smoke

Action: log out, create or log into a second account, then use `Load Latest`.

Expected: the second account does not see the first account's saved topology. Saving a new topology
under the second account does not affect the first account.

Problem signs: topologies leak between accounts, or simulation/probe/fault endpoints can access
another account's topology ID.
