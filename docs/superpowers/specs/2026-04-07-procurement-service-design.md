# Procurement Service — Design Specification

**Date:** 2026-04-07  
**Status:** Draft — awaiting user approval  
**Scope:** Full-featured procurement management service for industrial electronics manufacturing

---

## 1. Overview

A self-hosted web application for managing the full procurement lifecycle: component catalog, supplier database, RFQ distribution, proposal collection, and comparison. Designed for solo use initially, with multi-user support (small team of managers) from the start.

**Core value:** Automate the tedious parts (supplier discovery, component normalization, email parsing, price scraping) while keeping humans in control of decisions (category confirmation, supplier selection, strategy choice).

---

## 2. Architecture

### Approach: Modular Monolith with Async AI Worker

A single codebase with clear module boundaries. Heavy AI operations run in a background worker queue, keeping the web interface fast and non-blocking.

### Stack

| Layer | Technology |
|---|---|
| Backend API | Python / FastAPI + SQLAlchemy |
| Database | PostgreSQL |
| Frontend | Next.js (React + TypeScript) |
| Task Queue | Redis + ARQ |
| AI / LLM | OpenRouter (via OpenAI-compatible SDK) |
| Web Search | Tavily (`AsyncTavilyClient`) |
| Email Outbound | SMTP |
| Email Inbound | IMAP polling + AI parsing |
| Deployment | Docker Compose (self-hosted VPS) |

### Docker Compose Services

- `app` — FastAPI backend
- `web` — Next.js frontend
- `worker` — ARQ task worker (AI jobs)
- `postgres` — PostgreSQL
- `redis` — Redis (queue + cache)

### OpenRouter Integration

Uses standard OpenAI Python SDK with custom `base_url`:

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)
```

No additional dependencies. Model selection is runtime-configurable.

---

## 3. Data Model

### Category (hierarchical)

```
Category
  id, name, description
  parent_id → Category (nullable, self-referencing)
```

Arbitrary depth tree. Lots are formed at the **leaf node** level. Analytics aggregate up the tree.

### Component Catalog

```
Component
  id, name_internal, name_normalized, description
  search_queries[]        -- AI-generated search strings for supplier discovery
  category_id → Category  -- assigned at leaf level
  enrichment_status       -- pending | in_review | enriched
  created_at
```

### Products / BOM

```
Product
  id, name, description

ProductComponent
  product_id → Product
  component_id → Component
  quantity, unit
```

### Suppliers

```
Supplier
  id, name
  type                    -- company | marketplace
  email, website, phone, notes
  created_at

SupplierCategory
  supplier_id → Supplier
  category_id → Category  -- can be at any level of the tree
```

Two supplier types with different interaction mechanics:
- **company** — email RFQ flow
- **marketplace** — automated price scraping (async job)

### Procurement Session

```
ProcurementSession
  id, name, status        -- draft | active | comparing | closed
  created_by, created_at

SessionComponent
  session_id → ProcurementSession
  component_id → Component
  quantity

Lot
  id, session_id → ProcurementSession
  category_id → Category  -- leaf node
  status                  -- pending | sent | receiving | ready

RFQ
  id, lot_id → Lot
  supplier_id → Supplier
  status                  -- pending | sent | responded | expired
  sent_at, response_token (UUID), expires_at

Proposal                            -- header: one per RFQ response
  id, rfq_id → RFQ
  payment_terms                     -- free text: "100% prepayment", "net 30", etc.
  notes
  source                            -- email_reply | web_form | marketplace_scrape
  received_at

ProposalLine                        -- one row per component within the lot
  id, proposal_id → Proposal
  component_id → Component
  price_per_unit, currency
  delivery_days
  min_quantity
  available                         -- bool: supplier can supply this item
```

`ProposalLine` enables Strategy 2 (line-item award): the system compares per-component prices across all proposals in the lot to find the cheapest supplier for each line.

### Purchase History

```
PurchaseRecord
  id
  session_id → ProcurementSession
  supplier_id → Supplier
  component_id → Component
  quantity, price_per_unit, currency
  delivered_at, notes
```

Records the actual purchase outcome. Drives analytics and supplier-component relationship history.

### Background Jobs

```
Job
  id, type, status        -- pending | running | done | failed
  payload (JSON), result (JSON)
  created_at, completed_at, error
