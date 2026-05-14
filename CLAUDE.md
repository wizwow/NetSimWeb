# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**NetSim-Flow** — Web platform for IP network simulation and design. Users go from login to a working OSPF topology in under 60 seconds.

Stack: React 19 + React Flow (frontend), FastAPI Python 3.12 (backend), GNS3 (simulation engine), PostgreSQL + Redis. Monorepo managed with Turborepo + pnpm.

## Commands

```bash
# Start full dev environment
docker compose -f infra/docker-compose.dev.yml up -d
turbo dev

# Frontend only
cd apps/frontend && pnpm dev          # http://localhost:5173

# Backend only
cd apps/api && uvicorn app.main:app --reload --port 8000

# Tests
turbo test                            # all workspaces
cd apps/api && pytest                 # backend
cd apps/frontend && pnpm test         # frontend (Vitest)

# DB migrations
cd apps/api && alembic upgrade head
cd apps/api && alembic revision --autogenerate -m "description"

# Lint + format
turbo lint
cd apps/api && ruff check . && ruff format .
cd apps/frontend && pnpm lint

# Rebuild shared types (after changes in packages/shared-types)
cd packages/shared-types && pnpm build
```

## Environment Variables

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
SIMULATION_ENGINE=mock   # "gns3" | "mock" — use "mock" for dev without GNS3
SECRET_KEY=dev-secret-change-in-prod
CORS_ORIGINS=http://localhost:5173
```

## Repository Structure

```
apps/frontend/src/
  canvas/       → Everything React Flow (nodes, edges, canvas container)
  components/   → Generic reusable UI (NOT canvas-specific)
  store/        → Zustand slices ONLY
  hooks/        → Custom hooks ONLY
  services/     → API client (axios), WebSocket client

apps/api/app/
  routers/      → FastAPI route handlers (NO business logic)
  services/     → Business logic (testable without HTTP)
  engines/      → Simulation engine adapters (ONLY place that talks to GNS3)
  models/       → SQLAlchemy ORM
  schemas/      → Pydantic v2 request/response
  events/       → WebSocket + Redis pub/sub

packages/shared-types/src/
  topology.ts   → NetworkNode, NetworkLink, Topology
  simulation.ts → SimulationEvent, FaultRequest, ProbeResult
