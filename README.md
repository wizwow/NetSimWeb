# 🌐 NetSim-Flow

**NetSim-Flow** is a modern, web-based network simulation and design platform. It allows users to build IP network topologies using a high-performance interactive canvas, automate IP addressing, and simulate real-world configurations using the GNS3 engine.

![NetSim-Flow Preview](https://via.placeholder.com/1200x600.png?text=NetSim-Flow+Canvas+Preview)

---

## 🚀 Primary Objective
Enable users to go from a blank canvas to a working **OSPF/BGP topology in less than 60 seconds**.

## 👥 Who It's For
- **Teachers and students:** browser-first network lessons where a simple topology can be built, auto-addressed, simulated, and explained in minutes.
- **Network professionals:** planning real IP networks, OSPF/failover behavior, and implementation documentation before touching production equipment.
- **Enterprise teams:** long-term on-premise network twins for testing changes, planning maintenance, exporting documentation, and maintaining a network source of truth.

## ✨ Key Features
- **Interactive Canvas**: Drag-and-drop network nodes (Routers, Switches, Hosts, Cloud) using [React Flow](https://reactflow.dev/).
- **Auto-IP Engine**: Deterministic and idempotent algorithm that automatically assigns `/30` subnets to links and Loopback addresses to L3 devices.
- **Property Panel**: Sleek glassmorphism sidebar for real-time configuration of nodes and links.
- **JSON Export/Import**: Save and restore complete `.netsimflow.json` topology snapshots for demo and planning workflows.
- **Professional Reports**: Generate `.netsimflow.md`, WeasyPrint-rendered `.netsimflow.pdf`, and Word-compatible `.netsimflow.doc` reports with embedded topology diagrams.
- **Auth Stub**: Temporary dev-user ownership scope so topologies are tagged and gated before live GNS3 work.
- **Multi-vendor Support**: Designed to handle Cisco, Juniper, Arista, and generic Linux hosts.
- **Asynchronous Backend**: Powered by FastAPI and SQLAlchemy for high-performance state management.
- **Dockerized Infrastructure**: One-command setup for PostgreSQL, Redis, and GNS3.

## 🛠 Tech Stack
- **Frontend**: React 19, TypeScript, Zustand (State Management), Vite.
- **Canvas**: @xyflow/react (React Flow).
- **Backend**: FastAPI (Python 3.12), SQLAlchemy (Async), Alembic (Migrations).
- **Reports**: Jinja2 templates + WeasyPrint PDF rendering.
- **Database**: PostgreSQL (Persistence), Redis (Pub/Sub & Caching).
- **Monorepo**: Turborepo + pnpm.
- **Simulation**: GNS3 Server integration.

---

## 📂 Project Structure
```text
NetSimWeb/
├── apps/
│   ├── frontend/       # React application (Vite)
│   └── api/            # FastAPI backend
├── packages/
│   └── shared-types/   # TypeScript types shared across the monorepo
├── infra/              # Docker Compose and infra configurations
└── turbo.json          # Turborepo configuration
```

---

## 🚀 Getting Started

### Prerequisites
- Node.js 20+ & `pnpm`
- Python 3.12+
- Docker & Docker Compose

### 1. Infrastructure Setup
Spin up the database and required services:
```bash
docker compose -f infra/docker-compose.dev.yml up -d
```

### 2. Backend Setup
```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate  # Or .venv\Scripts\activate on Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

### 3. Frontend Setup
```bash
pnpm install
pnpm dev
```

---

## 📅 Roadmap

### Sprint 1: Canvas Foundation ✅
- [x] Monorepo Setup (Turborepo)
- [x] React Flow integration with custom nodes
- [x] Backend CRUD for Topologies
- [x] PostgreSQL + Alembic integration

### Sprint 2: Simulation Core 🚀 (In Progress)
- [x] **Auto-IP Engine**: Automatic subnetting for P2P links.
- [x] **Property Panel**: Advanced node/link configuration UI.
- [x] **Templates**: Blank, Hub-Spoke, and OSPF 3 Sites quick starts.
- [x] **Mock Probe/Fault UX**: Ping and link-down fault workflows for demo simulation.
- [x] **WebSocket Event Bridge**: Redis-backed event publication with local dev fallback.
- [x] **JSON Export/Import v1**: `.netsimflow.json` round trip for saved topologies.
- [x] **Report Export v1**: Markdown/PDF/DOC documentation with embedded topology diagrams.
- [x] **Auth Stub v1**: Dev bearer-token/current-user dependency and owner-scoped topology/simulation endpoints.
- [ ] **GNS3 Adapter**: Translation of logic graph to GNS3 project.
- [ ] **Simulation Lifecycle**: Real engine start/stop/status tracking.
- [ ] **Auth/Login**: JWT-backed users and topology ownership before real Pro/SaaS isolation.

---

## 📄 License
This project is licensed under the MIT License - see the LICENSE file for details.
