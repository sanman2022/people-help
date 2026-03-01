"""Tests for candidate intelligence — text building and cosine similarity (no API calls)."""

from services.candidate_intelligence import (
    _build_candidate_text,
    _build_req_text,
    _cosine_similarity,
)
from services.integrations import greenhouse_get_candidate, greenhouse_get_req


class TestBuildTexts:
    """Test text representation building for embeddings."""

    def test_build_req_text(self):
        req = greenhouse_get_req("GH-401")
        text = _build_req_text(req)
        assert "Senior Backend Engineer" in text
        assert "Python" in text
        assert "FastAPI or Django" in text
        assert "5 years" in text

    def test_build_candidate_text(self):
        cand = greenhouse_get_candidate("C-202")
        text = _build_candidate_text(cand)
        assert "Mia Garcia" in text
        assert "Airbnb" in text
        assert "FastAPI" in text
        assert "8 years" in text

    def test_build_req_text_with_missing_fields(self):
        """Handles reqs with minimal fields gracefully."""
        minimal_req = {"title": "Test", "department": "Eng", "req_id": "T-1"}
        text = _build_req_text(minimal_req)
        assert "Test" in text
        assert "Eng" in text


class TestCosineSimilarity:
    """Test cosine similarity computation."""

    def test_identical_vectors(self):
        v = [1.0, 2.0, 3.0]
        assert abs(_cosine_similarity(v, v) - 1.0) < 0.001

    def test_orthogonal_vectors(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert abs(_cosine_similarity(a, b)) < 0.001

    def test_opposite_vectors(self):
        a = [1.0, 2.0]
        b = [-1.0, -2.0]
        assert abs(_cosine_similarity(a, b) - (-1.0)) < 0.001

    def test_similar_vectors(self):
        a = [1.0, 2.0, 3.0]
        b = [1.1, 2.1, 3.1]
        similarity = _cosine_similarity(a, b)
        assert similarity > 0.99  # Very similar

    def test_zero_vector(self):
        a = [0.0, 0.0]
        b = [1.0, 2.0]
        assert _cosine_similarity(a, b) == 0.0

    def test_high_dimensional(self):
        """Works with embedding-sized vectors."""
        import random
        random.seed(42)
        a = [random.random() for _ in range(1536)]
        b = [random.random() for _ in range(1536)]
        similarity = _cosine_similarity(a, b)
        assert 0.0 < similarity < 1.0


class TestCandidateDataIntegrity:
    """Verify enriched candidate data is consistent across all reqs."""

    def test_all_candidates_have_required_fields(self):
        from services.integrations import MOCK_CANDIDATES
        required = {"candidate_id", "name", "req_id", "stage", "rating",
                     "skills", "resume_summary", "experience_years",
                     "current_company", "education"}
        for c in MOCK_CANDIDATES:
            missing = required - set(c.keys())
            assert not missing, f"Candidate {c['candidate_id']} missing: {missing}"

    def test_all_reqs_have_required_fields(self):
        from services.integrations import MOCK_REQUISITIONS
        required = {"req_id", "title", "department", "location", "hiring_manager",
                     "status", "candidates", "description", "requirements"}
        for r in MOCK_REQUISITIONS:
            missing = required - set(r.keys())
            assert not missing, f"Req {r['req_id']} missing: {missing}"

    def test_candidate_counts_match(self):
        """Verify the 'candidates' count on each req matches actual candidates."""
        from services.integrations import MOCK_CANDIDATES, MOCK_REQUISITIONS
        for req in MOCK_REQUISITIONS:
            actual = len([c for c in MOCK_CANDIDATES if c["req_id"] == req["req_id"]])
            assert actual == req["candidates"], (
                f"Req {req['req_id']}: listed {req['candidates']} candidates but found {actual}"
            )

    def test_every_req_has_candidates(self):
        """Every req (including closed) has at least one candidate."""
        from services.integrations import MOCK_CANDIDATES, MOCK_REQUISITIONS
        for req in MOCK_REQUISITIONS:
            cands = [c for c in MOCK_CANDIDATES if c["req_id"] == req["req_id"]]
            assert len(cands) > 0, f"Req {req['req_id']} has no candidates"
