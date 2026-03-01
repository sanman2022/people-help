# People Help

An AI-powered **Employee Experience platform** — one interface where employees ask HR questions, open support cases, and kick off workflows like onboarding. Built to demonstrate agentic AI, RAG, and workflow orchestration for People Technology.

**Stack:** FastAPI · Supabase (Postgres + pgvector) · OpenAI · LangChain · Tailwind CSS · Chart.js · Render

## What it does

| Feature | Description |
|---------|-------------|
| **People Concierge** | AI agent (LangChain, 15 tools) that takes actions — looks up employees, starts onboarding, creates cases, checks requisitions, ranks candidates. Multi-turn chat with conversation memory and human-in-the-loop confirmation. |
| **Knowledge Base** | RAG pipeline over 7 HR policy docs (PTO, expenses, onboarding, hiring, interviews, compensation, performance). Embeddings via `text-embedding-3-small`, vector search via pgvector, cited answers with feedback. |
| **Case Management** | Employees describe an issue → agent creates a support case with subject/description. Cases are tracked with open/closed status. |
| **Onboarding Workflows** | Offer accepted → onboarding checklist + approval pipeline created. Interactive checkboxes with progress tracking. |
| **Approval Workflows** | Multi-step approvals with role-based routing (manager → HR → IT). Approve/reject via UI or chat agent. Reject with notes. |
| **Candidate Intelligence** | AI-powered candidate-to-requisition matching. Embedding similarity scores rank candidates, LLM analyzes strengths/gaps/recommendation. Hiring manager dashboard with visual match bars and deep-dive analysis. |
| **Mock Integrations** | Mock Workday (employee lookup, org chart) and Greenhouse (requisitions, candidates with enriched profiles). Webhook receiver logs events. Integration health dashboard shows connector status. |
| **Analytics Dashboard** | Metric cards + Chart.js doughnut charts for feedback sentiment, case status, question volume, and event counts. |
| **Event Log** | Audit trail of system events (case created, workflow started, approval decisions, webhooks) with typed payloads. |

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

**Key design decisions:**
- Async throughout — `AsyncOpenAI` singleton, `async def` endpoints
- Agent with human-in-the-loop — confirms before creating cases or starting workflows
- Conversation memory — persisted in Supabase, loaded per session
- Interactive UI — Tailwind CSS, Chart.js, PATCH API for checklist toggling
- Candidate Intelligence — embedding similarity scoring + LLM-as-judge for hiring decision support
- Production-hardened — API key auth, per-IP rate limiting, Pydantic validation, structured logging, 84 tests

**Future improvements:**
- Migrate from LangChain `AgentExecutor` to **LangGraph** for production-grade state management, human-in-the-loop approvals, and parallel tool execution
- Streaming responses for the People Concierge (SSE)
- Real Workday / Greenhouse API connectors (replace mocks)

## Pages

| Route | Page |
|-------|------|
| `/people-help` | People Concierge — AI agent (main entry point) |
| `/knowledge` | Knowledge Base search with RAG + citations |
| `/workflows` | Workflow runs list + simulate |
| `/workflows/run/{id}` | Workflow detail with checklist + approval pipeline |
| `/workflows/approvals` | Pending approvals dashboard |
| `/integrations` | Integration health dashboard |
| `/integrations/hiring` | Hiring Intelligence dashboard (candidate matching) |
| `/integrations/hiring/match/{req_id}` | AI-ranked candidates for a requisition (JSON) |
| `/integrations/hiring/analyze/{req_id}/{cand_id}` | Deep-dive candidate analysis (JSON) |
| `/integrations/workday/employees?q=` | Mock Workday employee search (JSON) |
| `/integrations/greenhouse/requisitions` | Mock Greenhouse requisitions (JSON) |
| `/integrations/greenhouse/candidates/{id}` | Candidate detail profile (JSON) |
| `/integrations/webhooks/{source}` | Webhook receiver (POST) |
| `/events` | Event log |
| `/analytics` | Dashboard with charts |
| `/health` | Health check (JSON) |
| `/docs` | Auto-generated OpenAPI docs |

## Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Supabase** — Create a project at [supabase.com](https://supabase.com), then run `db/schema.sql` in the SQL Editor. This creates all tables including `conversations`, `conversation_messages`, `workflow_checklist`, and pgvector extensions.

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

