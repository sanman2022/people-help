"""Integrations router — mock Workday, Greenhouse APIs, webhook receiver, health dashboard."""

import logging

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse

from models import (
    EmployeeDetailResponse,
    EmployeeSearchResponse,
    ErrorResponse,
    OrgChartResponse,
    RequisitionDetailResponse,
    RequisitionListResponse,
    WebhookResponse,
)
from services.candidate_intelligence import get_candidate_analysis, rank_candidates_for_req
from services.integrations import (
    get_connectors,
    greenhouse_get_candidate,
    greenhouse_get_req,
    greenhouse_list_candidates,
    greenhouse_list_reqs,
    process_webhook,
    workday_get_employee,
    workday_lookup_employee,
    workday_org_chart,
)
from templates_ctx import templates

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Mock Workday API
# ---------------------------------------------------------------------------


@router.get("/workday/employees", response_model=EmployeeSearchResponse, responses={400: {"model": ErrorResponse}})
async def workday_search(q: str = Query("", min_length=1, description="Search query")):
    """Mock Workday: search employees by name/email/ID."""
    results = workday_lookup_employee(q)
    return JSONResponse({"source": "workday_mock", "query": q, "results": results})


@router.get("/workday/employees/{employee_id}", response_model=EmployeeDetailResponse, responses={404: {"model": ErrorResponse}})
async def workday_employee_detail(employee_id: str):
    """Mock Workday: get employee by ID."""
    emp = workday_get_employee(employee_id)
    if not emp:
        return JSONResponse({"error": f"Employee {employee_id} not found"}, status_code=404)
    return JSONResponse({"source": "workday_mock", "employee": emp})


@router.get("/workday/org-chart/{employee_id}", response_model=OrgChartResponse, responses={404: {"model": ErrorResponse}})
async def workday_org(employee_id: str):
    """Mock Workday: get org chart for employee."""
    result = workday_org_chart(employee_id)
    if "error" in result:
        return JSONResponse(result, status_code=404)
    return JSONResponse({"source": "workday_mock", **result})


# ---------------------------------------------------------------------------
# Mock Greenhouse API
# ---------------------------------------------------------------------------


@router.get("/greenhouse/requisitions", response_model=RequisitionListResponse)
async def greenhouse_reqs(status: str | None = None):
    """Mock Greenhouse: list requisitions. Optional ?status=open or ?status=closed."""
    reqs = greenhouse_list_reqs(status)
    return JSONResponse({"source": "greenhouse_mock", "count": len(reqs), "requisitions": reqs})


@router.get("/greenhouse/requisitions/{req_id}", response_model=RequisitionDetailResponse, responses={404: {"model": ErrorResponse}})
async def greenhouse_req_detail(req_id: str):
    """Mock Greenhouse: get requisition with candidates."""
    req = greenhouse_get_req(req_id)
    if not req:
        return JSONResponse({"error": f"Requisition {req_id} not found"}, status_code=404)
    candidates = greenhouse_list_candidates(req_id)
    return JSONResponse({"source": "greenhouse_mock", "requisition": req, "candidates": candidates})


# ---------------------------------------------------------------------------
# Candidate Intelligence — AI-powered matching & analysis
# ---------------------------------------------------------------------------


@router.get("/greenhouse/candidates/{candidate_id}")
async def greenhouse_candidate_detail(candidate_id: str):
    """Mock Greenhouse: get candidate profile."""
    candidate = greenhouse_get_candidate(candidate_id)
    if not candidate:
        return JSONResponse({"error": f"Candidate {candidate_id} not found"}, status_code=404)
    return JSONResponse({"source": "greenhouse_mock", "candidate": candidate})


@router.get("/hiring/match/{req_id}")
async def hiring_match(req_id: str):
    """Rank candidates for a requisition using AI embedding similarity."""
    result = await rank_candidates_for_req(req_id)
    if "error" in result:
        return JSONResponse(result, status_code=404)
    return JSONResponse(result)


@router.get("/hiring/analyze/{req_id}/{candidate_id}")
async def hiring_analyze(req_id: str, candidate_id: str):
    """Deep-dive AI analysis of a candidate's fit for a requisition."""
    result = await get_candidate_analysis(req_id, candidate_id)
    if "error" in result:
        return JSONResponse(result, status_code=400)
    return JSONResponse(result)


@router.get("/hiring", response_class=HTMLResponse)
async def hiring_page(request: Request):
    """Hiring Intelligence dashboard — view open reqs and rank candidates."""
    reqs = greenhouse_list_reqs("open")
    return templates.TemplateResponse(
        request,
        "hiring.html",
        {"reqs": reqs},
    )


# ---------------------------------------------------------------------------
# Webhook receiver
# ---------------------------------------------------------------------------


@router.post("/webhooks/{source}", response_model=WebhookResponse, responses={500: {"model": ErrorResponse}})
async def receive_webhook(request: Request, source: str):
    """Receive a webhook from any source. Logs to events table."""
    try:
        payload = await request.json()
    except Exception:
        payload = {"raw": (await request.body()).decode("utf-8", errors="replace")[:2000]}

    event_id = process_webhook(source, payload)
    if event_id:
        return JSONResponse({"ok": True, "event_id": event_id, "source": source})
    return JSONResponse({"error": "Failed to process webhook"}, status_code=500)


# ---------------------------------------------------------------------------
# Integration health dashboard
# ---------------------------------------------------------------------------


@router.get("", response_class=HTMLResponse)
async def integrations_page(request: Request):
    """Integration health dashboard."""
    connectors = get_connectors()
    return templates.TemplateResponse(
        request,
        "integrations.html",
        {"connectors": connectors},
    )
