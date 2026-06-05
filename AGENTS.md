# Octet — AI Agent Canon

**THIS FILE IS THE LAW.** Any AI agent working in this repo must read this file completely before writing a single line of code. If this file conflicts with anything else you think you know, this file wins.

---

## 0. Orientation — Read This First

You are working on **Octet**, a web platform for IP network topology simulation. The product has three user tiers (Education/Free, Professional/Pro, Enterprise) but the current scope is **MVP only**. Do not build for future tiers unless a spec explicitly says so.

**Project state: late Sprint 1 / early Sprint 2.** Core CRUD, auth, mock simulation, and export are working. You are likely implementing incremental features or tests, not building foundations.

**Before writing any code, you must:**

1. Read the relevant existing file(s) — never guess at an existing signature or pattern.
2. Confirm you know exactly which files you will create or modify.
3. Confirm your change does not break an existing test.
4. If you are unsure about anything architectural, **stop and ask** rather than invent.

---

## 1. Hard Stops — Never Do These

These are non-negotiable. Violating any of them requires a full rewrite.

| # | NEVER DO THIS |
|---|---------------|
| 1 | Make a direct HTTP call to GNS3 from anywhere except `apps/api/app/engines/` |
| 2 | Call `useReactFlow()` or import from `@xyflow/react` outside `apps/frontend/src/canvas/` |
| 3 | Put business logic in a FastAPI router function |
| 4 | Make an API call directly from a React component |
| 5 | Call Zustand store actions from inside a React component body |
| 6 | Add a new shared type in any file other than `packages/shared-types/src/` |
| 7 | Modify already-assigned IPs in `assign_topology_ips()` |
| 8 | Import `packages/shared-types` back into `apps/api` (Python backend has its own Pydantic schemas) |
| 9 | Add `console.log` or `print()` debug statements to committed code |
| 10 | Create a new file in a location not listed in the Repository Structure section |

---

## 2. Repository Structure — Exact File Placement

Every file has exactly one correct home. If you are unsure, default to asking.

```
apps/frontend/src/
  canvas/           React Flow nodes, edges, handles, canvas container, nodeTypes.ts
  canvas/nodes/     One file per node type: RouterNode.tsx, SwitchNode.tsx, etc.
  canvas/edges/     Custom edge components
  canvas/palette/   Palette sidebar items and metadata
  components/       Generic reusable UI components NOT tied to canvas
  store/            Zustand slices ONLY — one file per domain slice
  hooks/            Custom React hooks ONLY — one file per hook
  services/         API client, WebSocket client, export/import helpers
  types/            Frontend-only TS types that are not shared with backend

apps/api/app/
  routers/          FastAPI route handlers — validation + service call only, no logic
  services/         Business logic — testable without HTTP context
  engines/          Simulation engine adapters — the ONLY place that calls GNS3
  models/           SQLAlchemy ORM models — no suffix
  schemas/          Pydantic v2 request/response schemas — suffix: Schema
  events/           WebSocket pub/sub and Redis bridge
  core/             App config, dependency injection, startup

apps/api/tests/
  unit/             Tests with no DB, no HTTP, no Docker
  integration/      Tests that need a real DB or HTTP client

packages/shared-types/src/
  topology.ts       NetworkNode, NetworkLink, Topology
  simulation.ts     SimulationEvent, FaultRequest, ProbeResult
```

---

## 3. Architectural Rules

### Rule 1 — Simulation Engine Adapter

All simulation engine calls go through the `SimulationEngineInterface`. Never bypass it.

```python
# WRONG — direct HTTP in a service
async def start_sim(topology_id: str):
    await httpx.post("http://gns3:3080/v2/projects")

# CORRECT — injected adapter
async def start_sim(topology_id: str, engine: SimulationEngineInterface):
    await engine.start_topology(topology_id)
```

### Rule 2 — Shared Types are the Contract

TypeScript types in `packages/shared-types` define the data contract. Pydantic schemas in `apps/api/app/schemas/` must mirror them field-for-field. If you change a shared type, you must update the matching Pydantic schema and rebuild: `cd packages/shared-types && pnpm build`.

### Rule 3 — Backend Layering

```
Router → Service → Engine (or Repository)
```

- Router: receives request, validates with Pydantic, calls one service function, returns response.
- Service: all business logic, calls engine or DB, raises `HTTPException` if needed.
- Engine: only adapter code, no business logic.

