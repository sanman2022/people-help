"""Approval engine — create, advance, approve/reject approval steps in workflows."""

import logging
from datetime import datetime, timezone

from services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default workflow definitions (seeded on first use)
# ---------------------------------------------------------------------------

DEFAULT_DEFINITIONS = [
    {
        "name": "onboarding",
        "description": "New hire onboarding with manager and HR approval",
        "definition": {
            "steps": [
                {"name": "manager_approval", "label": "Manager Approval", "approver_role": "manager", "order": 1},
                {"name": "hr_review", "label": "HR Review", "approver_role": "hr", "order": 2},
                {"name": "it_provisioning", "label": "IT Provisioning", "approver_role": "it", "order": 3},
            ]
        },
    },
    {
        "name": "pto_request",
        "description": "PTO request requiring manager approval",
        "definition": {
            "steps": [
                {"name": "manager_approval", "label": "Manager Approval", "approver_role": "manager", "order": 1},
            ]
        },
    },
    {
        "name": "expense_reimbursement",
        "description": "Expense reimbursement with manager and finance approval",
        "definition": {
            "steps": [
                {"name": "manager_approval", "label": "Manager Approval", "approver_role": "manager", "order": 1},
                {"name": "finance_review", "label": "Finance Review", "approver_role": "finance", "order": 2},
            ]
        },
    },
]


def seed_definitions() -> int:
    """Seed default workflow definitions. Returns count of definitions created."""
    try:
        sb = get_supabase()
        existing = sb.table("workflow_definitions").select("name").execute()
        existing_names = {d["name"] for d in (existing.data or [])}
        created = 0
        for defn in DEFAULT_DEFINITIONS:
            if defn["name"] not in existing_names:
                sb.table("workflow_definitions").insert(defn).execute()
                created += 1
        return created
    except Exception as e:
        logger.error("Failed to seed workflow definitions: %s", e)
        return 0


def get_definitions() -> list[dict]:
    """Return all workflow definitions."""
    try:
        sb = get_supabase()
        result = sb.table("workflow_definitions").select("*").order("created_at").execute()
        return result.data or []
    except Exception as e:
        logger.error("Failed to load workflow definitions: %s", e)
        return []


def get_definition_by_name(name: str) -> dict | None:
    """Return a single workflow definition by name."""
    try:
        sb = get_supabase()
        result = sb.table("workflow_definitions").select("*").eq("name", name).limit(1).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error("Failed to load workflow definition %s: %s", name, e)
        return None


# ---------------------------------------------------------------------------
# Create approval steps for a workflow run
# ---------------------------------------------------------------------------


def create_approvals_for_run(workflow_run_id: str, definition_name: str) -> list[str]:
    """Create approval rows for a workflow run based on a definition. Returns list of approval IDs."""
    defn = get_definition_by_name(definition_name)
    if not defn:
        logger.warning("No definition found for '%s', skipping approvals", definition_name)
        return []

    steps = defn.get("definition", {}).get("steps", [])
    if not steps:
        return []

    try:
        sb = get_supabase()
        ids = []
        for step in sorted(steps, key=lambda s: s.get("order", 0)):
            row = sb.table("approvals").insert({
                "workflow_run_id": workflow_run_id,
                "step_name": step["name"],
                "step_order": step.get("order", 0),
                "approver_role": step["approver_role"],
                "status": "pending",
            }).execute()
            if row.data:
                ids.append(str(row.data[0]["id"]))
        # First step is active; rest are pending (we leave all as pending but only
        # the first one is "actionable" — the engine checks order)
        logger.info("Created %d approval steps for run %s", len(ids), workflow_run_id)
        return ids
    except Exception as e:
        logger.error("Failed to create approvals for run %s: %s", workflow_run_id, e)
        return []


# ---------------------------------------------------------------------------
# Query approvals
# ---------------------------------------------------------------------------


