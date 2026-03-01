import logging

from services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

DEFAULT_ONBOARDING_CHECKLIST = [
    "Complete I-9 and tax forms",
    "IT setup (laptop, access)",
    "Benefits enrollment",
    "Team intro and first 1:1",
]


def find_active_onboarding(trigger_name: str) -> list[str]:
    """Find active (in_progress) onboarding runs whose trigger contains the given name.
    Returns list of matching run IDs."""
    try:
        sb = get_supabase()
        # Use ilike on the JSONB trigger field for fuzzy name matching
        result = (
            sb.table("workflow_runs")
            .select("id")
            .eq("workflow_type", "onboarding")
            .eq("status", "in_progress")
            .ilike("payload->>trigger", f"%{trigger_name[:100]}%")
            .limit(5)
            .execute()
        )
        return [str(r["id"]) for r in (result.data or [])]
    except Exception as e:
        logger.error("find_active_onboarding failed: %s", e)
        return []


def create_onboarding_run(trigger: str) -> str | None:
    """Create an onboarding workflow run with default checklist. Returns run_id."""
    try:
        sb = get_supabase()
        run = (
            sb.table("workflow_runs")
            .insert({
                "workflow_type": "onboarding",
                "status": "in_progress",
                "payload": {"trigger": trigger[:200]},
            })
            .execute()
        )
        run_id = str(run.data[0]["id"]) if run.data else None
        if not run_id:
            return None

        for i, label in enumerate(DEFAULT_ONBOARDING_CHECKLIST):
            sb.table("workflow_checklist").insert(
                {"workflow_run_id": run_id, "label": label, "sort_order": i}
            ).execute()

        sb.table("events").insert(
            {"event_type": "offer_accepted", "payload": {"workflow_run_id": run_id, "trigger": trigger[:200]}}
        ).execute()

        # Create approval steps from the onboarding definition
        from services.approvals import create_approvals_for_run
        create_approvals_for_run(run_id, "onboarding")

        return run_id
    except Exception as e:
        logger.error("Failed to create onboarding run: %s", e)
        return None
