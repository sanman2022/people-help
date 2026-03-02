import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from models import ApprovalDecisionRequest, ChecklistToggleRequest, ChecklistToggleResponse, ErrorResponse
from services.approvals import (
    get_all_pending_approvals,
    get_approvals_for_run,
    get_definitions,
    process_approval,
    seed_definitions,
)
from services.supabase_client import get_supabase
from services.workflows import create_onboarding_run, find_active_onboarding
from templates_ctx import templates

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_class=HTMLResponse)
async def workflows_page(request: Request):
    try:
        sb = get_supabase()
        cases = sb.table("cases").select("*").order("created_at", desc=True).limit(50).execute()
        runs = (
            sb.table("workflow_runs")
            .select("*")
            .eq("workflow_type", "onboarding")
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )
    except Exception as e:
        logger.error("Failed to load workflows: %s", e)
        cases, runs = type("R", (), {"data": []})(), type("R", (), {"data": []})()
    return templates.TemplateResponse(
        request,
        "workflows.html",
        {
            "cases": cases.data or [],
            "runs": runs.data or [],
        },
    )


@router.get("/simulate-offer-accepted", response_class=RedirectResponse)
async def simulate_offer_accepted(request: Request, trigger: str = "New Hire"):
    trigger = trigger.strip()[:200]  # Sanitize
    # Check for duplicate — if an active run exists, redirect to it instead
    existing = find_active_onboarding(trigger)
    if existing:
        return RedirectResponse(url=f"/workflows/run/{existing[0]}?duplicate=1", status_code=302)
    run_id = create_onboarding_run(trigger=trigger)
    if run_id:
        return RedirectResponse(url=f"/workflows/run/{run_id}?new=1", status_code=302)
    return RedirectResponse(url="/workflows", status_code=302)


@router.get("/run/{run_id}", response_class=HTMLResponse)
async def workflow_run_detail(request: Request, run_id: str):
    try:
        sb = get_supabase()
        run = sb.table("workflow_runs").select("*").eq("id", run_id).single().execute()
        status = run.data.get("status", "—") if run.data else "—"
        payload = run.data.get("payload", {}) or {} if run.data else {}
        trigger = payload.get("trigger", "—")
        checklist = (
            sb.table("workflow_checklist")
            .select("*")
            .eq("workflow_run_id", run_id)
            .order("sort_order")
            .execute()
        )
        approvals = get_approvals_for_run(run_id)
    except Exception as e:
        logger.error("Failed to load workflow run %s: %s", run_id, e)
        status = "error"
        trigger = "—"
        checklist = type("R", (), {"data": []})()
        approvals = []
    return templates.TemplateResponse(
        request,
        "workflow_run.html",
        {
            "run_id": run_id,
            "status": status,
            "trigger": trigger,
            "checklist": checklist.data or [],
            "approvals": approvals,
        },
    )


# ---------------------------------------------------------------------------
# Approvals
# ---------------------------------------------------------------------------


@router.get("/approvals", response_class=HTMLResponse)
async def approvals_page(request: Request):
    """Show all pending approvals across all workflows."""
    try:
        pending = get_all_pending_approvals()
        definitions = get_definitions()
    except Exception as e:
        logger.error("Failed to load approvals page: %s", e)
        pending, definitions = [], []
    return templates.TemplateResponse(
        request,
        "approvals.html",
        {"pending": pending, "definitions": definitions},
    )


@router.post("/approvals/{approval_id}/decide", responses={400: {"model": ErrorResponse}})
async def decide_approval(approval_id: str, body: ApprovalDecisionRequest):
    """Approve or reject an approval step. Validated by Pydantic model."""
    result = process_approval(approval_id, body.action, body.decided_by, body.notes)

    if "error" in result:
        return JSONResponse(result, status_code=400)
    return JSONResponse(result)


@router.api_route("/definitions/seed", methods=["GET", "POST"])
async def seed_workflow_definitions(request: Request):
    """Seed default workflow definitions."""
    count = seed_definitions()
    if request.method == "GET":
        return RedirectResponse(url=f"/workflows/approvals?seeded={count}", status_code=302)
    return {"seeded": count}


@router.patch("/checklist/{item_id}", response_model=ChecklistToggleResponse, responses={500: {"model": ErrorResponse}})
async def toggle_checklist_item(item_id: str, body: ChecklistToggleRequest):
    """Toggle a checklist item's done status. Validated by Pydantic model."""
    try:
        sb = get_supabase()
        sb.table("workflow_checklist").update({"done": body.done}).eq("id", item_id).execute()
        return JSONResponse({"ok": True, "done": body.done})
    except Exception as e:
        logger.error("Failed to toggle checklist item %s: %s", item_id, e)
        return JSONResponse({"error": "Failed to update"}, status_code=500)
