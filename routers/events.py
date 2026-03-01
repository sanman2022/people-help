import json

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from services.supabase_client import get_supabase
from templates_ctx import templates

router = APIRouter()


@router.get("", response_class=HTMLResponse)
async def events_page(request: Request):
    sb = get_supabase()
    result = sb.table("events").select("*").order("created_at", desc=True).limit(100).execute()
    events = result.data or []
    for e in events:
        if e.get("payload") and not isinstance(e["payload"], str):
            e["payload"] = json.dumps(e["payload"], indent=2)
    return templates.TemplateResponse(request, "events.html", {"events": events})