5. **Seed data** (first run only)
   ```bash
   npm run seed
   ```
   This ingests 7 HR policy docs into the knowledge base and creates 3 workflow definitions (onboarding, PTO, expense reimbursement).

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
5. Seed: `POST https://your-app.onrender.com/knowledge/seed` and `POST https://your-app.onrender.com/workflows/definitions/seed`

`render.yaml` is included for one-click deploys.

## Project structure

```
├── main.py                  # FastAPI app + middleware + router registration
├── config.py                # Env var loading (Supabase, OpenAI, auth, rate limit)
├── models.py                # Pydantic request/response models
├── templates_ctx.py         # Jinja2 template setup
├── package.json             # npm scripts (start, test, seed)
├── pytest.ini               # Test configuration
├── middleware/
│   ├── auth.py              # API key authentication
│   ├── rate_limit.py        # Per-IP rate limiting on LLM endpoints
│   └── request_logging.py   # Structured request logging with request IDs
├── routers/
│   ├── people_help.py       # People Concierge chat API
│   ├── knowledge.py         # RAG search + seed (7 HR docs) + feedback
│   ├── workflows.py         # Workflow runs + checklist + approvals
│   ├── integrations.py      # Mock Workday/Greenhouse + hiring dashboard + webhooks
│   ├── analytics.py         # Dashboard with counts
│   └── events.py            # Event log
├── services/
│   ├── agent.py             # LangChain agent + 15 tools
│   ├── candidate_intelligence.py  # AI candidate matching + analysis
│   ├── rag.py               # Embeddings, vector search, RAG
│   ├── intent.py            # Intent classifier (legacy)
│   ├── approvals.py         # Approval engine + definitions
│   ├── integrations.py      # Mock Workday/Greenhouse data + webhooks
│   ├── workflows.py         # Shared onboarding logic
│   └── supabase_client.py   # Supabase singleton
├── tests/                   # Pytest test suite (84 tests)
│   ├── test_api.py          # API endpoint tests
│   ├── test_candidate_intelligence.py  # Candidate matching tests
│   ├── test_integrations.py # Mock Workday/Greenhouse tests
│   ├── test_middleware.py   # Auth + rate limiting tests
│   ├── test_models.py       # Pydantic validation tests
│   └── test_rag.py          # RAG chunking tests
├── templates/               # Jinja2 + Tailwind CSS (10 templates)
│   └── hiring.html          # Hiring Intelligence dashboard
├── db/schema.sql            # Full database schema (13 tables)
└── docs/
    └── PEOPLE_HELP_ENHANCEMENT_PLAN.md  # 8-phase roadmap (all complete)
```

## Enhancement plan

See [`docs/PEOPLE_HELP_ENHANCEMENT_PLAN.md`](docs/PEOPLE_HELP_ENHANCEMENT_PLAN.md) for the full roadmap.

| Phase | Status | Focus |
|-------|--------|-------|
| 0 — Foundation | Done | FastAPI, Supabase, RAG, 3 use cases |
| 1 — Backend fixes | Done | Async OpenAI, error handling, logging |
| 2 — Agentic AI | Done | LangChain agent, tools, conversation memory |
| 3 — Modern UI | Done | Tailwind CSS, Chart.js, interactive checklists |
| 4 — Approval workflows | Done | Multi-step approvals, role-based routing, agent tools |
| 5 — Mock integrations | Done | Workday/Greenhouse mocks, webhooks, health dashboard |
| 6 — Hardening | Done | API key auth, Pydantic validation, rate limiting, logging, 84 tests |
| 7 — Candidate Intelligence | Done | AI candidate matching (embeddings + LLM), hiring dashboard, enriched mock data, 7 HR seed docs |

**What's next (production roadmap):**
- **LangGraph migration** — Replace LangChain `AgentExecutor` with LangGraph for explicit state management, human-in-the-loop as graph nodes, and parallel tool execution
- **Streaming** — SSE streaming for People Concierge responses
- **Real integrations** — Workday, Greenhouse, Slack, Okta via OAuth connectors
- **RBAC** — Role-based access control (employee vs manager vs HR admin)
- **Deployment** — Render or Vercel with CI/CD pipeline

## Park and resume

All data lives in Supabase. Stop the Render service to pause; redeploy from the same repo to resume. No data loss, no secrets in repo.
