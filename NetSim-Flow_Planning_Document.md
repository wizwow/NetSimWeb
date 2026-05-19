# NetSim-Flow — Documento di Pianificazione Iniziale
**Versione:** 0.1-DRAFT | **Data:** 2026-05-14 | **Classificazione:** Internal / Confidential

---

## Executive Summary

NetSim-Flow è una web application per la simulazione e progettazione di reti IP, progettata su un modello di astrazione top-down: l'utente opera su oggetti logici ad alto livello con la possibilità di specializzarli progressivamente fino all'emulazione vendor-specific. Il vincolo di progetto primario è la time-to-topology ≤ 60 secondi dalla login a un modello OSPF multi-sede funzionante.

---

## Product Mission & End-State Vision

NetSim-Flow deve diventare una piattaforma web per progettare, simulare, spiegare e documentare reti IP, mantenendo una curva di ingresso bassa per la didattica e una profondità progressiva per ambienti professionali.

### Education / Free Web Account

Un docente di scuola superiore deve poter aprire il sito NetSimWeb con un account gratuito, costruire direttamente nel browser una topologia semplice con router, connessione Internet, switch e tre PC, trascinare i collegamenti, applicare Auto-IP e avviare la simulazione. Il prodotto deve rendere immediata una lezione su subnetting, default gateway, switching e routing, senza installazioni locali e senza configurazione manuale obbligatoria.

**Implicazioni prodotto:** UX rapida, template didattici, Auto-IP affidabile, simulazione mock/logica utile anche senza GNS3 reale, onboarding leggero, account free con limiti chiari.

### Professional / Pro Account

Un sysadmin deve poter usare NetSimWeb per pianificare una rete reale prima dell'implementazione: modellare tre o più sedi, inserire IP reali, scegliere hardware o ruoli logici, definire connessioni e host, simulare OSPF e verificare il comportamento quando alcuni link vanno giù. Quando il progetto è soddisfacente, deve poterlo salvare ed esportare come XML strutturato, DOC/PDF e documentazione operativa da usare come companion durante la configurazione della rete reale.

**Implicazioni prodotto:** salvataggio affidabile, gestione manuale degli IP, validazione conflitti, fault simulation, esportazioni strutturate, report leggibili, storico progetti, tier paid/pro.

### Enterprise / On-Premise

Una grande azienda deve poter installare NetSimWeb on-premise e usarlo come clone virtuale della propria rete: testare nuove apparecchiature, pianificare manutenzioni, validare cambiamenti, generare documentazione e mantenere una source of truth tecnica. Questo obiettivo è volutamente complesso e resta nel lungo periodo, dopo il consolidamento del SaaS MVP e del flusso pro.

**Implicazioni prodotto:** deployment self-hosted, sicurezza e RBAC avanzati, import/export estesi, audit trail, scalabilità, integrazione con inventari esterni e modello dati abbastanza fedele da rappresentare reti reali.

---

## 1. Architettura High-Level

### 1.1 Stack Tecnologico