```

---

## 4. Key Flows

### Flow 1: Component Enrichment

1. User imports CSV or adds components manually (`name_internal`)
2. Async job (OpenRouter): normalize name, generate `search_queries[]`, suggest `category_id`
3. User sees review screen — list of components with suggested categories; can approve all or correct individually
4. Status → `enriched`, component is ready for sessions

### Flow 2: Supplier Discovery

**Active channel (agent):**
1. User specifies category or component
2. Async job: Tavily searches web for suppliers in that category
3. OpenRouter extracts structured data: name, website, email, phone, categories covered
4. User reviews candidate list → approves → added to database

**Passive channel (inbound):**
1. Public supplier registration form (shareable link)
2. Supplier fills in their details and covered categories
3. User receives notification → reviews → approves

### Flow 3: Procurement Session

1. **Create session** — select Product (BOM) or arbitrary component list with quantities
2. **Coverage check** — system checks supplier count per leaf category in the session. If any category has fewer than the configured minimum (default: 3, adjustable per category) → warning with option to launch discovery agent
3. **Form lots** — components grouped by leaf category automatically; user confirms
4. **Assign suppliers** — per lot, system suggests suppliers from database matching the lot's category; user selects recipients
5. **Send RFQ** — one action:
   - *company* suppliers: email sent via SMTP with unique response link (token-based)
   - *marketplace* suppliers: async scraping job launched
6. **Collect proposals** — suppliers submit via form link, or reply by email (AI parses → structured Proposal); marketplaces populate automatically
7. **Strategy selection** — after proposals collected, system computes:
   - *Strategy 2*: line-item award (best price per component, multiple suppliers)
   - *Strategy 3*: primary supplier + gap fill (one main + cheapest for missing items)
   - Shows total cost, number of suppliers, number of deliveries for each strategy
8. **Award** — user selects strategy and confirms winners per lot
9. **Record outcome** — creates `PurchaseRecord` entries for history

---

## 5. AI Tasks (Async Worker)

| Task | Input | Output | Tools |
|---|---|---|---|
| Component normalization | `name_internal` | `name_normalized`, `search_queries[]`, `category_id` suggestion | OpenRouter |
| Supplier discovery | category + search queries | Candidate supplier list | Tavily + OpenRouter |
| Email reply parsing | Raw email text | Structured `Proposal` fields | OpenRouter |
| Marketplace price scraping | Component list + marketplace URL | `Proposal` entries per component | Tavily extract + OpenRouter |

All tasks are idempotent and retryable. Status tracked in `Job` table.

---

## 6. Analytics

### Supplier Coverage Dashboard

- Per category (with drill-down into subcategories): count of active suppliers, historical supplier count trend
- Traffic-light indicator: red < 2, yellow 2–3, green ≥ 4 suppliers
- Per component: list of suppliers who have supplied it historically (from `PurchaseRecord`)

### Procurement History

- Cost trends per category over time
- Price variance per component across suppliers and sessions
- Supplier performance: response rate, coverage of requested items

### Session-level

- Coverage completeness at session start (% of components with ≥ threshold suppliers)
- Strategy comparison: cost delta between Strategy 2 and 3

---

## 7. Error Handling

| Scenario | Handling |
|---|---|
| Supplier no response after N days | Auto-reminder email or manual nudge from UI |
| AI cannot parse email reply | Marked `requires_manual_review`, user notified |
| Response link expired | User can extend or resend |
| Marketplace blocked scraping | Job fails gracefully, status shown, manual fallback suggested |
| Component not found on marketplace | Marked `not_found` for that line item, rest of lot unaffected |
| Component not enriched at session creation | Warning + blocked from RFQ until enriched |
| Supplier missing email | Warning at RFQ formation step |
| Tavily found supplier with no contact info | Saved as `incomplete` card, prompts manual completion |

---

## 8. Testing

**Unit tests** — business logic: lot formation from BOM, strategy 2/3 cost calculation, coverage check, AI response parsing.

**Integration tests** — API endpoints with test database: full session lifecycle from creation to award.

**AI component tests** — run with fixed mocks (no real OpenRouter/Tavily calls in CI). Test prompt outputs, structured extraction, error handling.

**Manual E2E** — key user journeys on staging before each deploy.

---

## 9. Development Sequence

Recommended build order (each phase is independently deployable):

### Phase 1 — Foundation
- Docker Compose setup (all services)
- Database schema + migrations (Alembic)
- FastAPI project structure + auth (JWT, single user)
- Category tree CRUD (hierarchical, arbitrary depth)
- Component catalog CRUD + CSV import
- Basic Next.js shell with auth

### Phase 2 — Component Enrichment
- ARQ worker setup + Job tracking
- OpenRouter integration (normalization task)
- Component enrichment flow + review UI

### Phase 3 — Supplier Management
- Supplier CRUD (company + marketplace types)
- Supplier-category association UI
- Coverage dashboard (basic)

### Phase 4 — Supplier Discovery Agent
- Tavily integration
- Supplier discovery async job
- Candidate review UI
- Public supplier registration form

### Phase 5 — Procurement Session & RFQ
- Session creation (BOM selection + coverage check)
- Lot formation (auto-group by leaf category)
- RFQ creation + supplier assignment
- SMTP email sending with response tokens
- Public response form (token-based)

### Phase 6 — Proposal Collection & Parsing
- IMAP polling + AI email parsing job
- Marketplace scraping job
- Proposal ingestion from all sources

### Phase 7 — Comparison & Award
- Lot comparison table (line-item level)
- Strategy 2 and 3 calculation + UI
- Award confirmation + PurchaseRecord creation

### Phase 8 — Analytics
- Coverage dashboard with category drill-down
- Procurement history views
- Price trend charts

### Phase 9 — Multi-user
- User management (roles: admin, manager)
- Per-user assignments and notifications

---

## 10. Out of Scope (v1)

- ERP integration (manual CSV import only)
- Contract management
- Delivery tracking
- Supplier ratings / historical reliability scoring
- Mobile app
- Multi-tenancy (SaaS)
