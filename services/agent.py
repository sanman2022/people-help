"""LangChain agent for People Help — tools, memory, multi-turn conversation."""

import logging
from typing import Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from config import OPENAI_API_KEY, OPENAI_CHAT_MODEL
from services.approvals import get_all_pending_approvals, get_approvals_for_run, process_approval
from services.candidate_intelligence import get_candidate_analysis, rank_candidates_for_req
from services.integrations import (
    greenhouse_get_req,
    greenhouse_list_reqs,
    workday_lookup_employee,
    workday_org_chart,
)
from services.rag import search_chunks
from services.supabase_client import get_supabase
from services.workflows import create_onboarding_run

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tools — the agent can call these to take actions
# ---------------------------------------------------------------------------


@tool
async def search_knowledge(query: str) -> str:
    """Search the internal knowledge base for HR policy and process documents.
    Use this when the user asks a question about company policies, PTO, expenses,
    benefits, onboarding, or any HR-related topic."""
    chunks = await search_chunks(query, top_k=5)
    if not chunks:
        return "No relevant documents found. The user may need to contact HR directly."
    results = []
    for i, c in enumerate(chunks):
        content = c.get("content", "")[:300]
        results.append(f"[{i+1}] {content}")
    return "\n\n---\n\n".join(results)


@tool
def create_case(subject: str, description: str) -> str:
    """Create a support case for the employee. Use this when the user has an issue
    that needs human follow-up (payroll problems, system access issues, complaints, etc.).
    Always confirm with the user BEFORE calling this tool."""
    try:
        sb = get_supabase()
        row = (
            sb.table("cases")
            .insert({"subject": subject[:200], "description": description, "status": "open"})
            .execute()
        )
        case_id = str(row.data[0]["id"]) if row.data else "unknown"
        sb.table("events").insert(
            {"event_type": "case_created", "payload": {"subject": subject[:200], "case_id": case_id}}
        ).execute()
        return f"Case created successfully. Case ID: {case_id}. An HR team member will follow up."
    except Exception as e:
        logger.error("create_case tool failed: %s", e)
        return "Sorry, I couldn't create the case right now. Please try again or contact HR directly."


@tool
def start_onboarding(trigger: str) -> str:
    """Start the onboarding workflow for a new hire. This creates a checklist with
    standard onboarding tasks (I-9 forms, IT setup, benefits, team intro).
    Always confirm with the user BEFORE calling this tool."""
    run_id = create_onboarding_run(trigger=trigger)
    if run_id:
        return f"Onboarding workflow started for {trigger}. Track progress: [View Workflow](/workflows/run/{run_id})"
    return "Sorry, I couldn't start the onboarding workflow right now. Please try again."


@tool
def check_case_status(case_id: str) -> str:
    """Check the status of an existing support case by its ID."""
    try:
        sb = get_supabase()
        result = sb.table("cases").select("*").eq("id", case_id).single().execute()
        if result.data:
            d = result.data
            return f"Case '{d.get('subject', 'N/A')}' — Status: {d.get('status', 'unknown')}. Created: {d.get('created_at', 'N/A')[:10]}"
        return f"No case found with ID {case_id}."
    except Exception as e:
        logger.error("check_case_status tool failed: %s", e)
        return "Sorry, I couldn't look up that case right now."


@tool
def check_workflow_status(run_id: str) -> str:
    """Check the status of a workflow run (e.g. onboarding) by its run ID."""
    try:
        sb = get_supabase()
        run = sb.table("workflow_runs").select("*").eq("id", run_id).single().execute()
        if not run.data:
            return f"No workflow run found with ID {run_id}."
        checklist = (
            sb.table("workflow_checklist")
            .select("label, done")
            .eq("workflow_run_id", run_id)
            .order("sort_order")
            .execute()
        )
        items = checklist.data or []
        done_count = sum(1 for item in items if item.get("done"))
        lines = [f"Workflow status: {run.data.get('status', 'unknown')} ({done_count}/{len(items)} tasks done)"]
        for item in items:
            mark = "x" if item.get("done") else " "
            lines.append(f"  [{mark}] {item.get('label', '')}")
        return "\n".join(lines)
    except Exception as e:
        logger.error("check_workflow_status tool failed: %s", e)
        return "Sorry, I couldn't look up that workflow right now."