| Layer | Tecnologia | Razionale |
|---|---|---|
| **Canvas / UI** | React 19 + [React Flow](https://reactflow.dev/) | Grafo drag-and-drop nativo, stato gestito con Zustand, performance ottimale su grafi >200 nodi |
| **Rendering grafico** | React Flow (internamente SVG/HTML) | Preferibile a Canvas API raw per accessibilità e interattività DOM; fallback WebGL con Pixi.js per topologie massive |
| **State Management** | Zustand + Immer | Mutazioni immutabili, devtools, slicing modulare per topology/simulation/ui state |
| **Frontend Build** | Vite + TypeScript strict | HMR veloce, tree-shaking aggressivo |
| **Comunicazione RT** | WebSocket (Socket.io) + REST API | WS per eventi simulazione real-time (link flap, failover, log stream); REST per CRUD topologie |
| **API Gateway** | FastAPI (Python 3.12) | Async nativo, Pydantic v2 per validation/serialization del graph model, OpenAPI auto-gen |
| **Motore Simulazione** | GNS3 Server (self-hosted) o motore custom Python | GNS3 per fase MVP (API REST mature); migrazione a motore proprietario in v2 |
| **Emulazione nodi** | QEMU/KVM + Docker | QEMU per immagini Cisco/Juniper; Docker per nodi lightweight (FRRouting, Alpine) |
| **Orchestrazione container** | Docker Compose (dev) → Kubernetes (prod) | Isolamento per topologia, scaling orizzontale del simulation backend |
| **Database** | PostgreSQL 16 + Redis | Postgres per persistenza topologie/utenti; Redis per session state e pub/sub eventi simulazione |
| **Auth** | Keycloak / Auth0 | SSO, RBAC (student/designer/admin), JWT |
| **Export / Report** | WeasyPrint (PDF) + Jinja2 templates | Generazione report configurazione lato server |
| **Infrastruttura** | Docker, Nginx reverse proxy | Nessuna dipendenza cloud mandatory; deploy on-premise friendly per ambienti didattici |

### 1.2 Diagramma Architetturale

```
┌─────────────────────────────────────────────────────┐
│                    BROWSER CLIENT                    │
│  React 19 + React Flow + Zustand                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐ │
│  │ Canvas   │ │ Props    │ │ CLI Terminal (xterm.js)│ │
│  │ Editor   │ │ Panel    │ │ (deep-dive mode)      │ │
│  └────┬─────┘ └────┬─────┘ └──────────┬────────────┘ │
└───────┼─────────────┼─────────────────┼──────────────┘
        │  REST/WS    │                 │ WebSocket
┌───────▼─────────────▼─────────────────▼──────────────┐
│                  API GATEWAY (FastAPI)                 │
│  /api/v1/topology  /api/v1/simulation  /ws/events     │
└───────┬──────────────────────┬────────────────────────┘
        │                      │
┌───────▼──────┐    ┌──────────▼──────────────────────┐
│  PostgreSQL  │    │     SIMULATION ENGINE            │
│  + Redis     │    │  GNS3 Server / Custom Python     │
└──────────────┘    │  ┌──────────┐  ┌─────────────┐  │
                    │  │ QEMU/KVM │  │   Docker    │  │
                    │  │(Cisco IOS│  │ (FRRouting) │  │
                    │  │ Juniper) │  │             │  │
                    │  └──────────┘  └─────────────┘  │
                    └─────────────────────────────────┘
```

---

## 2. MVP — Minimum Viable Product (Sprint 1-3)

### 2.1 Scope MVP (≈ 6 settimane)

L'MVP deve dimostrare il core value: **topologia funzionante in <60s**, senza pretesa di completezza feature.

### 2.2 Feature Set MVP

| Priorità | Feature | Note |
|---|---|---|
| P0 | **Canvas drag-and-drop** | Palette con: Cloud, Sede, Router, Switch, PC |
| P0 | **Connessione link tra nodi** | Click su porta output → click su porta input |
| P0 | **Auto-IP assignment** | Subnetting automatico RFC 1918 per ogni link point-to-point |
| P0 | **Template topologie** | 3 template predefiniti: Hub-and-Spoke, OSPF 3 sedi, Basic LAN |
| P0 | **Avvio simulazione** | Play/Stop dell'intera topologia con feedback visivo stato nodi |
| P1 | **Ping/Trace emulato** | Tool di verifica connettività inline nel canvas |
| P1 | **Failover simulation** | Right-click su link → "Simula guasto" con propagazione visiva |
| P1 | **Export topologia JSON** | Salvataggio/caricamento stato completo; v1 `.netsimflow.json` implementato |
| P1 | **Log panel** | Stream real-time eventi simulazione (link state, OSPF adjacency) |
| P2 | **CLI terminal** | Accesso xterm.js per nodi specializzati (solo Cisco IOS in MVP) |
| P2 | **Report PDF base** | Export configurazione con IP table e link diagram |

### 2.3 Out of Scope MVP

- Multi-vendor deep emulation (Juniper, Arista)
- BGP / MPLS / SD-WAN scenarios
- Collaborazione multi-utente real-time
- Mobile/touch UI

---

## 3. Logica di Astrazione vs Specificità — Modello Dati

### 3.1 Principio: Abstract Device → Specialization Chain

Il modello adotta un pattern simile al **prototype chain**: ogni nodo ha una `baseType` e può essere progressivamente specializzato aggiungendo layer di configurazione. La specializzazione è **additiva e reversibile**.

### 3.2 Schema Dati — Node Object

```typescript
interface NetworkNode {
  // === LAYER 0: Identità ===
  id: string;                        // UUID v4
  label: string;                     // Nome display
  position: { x: number; y: number };

  // === LAYER 1: Astrazione logica (sempre presente) ===
  baseType: 'router' | 'switch' | 'firewall' | 'cloud' | 'host' | 'site';
  role?: 'core' | 'distribution' | 'access' | 'edge' | 'hub' | 'spoke';
  protocols?: Array<'ospf' | 'bgp' | 'eigrp' | 'static' | 'rip'>;

  // === LAYER 2: Configurazione logica (opzionale) ===
  logicalConfig?: {
    interfaces: LogicalInterface[];   // Porte logiche, IP auto o manuali
    routingConfig?: OSPFConfig | BGPConfig | StaticRoutes;
    loopback?: string;               // Auto-assegnato se non specificato
  };

  // === LAYER 3: Specializzazione vendor (opzionale) ===
  vendorSpec?: {
    vendor: 'cisco' | 'juniper' | 'arista' | 'mikrotik' | 'generic';
    platform: string;                // es. "c7200", "vmx", "eos"
    imageRef?: string;               // Riferimento immagine QEMU/Docker
    cliConfig?: string;              // Config testuale (IOS/JunOS syntax)
    features: Record<string, unknown>; // Feature vendor-specific
  };

  // === LAYER 4: Runtime state (volatile, non persistito) ===
  runtimeState?: {
    status: 'stopped' | 'booting' | 'running' | 'error' | 'degraded';
    cpuPercent?: number;
    memMB?: number;
    nodeId?: string;                 // ID nodo nel simulation engine
  };

  // === Metadata ===
  tags: string[];
  createdAt: string;
  updatedAt: string;
  lockedBy?: string;                 // Per future implementazioni collaborative
}
```

### 3.3 Schema Dati — Link Object

```typescript
interface NetworkLink {
  id: string;
  sourceNodeId: string;
  sourcePort: string;               // "GigabitEthernet0/0" o "eth0" (astratto)
  targetNodeId: string;
  targetPort: string;
  
  linkType: 'ethernet' | 'serial' | 'fiber' | 'vpn-tunnel' | 'logical';
  
  ipConfig?: {
    subnet: string;                  // CIDR, auto-assegnato se null
    sourceIp?: string;
    targetIp?: string;
  };
  
  qos?: {
    bandwidthMbps?: number;
    latencyMs?: number;
    packetLossPercent?: number;
  };
  
  // Failover simulation
  faultState?: {
    active: boolean;
    type?: 'link-down' | 'high-latency' | 'packet-loss';
    triggeredAt?: string;
  };
}
```

### 3.4 Specializzazione Progressiva

```
NetworkNode (baseType: 'router')
    │
    ▼ Utente aggiunge protocollo
    + logicalConfig.protocols: ['ospf']
    + logicalConfig.routingConfig: { area: 0, processId: 1 }
    │
    ▼ Utente sceglie vendor
    + vendorSpec.vendor: 'cisco'
    + vendorSpec.platform: 'c7200'
    │
    ▼ Sistema/Utente genera CLI config
    + vendorSpec.cliConfig: "router ospf 1\n network..."
```

**La topologia rimane esportabile e simulabile a qualsiasi livello della chain.**

---

## 4. User Journey — Modellazione in <60 Secondi

### 4.1 Flusso Target: "OSPF tra tre sedi"

```
[00s] Login  ──→  [05s] Dashboard  ──→  [08s] "Nuovo progetto"
                                              │
                         ┌────────────────────▼──────────────────────┐
                         │         TEMPLATE PICKER (modal)           │
                         │  [Blank] [Hub-Spoke] [★ OSPF Multi-Sede]  │
                         └────────────────────┬──────────────────────┘
                                              │ Click "OSPF Multi-Sede"
[12s] Canvas popolato automaticamente con:   ▼
      - 3 nodi "Sede" interconnessi
      - 1 nodo "Core Router" centrale
      - Link point-to-point con IP auto-assegnati
      - OSPF area 0 pre-configurato su tutti i nodi
                                              │
[15s] Click "▶ Avvia Simulazione"           ▼
[30s] Nodi in stato "running" (feedback     ▼
      visivo: icone verdi, link animati)
                                              │
[35s] Click su link → "Ping test"           ▼
[40s] Output: "Reply from 10.0.1.2: 3ms"   ▼
                                              │
[50s] Right-click link → "Simula guasto"   ▼
[55s] Visualizzazione failover OSPF         ▼
      (rerouting animato, log panel attivo)
                                              │
[60s] ✅ OBIETTIVO RAGGIUNTO               ▼
```

### 4.2 Meccanismi Tecnici Abilitanti

| Requisito UX | Implementazione |
|---|---|
| Template istantaneo | JSON pre-baked lato server, hydration client-side in <200ms |
| Auto-IP | Algoritmo subnetting: pool 10.0.0.0/8, /30 per ogni link P2P, loopback /32 |
| Pre-configurazione OSPF | Template genera direttamente `logicalConfig` completo; motore traduce in CLI al momento dell'avvio |
| Feedback avvio simulazione | WebSocket events: `node.status.changed` → aggiornamento Zustand store → re-render React Flow |
| Ping test inline | API call `POST /api/v1/simulation/{id}/probe` con risposta streaming |
| Animazione failover | Link `faultState.active = true` → CSS class change + React Flow edge style update + log event push |

---

## 5. Struttura del Report di Esportazione

### 5.1 Formato: Markdown (primary) + PDF (derived)

Il documento viene generato server-side da un template Jinja2 e servito come PDF via WeasyPrint. Il Markdown sorgente è sempre disponibile per versionamento Git. La v1 include anche un diagramma SVG deterministico generato dal backend a partire dalle posizioni salvate del canvas.

### 5.2 Schema del Report

```
NetSim-Flow — Network Configuration Report
==========================================
Project: <nome_progetto>
Version: <version>
Generated: <ISO8601 timestamp>
Author: <username>
Simulation Engine: <engine_type> <engine_version>

---

## 1. Topology Overview
- **Nodes:** N
- **Links:** M
- **Protocols:** OSPF (Area 0), Static
- **Address Space:** 10.0.0.0/8 (auto-assigned)

### Topology Diagram
[Embedded SVG export del canvas]

---

## 2. Node Inventory

| Node ID | Label | Type | Vendor | Platform | Status |
|---------|-------|------|--------|----------|--------|
| node-1  | HQ    | Router | Cisco | c7200   | Running |
| node-2  | Branch-A | Router | Generic | - | Running |

---

## 3. Interface & IP Table

| Node | Interface | IP Address | Subnet | Peer Node | Peer Interface |
|------|-----------|------------|--------|-----------|----------------|
| HQ   | Gi0/0     | 10.0.1.1   | /30    | Branch-A  | Gi0/0 |
| HQ   | Gi0/1     | 10.0.2.1   | /30    | Branch-B  | Gi0/0 |

---

## 4. Routing Configuration

### 4.1 OSPF Summary
- Process ID: 1
- Router-ID assignments: [tabella]
- Area topology: [lista adjacency]

### 4.2 Per-Node Routing Config (CLI Format)

#### HQ (Cisco IOS)
```
hostname HQ
!
interface GigabitEthernet0/0
 ip address 10.0.1.1 255.255.255.252
 no shutdown
!
router ospf 1
 router-id 10.255.0.1
 network 10.0.1.0 0.0.0.3 area 0
```

---

## 5. Link Specifications

| Link ID | Source | Source Port | Target | Target Port | Type | Bandwidth | Latency |
|---------|--------|-------------|--------|-------------|------|-----------|---------|
| lnk-1   | HQ     | Gi0/0       | Branch-A | Gi0/0    | Ethernet | 1Gbps | 5ms |

---

## 6. Simulation Events Log
[Ultimi 100 eventi ordinati cronologicamente]

| Timestamp | Event Type | Node/Link | Detail |
|-----------|------------|-----------|--------|
| 2026-05-14T10:15:32Z | OSPF_ADJ_UP | HQ↔Branch-A | Neighbor 10.0.1.2 Full |
| 2026-05-14T10:16:01Z | LINK_FAULT | lnk-2 | Fault injected by user |
| 2026-05-14T10:16:02Z | OSPF_REROUTE | Branch-B | Via 10.0.1.1 (HQ) |

---

## 7. Validation Checklist

- [x] All nodes reachable (ping matrix: NxN)
- [x] OSPF full adjacency on all P2P links
- [x] No routing loops detected
- [ ] Redundant path for all sites
- [ ] QoS policies configured

---

## 8. Export Metadata

```json
{
  "exportFormat": "netsimflow-v1",
  "topologyId": "topo-uuid",
  "checksum": "sha256:abc...",
  "compatibleEngines": ["gns3>=2.2", "netsimflow-engine>=1.0"],
  "abstractionLevel": "logical"  // "logical" | "vendor-specific"
}
```
```

### 5.3 Formati di Export Supportati

| Formato | Use Case |
|---|---|
| `.netsimflow.json` | Stato completo topologia, reimportabile |
| `.md` / `.pdf` | Report documentazione per clienti/docenti |
| GNS3 `.gns3` | Interop con GNS3 desktop esistente |
| Ansible inventory YAML | Automation bootstrap per ambienti reali |
| Cisco CML topology YAML | Interop con Cisco Modeling Labs |

---

## 6. Roadmap di Sviluppo

### Sprint 1 (Settimane 1-2) — Canvas Foundation
- [ ] Setup monorepo (Turborepo): `apps/frontend`, `apps/api`, `packages/shared-types`
- [ ] React Flow integration con nodi custom (Router, Switch, Cloud, Host)
- [ ] Zustand store: slice `topology` (nodes, edges, selection)
- [ ] FastAPI skeleton: CRUD `/topology`, WebSocket `/ws/events`
- [ ] PostgreSQL schema v1: `topologies`, `nodes`, `links`, `users`
- [ ] Docker Compose dev environment completo

### Sprint 2 (Settimane 3-4) — Simulation Core
- [ ] Integrazione GNS3 Server API (start/stop topology, get node status)
- [x] Auto-IP engine: subnetting algoritmo + conflict detection
- [x] WebSocket event bridge: backend events → Redis pub/sub → client WS, con fallback in-memory per dev
- [x] Template engine: 3 template pre-baked (Blank, Hub-Spoke, OSPF 3 sedi)
- [x] Node status visualization (colori stati, animazione link attivi)
- [x] Probe/fault mock UX hardening e test route backend
- [x] Manual testing checklist MVP in `MANUAL_TESTING.md`
- [x] Export/import JSON v1 (`.netsimflow.json`) per topologie salvate

### Sprint 3 (Settimane 5-6) — MVP Completion
- [x] Failover injection logico (link fault) + propagazione visiva mock
- [x] Probe tool ping inline con mock engine
- [ ] Log panel real-time
- [x] Export JSON topologia
- [x] Report PDF basic (Jinja2 + WeasyPrint) con diagramma SVG embedded
- [ ] Auth integration (JWT, login page)
- [x] UX polish: toolbar canvas raggruppata in menu dropdown

### Sprint 4 (Settimane 7-9) — Deep Dive & Polish
- [ ] CLI terminal (xterm.js) per nodi Cisco IOS
- [ ] Vendor specialization UI (modal property panel)
- [ ] QoS/latency simulation per link
- [ ] Ping matrix automatica (validazione post-simulazione)
- [ ] Export Ansible inventory

### Sprint 5+ (v2 Backlog)
- [ ] Motore simulazione proprietario (rimpiazza GNS3 per ambienti cloud)
- [ ] Collaborazione real-time (CRDT / Yjs)
- [ ] BGP / MPLS / SD-WAN templates
- [ ] AI assistant ("Suggest me a topology for WAN redundancy")
- [ ] Mobile-friendly canvas (touch drag-and-drop)
- [ ] Marketplace template community

---

## 7. Considerazioni su Failover & Fault Simulation

Il motore di failover deve operare a **due livelli**:

**Livello 1 — Simulazione logica (MVP):** Nessuna emulazione reale; il backend marca un link come `faultState.active = true`, inietta un evento WebSocket `LINK_DOWN`, e il frontend aggiorna visualizzazione + log. I nodi emulati ricevono un `shutdown` sull'interfaccia corrispondente via GNS3 API. I protocolli di routing reagiscono realmente (OSPF riconverge, BGP session cade).

**Livello 2 — Fault injection avanzata (v2):** Iniezione di packet loss parziale, jitter, asimmetria di banda via `tc netem` sul bridge kernel del container, per simulare scenari WAN degradati realistici.

**Pattern di implementazione:**

```python
# FastAPI endpoint
@router.post("/simulation/{sim_id}/fault/inject")
async def inject_fault(sim_id: str, fault: FaultRequest):
    link = await get_link(fault.link_id)
    # Shutdown interface on GNS3 node
    await gns3_client.set_link_suspended(link.gns3_link_id, True)
    # Publish event
    await redis.publish(f"sim:{sim_id}:events", FaultEvent(
        type="LINK_DOWN",
        link_id=fault.link_id,
        timestamp=datetime.utcnow().isoformat()
    ).json())
    return {"status": "fault_injected"}
```

---

## 8. Rischi e Mitigazioni

| Rischio | Probabilità | Impatto | Mitigazione |
|---------|-------------|---------|-------------|
| Dipendenza da GNS3 (API instabile) | Media | Alto | Adapter pattern: `SimulationEngineInterface` astratto; implementazioni GNS3 e mock intercambiabili |
| Performance canvas con >100 nodi | Media | Medio | React Flow virtualizzazione; fallback WebGL con Pixi.js oltre soglia |
| Licenze immagini router (Cisco IOS) | Alta | Alto | MVP con FRRouting (open source) + Cisco su licenza utente; documentare chiaramente |
| Latenza avvio VM QEMU | Alta | Medio | Pre-warming pool di VM per template comuni; Docker-first per MVP |
| Complessità auto-IP con overlap | Bassa | Alto | Unit test coverage 100% su subnetting engine; validazione server-side pre-simulazione |

---

*Documento generato da: NetSim-Flow Planning Session — v0.1-DRAFT*
*Next Review: Sprint 1 Kickoff*
