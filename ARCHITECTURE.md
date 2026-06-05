# Octet — Architecture Decision Record
**Versione:** 0.1 | Aggiornare questo file ad ogni decisione architetturale rilevante.

---

## 0. Product Architecture Constraints

Octet has three product horizons that must remain compatible with architecture decisions:

- **Education/free SaaS:** the MVP must stay browser-first, fast to start, and useful with logical/mock simulation so teachers can run lessons without local setup.
- **Professional/pro SaaS:** project persistence, manual IP fidelity, fault simulation, JSON interchange, and export/report workflows are first-class product capabilities, not optional extras.
- **Enterprise/on-premise:** self-hosted deployment, stronger RBAC, auditability, integrations, and network-source-of-truth workflows are long-term objectives; avoid architectural choices that would block them.
- **Abstraction fidelity:** the data model must support both quick teaching demos and progressively detailed real-network models without forcing early vendor-specific complexity.

---

## 1. Repository Structure

```
octet/
├── apps/
│   ├── frontend/                  # React 19 + Vite + TypeScript
│   │   ├── src/
│   │   │   ├── canvas/            # React Flow nodi, edge, canvas container
│   │   │   ├── components/        # UI generica (panel, modal, toolbar)
│   │   │   ├── store/             # Zustand slices
│   │   │   ├── hooks/             # Custom hooks (useSimulation, useWebSocket)
│   │   │   ├── services/          # API client (axios), WS client
│   │   │   └── types/             # Tipi locali (re-export da shared-types)
│   │   ├── public/
│   │   └── vite.config.ts
│   │
│   └── api/                       # FastAPI Python 3.12
│       ├── app/
│       │   ├── routers/           # Un file per dominio: topology, simulation, auth
│       │   ├── models/            # SQLAlchemy ORM models
│       │   ├── schemas/           # Pydantic v2 request/response schemas
│       │   ├── services/          # Business logic (no logic nei router)
│       │   ├── engines/           # Simulation engine adapters
│       │   │   ├── base.py        # SimulationEngineInterface (ABC)
│       │   │   ├── gns3.py        # GNS3 implementation
│       │   │   └── mock.py        # Mock per test/dev senza GNS3
│       │   ├── events/            # WebSocket event publisher (Redis pub/sub)
│       │   └── core/              # Config, DB session, auth, logging
│       ├── tests/
│       │   ├── unit/
│       │   └── integration/
│       ├── alembic/               # DB migrations
│       └── pyproject.toml
│
├── packages/
│   └── shared-types/              # TypeScript types condivisi frontend/API codegen
│       └── src/
│           ├── topology.ts        # NetworkNode, NetworkLink, Topology
│           ├── simulation.ts      # SimulationEvent, FaultRequest, ProbeResult
│           └── index.ts
│
├── infra/
│   ├── docker-compose.dev.yml
│   ├── docker-compose.prod.yml
│   └── nginx/
│
├── .claude/
│   └── CLAUDE.md                  # Claude Code project memory
├── ARCHITECTURE.md                # Questo file
└── turbo.json                     # Turborepo config
```

---

## 2. Frontend Architecture

### 2.1 State Management — Zustand Slices

Ogni slice è un file separato. **Nessun slice conosce un altro slice direttamente** — comunicazione via actions o selettori condivisi da `store/index.ts`.

```
store/
├── topology.slice.ts      # nodes[], edges[], selectedIds
├── simulation.slice.ts    # status, events[], activeProbes
├── ui.slice.ts            # panels aperti, zoom, sidebar state
└── index.ts               # combine slices + devtools middleware
```

**Regola:** La UI legge dallo store. Le API calls partono da hooks (`useSimulation.ts`), mai da componenti direttamente.

### 2.2 Canvas Layer — React Flow

- Nodi custom in `canvas/nodes/`: un file per tipo (`RouterNode.tsx`, `SwitchNode.tsx`, ecc.)
- Edge custom in `canvas/edges/`: `SimulatedEdge.tsx` (gestisce animazione e fault state)
- Il canvas container (`canvas/TopologyCanvas.tsx`) è l'unico punto di integrazione con React Flow
- **Vietato** accedere a `useReactFlow()` fuori da `canvas/`