@tool
def list_open_cases() -> str:
    """List all currently open support cases."""
    try:
        sb = get_supabase()
        result = (
            sb.table("cases")
            .select("id, subject, status, created_at")
            .eq("status", "open")
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )
        cases = result.data or []
        if not cases:
            return "No open cases found."
        lines = [f"Open cases ({len(cases)}):"]
        for c in cases:
            lines.append(f"  - [{c['id'][:8]}] {c.get('subject', 'N/A')} (created {c.get('created_at', '')[:10]})")
        return "\n".join(lines)
    except Exception as e:
        logger.error("list_open_cases tool failed: %s", e)
        return "Sorry, I couldn't retrieve cases right now."


@tool
def list_pending_approvals() -> str:
    """List all pending approval requests across workflows. Shows which steps
    are waiting for approval and by which role."""
    approvals = get_all_pending_approvals()
    if not approvals:
        return "No pending approvals found."
    lines = [f"Pending approvals ({len(approvals)}):"]
    for a in approvals:
        run_info = a.get("workflow_runs", {}) or {}
        wf_type = run_info.get("workflow_type", "unknown")
        lines.append(
            f"  - [{a['id'][:8]}] {a.get('step_name', 'N/A')} "
            f"(role: {a.get('approver_role', 'N/A')}, workflow: {wf_type}, "
            f"run: {a.get('workflow_run_id', '')[:8]})"
        )
    return "\n".join(lines)


@tool
def approve_step(approval_id: str, notes: str = "") -> str:
    """Approve a pending approval step. Always confirm with the user BEFORE calling this tool.
    Use list_pending_approvals first to find the approval_id."""
    result = process_approval(approval_id, "approved", decided_by="chat_agent", notes=notes or None)
    if "error" in result:
        return f"Error: {result['error']}"
    run_status = result.get("run_status", "unknown")
    return f"Approved. Workflow run status: {run_status}."


@tool
def reject_step(approval_id: str, notes: str = "") -> str:
    """Reject a pending approval step. Always confirm with the user BEFORE calling this tool.
    Provide a reason in notes. Use list_pending_approvals first to find the approval_id."""
    result = process_approval(approval_id, "rejected", decided_by="chat_agent", notes=notes or None)
    if "error" in result:
        return f"Error: {result['error']}"
    return f"Rejected. Workflow run status: {result.get('run_status', 'unknown')}."


@tool
def lookup_employee(query: str) -> str:
    """Look up an employee in Workday by name, email, or employee ID.
    Use this when the user asks about a specific person, their role, or contact info."""
    results = workday_lookup_employee(query)
    if not results:
        return f"No employees found matching '{query}'."
    lines = [f"Found {len(results)} employee(s):"]
    for emp in results:
        lines.append(
            f"  - {emp['name']} ({emp['employee_id']}): {emp['title']}, "
            f"{emp['department']}, {emp['location']} | Manager: {emp.get('manager') or 'None'}"
        )
    return "\n".join(lines)


@tool
def get_org_chart(employee_id: str) -> str:
    """Get the org chart for an employee — shows their manager chain and direct reports.
    Use lookup_employee first to find the employee_id (format: WD-XXXX)."""
    result = workday_org_chart(employee_id)
    if "error" in result:
        return f"Error: {result['error']}"
    emp = result["employee"]
    lines = [f"Org chart for {emp['name']} ({emp['title']}):"]
    if result["manager_chain"]:
        lines.append("  Manager chain (upward):")
        for m in result["manager_chain"]:
            lines.append(f"    ↑ {m['name']} — {m['title']}")
    if result["direct_reports"]:
        lines.append("  Direct reports:")
        for r in result["direct_reports"]:
            lines.append(f"    ↓ {r['name']} — {r['title']}")
    else:
        lines.append("  No direct reports.")
    return "\n".join(lines)


