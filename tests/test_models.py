"""Tests for Pydantic request/response models — input validation."""

import pytest
from pydantic import ValidationError

from models import ApprovalDecisionRequest, ChatRequest, ChecklistToggleRequest


class TestChatRequest:
    def test_valid_message(self):
        req = ChatRequest(message="What is the PTO policy?")
        assert req.message == "What is the PTO policy?"
        assert req.conversation_id is None

    def test_valid_with_conversation_id(self):
        req = ChatRequest(message="Follow up", conversation_id="abc-123")
        assert req.conversation_id == "abc-123"

    def test_empty_message_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(message="")
        assert "min_length" in str(exc_info.value).lower() or "at least" in str(exc_info.value).lower()

    def test_missing_message_rejected(self):
        with pytest.raises(ValidationError):
            ChatRequest()  # type: ignore

    def test_oversized_message_rejected(self):
        with pytest.raises(ValidationError):
            ChatRequest(message="x" * 2001)

    def test_max_length_message_accepted(self):
        req = ChatRequest(message="x" * 2000)
        assert len(req.message) == 2000


class TestApprovalDecisionRequest:
    def test_valid_approved(self):
        req = ApprovalDecisionRequest(action="approved")
        assert req.action == "approved"
        assert req.decided_by == "demo_user"
        assert req.notes is None

    def test_valid_rejected_with_notes(self):
        req = ApprovalDecisionRequest(action="rejected", decided_by="admin", notes="Missing docs")
        assert req.action == "rejected"
        assert req.notes == "Missing docs"

    def test_invalid_action_rejected(self):
        with pytest.raises(ValidationError):
            ApprovalDecisionRequest(action="maybe")

    def test_blank_action_rejected(self):
        with pytest.raises(ValidationError):
            ApprovalDecisionRequest(action="")


class TestChecklistToggleRequest:
    def test_done_true(self):
        req = ChecklistToggleRequest(done=True)
        assert req.done is True

    def test_done_false(self):
        req = ChecklistToggleRequest(done=False)
        assert req.done is False

    def test_missing_done_rejected(self):
        with pytest.raises(ValidationError):
            ChecklistToggleRequest()  # type: ignore
