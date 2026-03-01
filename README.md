# People Help

An AI-powered **Employee Experience platform** — one interface where employees ask HR questions, open support cases, and kick off workflows like onboarding. Built to demonstrate agentic AI, RAG, and workflow orchestration for People Technology.

**Stack:** FastAPI · Supabase (Postgres + pgvector) · OpenAI · LangChain · Tailwind CSS · Chart.js

## What it does

| Feature | Description |
|---------|-------------|
| **People Concierge** | AI agent (LangChain, 15 tools) that takes actions — looks up employees, starts onboarding, creates cases, checks requisitions, ranks candidates. Multi-turn chat with conversation memory and human-in-the-loop confirmation. Duplicate onboarding detection warns before creating redundant runs. |
| **Knowledge Base** | RAG pipeline over 7 HR policy docs (PTO, expenses, onboarding, hiring, interviews, compensation, performance). Embeddings via `text-embedding-3-small`, vector search via pgvector, cited answers with feedback. Suggested question chips for discoverability. |
| **Case Management** | Employees describe an issue → agent creates a support case with subject/description. Cases tracked with open/resolved status. Case IDs in chat auto-link to the Workflows page. |
| **Onboarding Workflows** | Offer accepted → onboarding checklist + approval pipeline created. Interactive checkboxes with progress tracking. New-hire name displayed in runs table and detail page. |
| **Approval Workflows** | Multi-step approvals with role-based routing (manager → HR → IT). Approve/reject via UI or chat agent. Reject with notes. Role-scoped view messaging. |
| **Candidate Intelligence** | AI-powered candidate-to-requisition matching. Embedding similarity scores rank candidates, LLM analyzes strengths/gaps/recommendation. Hiring manager dashboard with visual match bars and deep-dive analysis. |
| **Mock Integrations** | Mock Workday (employee lookup, org chart) and Greenhouse (requisitions, candidates with enriched profiles). Webhook receiver logs events. Admin integration health dashboard shows connector status and API reference. |
| **Analytics Dashboard** | 5 metric cards (KB Questions, Events, Cases Open, Cases Total, Onboarding Runs) + 3 Chart.js doughnut charts (Feedback Sentiment, Case Status, Onboarding Status). |
| **Event Log** | System audit trail — every workflow, case, and approval action creates a traceable event with typed payloads. |
| **Seed System** | One-command `npm run seed` resets all tables and populates with realistic demo data: 7 KB docs, 8 cases, 5 onboarding runs at different stages, approval pipelines, events, and feedback. |

## Architecture

