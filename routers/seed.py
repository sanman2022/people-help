"""Seed endpoints for demo data setup.

These are called by `db/seed.py` (or `npm run seed`) to populate the demo
with realistic data — cases, onboarding runs, events, feedback, connectors.
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from services.supabase_client import get_supabase
from services.workflows import create_onboarding_run

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Tables to truncate (order matters — children before parents for FK safety)
# ---------------------------------------------------------------------------

TRUNCATE_TABLES = [
    "conversation_messages",
    "conversations",
    "feedback",
    "questions",
    "document_chunks",
    "documents",
    "workflow_checklist",
    "approvals",
    "workflow_runs",
    "events",
    "cases",
    "connectors",
    "workflow_definitions",
]


@router.post("/reset")
async def reset_all_tables():
    """Truncate all data tables for a clean demo reset."""
    sb = get_supabase()
    cleaned = 0
    for table in TRUNCATE_TABLES:
        try:
            # Delete all rows (Supabase doesn't expose TRUNCATE via REST)
            sb.table(table).delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
            cleaned += 1
        except Exception as e:
            logger.warning("Failed to clean table %s: %s", table, e)

    # Clear Pinecone index (vector store)
    try:
        from services.rag import _get_pinecone_index
        index = _get_pinecone_index()
        index.delete(delete_all=True)
        logger.info("Pinecone index cleared")
    except Exception as e:
        logger.warning("Failed to clear Pinecone index: %s", e)

    return {"tables_cleaned": cleaned}


@router.post("/connectors")
async def seed_connectors():
    """Seed connector health records for the Integrations page."""
    sb = get_supabase()
    now = datetime.now(timezone.utc).isoformat()
    connectors = [
        {"name": "workday", "label": "Workday", "type": "hris", "status": "connected", "last_event_at": now},
        {"name": "greenhouse", "label": "Greenhouse", "type": "ats", "status": "connected", "last_event_at": now},
        {"name": "slack", "label": "Slack", "type": "messaging", "status": "connected", "last_event_at": None},
        {"name": "okta", "label": "Okta", "type": "identity", "status": "not_configured", "last_event_at": None},
    ]
    count = 0
    for c in connectors:
        try:
            sb.table("connectors").upsert(c, on_conflict="name").execute()
            count += 1
        except Exception as e:
            logger.warning("Failed to seed connector %s: %s", c["name"], e)
    return {"count": count}


@router.post("/demo-data")
async def seed_demo_data():
    """Create realistic demo cases, onboarding runs, events, and feedback."""
    sb = get_supabase()
    counts = {"cases": 0, "onboarding_runs": 0, "events": 0, "feedback": 0}
    now = datetime.now(timezone.utc)

    # -----------------------------------------------------------------------
    # Cases — a mix of open and resolved
    # -----------------------------------------------------------------------
    demo_cases = [
        {"subject": "Direct deposit not updating after bank change", "description": "Employee changed banks two weeks ago but payroll still going to old account. Submitted form twice via HR portal.", "status": "open"},
        {"subject": "Laptop replacement request — cracked screen", "description": "Screen cracked during commute. Need replacement to continue working. Currently using personal device.", "status": "open"},
        {"subject": "Benefits enrollment deadline extension", "description": "New hire missed 30-day enrollment window due to delayed start date. Requesting exception to enroll in health plan.", "status": "open"},
        {"subject": "VPN access not working from home office", "description": "Getting 'connection refused' error since Tuesday. Tried reinstalling client. IT ticket #4521 also open.", "status": "open"},
        {"subject": "Manager not appearing in org chart", "description": "After reorg, my manager shows as 'TBD' in Workday. Need this corrected for performance review cycle.", "status": "open"},
        {"subject": "PTO balance discrepancy", "description": "System shows 12 days remaining but I've only used 3 of my 15. Carry-over from last year may not have been applied.", "status": "resolved"},
        {"subject": "Expense report rejected — need clarification", "description": "Q4 travel expense rejected by finance. Receipt was attached. Requesting re-review or explanation of rejection reason.", "status": "resolved"},
        {"subject": "Request for ergonomic desk setup", "description": "Doctor recommended standing desk and ergonomic keyboard. Need approval and equipment ordering process.", "status": "resolved"},
    ]
    for i, case in enumerate(demo_cases):
        try:
            # Stagger creation dates for realism
            created = (now - timedelta(days=len(demo_cases) - i, hours=i * 3)).isoformat()
            row = sb.table("cases").insert({
                "subject": case["subject"],
                "description": case["description"],
                "status": case["status"],
                "created_at": created,
            }).execute()
            counts["cases"] += 1
            # Create a corresponding event
            case_id = str(row.data[0]["id"]) if row.data else "unknown"
            sb.table("events").insert({
                "event_type": "case_created",
                "payload": {"subject": case["subject"], "case_id": case_id},
                "created_at": created,
            }).execute()
            counts["events"] += 1
        except Exception as e:
            logger.warning("Failed to seed case '%s': %s", case["subject"][:30], e)

    # -----------------------------------------------------------------------
    # Onboarding runs — different stages of completion
    # -----------------------------------------------------------------------
    onboarding_scenarios = [
        {
            "trigger": "Jamie Lee — Senior Backend Engineer",
            "status": "in_progress",
            "days_ago": 5,
            "checklist_done": [True, True, False, False],  # I-9 done, IT done, benefits pending, intro pending
            "approval_statuses": ["approved", "pending", "pending"],  # Manager approved, HR pending
        },
        {
            "trigger": "Priya Sharma — Product Designer",
            "status": "completed",
            "days_ago": 21,
            "checklist_done": [True, True, True, True],
            "approval_statuses": ["approved", "approved", "approved"],
        },
        {
            "trigger": "Marcus Chen — Data Analyst",
            "status": "in_progress",
            "days_ago": 2,
            "checklist_done": [True, False, False, False],  # Just I-9 done
            "approval_statuses": ["approved", "pending", "pending"],
        },
        {
            "trigger": "Sofia Rodriguez — Engineering Manager",
            "status": "completed",
            "days_ago": 45,
            "checklist_done": [True, True, True, True],
            "approval_statuses": ["approved", "approved", "approved"],
        },
        {
            "trigger": "Aiden Park — Security Engineer",
            "status": "in_progress",
            "days_ago": 1,
            "checklist_done": [False, False, False, False],  # Brand new
            "approval_statuses": ["pending", "pending", "pending"],
        },
    ]

    checklist_labels = [
        "Complete I-9 and tax forms",
        "IT setup (laptop, access)",
        "Benefits enrollment",
        "Team intro and first 1:1",
    ]

    approval_steps = [
        {"name": "manager_approval", "label": "Manager Approval", "role": "manager", "order": 1},
        {"name": "hr_review", "label": "HR Review", "role": "hr", "order": 2},
        {"name": "it_provisioning", "label": "IT Provisioning", "role": "it", "order": 3},
    ]

    for scenario in onboarding_scenarios:
        try:
            created = (now - timedelta(days=scenario["days_ago"])).isoformat()

            # Create workflow run
            run_row = sb.table("workflow_runs").insert({
                "workflow_type": "onboarding",
                "status": scenario["status"],
                "payload": {"trigger": scenario["trigger"]},
                "created_at": created,
            }).execute()
            run_id = str(run_row.data[0]["id"])
            counts["onboarding_runs"] += 1

            # Create checklist items
            for i, label in enumerate(checklist_labels):
                sb.table("workflow_checklist").insert({
                    "workflow_run_id": run_id,
                    "label": label,
                    "done": scenario["checklist_done"][i],
                    "sort_order": i,
                }).execute()

            # Create approval steps
            for i, step in enumerate(approval_steps):
                status = scenario["approval_statuses"][i]
                approval_data = {
                    "workflow_run_id": run_id,
                    "step_name": step["name"],
                    "step_order": step["order"],
                    "approver_role": step["role"],
                    "status": status,
                }
                if status == "approved":
                    approval_data["decided_by"] = "demo_seed"
                    approval_data["decided_at"] = (now - timedelta(days=scenario["days_ago"] - 1)).isoformat()
                sb.table("approvals").insert(approval_data).execute()

            # Create event
            sb.table("events").insert({
                "event_type": "offer_accepted",
                "payload": {"workflow_run_id": run_id, "trigger": scenario["trigger"]},
                "created_at": created,
            }).execute()
            counts["events"] += 1

            # Add approval events for completed steps
            for i, step in enumerate(approval_steps):
                if scenario["approval_statuses"][i] == "approved":
                    sb.table("events").insert({
                        "event_type": "approval_approved",
                        "payload": {
                            "workflow_run_id": run_id,
                            "step_name": step["name"],
                            "approver_role": step["role"],
                            "decided_by": "demo_seed",
                        },
                        "created_at": (now - timedelta(days=scenario["days_ago"] - 1, hours=i)).isoformat(),
                    }).execute()
                    counts["events"] += 1

        except Exception as e:
            logger.warning("Failed to seed onboarding '%s': %s", scenario["trigger"][:30], e)

    # -----------------------------------------------------------------------
    # Additional events — webhook & integration events
    # -----------------------------------------------------------------------
    extra_events = [
        {"event_type": "webhook_received", "payload": {"source": "workday", "event": "employee.updated", "employee_id": "WD-1001"}, "days_ago": 3},
        {"event_type": "webhook_received", "payload": {"source": "greenhouse", "event": "candidate.stage_change", "candidate_id": "C-201"}, "days_ago": 2},
        {"event_type": "webhook_received", "payload": {"source": "workday", "event": "employee.created", "employee_id": "WD-1006"}, "days_ago": 1},
    ]
    for evt in extra_events:
        try:
            sb.table("events").insert({
                "event_type": evt["event_type"],
                "payload": evt["payload"],
                "created_at": (now - timedelta(days=evt["days_ago"])).isoformat(),
            }).execute()
            counts["events"] += 1
        except Exception as e:
            logger.warning("Failed to seed event: %s", e)

    # -----------------------------------------------------------------------
    # Feedback — simulate KB question + feedback entries for analytics charts
    # -----------------------------------------------------------------------
    demo_questions = [
        {"query": "How do I request PTO?", "helpful": True},
        {"query": "What are the expense limits for meals?", "helpful": True},
        {"query": "When is the next performance review cycle?", "helpful": True},
        {"query": "How do I enroll in benefits?", "helpful": True},
        {"query": "What's the interview process?", "helpful": False},
        {"query": "Can I carry over PTO to next year?", "helpful": True},
        {"query": "Who approves my expense reports?", "helpful": True},
        {"query": "What's the relocation policy?", "helpful": False},
        {"query": "How do I get a standing desk?", "helpful": True},
        {"query": "What's the hiring timeline for open reqs?", "helpful": True},
    ]
    for i, q in enumerate(demo_questions):
        try:
            created = (now - timedelta(days=10 - i, hours=i * 2)).isoformat()
            q_row = sb.table("questions").insert({
                "query": q["query"],
                "answer_text": f"(Demo seed answer for: {q['query']})",
                "sources_json": [],
                "created_at": created,
            }).execute()
            q_id = str(q_row.data[0]["id"]) if q_row.data else None
            if q_id:
                sb.table("feedback").insert({
                    "question_id": q_id,
                    "helpful": q["helpful"],
                    "created_at": created,
                }).execute()
                counts["feedback"] += 1
        except Exception as e:
            logger.warning("Failed to seed question/feedback: %s", e)

    return counts