@tool
def list_open_reqs(status: str = "open") -> str:
    """List open job requisitions from Greenhouse. Use this when the user asks about
    open positions, hiring, or headcount."""
    reqs = greenhouse_list_reqs(status if status in ("open", "closed") else "open")
    if not reqs:
        return f"No {status} requisitions found."
    lines = [f"{status.title()} requisitions ({len(reqs)}):"]
    for r in reqs:
        lines.append(
            f"  - [{r['req_id']}] {r['title']} — {r['department']}, "
            f"{r['location']} ({r['candidates']} candidates)"
        )
    return "\n".join(lines)


@tool
def get_req_detail(req_id: str) -> str:
    """Get details of a job requisition including candidates and their stages.
    Use list_open_reqs first to find the req_id (format: GH-XXX)."""
    from services.integrations import greenhouse_list_candidates
    req = greenhouse_get_req(req_id)
    if not req:
        return f"Requisition {req_id} not found."
    candidates = greenhouse_list_candidates(req_id)
    lines = [
        f"Requisition {req['req_id']}: {req['title']}",
        f"  Department: {req['department']} | Location: {req['location']}",
        f"  Hiring Manager: {req['hiring_manager']} | Status: {req['status']}",
        f"  Candidates ({len(candidates)}):",
    ]
    for c in candidates:
        stars = "★" * c["rating"] + "☆" * (5 - c["rating"])
        lines.append(f"    - {c['name']} — Stage: {c['stage']} | Rating: {stars}")
    return "\n".join(lines)


@tool
async def match_candidates(req_id: str) -> str:
    """Rank candidates for a job requisition by AI-powered match scoring.
    Uses embedding similarity to compare candidate profiles against job requirements.
    Use list_open_reqs first to find the req_id (format: GH-XXX)."""
    result = await rank_candidates_for_req(req_id)
    if "error" in result:
        return f"Error: {result['error']}"
    lines = [f"Candidate rankings for {result['req_title']} ({req_id}):"]
    for i, entry in enumerate(result["ranked_candidates"]):
        c = entry["candidate"]
        pct = entry["match_pct"]
        bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
        lines.append(
            f"  {i+1}. {c['name']} — {c.get('current_title', 'N/A')} at {c.get('current_company', 'N/A')}\n"
            f"     Match: {pct}% {bar} | Stage: {c['stage']} | Exp: {c.get('experience_years', '?')}yr\n"
            f"     Skills: {', '.join(c.get('skills', [])[:6])}"
        )
    return "\n".join(lines)


@tool
async def analyze_candidate(req_id: str, candidate_id: str) -> str:
    """Get detailed AI analysis of a specific candidate's fit for a requisition.
    Returns strengths, gaps, and a recommendation. Use match_candidates first to
    see available candidates, then use this for deep-dive analysis."""
    result = await get_candidate_analysis(req_id, candidate_id)
    if "error" in result:
        return f"Error: {result['error']}"
    c = result["candidate"]
    a = result["analysis"]
    lines = [
        f"Analysis: {c['name']} for {result['requisition']['title']}",
        f"  Match score: {a.get('match_score', 'N/A')}%",
        f"  Embedding similarity: {int(result['embedding_similarity'] * 100)}%",
        f"  Strengths: {', '.join(a.get('strengths', []))}",
        f"  Gaps: {', '.join(a.get('gaps', []))}",
        f"  Recommendation: {a.get('recommendation', 'N/A')}",
    ]
    return "\n".join(lines)


# All tools available to the agent
TOOLS = [
    search_knowledge, create_case, start_onboarding,
    check_case_status, check_workflow_status, list_open_cases,
    list_pending_approvals, approve_step, reject_step,
    lookup_employee, get_org_chart, list_open_reqs, get_req_detail,
    match_candidates, analyze_candidate,
]

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are People Help, an AI assistant for employee experience at the company.
Your role is to help employees with HR questions, processes, and workflows.

What you can do:
- Answer HR/policy questions by searching the knowledge base
- Create support cases for issues that need human follow-up
- Start onboarding workflows for new hires
- Check the status of cases and workflows
- List open cases
- View pending approvals and approve or reject them
- Track approval progress across workflow runs
- Look up employees in Workday (name, role, department, manager)
- View org charts (manager chain and direct reports)
- List open job requisitions from Greenhouse
- View requisition details with candidate pipeline stages
- Rank candidates for a requisition by AI match scoring (Candidate Intelligence)
- Analyze a specific candidate's fit with strengths, gaps, and recommendation

