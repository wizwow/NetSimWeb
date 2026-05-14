# 🌐 NetSim-Flow

**NetSim-Flow** is a modern, web-based network simulation and design platform. It allows users to build IP network topologies using a high-performance interactive canvas, automate IP addressing, and simulate real-world configurations using the GNS3 engine.

![NetSim-Flow Preview](https://via.placeholder.com/1200x600.png?text=NetSim-Flow+Canvas+Preview)

---

## 🚀 Primary Objective
Enable users to go from a blank canvas to a working **OSPF/BGP topology in less than 60 seconds**.

## ✨ Key Features
- **Interactive Canvas**: Drag-and-drop network nodes (Routers, Switches, Hosts, Cloud) using [React Flow](https://reactflow.dev/).
- **Auto-IP Engine**: Deterministic and idempotent algorithm that automatically assigns `/30` subnets to links and Loopback addresses to L3 devices.
- **Property Panel**: Sleek glassmorphism sidebar for real-time configuration of nodes and links.
- **Multi-vendor Support**: Designed to handle Cisco, Juniper, Arista, and generic Linux hosts.
- **Asynchronous Backend**: Powered by FastAPI and SQLAlchemy for high-performance state management.
- **Dockerized Infrastructure**: One-command setup for PostgreSQL, Redis, and GNS3.

## 🛠 Tech Stack
- **Frontend**: React 19, TypeScript, Zustand (State Management), Vite.
- **Canvas**: @xyflow/react (React Flow).
- **Backend**: FastAPI (Python 3.12), SQLAlchemy (Async), Alembic (Migrations).
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
- [ ] **GNS3 Adapter**: Translation of logic graph to GNS3 project.
- [ ] **Simulation Lifecycle**: Start/Stop/Status tracking.
- [ ] **WebSocket Event Bridge**: Real-time log streaming.

---

## 📄 License
This project is licensed under the MIT License - see the LICENSE file for details.