### Rule 4 — Frontend Data Flow

```
API ← Service ← Hook ← Component (read-only via selector)
                Store ←
```

- Components read state via Zustand selectors only.
- Components trigger actions only via hooks.
- Hooks call services or dispatch store actions.
- No API calls, no store dispatch, no side effects in component bodies.

```typescript
// WRONG — API call in component
const MyComponent = () => {
  const data = await axios.get('/api/topology');
};

// CORRECT — hook/selector pattern
const MyComponent = () => {
  const topology = useTopologyStore(s => s.nodes); // read via selector
  const { saveTopology } = useTopology();           // action via hook
};
```

### Rule 5 — Canvas Isolation

`useReactFlow()`, `useNodes()`, `useEdges()`, and any import from `@xyflow/react` must appear **only inside `apps/frontend/src/canvas/`**. If a non-canvas component needs topology data, it reads from the Zustand store.

### Rule 6 — Auto-IP is Idempotent

`assign_topology_ips()` in `apps/api/app/services/autoip.py` must never modify an IP that is already assigned. Same input always produces same output.

---

## 4. Code Conventions

### TypeScript / React

| Thing | Convention | Example |
|-------|-----------|---------|
| Components | PascalCase | `RouterNode.tsx` |
| Types/Interfaces | PascalCase | `NetworkNode`, `TopologyState` |
| Hooks | camelCase with `use` prefix | `useTopology`, `useSimulationEvents` |
| Functions / variables | camelCase | `saveTopology`, `nodeCount` |
| Global constants | SCREAMING_SNAKE_CASE | `MAX_NODES_FREE_TIER` |
| Test files | Beside the unit under test | `useTopology.test.ts` next to `useTopology.ts` |

- No `any`. Use `unknown` and narrow it.
- No inline styles. Use Tailwind classes.
- No default exports from hooks or services. Use named exports.
- `React.memo` required on all canvas node components.

### Python

| Thing | Convention | Example |
|-------|-----------|---------|
| Functions / variables | snake_case | `assign_topology_ips` |
| Pydantic schemas | PascalCase + `Schema` suffix | `TopologyCreateSchema` |
| SQLAlchemy models | PascalCase, no suffix | `Topology`, `User` |
| Async | Required everywhere in routers/services | `async def get_topology(...)` |
| Type hints | Required on all public functions | `async def get(...) -> TopologySchema` |

### Git Branches and Commits

- Branch prefixes: `feat/`, `fix/`, `chore/`, `docs/`
- Commit style: Conventional Commits — `feat: add password reset endpoint`
- Never revert or modify unrelated code in your branch

---

## 5. Common Recipes

Copy these patterns exactly. Do not invent variations unless explicitly told to.

### New Canvas Node Type

1. `apps/frontend/src/canvas/nodes/NameNode.tsx` — component wrapped in `React.memo`
2. `packages/shared-types/src/topology.ts` — add the new type literal to `NodeType`
3. `apps/frontend/src/canvas/nodeTypes.ts` — register the component
4. `apps/frontend/src/canvas/palette/PaletteItems.ts` — add icon + label metadata
5. Run `cd packages/shared-types && pnpm build`

### New API Endpoint

1. `apps/api/app/schemas/domain.py` — add `RequestSchema` and `ResponseSchema`
2. `apps/api/app/services/domain_service.py` — add business logic function
3. `apps/api/app/routers/domain.py` — add route: validate input, call service, return response
4. `apps/api/tests/unit/test_domain_service.py` — add unit test for the service function
5. `apps/api/tests/integration/test_domain_router.py` — add integration test for the route

### New WebSocket Event

1. `packages/shared-types/src/simulation.ts` — add the event type
2. `apps/api/app/events/` — publish from the event manager
3. `apps/frontend/src/hooks/useSimulationEvents.ts` — add handler
4. Never change an existing event's shape without a migration plan

### New Zustand Slice

1. `apps/frontend/src/store/domainSlice.ts` — define state + actions
2. Wire into the root store in `apps/frontend/src/store/index.ts`
3. Access in hooks via `useDomainStore(s => s.field)` — never destructure the whole store

### New Engine Adapter