### 2.3 Tipi — Fonte di Verità

I tipi in `packages/shared-types` sono la **fonte di verità assoluta**.
Il frontend li importa da `@octet/shared-types`.
Il backend Python ha Pydantic schemas che devono **specchiare** quei tipi — se divergono, il test di integrazione fallisce.

---

## 3. Backend Architecture

### 3.1 Layering — Regola Ferrea

```
Router → Service → Engine Adapter / Repository
```

- I **Router** validano input (Pydantic) e restituiscono response. Zero business logic.
- I **Service** contengono tutta la logica. Sono testabili senza HTTP context.
- Gli **Engine Adapter** implementano `SimulationEngineInterface` e sono iniettati nei Service via FastAPI Depends.
- I **Repository** (opzionale per ora, usare SQLAlchemy direttamente nei Service) gestiscono persistenza.

### 3.2 SimulationEngineInterface — Contratto Obbligatorio

```python
# engines/base.py
from abc import ABC, abstractmethod

class SimulationEngineInterface(ABC):

    @abstractmethod
    async def create_topology(self, topology: TopologySchema) -> str:
        """Restituisce engine_topology_id"""

    @abstractmethod
    async def start_topology(self, engine_topology_id: str) -> None: ...

    @abstractmethod
    async def stop_topology(self, engine_topology_id: str) -> None: ...

    @abstractmethod
    async def get_node_status(self, engine_node_id: str) -> NodeStatus: ...

    @abstractmethod
    async def inject_fault(self, engine_link_id: str, fault: FaultType) -> None: ...

    @abstractmethod
    async def run_probe(self, source_node_id: str, target_ip: str, probe_type: ProbeType) -> ProbeResult: ...
```

**Regola:** Non esiste chiamata diretta a GNS3 fuori da `engines/gns3.py`. Mai.

### 3.3 WebSocket Event Flow

```
GNS3 Webhook → POST /internal/events → Redis PUBLISH sim:{id}:events
                                              ↓
                              Redis SUBSCRIBE (nel WS handler)
                                              ↓
                              WebSocket → Client (tutti i subscriber della topology)
```

Il client riceve eventi tipizzati:

```typescript
type SimulationEvent =
  | { type: 'NODE_STATUS_CHANGED'; nodeId: string; status: NodeStatus }
  | { type: 'LINK_FAULT_INJECTED'; linkId: string; faultType: FaultType }
  | { type: 'OSPF_ADJACENCY_CHANGED'; nodeId: string; neighborId: string; state: string }
  | { type: 'PROBE_RESULT'; probeId: string; result: ProbeResult };
```

---

## 4. Database Schema (PostgreSQL)

```sql
-- Core tables Sprint 1

CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT UNIQUE NOT NULL,
    role        TEXT NOT NULL DEFAULT 'designer', -- student | designer | admin
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE topologies (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id        UUID REFERENCES users(id),
    name            TEXT NOT NULL,
    description     TEXT,
    abstraction_level TEXT DEFAULT 'logical', -- logical | vendor-specific
    engine_topo_id  TEXT,                     -- ID nel simulation engine (nullable)
    status          TEXT DEFAULT 'draft',     -- draft | running | stopped | error
    graph_json      JSONB NOT NULL DEFAULT '{}', -- Full topology state
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE simulation_events (
    id          BIGSERIAL PRIMARY KEY,
    topology_id UUID REFERENCES topologies(id) ON DELETE CASCADE,
    event_type  TEXT NOT NULL,
    payload     JSONB NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_sim_events_topology ON simulation_events(topology_id, created_at DESC);
```

**Nota:** `graph_json` contiene l'intero stato nodes+edges. Non normalizzare ulteriormente prima della v2 — la flessibilità del JSONB è necessaria durante le iterazioni rapide del MVP.

