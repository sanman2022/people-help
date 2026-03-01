import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from services.supabase_client import get_supabase
from templates_ctx import templates

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_class=HTMLResponse)
async def analytics_page(request: Request):
    try:
        sb = get_supabase()
        q_res = sb.table("questions").select("id", count="exact").limit(1).execute()
        questions_count = q_res.count if q_res.count is not None else len(q_res.data or [])
        fb = sb.table("feedback").select("helpful").execute()
        data = fb.data or []
        feedback_yes = sum(1 for r in data if r.get("helpful") is True)
        feedback_no = len(data) - feedback_yes
        ev_res = sb.table("events").select("id", count="exact").limit(1).execute()
        events_count = ev_res.count if ev_res.count is not None else len(ev_res.data or [])
        cases_data = (sb.table("cases").select("id, status").execute()).data or []
        cases_total = len(cases_data)
        cases_open = sum(1 for c in cases_data if c.get("status") == "open")
        # Onboarding runs
        onboarding_data = (
            sb.table("workflow_runs")
            .select("id, status")
            .eq("workflow_type", "onboarding")
            .execute()
        ).data or []
        onboarding_total = len(onboarding_data)
        onboarding_in_progress = sum(1 for r in onboarding_data if r.get("status") == "in_progress")
        onboarding_completed = sum(1 for r in onboarding_data if r.get("status") == "completed")
    except Exception as e:
        logger.error("Failed to load analytics: %s", e)
        questions_count = feedback_yes = feedback_no = events_count = cases_open = cases_total = 0
        onboarding_total = onboarding_in_progress = onboarding_completed = 0
    return templates.TemplateResponse(
        request,
        "analytics.html",
        {
            "questions_count": questions_count,
            "feedback_yes": feedback_yes,
            "feedback_no": feedback_no,
            "events_count": events_count,
            "cases_open": cases_open,
            "cases_total": cases_total,
            "onboarding_total": onboarding_total,
            "onboarding_in_progress": onboarding_in_progress,
            "onboarding_completed": onboarding_completed,
        },
    )