Important rules:
1. Always search the knowledge base before answering HR questions — don't guess.
2. ALWAYS ask for confirmation before creating a case, starting a workflow,
   or approving/rejecting an approval step.
   Say something like "I can create a case for this. Should I go ahead?"
3. Be concise and practical. Employees want quick answers, not essays.
4. If you don't have enough information from the knowledge base, say so honestly
   and suggest the employee contact HR directly.
5. Cite source numbers [1], [2] when referencing knowledge base results.
6. When approving or rejecting, explain what will happen (e.g. "This will advance
   the workflow to the next step" or "This will reject the entire workflow run").
7. For candidate matching, use match_candidates first to get the ranked list,
   then analyze_candidate for a deep-dive on a specific person.
"""

# ---------------------------------------------------------------------------
# Agent runner
# ---------------------------------------------------------------------------


def _get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=OPENAI_CHAT_MODEL,
        api_key=OPENAI_API_KEY,
        temperature=0.1,
    )


def _load_history(conversation_id: str) -> list:
    """Load conversation history from Supabase."""
    try:
        sb = get_supabase()
        result = (
            sb.table("conversation_messages")
            .select("role, content")
            .eq("conversation_id", conversation_id)
            .order("created_at")
            .limit(20)
            .execute()
        )
        messages = []
        for m in (result.data or []):
            if m["role"] == "user":
                messages.append(HumanMessage(content=m["content"]))
            elif m["role"] == "assistant":
                messages.append(AIMessage(content=m["content"]))
        return messages
    except Exception as e:
        logger.error("Failed to load conversation history: %s", e)
        return []


def _save_message(conversation_id: str, role: str, content: str) -> None:
    """Save a message to conversation history."""
    try:
        sb = get_supabase()
        sb.table("conversation_messages").insert({
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
        }).execute()
    except Exception as e:
        logger.error("Failed to save message: %s", e)


def create_conversation() -> Optional[str]:
    """Create a new conversation and return its ID."""
    try:
        sb = get_supabase()
        result = sb.table("conversations").insert({}).execute()
        if result.data:
            return str(result.data[0]["id"])
    except Exception as e:
        logger.error("Failed to create conversation: %s", e)
    return None


async def run_agent(message: str, conversation_id: Optional[str] = None) -> tuple[str, str]:
    """Run the agent with a user message. Returns (response, conversation_id).

    If conversation_id is None, creates a new conversation.
    Loads history, appends the new message, invokes the agent, and saves the response.
    """
    # Create or validate conversation
    if not conversation_id:
        conversation_id = create_conversation()
    if not conversation_id:
        return "Sorry, I couldn't start a conversation right now. Please try again.", ""

    # Build message list
    history = _load_history(conversation_id)
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + history + [HumanMessage(content=message)]

    # Save user message
    _save_message(conversation_id, "user", message)

    # Invoke agent
    try:
        llm = _get_llm()
        llm_with_tools = llm.bind_tools(TOOLS)

        # Agent loop: keep calling until the LLM stops requesting tools
        response = await llm_with_tools.ainvoke(messages)

        # Handle tool calls iteratively
        max_iterations = 5
        iteration = 0
        while response.tool_calls and iteration < max_iterations:
            messages.append(response)

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                # Find and execute the tool
                tool_fn = next((t for t in TOOLS if t.name == tool_name), None)
                if tool_fn:
                    try:
                        result = await tool_fn.ainvoke(tool_args)
                    except Exception as e:
                        logger.error("Tool %s failed: %s", tool_name, e)
                        result = f"Tool error: {e}"
                else:
                    result = f"Unknown tool: {tool_name}"

                from langchain_core.messages import ToolMessage
                messages.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))

            response = await llm_with_tools.ainvoke(messages)
            iteration += 1

        answer = response.content or "I'm not sure how to help with that. Could you rephrase?"

        # Save assistant response
        _save_message(conversation_id, "assistant", answer)

        return answer, conversation_id

    except Exception as e:
        logger.error("Agent invocation failed: %s", e)
        error_msg = "Sorry, I'm having trouble processing your request right now. Please try again."
        _save_message(conversation_id, "assistant", error_msg)
        return error_msg, conversation_id
