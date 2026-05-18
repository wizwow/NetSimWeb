# NetSim-Flow — AI Agent Project Memory

This file is the canonical guidance for any AI coding agent working in this repository.
Keep it current whenever roadmap, architecture, commands, or conventions change.

## Project Overview

**NetSim-Flow** is a web platform for IP network simulation and design. The target experience is: a user goes from login to a working OSPF topology in under 60 seconds.

Stack: React 19 + React Flow frontend, FastAPI Python 3.12 backend, GNS3 simulation engine target, PostgreSQL + Redis, Turborepo + pnpm monorepo.

### Product Mission

NetSim-Flow must serve three end states:

1. **Education / Free Web Account:** teachers can open the website, build a small router/switch/PC topology entirely in-browser, let Auto-IP configure addressing, start the simulation, and teach subnetting/routing quickly.
2. **Professional / Pro Account:** sysadmins can model real sites with real IPs, hardware, links, and hosts; simulate routing/failover; save projects; and export structured XML, DOC/PDF, and implementation companion documentation.
3. **Enterprise / On-Premise:** large organizations can eventually run a private installation as a virtual network twin for testing, maintenance planning, documentation, and long-term network source of truth. This is strategic and late-roadmap, not MVP scope.

## Commands

```powershell
# Start full dev environment
# Terminal 1: infrastructure only (PostgreSQL + Redis)
docker compose -f infra/docker-compose.dev.yml up -d

# Terminal 2: backend API (Python venv)
cd apps/api
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000

# Terminal 3: frontend / workspace dev tasks (repo root)
pnpm dev

# Note: turbo dev / pnpm dev currently starts workspaces with a dev script.
# The FastAPI backend is Python-only and is not wired into Turbo yet.

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

# Rebuild shared types after changes in packages/shared-types
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

```text
apps/frontend/src/
  canvas/       -> Everything React Flow: nodes, edges, canvas container
  components/   -> Generic reusable UI, not canvas-specific
  store/        -> Zustand slices only
  hooks/        -> Custom hooks only
  services/     -> API client, WebSocket client, browser-side I/O helpers

apps/api/app/
  routers/      -> FastAPI route handlers, no business logic
  services/     -> Business logic, testable without HTTP
  engines/      -> Simulation engine adapters, only place that talks to GNS3
  models/       -> SQLAlchemy ORM
  schemas/      -> Pydantic v2 request/response schemas
  events/       -> WebSocket + Redis pub/sub

packages/shared-types/src/
  topology.ts   -> NetworkNode, NetworkLink, Topology
  simulation.ts -> SimulationEvent, FaultRequest, ProbeResult
```

## Architectural Rules

1. **Adapter pattern for simulation engine.** All GNS3 calls go through `engines/gns3.py` implementing `SimulationEngineInterface`. No direct HTTP calls to GNS3 from routers or services.
2. **Shared types are the source of truth.** TypeScript types in `packages/shared-types` define the contract. Backend Pydantic schemas must mirror them.
3. **Backend layering: Router -> Service -> Engine/Repository.** Routers contain no business logic. Services make no direct HTTP calls to external simulation systems.
4. **No Zustand logic in React components.** Components read from store via selectors. Actions and side effects originate from hooks. No direct API calls from components.
5. **Canvas is isolated.** `useReactFlow()` and React Flow hooks are used only inside `canvas/`. Nothing outside `canvas/` imports from `@xyflow/react`.
6. **Auto-IP is idempotent and deterministic.** `assign_topology_ips()` in `services/autoip.py`: same input -> same output, and does not modify already-assigned IPs.

## Common Patterns

### New Canvas Node Type

1. Create `canvas/nodes/NameNode.tsx` with `React.memo`.
2. Add the type to `packages/shared-types/src/topology.ts`.
3. Register in `canvas/nodeTypes.ts`.
4. Add icon/palette metadata in `canvas/palette/PaletteItems.ts`.

### New API Endpoint

1. Add Pydantic schema in `schemas/`.
2. Add logic in `services/`.
3. Add route in `routers/` with validation and service call only.
4. Add tests in `tests/unit/` or `tests/integration/` as appropriate.

### New WebSocket Event

1. Add the type to `packages/shared-types/src/simulation.ts`.
2. Publish from backend `events/`.
3. Handle in frontend `hooks/useSimulationEvents.ts`.
4. Preserve existing event shapes unless a migration is planned.

### New Engine Adapter

1. Implement `SimulationEngineInterface` in `engines/new_adapter.py`.
2. Register in `core/dependencies.py` via config flag.
3. Keep mock engine behavior compatible with the real adapter contract.

## Anti-Patterns

```typescript
// Bad: API call in a component
const MyComponent = () => {
  const data = await axios.get('/api/topology');
};

