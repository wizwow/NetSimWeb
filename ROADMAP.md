# Octet — Product Roadmap
**Last updated:** 2026-06-05 | **Status:** active

---

## Product Vision

Octet is a professional web platform for IP network design, simulation, and
documentation. A network engineer opens Octet, builds a topology with real IPs
and routing protocols, validates it against a live GNS3 simulation, and exports
an implementation guide for himself or a technician. The primary workflow is
**design first, simulate to validate, document to ship**.

**Deployment model:** SaaS — Octet-managed GNS3 servers, users bring nothing.
On-premise — customer provides and connects their own GNS3 server.

**Primary tier:** Professional (network engineers, sysadmins).
Secondary: Education (browser-only mock, no GNS3 required). Enterprise (on-premise, vendor configs) is long-roadmap.

---

## Current State — green-v0 (tagged on `main`, 2026-06-05)

| Area | Status | Notes |
|------|--------|-------|
| Topology canvas | ✅ Working | Reliable linking, interface-aware ports, save/reload |
| Node types | ✅ Working | Router (4 ports), Switch (8), Host (1), Cloud (1) |
| Interface model | ✅ Working | IP + mask per interface, persists on save/reload |
| Inspector | ✅ Working | Editable IP, mask dropdown, connected-peer display |
| Templates | ✅ Working | Blank, Hub-Spoke, OSPF 3 Sites (IPs baked in) |
| Save / Load | ✅ Working | PostgreSQL, JWT-scoped, owner isolation |
| Mock simulation | ✅ Working | Start/stop lifecycle, node status events via WebSocket |
| Fault injection | ✅ Working | Link-down fault, visual feedback |
| Ping (mock) | ⚠️ Partial | Wired but needs source/target rework after Auto-IP removal |
| Export JSON | ✅ Working | Full round-trip, includes interface IPs |
| Export MD/PDF/DOC | ✅ Working | Report generation; IP table needs verification |
| Auth | ✅ Working | JWT register/login, owner-scoped topologies |
| Delete nodes/links | ✅ Working | Via inspector button and keyboard Delete/Backspace |
| GNS3 integration | ❌ Not done | Adapter skeleton exists; no live provisioning yet |
| CLI terminal | ❌ Not done | Not started |
| Config generation | ❌ Not done | Not started |

---

## Roadmap

### Phase 1 — Mock Polish *(current)*

**Goal:** The mock simulation is complete, reliable, and genuinely useful as a
design-validation tool before GNS3 is connected.

**Done when:** Every step in `MANUAL_TESTING.md` passes green on the first try
with zero workarounds.

| Task | Priority | Notes |
|------|----------|-------|
| Fix ping | P0 | Source = selected interface IP; target = typed or peer IP. One small slice. |
| Verify report IPs | P0 | Check MD/PDF/DOC report includes interface IPs from inspector. Fix if missing. |
| "No free interfaces" toast | P1 | Silently blocked connection needs a visible message |
| Delete nodes/links (spec done) | P1 | In `specs/SPEC-minor-ux-improvements.md` |
| UX improvements (spec done) | P1 | Launch script, mask dropdown, smoothstep edges |

---

### Phase 2 — GNS3 Foundation

**Goal:** A topology built in Octet can be provisioned in GNS3 and basic
connectivity verified. No config generation yet — just topology existence and
ping.

**Done when:** Build a 3-router topology → Start → nodes appear in GNS3 with
links → ping between directly connected interfaces succeeds.

| Task | Notes |
|------|-------|
| GNS3 template ID mapping | Map Octet `baseType` (router/switch/host/cloud) to configured GNS3 template IDs via env/config |
| Node provisioning | Create GNS3 nodes from the engine-neutral deployment plan |
| Link provisioning | Create GNS3 links after node IDs are returned |
| Start/stop with real nodes | Extend current lifecycle to use real GNS3 project |
| IP address push | Assign interface IPs from `logicalConfig.interfaces` to nodes at start time |
| Basic ping validation | Run a ping between two directly connected nodes, surface result in the log console |
| GNS3 readiness check | Surface clear error if GNS3 server is unreachable or template IDs are not configured |

**Reference:** `apps/api/app/engines/gns3.py` already has an adapter skeleton and
HTTP boundary tests. `feature/gns3` branch has additional WIP to review as a
parts bin — do not merge wholesale, cherry-pick deliberately.

---

### Phase 3 — Routing Config Generation & Push

**Goal:** Nodes start with real routing configs. A sysadmin can verify OSPF
adjacencies and routing tables without manually configuring each device.

**Done when:** Load an OSPF 3-Sites topology → Start → OSPF adjacencies form
automatically → `show ip route` on any router shows expected prefixes.

**Protocol priority order (implement in this sequence):**

