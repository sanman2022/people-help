# People Help

**A working prototype of an AI-powered internal operating system for Employee Experience — where one conversational agent stitches together HR tools, knowledge, and workflows into a seamless interface for employees and managers.**

People Help demonstrates how agentic AI can transform the way organizations deliver HR services. Instead of navigating Workday for employee data, Greenhouse for hiring, a wiki for policy answers, and a ticketing system for support — employees get one intelligent front door that understands context, takes action, and learns.

> **Stack:** FastAPI · Supabase (Postgres + pgvector) · OpenAI · LangChain · Tailwind CSS · Chart.js

---

## Why This Exists

HR technology at scale is fragmented. Employee data lives in Workday, candidates in Greenhouse, policies in Confluence, support cases in ServiceNow, approvals in email. Employees context-switch across 4–5 systems to do basic things — and every system has its own login, its own UX, and its own gaps.

The cost:
- **Case deflection stays low** — employees file tickets for questions that policy docs already answer
- **Onboarding is manual** — checklists and approvals span tools with no orchestration layer
- **Hiring decisions lack data** — managers evaluate candidates on intuition, not structured scoring
- **No single pane of glass** — HR operations are invisible until something breaks

**People Help is a prototype that validates a different model**: a single AI agent that connects to your HRIS, ATS, and knowledge base — answers questions grounded in real policy, kicks off workflows, and provides decision support. Built as a rapid prototype to show how this works end-to-end, not just in slides.

---

## What It Does

### One Agent, Many Systems

The **People Concierge** is a multi-turn AI agent backed by 15 tools. It doesn't just answer questions — it takes actions across connected systems:

- *"Start onboarding for Jamie Lee"* → checks for duplicate runs, creates a 4-step checklist, triggers a 3-stage approval pipeline (manager → HR → IT), logs an audit event
- *"Look up Alice Chen in Workday"* → queries the HRIS, returns employee profile and org chart
- *"Rank candidates for the Senior Backend Engineer role"* → embeds the JD and candidate profiles, computes similarity scores, returns a ranked list with AI-generated analysis
- *"What's the PTO policy?"* → searches 7 HR policy documents via RAG, returns a cited answer grounded in actual policy text
- *"Create a case: employee can't update direct deposit"* → creates a structured support ticket with status tracking

The agent maintains conversation memory across turns and asks for human confirmation before taking destructive actions (creating cases, starting workflows, processing approvals). Duplicate detection warns before creating redundant onboarding runs.

### Knowledge Management (RAG)

A retrieval-augmented generation pipeline over HR policy documents — PTO, expenses, onboarding, hiring, interviews, compensation, performance reviews. Employees ask questions in natural language and get answers with source citations, not hallucinated summaries. Includes a feedback mechanism (helpful / not helpful) to create a product feedback loop.

### Workflow Orchestration

**Onboarding**: Offer accepted → checklist created → approval pipeline triggered → progress tracked. Interactive checkboxes, new-hire names that flow from trigger through dashboard to detail page, and duplicate detection before creating redundant runs.

**Approvals**: Configurable multi-step workflows with role-based routing. Manager approves step 1, HR approves step 2, IT provisions step 3 — enforced in order. Approve or reject through the dashboard or by talking to the agent. Rejection captures notes for the audit trail.

**Cases**: Natural-language issue descriptions become structured support tickets with subject, description, and status tracking. Case IDs auto-link in the chat interface.

### Decision Support — Candidate Intelligence

AI-powered candidate-to-requisition matching for hiring managers. The system embeds job descriptions and candidate profiles, computes similarity scores to rank the talent pool, then runs an LLM analysis on each candidate's strengths, gaps, and overall fit. The goal: give hiring managers a data-driven starting point, not a replacement for judgment.

### Systems Integration Pattern

Mock Workday and Greenhouse connectors demonstrate how the agent stitches together HRIS and ATS data flows — employee lookup, org chart traversal, requisition pipelines, candidate profiles. A webhook receiver logs inbound events. An admin dashboard shows connector health and API status. The architecture is designed so mocks can be swapped for OAuth-based production connectors without changing the agent layer.

### Metrics & Feedback Loops

An analytics dashboard tracks KB engagement, case volume, feedback sentiment, and onboarding progress — 5 live metrics and 3 charts. Every action in the system (workflow created, case opened, approval decided, webhook received) is logged as a typed event with a JSON payload, creating a full audit trail for measuring impact and debugging issues.

---

## Architecture