```
Browser → FastAPI → LangChain Agent → Tools (15)
                                        ├── search_knowledge (RAG)
                                        ├── create_case / check_case_status / list_open_cases
                                        ├── start_onboarding / check_workflow_status
                                        ├── list_pending_approvals / approve_step / reject_step
                                        ├── lookup_employee / get_org_chart (Mock Workday)
                                        ├── list_open_reqs / get_req_detail (Mock Greenhouse)
                                        └── match_candidates / analyze_candidate (AI Matching)
                  → Supabase (Postgres + pgvector)
                  → OpenAI API (embeddings + chat + candidate analysis)
                  → Webhook receiver (/integrations/webhooks/{source})
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full design document with data model, agent design, and production roadmap.

**Key design decisions:**
- Async throughout — `AsyncOpenAI` singleton, `async def` endpoints
- Agent with human-in-the-loop — confirms before creating cases or starting workflows
- Duplicate detection — warns if active onboarding run already exists for a name
- Conversation memory — persisted in Supabase, loaded per session
- Interactive UI — Tailwind CSS, Chart.js, PATCH API for checklist toggling
- Candidate Intelligence — embedding similarity scoring + LLM-as-judge for hiring decisions
- Comprehensive seed data — one command resets and populates all demo data
- Production-hardened — API key auth, per-IP rate limiting, Pydantic validation, structured logging, 84 tests

**Future improvements:**
- Migrate from LangChain `AgentExecutor` to **LangGraph** for production-grade state management, human-in-the-loop approvals, and parallel tool execution
- Streaming responses for the People Concierge (SSE)
- Real Workday / Greenhouse API connectors (replace mocks)

## Pages

| Route | Page |
|-------|------|
| `/people-help` | People Concierge — AI agent (main entry point) |
| `/knowledge` | Knowledge Base search with RAG + citations + suggested questions |
| `/workflows` | Cases + Onboarding runs (with new-hire names) + simulate button |
| `/workflows/run/{id}` | Workflow detail with checklist + approval pipeline |
| `/workflows/approvals` | Pending approvals dashboard (role-scoped) |
| `/integrations` | Admin integration health dashboard + API reference |
| `/integrations/hiring` | Hiring Intelligence dashboard (candidate matching) |
| `/events` | System audit trail |
| `/analytics` | Dashboard with 5 metrics + 3 charts |
| `/health` | Health check (JSON) |
| `/docs` | Auto-generated OpenAPI docs |

## Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Supabase** — Create a project at [supabase.com](https://supabase.com), then run `db/schema.sql` in the SQL Editor. This creates all 13 tables including conversations, approvals, connectors, and pgvector extensions.

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

5. **Seed demo data** (requires server to be running)
   ```bash
   npm run seed
   ```
   This cleans all tables and populates:
   - 7 HR policy docs in the knowledge base (with embeddings)
   - 3 workflow definitions (onboarding, PTO, expense reimbursement)
   - 4 connectors (Workday, Greenhouse, Slack, Okta)
   - 8 support cases (5 open, 3 resolved)
   - 5 onboarding runs at different stages with approval pipelines
   - 20+ system events
   - 10 KB question/feedback entries (for analytics charts)

## Tests

```bash
npm test
```

84 tests across 6 test files covering API endpoints, integrations, RAG chunking, Pydantic models, middleware (auth + rate limiting), and candidate intelligence.

## Deploy on Render

1. New Web Service → connect this repo
2. Build: `pip install -r requirements.txt`
3. Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Set env vars: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `OPENAI_API_KEY`
5. Seed: run `python db/seed.py` after deploy (server must be running)

`render.yaml` is included for one-click deploys.

## Project structure

```
├── main.py                  # FastAPI app + middleware + router registration
├── config.py                # Env var loading (Supabase, OpenAI, auth, rate limit)
├── models.py                # Pydantic request/response models
├── templates_ctx.py         # Jinja2 template setup
├── package.json             # npm scripts (start, test, seed)
├── middleware/
│   ├── auth.py              # API key authentication
│   ├── rate_limit.py        # Per-IP rate limiting on LLM endpoints
│   └── request_logging.py   # Structured request logging with request IDs
├── routers/
│   ├── people_help.py       # People Concierge chat API
│   ├── knowledge.py         # RAG search + seed (7 HR docs) + feedback
│   ├── workflows.py         # Workflow runs + checklist + approvals
│   ├── integrations.py      # Mock Workday/Greenhouse + hiring dashboard + webhooks
│   ├── analytics.py         # Dashboard with counts + onboarding metrics
│   ├── events.py            # Event log
│   └── seed.py              # Demo data seed endpoints (reset, connectors, demo-data)
├── services/
│   ├── agent.py             # LangChain agent + 15 tools + duplicate detection
│   ├── candidate_intelligence.py  # AI candidate matching + analysis
│   ├── rag.py               # Embeddings, vector search, RAG
│   ├── approvals.py         # Approval engine + definitions
│   ├── integrations.py      # Mock Workday/Greenhouse data + webhooks
│   ├── workflows.py         # Onboarding logic + duplicate detection
│   └── supabase_client.py   # Supabase singleton
├── tests/                   # Pytest test suite (84 tests)
├── templates/               # Jinja2 + Tailwind CSS (10 templates)
├── db/
│   ├── schema.sql           # Full database schema (13 tables)
│   └── seed.py              # Seed script (clean + populate demo data)
└── docs/
    ├── ARCHITECTURE.md       # Design document
    └── PEOPLE_HELP_ENHANCEMENT_PLAN.md  # Build phases (all complete)
```