```

## Architectural Rules — Never Violate

1. **Adapter pattern for simulation engine.** All GNS3 calls go through `engines/gns3.py` implementing `SimulationEngineInterface`. No direct HTTP calls to GNS3 from routers or services.

2. **Shared types are the source of truth.** TypeScript types in `packages/shared-types` define the contract. Backend Pydantic schemas must mirror them — divergence breaks integration tests intentionally.

3. **Backend layering: Router → Service → Engine/Repository.** Routers contain no logic. Services make no direct HTTP calls.

4. **No Zustand logic in React components.** Components read from store via selectors. Actions originate from hooks. No direct API calls from components.

5. **Canvas is isolated.** `useReactFlow()` and all React Flow hooks are used ONLY inside `canvas/`. Nothing outside `canvas/` imports from `@xyflow/react`.

6. **Auto-IP engine is idempotent and deterministic.** `assign_topology_ips()` in `services/autoip.py`: same input → same output, does not modify already-assigned IPs. Test coverage: 100%.

## Common Patterns

### Adding a new canvas node type
1. Create `canvas/nodes/NameNode.tsx` with `React.memo`
2. Add the type to `shared-types/topology.ts`
3. Register in `canvas/nodeTypes.ts`
4. Add icon to `canvas/palette/PaletteItems.ts`

### Adding a new API endpoint
1. Pydantic schema in `schemas/`
2. Logic in `services/`
3. Route in `routers/` (validation + service call only)
4. Tests in `tests/unit/` (service) and `tests/integration/` (route)

### Adding a new WebSocket event
1. Add type to `shared-types/simulation.ts` discriminated union
2. Publisher in `events/publisher.py`
3. Handler in frontend `hooks/useSimulationEvents.ts`

### Adding a new engine adapter
1. Implement `SimulationEngineInterface` in `engines/new.py`
2. Register in `core/dependencies.py` via config flag
3. Mock engine in `engines/mock.py` must maintain behavioral parity

## Code Conventions

**TypeScript:** `PascalCase` for components/types, `camelCase` for functions/variables/hooks, `SCREAMING_SNAKE_CASE` for global constants. Hook prefix: `use`. Test file alongside component: `ComponentName.test.tsx`.

**React 19 patterns — enforce these, never use the pre-19 equivalents:**
- `use(promise)` instead of `useEffect` + state for async data
- `useTransition` / `useDeferredValue` for non-urgent updates; avoid manual `startTransition` wrappers
- Server Actions where applicable (not yet wired but keep the door open)
- `useOptimistic` for optimistic UI updates instead of manual state rollback
- `ref` as a prop (ref-as-prop) — no `forwardRef` wrapper needed
- `useEffect` cleanup must use the stable function identity pattern; avoid recreating functions inside effects

**Python:** `snake_case` everywhere (PEP 8). Pydantic models suffixed `Schema` (e.g. `TopologySchema`). SQLAlchemy models no suffix. Async everywhere — no sync functions in routers/services. Type hints required on all public functions.

**Git:** Branch prefixes `feat/`, `fix/`, `chore/`, `docs/`. Conventional Commits format. PRs require green tests and no unjustified TypeScript `any`.

## Testing Strategy

| Layer | Tool | Minimum coverage |
|-------|------|-----------------|
| AutoIP engine | pytest | 100% |
| Backend services | pytest + pytest-asyncio | 80% |
| API routes | pytest + httpx TestClient | main endpoints |
| Frontend hooks | Vitest | 70% |
| Canvas components | Vitest + Testing Library | smoke test per node type |
| E2E | Playwright (Sprint 3+) | happy path template → simulation |

## Key Type Reference

```typescript
type NodeBaseType = 'router' | 'switch' | 'firewall' | 'cloud' | 'host' | 'site';
type NodeStatus   = 'stopped' | 'booting' | 'running' | 'error' | 'degraded';
type VendorType   = 'cisco' | 'juniper' | 'arista' | 'mikrotik' | 'generic';
type Protocol     = 'ospf' | 'bgp' | 'eigrp' | 'static' | 'rip';

type SimulationEvent =
  | { type: 'NODE_STATUS_CHANGED'; nodeId: string; status: NodeStatus }
  | { type: 'LINK_FAULT_INJECTED'; linkId: string; faultType: FaultType }
  | { type: 'OSPF_ADJACENCY_CHANGED'; nodeId: string; neighborId: string; state: string }
  | { type: 'PROBE_RESULT'; probeId: string; result: ProbeResult };
```

## Export Formats

| Format | Use case |
|--------|----------|
| `.netsimflow.json` | Full topology state, re-importable |
| `.md` / `.pdf` | Documentation report for clients/instructors (WeasyPrint + Jinja2) |
| GNS3 `.gns3` | Interop with existing GNS3 desktop |
| Ansible inventory YAML | Automation bootstrap for real environments |
| Cisco CML topology YAML | Interop with Cisco Modeling Labs |

## Known Technical Debt

| Area | Issue | Priority |
|------|-------|----------|
| `events/manager.py` | `ConnectionManager` is in-memory — WebSocket events are lost if the backend runs with `--workers > 1`. Redis pub/sub adapter needed before horizontal scaling. Single-worker dev is fine. | v2 |
| `shared-types` `NetworkNode` / `NetworkLink` | `[key: string]: unknown` index signature was added to satisfy React Flow v12's `Record<string, unknown>` constraint. It weakens type-checking on these interfaces. Remove when wrapping with `Node<NetworkNode>` properly (requires React Flow custom node typing refactor). | v2 |

## Architecture References

- [ARCHITECTURE.md](ARCHITECTURE.md) — Full ADR, DB schema, detailed specs
- [NetSim-Flow_Planning_Document.md](NetSim-Flow_Planning_Document.md) — Sprint planning, feature roadmap