```
Employee → People Concierge (AI Agent) → 15 Tools
                                           ├── Knowledge (RAG over HR policies)
                                           ├── Cases (create, track, resolve)
                                           ├── Workflows (onboarding checklists)
                                           ├── Approvals (multi-step, role-based)
                                           ├── Workday (employee lookup, org chart)
                                           ├── Greenhouse (requisitions, candidates)
                                           └── Intelligence (AI candidate matching)
                                         → Supabase (13 tables + pgvector)
                                         → OpenAI (embeddings + reasoning)
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full design document — data model, agent design, interactive Mermaid diagrams, and production roadmap.

### Design Philosophy

- **Agentic, not scripted** — The LLM decides which tools to call based on intent, not a hardcoded decision tree. This is how real EX platforms need to work — employee queries are unpredictable.
- **Human-in-the-loop** — AI proposes, humans approve. The agent asks for confirmation before creating cases, starting workflows, or processing approvals. Trust is built incrementally.
- **RAG with citations** — Policy answers are grounded in source documents with numbered citations. Employees can verify. No black-box hallucinations.
- **Integration-first** — The agent layer is decoupled from data sources. Swap mock Workday for real Workday; the conversational experience doesn't change.
- **Feedback loops built in** — KB feedback, event logging, and analytics are first-class features, not afterthoughts. You can't improve what you don't measure.

### Production Roadmap

If evolving People Help from prototype to production:

| Priority | Initiative | Why |
|----------|-----------|-----|
| **P0** | **LangGraph migration** | Replace LangChain AgentExecutor with explicit state machines — human-in-the-loop as graph nodes, parallel tool execution, better error recovery |
| **P0** | **SSO + RBAC** | Okta/Azure AD integration, role-gated views (employee vs. manager vs. HR admin vs. IT) |
| **P1** | **Real connectors** | OAuth-based Workday, Greenhouse, Slack, Okta — replace mocks with production APIs |
| **P1** | **Streaming** | SSE for instant first-token in the Concierge — perceived latency from 3s to instant |
| **P2** | **Observability** | LangSmith/LangFuse for agent tracing, tool-level latency metrics, error budgets |
| **P2** | **Knowledge management** | Admin UI for uploading/versioning policy docs with content approval workflows |

---

## Demo

### Pages

| Route | What you'll see |
|-------|-----------------|
| `/people-help` | AI agent chat — the main entry point |
| `/knowledge` | Search HR policies with cited answers + suggested questions |
| `/workflows` | Support cases + onboarding runs with new-hire names |
| `/workflows/run/{id}` | Checklist progress + approval pipeline status |
| `/workflows/approvals` | Pending approvals dashboard (role-scoped) |
| `/integrations` | Connector health + API reference |
| `/integrations/hiring` | Candidate matching with AI similarity scores |
| `/analytics` | Live metrics + charts |
| `/events` | System audit trail |

### Try These in the Concierge

> *"Start onboarding for Jamie Lee, starting March 15"*
> *"Look up Alice Chen in Workday"*
> *"Show open requisitions I'm the hiring manager for"*
> *"Create a case: employee needs help updating their direct deposit info"*
> *"What's the PTO policy?"*
> *"Rank candidates for the Senior Backend Engineer role"*

---

## Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Supabase** — Create a project at [supabase.com](https://supabase.com), then run `db/schema.sql` in the SQL Editor (creates all 13 tables + pgvector).

3. **Environment variables**
   ```bash
   cp .env.example .env
   ```
   Set `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and `OPENAI_API_KEY`.

4. **Run**
   ```bash
   npm start
   ```
   Open http://127.0.0.1:8000/people-help

5. **Seed demo data** (server must be running)
   ```bash
   npm run seed
   ```
   Populates 7 KB docs, 8 cases, 5 onboarding runs at different stages, approval pipelines, 20+ events, and analytics data.

### Tests

```bash
npm test
```

84 tests across 6 files — API endpoints, integrations, RAG chunking, Pydantic models, middleware, and candidate intelligence.

### Deploy

`render.yaml` is included for one-click Render deploys. Set `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `OPENAI_API_KEY` as env vars.

---

## Project Structure

```
├── main.py                  # FastAPI app + middleware stack
├── config.py                # Environment configuration
├── models.py                # Pydantic request/response models
├── middleware/               # Auth, rate limiting, request logging
├── routers/                  # API endpoints (7 routers)
├── services/
│   ├── agent.py             # LangChain agent (15 tools)
│   ├── candidate_intelligence.py
│   ├── rag.py               # Embedding + vector search
│   ├── approvals.py         # Multi-step approval engine
│   ├── integrations.py      # Mock Workday/Greenhouse
│   └── workflows.py         # Onboarding orchestration
├── templates/                # Jinja2 + Tailwind CSS (10 pages)
├── tests/                    # 84 tests
├── db/
│   ├── schema.sql           # Full schema (13 tables)
│   └── seed.py              # Demo data seeder
└── docs/
    └── ARCHITECTURE.md       # Full design document
```