1. Create `apps/api/app/engines/adapter_name.py` implementing `SimulationEngineInterface`
2. Register in `apps/api/app/core/dependencies.py` behind a config flag
3. The mock engine in `engines/mock.py` is the reference implementation

---

## 6. Testing Rules

| Layer | Tool | Rule |
|-------|------|------|
| Python unit | pytest | No DB, no HTTP, no Docker required |
| Python integration | pytest + httpx TestClient | Real DB via test fixtures |
| Frontend services/helpers | Vitest | No browser, no backend required |
| Frontend hooks/components | Vitest + Testing Library | No browser, no backend required |
| Canvas / E2E | Playwright (future) | Not yet in scope |

**A test that needs Docker to pass is an integration test.** Put it in `tests/integration/`, not `tests/unit/`.

**Every new service function gets at least one unit test.** No exceptions.

**Every new API route gets at least one integration test.** No exceptions.

---

## 7. Run Commands

```powershell
# Infrastructure (PostgreSQL + Redis) — Terminal 1
docker compose -f infra/docker-compose.dev.yml up -d

# Backend — Terminal 2
cd apps/api
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000

# Frontend — Terminal 3
pnpm dev
# or: cd apps/frontend && pnpm dev   →  http://localhost:5173

# All tests
turbo test

# Backend tests only
cd apps/api && pytest

# Frontend tests only (no Docker needed)
cd apps/frontend && pnpm test

# DB migrations
cd apps/api && alembic upgrade head
cd apps/api && alembic revision --autogenerate -m "description"

# Lint
turbo lint
cd apps/api && ruff check . && ruff format .
cd apps/frontend && pnpm lint

# Rebuild shared types after any change to packages/shared-types
cd packages/shared-types && pnpm build
```

---

## 8. Environment Variables

```bash
# apps/frontend/.env.local
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws

# apps/api/.env
DATABASE_URL=postgresql+asyncpg://octet:password@localhost:5432/octet
REDIS_URL=redis://localhost:6379/0
GNS3_URL=http://localhost:3080
GNS3_USER=admin
GNS3_PASSWORD=admin
SIMULATION_ENGINE=mock          # "gns3" | "mock" — use "mock" for dev without GNS3
GNS3_TEMPLATE_MAPPINGS={}
SECRET_KEY=dev-secret-change-in-prod
CORS_ORIGINS=http://localhost:5173
DEV_AUTH_EMAIL=dev@octet.local
DEV_AUTH_ENABLED=false          # set true only for local dev bypass
```

Auth: signed JWTs from `POST /api/v1/auth/register` and `POST /api/v1/auth/login`.
Dev bypass: `DEV_AUTH_ENABLED=true` → missing `Authorization` uses `DEV_AUTH_EMAIL`.

---

## 9. Known Technical Debt (Do Not Touch Without a Spec)

| Area | Issue | Priority |
|------|-------|----------|
| `events/manager.py` | Redis pub needs multi-worker smoke test before prod scaling claims | v1 hardening |
| `shared-types` index signatures | `[key: string]: unknown` weakens type checking | v2 |
| Simulation engine | Mock only; GNS3 live node/link provisioning pending | Sprint 2/3 |
| Auth | No password reset, no OAuth, no email verification, no billing | next hardening |

---

## 10. Roadmap Quick Reference

**Done (do not re-implement):** monorepo, React Flow canvas, Zustand stores, FastAPI CRUD, PostgreSQL schema, Alembic migration, Docker Compose dev infra, mock simulation engine, WebSocket events, Auto-IP, property panel, log console, topology templates (Blank/Hub-Spoke/OSPF 3 Sites), probe endpoint, link fault endpoint, Redis event bridge, export routes (JSON/MD/PDF/DOC), JWT auth v1 (register/login/me), frontend login screen.

**Partial (extend, do not rebuild):** auth hardening, GNS3 live provisioning, Redis multi-worker testing, frontend hook/canvas tests.

**Not started:** live GNS3 node/link provisioning, native DOCX export, CLI terminal.

---

## 11. Reference Documents

| File | Purpose |
|------|---------|
| `MANUAL_TESTING.md` | Step-by-step manual smoke checklist |
| `ARCHITECTURE.md` | Architecture decisions and constraints |
| `Octet_Planning_Document.md` | Full product and roadmap narrative |
| `README.md` | Public-facing project overview |
| `specs/` | Task specs written by the architect for implementation |
