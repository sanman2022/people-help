"""Pydantic request/response models — input validation and API contracts."""

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    conversation_id: str | None = Field(None, description="Existing conversation ID to continue")


class ChatResponse(BaseModel):
    response: str
    conversation_id: str


# ---------------------------------------------------------------------------
# Approvals
# ---------------------------------------------------------------------------


class ApprovalDecisionRequest(BaseModel):
    action: str = Field(..., pattern="^(approved|rejected)$", description="Must be 'approved' or 'rejected'")
    decided_by: str = Field("demo_user", max_length=100)
    notes: str | None = Field(None, max_length=1000)


class ApprovalDecisionResponse(BaseModel):
    ok: bool = True
    run_status: str
    approval: dict | None = None


# ---------------------------------------------------------------------------
# Workflows
# ---------------------------------------------------------------------------


class ChecklistToggleRequest(BaseModel):
    done: bool = Field(..., description="New done state for the checklist item")


class ChecklistToggleResponse(BaseModel):
    ok: bool = True
    done: bool


# ---------------------------------------------------------------------------
# Webhooks
# ---------------------------------------------------------------------------


class WebhookResponse(BaseModel):
    ok: bool = True
    event_id: str
    source: str


# ---------------------------------------------------------------------------
# Knowledge
# ---------------------------------------------------------------------------


class SeedResponse(BaseModel):
    ingested: int
    document_ids: list[str]


# ---------------------------------------------------------------------------
# Integrations — response models
# ---------------------------------------------------------------------------


class EmployeeSearchResponse(BaseModel):
    source: str = "workday_mock"
    query: str
    results: list[dict]


class EmployeeDetailResponse(BaseModel):
    source: str = "workday_mock"
    employee: dict


class OrgChartResponse(BaseModel):
    source: str = "workday_mock"
    employee: dict
    manager_chain: list[dict]
    direct_reports: list[dict]


class RequisitionListResponse(BaseModel):
    source: str = "greenhouse_mock"
    count: int
    requisitions: list[dict]


class RequisitionDetailResponse(BaseModel):
    source: str = "greenhouse_mock"
    requisition: dict
    candidates: list[dict]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ErrorResponse(BaseModel):
    error: str
