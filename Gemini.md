# NetSim-Flow — Claude Code Project Memory

> Questo file viene letto da Claude Code ad ogni sessione.
> Tienilo aggiornato. È la fonte di verità per decisioni di progetto.

---

## Cos'è questo progetto

Web application per simulazione e progettazione di reti IP.
Stack: React 19 + React Flow (frontend), FastAPI Python 3.12 (backend), GNS3 (simulation engine), PostgreSQL + Redis.
Monorepo gestito con Turborepo.

**Obiettivo primario:** Utente passa da login a topologia OSPF funzionante in <60 secondi.

---

## Comandi Essenziali

```bash
# Avvio dev environment completo
docker compose -f infra/docker-compose.dev.yml up -d
turbo dev

# Frontend only
cd apps/frontend && pnpm dev

# Backend only
cd apps/api && uvicorn app.main:app --reload --port 8000

# Test
turbo test                          # tutti i workspace
cd apps/api && pytest               # backend
cd apps/frontend && pnpm test       # frontend (Vitest)

# DB migrations
cd apps/api && alembic upgrade head
cd apps/api && alembic revision --autogenerate -m "descrizione"

# Type generation (shared-types → Python schemas)
cd packages/shared-types && pnpm build
# Poi nel backend rigenera se necessario

# Lint + format
turbo lint
cd apps/api && ruff check . && ruff format .
cd apps/frontend && pnpm lint
```

---

## Struttura Repo — Dove Mettere le Cose

```
apps/frontend/src/
  canvas/          → Tutto ciò che riguarda React Flow (nodi, edge, canvas)
  components/      → UI generica riusabile (NON specifica di canvas)
  store/           → Zustand slices SOLO
  hooks/           → Custom hooks SOLO
  services/        → API client, WebSocket client

apps/api/app/
  routers/         → FastAPI route handlers (NO business logic)
  services/        → Business logic (testabile senza HTTP)
  engines/         → Simulation engine adapters (SOLO qui si parla a GNS3)
  models/          → SQLAlchemy ORM
  schemas/         → Pydantic v2 request/response
  events/          → WebSocket + Redis pub/sub

packages/shared-types/src/
  topology.ts      → NetworkNode, NetworkLink, Topology
  simulation.ts    → SimulationEvent, FaultRequest, ProbeResult
```

---

## Regole Architetturali — NON Violare

1. **Adapter pattern obbligatorio per il simulation engine.**
   Qualsiasi chiamata a GNS3 deve passare per `engines/gns3.py` che implementa `engines/base.py` (`SimulationEngineInterface`).
   MAI chiamate HTTP dirette a GNS3 da router o service.

2. **Shared types come fonte di verità.**
   I tipi TypeScript in `packages/shared-types` definiscono il contratto.
   Gli schema Pydantic nel backend devono specchiare quei tipi.
   Se divergono → rompono i test di integrazione (è intenzionale).

3. **Layering backend: Router → Service → Engine/Repository.**
   I router NON contengono logica. I service NON fanno chiamate HTTP dirette.

4. **Nessuna logica Zustand nei componenti React.**
   I componenti leggono dallo store con selettori. Le azioni partono da hooks.
   Nessuna chiamata API diretta da un componente.

5. **Il canvas è isolato.**
   `useReactFlow()` e tutto React Flow si usa SOLO dentro `canvas/`.
   I componenti fuori da `canvas/` non importano da `reactflow`.

6. **Auto-IP engine è idempotente e deterministico.**
   `assign_topology_ips()` in `services/autoip.py`:
   stesso input → stesso output, non modifica IP già presenti.
   Copertura test: 100%.

---

## Pattern da Usare

### Nuovo nodo canvas (frontend)
1. Crea `canvas/nodes/NomeNode.tsx` con `React.memo`
2. Aggiungi il tipo a `shared-types/topology.ts`
3. Registra in `canvas/nodeTypes.ts`
4. Aggiungi icona in `canvas/palette/PaletteItems.ts`

### Nuovo endpoint API (backend)
1. Schema Pydantic in `schemas/`
2. Logica in `services/`
3. Route in `routers/` (solo validazione + chiamata service)
4. Test in `tests/unit/` (service) e `tests/integration/` (route)

### Nuovo evento WebSocket
1. Aggiungi tipo a `shared-types/simulation.ts`
2. Publisher in `events/publisher.py`
3. Handler nel frontend in `hooks/useSimulationEvents.ts`
4. Aggiorna discriminated union `SimulationEvent`

### Nuovo engine adapter
1. Implementa `SimulationEngineInterface` in `engines/nuovo.py`
2. Registra in `core/dependencies.py` con flag di config
3. Il mock engine in `engines/mock.py` deve avere parità di comportamento

---

## Anti-Pattern — Non Fare Mai

```typescript
// ❌ API call in un componente
const MyComponent = () => {
  const data = await axios.get('/api/topology'); // NO
}

// ✅ Corretto: hook + store
const MyComponent = () => {
  const topology = useTopologyStore(s => s.topology);
}
```