def get_approvals_for_run(workflow_run_id: str) -> list[dict]:
    """Return all approval steps for a workflow run, ordered by step_order."""
    try:
        sb = get_supabase()
        result = (
            sb.table("approvals")
            .select("*")
            .eq("workflow_run_id", workflow_run_id)
            .order("step_order")
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error("Failed to load approvals for run %s: %s", workflow_run_id, e)
        return []


def get_pending_approvals(approver_role: str | None = None) -> list[dict]:
    """Return pending approvals, optionally filtered by approver_role.
    Only returns approvals that are currently actionable (all prior steps approved)."""
    try:
        sb = get_supabase()
        query = sb.table("approvals").select("*, workflow_runs(id, workflow_type, status, payload)")
        if approver_role:
            query = query.eq("approver_role", approver_role)
        query = query.eq("status", "pending").order("created_at")
        result = query.execute()
        approvals = result.data or []

        # Filter to only actionable approvals (all prior steps in same run are approved)
        actionable = []
        for approval in approvals:
            run_id = approval.get("workflow_run_id")
            step_order = approval.get("step_order", 0)
            # Check if all earlier steps are approved
            prior = (
                sb.table("approvals")
                .select("status")
                .eq("workflow_run_id", run_id)
                .lt("step_order", step_order)
                .execute()
            )
            prior_steps = prior.data or []
            if all(s.get("status") == "approved" for s in prior_steps):
                actionable.append(approval)
        return actionable
    except Exception as e:
        logger.error("Failed to load pending approvals: %s", e)
        return []


def get_all_pending_approvals() -> list[dict]:
    """Return all pending approvals (no role filter), only actionable ones."""
    return get_pending_approvals(approver_role=None)


# ---------------------------------------------------------------------------
# Approve / Reject
# ---------------------------------------------------------------------------


def _send_notification(action: str, approval: dict, notes: str | None = None) -> None:
    """Stub: log what notification would be sent. Replace with email/Slack in production."""
    role = approval.get("approver_role", "unknown")
    step = approval.get("step_name", "unknown")
    run_id = approval.get("workflow_run_id", "unknown")
    logger.info(
        "NOTIFICATION STUB: [%s] Step '%s' %s by %s for run %s. Notes: %s",
        action.upper(), step, action, role, run_id, notes or "(none)"
    )
    # Log to events table for audit trail
    try:
        sb = get_supabase()
        sb.table("events").insert({
            "event_type": f"approval_{action}",
            "payload": {
                "approval_id": approval.get("id"),
                "workflow_run_id": run_id,
                "step_name": step,
                "approver_role": role,
                "decided_by": approval.get("decided_by"),
                "notes": notes,
            },
        }).execute()
    except Exception as e:
        logger.error("Failed to log approval event: %s", e)


def process_approval(approval_id: str, action: str, decided_by: str = "demo_user", notes: str | None = None) -> dict:
    """Approve or reject an approval step. Returns updated approval or error dict.

    After approving, checks if all steps for the run are approved → marks run as completed.
    After rejecting, marks the workflow run as rejected.
    """
    if action not in ("approved", "rejected"):
        return {"error": f"Invalid action: {action}. Must be 'approved' or 'rejected'."}

    try:
        sb = get_supabase()

        # Load the approval
        result = sb.table("approvals").select("*").eq("id", approval_id).single().execute()
        if not result.data:
            return {"error": f"Approval {approval_id} not found."}

        approval = result.data
        if approval["status"] != "pending":
            return {"error": f"Approval already {approval['status']}."}

        # Check this step is actionable (all prior steps approved)
        run_id = approval["workflow_run_id"]
        step_order = approval["step_order"]
        prior = (
            sb.table("approvals")
            .select("status")
            .eq("workflow_run_id", run_id)
            .lt("step_order", step_order)
            .execute()
        )
        if not all(s.get("status") == "approved" for s in (prior.data or [])):
            return {"error": "Previous approval steps must be completed first."}

        # Update the approval
        now = datetime.now(timezone.utc).isoformat()
        sb.table("approvals").update({
            "status": action,
            "decided_by": decided_by,
            "notes": notes,
            "decided_at": now,
        }).eq("id", approval_id).execute()

        approval["status"] = action
        approval["decided_by"] = decided_by
        approval["decided_at"] = now

        # Send notification
        _send_notification(action, approval, notes)

        # If rejected, mark the workflow run as rejected
        if action == "rejected":
            sb.table("workflow_runs").update({"status": "rejected"}).eq("id", run_id).execute()
            return {"ok": True, "approval": approval, "run_status": "rejected"}

        # If approved, check if all steps are now approved
        all_steps = (
            sb.table("approvals")
            .select("status")
            .eq("workflow_run_id", run_id)
            .execute()
        )
        all_approved = all(s.get("status") == "approved" for s in (all_steps.data or []))
        if all_approved:
            sb.table("workflow_runs").update({"status": "completed"}).eq("id", run_id).execute()
            _send_notification("workflow_completed", {"workflow_run_id": run_id, "approver_role": "system", "step_name": "all"})
            return {"ok": True, "approval": approval, "run_status": "completed"}

        return {"ok": True, "approval": approval, "run_status": "in_progress"}

    except Exception as e:
        logger.error("Failed to process approval %s: %s", approval_id, e)
        return {"error": f"Failed to process approval: {e}"}
