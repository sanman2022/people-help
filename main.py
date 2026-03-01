import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import BASE_DIR
from middleware.auth import APIKeyMiddleware
from middleware.rate_limit import RateLimitMiddleware
from middleware.request_logging import RequestLoggingMiddleware
from routers import analytics, events, integrations, knowledge, people_help, seed, workflows

# ---------------------------------------------------------------------------
# Structured logging — configure once at app startup
# ---------------------------------------------------------------------------

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s  %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
# Silence noisy libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="People Help",
    description="Internal operating system for EX: answer, guide, orchestrate.",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# Middleware (order matters — outermost runs first)
# ---------------------------------------------------------------------------

# 1. Request logging (outermost — logs every request with timing)
app.add_middleware(RequestLoggingMiddleware)

# 2. CORS — allow frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:8000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Rate limiting on LLM endpoints
app.add_middleware(RateLimitMiddleware)

# 4. API key auth (innermost — closest to route handlers)
app.add_middleware(APIKeyMiddleware)

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------

static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(people_help.router, tags=["people_help"])
app.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
app.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
app.include_router(events.router, prefix="/events", tags=["events"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
app.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
app.include_router(seed.router, prefix="/seed", tags=["seed"])


@app.get("/")
async def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/people-help", status_code=302)


@app.get("/health")
async def health():
    """Health check — always returns 200. Used by load balancers and uptime monitors."""
    return {"status": "ok", "service": "people-help"}


logger.info("People Help app initialized with %d routers", 7)