---

## 5. Auto-IP Engine — Specifiche

Il modulo `api/app/services/autoip.py` deve rispettare queste regole:

- Pool primario: `10.0.0.0/8`
- Link P2P: subnet `/30` allocate sequenzialmente (`10.0.1.0/30`, `10.0.1.4/30`, ...)
- Loopback: `10.255.x.y/32` dove x.y è derivato dall'indice del nodo
- Conflitti: rileva overlap prima di assegnare, solleva `IPConflictError`
- Idempotenza: stesso input → stesso output (deterministico, basato su hash del link ID)
- Override: se l'utente specifica un IP manualmente, il motore lo rispetta e skippa quella subnet

```python
# Interfaccia attesa
def assign_topology_ips(topology: TopologySchema) -> TopologySchema:
    """
    Ritorna la topologia con tutti gli IP mancanti compilati.
    Non modifica IP già presenti. Idempotente.
    """
```

Unit test coverage: **100%** su questo modulo. È critico.

---

## 6. Template Engine

I template sono file JSON statici in `api/app/data/templates/`.
Ogni template ha questa struttura:

```json
{
  "id": "ospf-3-sites",
  "name": "OSPF Multi-Sede (3 sedi)",
  "description": "Hub-and-spoke con OSPF area 0 preconfigurato",
  "tags": ["ospf", "wan", "multi-site"],
  "abstractionLevel": "logical",
  "nodes": [ /* array di NetworkNode parziali (senza IP, senza vendor) */ ],
  "edges": [ /* array di NetworkLink parziali */ ],
  "postProcessors": ["autoip", "ospf-config-gen"]
}
```

Il campo `postProcessors` è una lista ordinata di trasformazioni da applicare dopo il caricamento del template. Ogni processor è registrato in `services/template_processors.py`.

---

## 7. Decisioni ADR (Architecture Decision Records)

| # | Decisione | Razionale | Data |
|---|-----------|-----------|------|
| ADR-001 | React Flow invece di Canvas API raw | Gestione grafo come DOM: accessibilità, edge cliccabili, animazioni CSS senza hit-testing custom | 2026-05-14 |
| ADR-002 | Adapter pattern su simulation engine | GNS3 è MVP; rimpiazzabile in v2 senza impatto frontend | 2026-05-14 |
| ADR-003 | JSONB per graph state (non normalizzato) | Schema topologia cambia rapidamente in MVP; normalizzare in v2 | 2026-05-14 |
| ADR-004 | FRRouting come nodo default (non Cisco IOS) | Open source, Docker-based (avvio 2s), nessun problema licenze | 2026-05-14 |
| ADR-005 | Redis pub/sub per eventi simulazione | Disaccoppia GNS3 webhook dal WebSocket handler; scaling orizzontale natale | 2026-05-14 |
| ADR-006 | Turborepo monorepo | Shared types compilati una volta, cache build condivisa, task pipeline | 2026-05-14 |

---

## 8. Convenzioni di Codice

### TypeScript (Frontend)
- `PascalCase` per componenti e tipi
- `camelCase` per funzioni, variabili, hook
- `SCREAMING_SNAKE_CASE` per costanti globali
- Hook custom sempre prefissati `use`
- File componente: `ComponentName.tsx` + `ComponentName.test.tsx` nella stessa cartella

### Python (Backend)
- `snake_case` ovunque (PEP 8 strict)
- Pydantic models: suffix `Schema` (es. `TopologySchema`, `NodeSchema`)
- SQLAlchemy models: no suffix (es. `Topology`, `Node`)
- Async ovunque: nessuna funzione sync nei router/service (usa `run_in_executor` se necessario)
- Type hints obbligatori su tutte le funzioni pubbliche

### Git
- Branch: `feat/`, `fix/`, `chore/`, `docs/`
- Commit: Conventional Commits (`feat: add autoip engine`, `fix: ospf template missing loopback`)
- PR richiede: test verdi + nessun `any` TypeScript non giustificato