| # | Protocol | Notes |
|---|----------|-------|
| 1 | Static routing | Simplest; needed for host default gateways and P2P links |
| 2 | OSPF | Core professional protocol; already in templates |
| 3 | BGP | Inter-AS; required for most real enterprise/SP designs |
| 4 | OSPFv3 | IPv6 variant; low incremental effort after OSPF |
| 5 | EIGRP | Cisco-heavy environments |
| 6 | IS-IS | SP and large enterprise; often paired with SR |
| 7 | RIP | Legacy; low priority |
| 8 | BGP EVPN-VXLAN | Data centre fabric; high complexity, high value |
| 9 | Segment Routing (SR/SRv6) | Advanced; requires SR capability in GNS3 images |

**Config model:** config generation is **logical/generic** — Octet generates
abstract configs (e.g. `router ospf 1 / network ... area 0`) that work on any
standards-compliant image. Vendor-specific config generation (IOS-XE syntax,
Junos) is a future tier feature.

---

### Phase 4 — CLI Terminal

**Goal:** Click any running node → browser opens an in-app terminal connected
to that node's GNS3 console. Type commands, see output. The design loop becomes:
design → start → open terminal → verify → adjust → export.

**Done when:** Open a terminal to any running router → type `show ip ospf neighbor`
→ see real output.

| Task | Notes |
|------|-------|
| xterm.js integration | Embed terminal emulator in the inspector or a drawer panel |
| WebSocket tunnel | Proxy GNS3 console WebSocket through the Octet backend |
| Console endpoint per node | Map Octet node ID → GNS3 node ID → console port |
| Multi-terminal support | Open terminals to multiple nodes simultaneously |

---

### Phase 5 — Professional Polish

**Goal:** The tool is something a professional would pay for and recommend to a
colleague.

| Task | Notes |
|------|-------|
| Report quality | Implementation guide format: per-device config section, addressing table, routing summary |
| Native DOCX export | Real Word document, not HTML-as-doc |
| Topology validation | Flag IP conflicts, missing gateway, disconnected segments before start |
| Project management | List / search saved topologies, rename, duplicate, archive |
| Vendor-specific configs (scoping) | Decide: Pro tier or Enterprise only. Design the config template system. |

---

### Phase 6 — Vendor-Specific Configs *(long roadmap, tier TBD)*

**Goal:** For a Cisco IOS-XE router, Octet generates actual IOS syntax. The
technician copy-pastes it or Octet pushes it directly.

This phase is intentionally unscoped. It requires:
- Vendor image availability in GNS3
- Per-vendor config template system
- Tier decision (Pro vs Enterprise)
- A dedicated scoping spec before any implementation

---

## Explicit Out of Scope

These will not be built without a dedicated spec and explicit approval:

| Item | Reason |
|------|--------|
| Auto-IP | Removed. May return as optional convenience, not a core feature. |
| 60-second to working topology | Incompatible with professional/deliberate design workflow |
| Education fast-path UX | Secondary tier; not blocking Professional progress |
| Real-time collaboration (multi-cursor) | Significant architecture change; not in demand yet |
| Billing / payment integration | Infrastructure concern; out of scope for product roadmap |
| Keycloak / external SSO | Current JWT is sufficient; OAuth is next auth hardening slice |
| Mobile / tablet UI | Desktop-first tool |
| WebRTC / video | N/A |

---

## Protocol Capability Matrix *(target state)*

| Protocol | Canvas config | Config gen | GNS3 validation | Phase |
|----------|--------------|------------|-----------------|-------|
| Static routing | ✅ | Phase 3 | Phase 3 | 3 |
| OSPF | ✅ (templates) | Phase 3 | Phase 3 | 3 |
| BGP | Phase 2 canvas | Phase 3 | Phase 3 | 3 |
| OSPFv3 | Phase 3 | Phase 3 | Phase 3 | 3 |
| EIGRP | Phase 3 | Phase 3 | Phase 3 | 3 |
| IS-IS | Phase 3 | Phase 3 | Phase 3 | 3 |
| RIP | Phase 3 | Phase 3 | Phase 3 | 3 |
| BGP EVPN-VXLAN | Phase 5 | Phase 5 | Phase 5 | 5 |
| SR / SRv6 | Phase 5 | Phase 5 | Phase 5 | 5 |

---

## Architecture Constraints That Drive the Roadmap

1. **GNS3 is the only simulation engine for production.** The mock engine is a
   development convenience and Education fallback — never a substitute for
   real routing validation.

2. **Config generation is protocol-aware, not vendor-aware (for now).** We generate
   standard configs that work on any RFC-compliant image. Vendor syntax is a
   future layer on top.

3. **One GNS3 project per topology.** Multi-tenancy is enforced at the Octet
   service layer (owner-scoped topologies). GNS3 project IDs are stored in
   `Topology.engine_topo_id`.

4. **The interface model is the source of truth.** IPs live on
   `NetworkNode.logicalConfig.interfaces`, not on links. Config generation reads
   from interfaces. GNS3 provisioning reads from interfaces. Reports read from
   interfaces.

5. **Feature/gns3 branch is a parts bin, not a merge candidate.** Review it
   deliberately, take what works, discard what doesn't.