```python
# ❌ Chiamata diretta a GNS3 in un service
async def start_sim(topology_id: str):
    await httpx.post("http://gns3:3080/v2/projects")  # NO

# ✅ Corretto: via adapter iniettato
async def start_sim(topology_id: str, engine: SimulationEngineInterface):
    await engine.start_topology(topology_id)
```

```python
# ❌ Logica in un router
@router.post("/topology/{id}/start")
async def start(id: str, db: Session = Depends(get_db)):
    topo = db.query(Topology).get(id)
    topo.status = "running"           # NO — logica nel router
    await httpx.post(...)             # NO — engine chiamato direttamente

# ✅ Corretto
@router.post("/topology/{id}/start")
async def start(id: str, svc: SimulationService = Depends()):
    return await svc.start_topology(id)
```

---

## Tipi Core — Riferimento Rapido

```typescript
// packages/shared-types/src/topology.ts

type NodeBaseType = 'router' | 'switch' | 'firewall' | 'cloud' | 'host' | 'site';
type NodeStatus   = 'stopped' | 'booting' | 'running' | 'error' | 'degraded';
type VendorType   = 'cisco' | 'juniper' | 'arista' | 'mikrotik' | 'generic';
type Protocol     = 'ospf' | 'bgp' | 'eigrp' | 'static' | 'rip';

interface NetworkNode {
  id: string;
  label: string;
  position: { x: number; y: number };
  baseType: NodeBaseType;
  role?: 'core' | 'distribution' | 'access' | 'edge' | 'hub' | 'spoke';
  protocols?: Protocol[];
  logicalConfig?: { interfaces: LogicalInterface[]; routingConfig?: RoutingConfig; loopback?: string; };
  vendorSpec?: { vendor: VendorType; platform: string; imageRef?: string; cliConfig?: string; };
  runtimeState?: { status: NodeStatus; cpuPercent?: number; memMB?: number; nodeId?: string; };
  tags: string[];
}

interface NetworkLink {
  id: string;
  sourceNodeId: string; sourcePort: string;
  targetNodeId: string; targetPort: string;
  linkType: 'ethernet' | 'serial' | 'fiber' | 'vpn-tunnel' | 'logical';
  ipConfig?: { subnet: string; sourceIp?: string; targetIp?: string; };
  qos?: { bandwidthMbps?: number; latencyMs?: number; packetLossPercent?: number; };
  faultState?: { active: boolean; type?: 'link-down' | 'high-latency' | 'packet-loss'; triggeredAt?: string; };
}
```

---

## Variabili d'Ambiente

```bash
# apps/frontend/.env.local
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws

# apps/api/.env
DATABASE_URL=postgresql+asyncpg://netsimflow:password@localhost:5432/netsimflow
REDIS_URL=redis://localhost:6379/0
GNS3_URL=http://localhost:3080
GNS3_USER=admin
GNS3_PASSWORD=admin
SIMULATION_ENGINE=mock   # "gns3" | "mock" — usa "mock" per dev senza GNS3
SECRET_KEY=dev-secret-change-in-prod
CORS_ORIGINS=http://localhost:5173
```

---

## Testing Strategy

| Layer | Tool | Copertura minima |
|-------|------|-----------------|
| AutoIP engine | pytest | 100% |
| Services backend | pytest + pytest-asyncio | 80% |
| API routes | pytest + httpx (TestClient) | endpoint principali |
| Frontend hooks | Vitest | 70% |
| Canvas components | Vitest + Testing Library | smoke test per nodo type |
| E2E | Playwright (Sprint 3+) | happy path template → simulazione |

---

## Sprint Corrente

**Sprint 1 — Canvas Foundation**

Task aperti:
- [ ] Setup monorepo Turborepo con `apps/frontend`, `apps/api`, `packages/shared-types`
- [ ] React Flow integration con nodi custom (Router, Switch, Cloud, Host)
- [ ] Zustand store: slice `topology` (nodes, edges, selectedIds)
- [ ] FastAPI skeleton: CRUD `/api/v1/topology`, WebSocket `/ws/events/{topology_id}`
- [ ] PostgreSQL schema + Alembic migration v1
- [ ] Docker Compose dev environment
- [ ] Mock simulation engine (risponde correttamente senza GNS3)

**Definition of Done Sprint 1:**
Posso aprire il browser, trascinare 3 router sul canvas, connetterli, salvare la topologia via API e ricaricarla. Il WebSocket è connesso e logga eventi mock.

---

## Documentazione di Riferimento

- Planning completo: `NetSim-Flow_Planning_Document.md`
- Architettura dettagliata: `ARCHITECTURE.md`
- React Flow docs: https://reactflow.dev/docs
- FastAPI docs: https://fastapi.tiangolo.com
- GNS3 API: http://localhost:3080/docs (quando GNS3 è up)
- Pydantic v2: https://docs.pydantic.dev/latest/