// Good: hook/service/store boundary
const MyComponent = () => {
  const topology = useTopologyStore(s => s.nodes);
};
```

```python
# Bad: direct GNS3 call in a service
async def start_sim(topology_id: str):
    await httpx.post("http://gns3:3080/v2/projects")

# Good: injected adapter
async def start_sim(topology_id: str, engine: SimulationEngineInterface):
    await engine.start_topology(topology_id)
```

## Code Conventions

**TypeScript:** `PascalCase` for components/types, `camelCase` for functions/variables/hooks, `SCREAMING_SNAKE_CASE` for global constants. Hook prefix: `use`. Test files beside the unit under test.

**React:** keep side effects in hooks/services. Keep React Flow logic inside `canvas/`. Use existing UI/store patterns before inventing abstractions.

**Python:** `snake_case`, Pydantic models suffixed `Schema`, SQLAlchemy models without suffix. Async everywhere in routers/services. Type hints required on public functions.

**Git:** branch prefixes `feat/`, `fix/`, `chore/`, `docs/`. Conventional Commits preferred. Do not revert unrelated user changes.

## Testing Strategy

| Layer | Tool | Current expectation |
|-------|------|---------------------|
| Auto-IP engine | pytest | deterministic behavior covered |
| Backend services/routes | pytest + pytest-asyncio/httpx | main endpoints covered |
| Frontend services/helpers | Vitest | no backend/Docker required |
| Frontend hooks/components | Vitest + Testing Library | expand incrementally |
| Canvas/E2E | Playwright later | happy path template -> simulation |

## Export Formats

| Format | Use case |
|--------|----------|
| `.netsimflow.json` | Full topology state, re-importable; v1 implemented |
| `.md` | Markdown documentation report for clients/instructors; v1 implemented |
| `.pdf` | PDF documentation report for clients/instructors; v1 implemented |
| `.doc` | Word-compatible companion documentation; v1 implemented |
| `.docx` | Native Word document export |
| GNS3 `.gns3` | Interop with existing GNS3 desktop |
| Ansible inventory YAML | Automation bootstrap for real environments |
| Cisco CML topology YAML | Interop with Cisco Modeling Labs |

## Known Technical Debt

| Area | Issue | Priority |
|------|-------|----------|
| `events/manager.py` | Redis-backed publication exists with in-memory fallback, but needs multi-worker smoke testing before production scaling claims. | v1 hardening |
| `shared-types` `NetworkNode` / `NetworkLink` | `[key: string]: unknown` index signatures satisfy React Flow v12 constraints but weaken type checking. | v2 |
| Simulation engine | Mock engine supports demo UX; topology translation contract and mocked GNS3 adapter skeleton exist; live GNS3 node/link provisioning is still pending. | Sprint 2/3 |

## Current Roadmap Status

**Project state:** late Sprint 1 / early Sprint 2. The old "Sprint 1 open" status is stale.

**Done:**
- Monorepo with Turborepo, `apps/frontend`, `apps/api`, and `packages/shared-types`
- React Flow canvas, custom Router/Switch/Cloud/Host nodes, and simulated edges
- Zustand topology, UI, and simulation stores
- FastAPI topology CRUD, PostgreSQL schema, and Alembic initial migration
- Docker Compose dev infrastructure for PostgreSQL + Redis
- Mock simulation engine and start/stop lifecycle against saved topologies
- Basic WebSocket events for node status updates
- Auto-IP engine with unit tests
- Property panel and log console
- Template engine/UI for Blank, Hub-Spoke, and OSPF 3 Sites
- Probe endpoint/UI through the mock engine
- Logical link fault endpoint/UI with visual edge feedback
- Redis-backed WebSocket event bridge with in-memory dev fallback
- Backend route coverage for templates, probe, fault, export, and import
- Manual MVP smoke checklist in `MANUAL_TESTING.md`
- `.netsimflow.json` export/import v1 for saved topologies
- Frontend Vitest foundation for API/export helper logic
- Backend topology translation contract v1 with deterministic engine-neutral deployment plans
- Mock-tested GNS3 adapter skeleton for project create/open/close, status mapping, and clear unsupported feature errors
- Markdown report export v1 for saved topologies
- PDF and DOC report export v1 for saved topologies

**Partial:**
- Simulation lifecycle is mock-engine only by default; GNS3 mode has a tested HTTP boundary but no live node/link provisioning yet
- Redis event bridge is implemented but still needs manual multi-worker smoke testing
- Frontend test coverage exists for services/helpers, but not yet for hooks/canvas workflows

**Not started:**
- Real GNS3 topology translation and lifecycle integration
- Native DOCX report export workflow
- Auth/login/JWT
- CLI terminal

## Next Development Steps

### Step 1: Commit/Checkpoint The Stable MVP Demo

Goal: preserve the currently tested state before deeper changes.

Validation:
- `git diff --check`
- `cd apps/api && .\.venv\Scripts\python.exe -m pytest`
- `pnpm --filter @netsimflow/frontend test`
- `pnpm --filter @netsimflow/frontend build`

Expected behavior:
- Manual flow in `MANUAL_TESTING.md` remains green: template -> Auto-IP -> save -> start -> ping -> fault -> export -> import.

### Step 2: Frontend Test Expansion

Goal: cover hook/service behavior before real engine work increases complexity.

Implement:
- Tests around `useTopology` save/load/export/import behavior.
- Tests for disabled/empty-state logic where it can be extracted cleanly.
- Keep React Flow canvas interaction E2E for later.

Expected behavior:
- `pnpm --filter @netsimflow/frontend test` runs without backend, Docker, Redis, or browser window.

### Step 3: Live GNS3 Node/Link Provisioning

Goal: use the tested GNS3 adapter boundary to create real nodes and links when a local GNS3 server and template IDs are available.

Implement:
- Configure concrete GNS3 template IDs for the supported MVP device subset.
- Create real nodes and links from the engine-neutral deployment plan.
- Extend start/stop/status smoke tests against a local GNS3 server.
- Keep `SIMULATION_ENGINE=mock` as default.

Expected behavior:
- Existing frontend buttons still call the same API.
- Mock mode remains fully usable.
- GNS3 mode can be tested separately when a local GNS3 server is available.

### Step 4: Professional Export v2

Goal: build on Markdown/PDF/DOC report stability toward richer pro-account deliverables.

Implement:
- Generate native DOCX from the report model.
- Add report branding, pagination, and richer validation summaries.
- Keep Markdown as the stable source report format.

Expected behavior:
- Exported documents are useful as implementation companions, not just screenshots.

## Reference Docs

- `MANUAL_TESTING.md` — exact manual validation checklist
- `ARCHITECTURE.md` — architecture decisions and product constraints
- `NetSim-Flow_Planning_Document.md` — richer product and roadmap narrative
- `README.md` — public-facing overview
