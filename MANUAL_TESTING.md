# NetSim-Flow Manual Testing Checklist

Use this checklist after each feature batch. Keep Docker, the backend, and the frontend running:

```powershell
docker compose -f infra/docker-compose.dev.yml up -d

cd apps/api
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000

# separate terminal, repo root
pnpm dev
```

Open the app at `http://localhost:5173`.

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

Expected: the console logs a successful save, and `Start`, `Ping`, `Fault`, and `Export JSON` become available when their selection rules are met.

Problem signs: save logs an error, start remains disabled after saving, or refreshing then `Load Latest` cannot recover the topology.

## 4. Start Simulation

Action: click `Start`.

Expected: node status dots turn running/green and the console logs simulation events.

Problem signs: nodes remain stopped, the backend returns an error, or WebSocket errors appear repeatedly.

## 5. Ping

Action: select a router node and click `Ping`.

Expected: the console logs a successful ping result such as `Reply from ...`.

Problem signs: the Ping button stays disabled after saving and selecting a router, or the target IP is missing after Auto-IP.

## 6. Fault

Action: select a link and click `Fault`.

Expected: the selected link becomes red/dashed and the console logs a link-down fault.

Problem signs: the link does not visually change, the fault button is enabled without selecting a link, or the topology cannot be saved after the fault.

## 7. Export JSON

Action: click `Export JSON`.

Expected: a `.netsimflow.json` file downloads. It contains `exportFormat`, topology metadata, nodes, and edges.

Problem signs: the file is empty, invalid JSON, missing links/IPs, or has no format metadata.

## 8. Import JSON

Action: load another template, then import the previously exported `.netsimflow.json`.

Expected: the original topology reappears with positions, nodes, links, IPs, and fault state preserved.

Problem signs: node positions reset, links disappear, IP data is missing, or the imported topology cannot be saved/start/ping/faulted.

## 9. Final Smoke

Action: after importing, click `Save`, `Start`, select a router and `Ping`, select a link and `Fault`.

Expected: the imported topology behaves like a normal saved topology.

Problem signs: imported data looks correct visually but fails on save, simulation, ping, or fault.
