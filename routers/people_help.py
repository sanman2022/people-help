import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from models import ChatRequest, ChatResponse, ErrorResponse
from services.agent import run_agent
from services.intent import INTENT_ANSWER, INTENT_CREATE_CASE, INTENT_START_WORKFLOW, classify_intent
from services.rag import answer_with_rag, store_question_and_feedback
from services.supabase_client import get_supabase
from services.workflows import create_onboarding_run
from templates_ctx import templates

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Chat API — agentic multi-turn endpoint (Phase 2)
# ---------------------------------------------------------------------------


@router.post("/people-help/chat", response_model=ChatResponse, responses={400: {"model": ErrorResponse}})
async def people_help_chat(body: ChatRequest):
    """Agentic chat endpoint. Validated by Pydantic — rejects empty/oversized messages.
    Returns JSON {response, conversation_id}."""
    response, conv_id = await run_agent(body.message.strip(), body.conversation_id)
    return JSONResponse({"response": response, "conversation_id": conv_id})


# ---------------------------------------------------------------------------
# HTML pages — form-based (legacy, still works)
# ---------------------------------------------------------------------------


@router.get("/people-help", response_class=HTMLResponse)
async def people_help_page(request: Request):
    return templates.TemplateResponse(request, "people_help.html", {"result": None})


@router.post("/people-help", response_class=HTMLResponse)
async def people_help_submit(request: Request):
    form = await request.form()
    query = (form.get("query") or "").strip()
    if not query:
        return templates.TemplateResponse(request, "people_help.html", {"result": None})

    intent = await classify_intent(query)

    if intent == INTENT_ANSWER:
        answer, sources = await answer_with_rag(query)
        question_id = await store_question_and_feedback(query, answer, sources)
        return templates.TemplateResponse(
            request,
            "people_help.html",
            {
                "result": {
                    "intent": "answer",
                    "answer": answer,
                    "sources": sources,
                    "question_id": question_id,
                },
            },
        )

    if intent == INTENT_CREATE_CASE:
        try:
            sb = get_supabase()
            row = (
                sb.table("cases")
                .insert({"subject": query[:200], "description": query, "status": "open"})
                .execute()
            )
            case_id = str(row.data[0]["id"]) if row.data else None
            sb.table("events").insert(
                {"event_type": "case_created", "payload": {"subject": query[:200], "case_id": case_id}}
            ).execute()
        except Exception as e:
            logger.error("Failed to create case: %s", e)
            case_id = None
        return templates.TemplateResponse(
            request,
            "people_help.html",
            {"result": {"intent": "create_case", "case_id": case_id}},
        )

    # start_workflow (e.g. onboarding)
    run_id = create_onboarding_run(trigger=query)
    return templates.TemplateResponse(
        request,
        "people_help.html",
        {"result": {"intent": "start_workflow", "workflow_run_id": run_id}},
    )
