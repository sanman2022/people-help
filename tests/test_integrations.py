"""Tests for mock Workday and Greenhouse integrations (no external deps)."""

from services.integrations import (
    greenhouse_get_candidate,
    greenhouse_get_req,
    greenhouse_list_candidates,
    greenhouse_list_reqs,
    workday_get_employee,
    workday_lookup_employee,
    workday_org_chart,
)


# ---------------------------------------------------------------------------
# Workday — employee lookup
# ---------------------------------------------------------------------------


class TestWorkdayLookup:
    def test_search_by_name(self):
        results = workday_lookup_employee("alice")
        assert len(results) == 1
        assert results[0]["name"] == "Alice Chen"
        assert results[0]["employee_id"] == "WD-1001"

    def test_search_by_email(self):
        results = workday_lookup_employee("bob.martinez@company.com")
        assert len(results) == 1
        assert results[0]["name"] == "Bob Martinez"

    def test_search_by_id(self):
        results = workday_lookup_employee("WD-1003")
        assert len(results) == 1
        assert results[0]["title"] == "VP of Engineering"

    def test_search_case_insensitive(self):
        results = workday_lookup_employee("ALICE")
        assert len(results) == 1

    def test_search_no_match(self):
        results = workday_lookup_employee("zzz-nonexistent")
        assert results == []

    def test_search_partial_match(self):
        results = workday_lookup_employee("mar")  # matches Bob Martinez
        assert any(e["name"] == "Bob Martinez" for e in results)

    def test_get_employee_by_id(self):
        emp = workday_get_employee("WD-1004")
        assert emp is not None
        assert emp["name"] == "Diana Lee"
        assert emp["title"] == "Chief People Officer"

    def test_get_employee_not_found(self):
        emp = workday_get_employee("WD-9999")
        assert emp is None


# ---------------------------------------------------------------------------
# Workday — org chart
# ---------------------------------------------------------------------------


class TestWorkdayOrgChart:
    def test_org_chart_with_manager_chain(self):
        result = workday_org_chart("WD-1001")  # Alice → Bob → Carol → Diana
        assert "error" not in result
        assert result["employee"]["name"] == "Alice Chen"
        chain = result["manager_chain"]
        assert len(chain) >= 2
        assert chain[0]["name"] == "Bob Martinez"  # direct manager

    def test_org_chart_with_direct_reports(self):
        result = workday_org_chart("WD-1002")  # Bob manages Alice and Julia
        assert "error" not in result
        reports = result["direct_reports"]
        report_names = {r["name"] for r in reports}
        assert "Alice Chen" in report_names
        assert "Julia Torres" in report_names

    def test_org_chart_top_level(self):
        result = workday_org_chart("WD-1004")  # Diana — no manager
        assert "error" not in result
        assert result["manager_chain"] == []
        assert len(result["direct_reports"]) > 0

    def test_org_chart_not_found(self):
        result = workday_org_chart("WD-9999")
        assert "error" in result


# ---------------------------------------------------------------------------
# Greenhouse — requisitions
# ---------------------------------------------------------------------------


class TestGreenhouseRequisitions:
    def test_list_all_reqs(self):
        reqs = greenhouse_list_reqs()
        assert len(reqs) == 4

    def test_list_open_reqs(self):
        reqs = greenhouse_list_reqs("open")
        assert all(r["status"] == "open" for r in reqs)
        assert len(reqs) == 3

    def test_list_closed_reqs(self):
        reqs = greenhouse_list_reqs("closed")
        assert len(reqs) == 1
        assert reqs[0]["req_id"] == "GH-404"

    def test_get_req_detail(self):
        req = greenhouse_get_req("GH-401")
        assert req is not None
        assert req["title"] == "Senior Backend Engineer"
        assert req["hiring_manager"] == "Bob Martinez"

    def test_get_req_not_found(self):
        req = greenhouse_get_req("GH-999")
        assert req is None


# ---------------------------------------------------------------------------
# Greenhouse — candidates
# ---------------------------------------------------------------------------


class TestGreenhouseCandidates:
    def test_list_candidates_for_req(self):
        candidates = greenhouse_list_candidates("GH-401")
        assert len(candidates) == 3
        stages = {c["stage"] for c in candidates}
        assert "Offer" in stages

    def test_list_candidates_closed_req(self):
        candidates = greenhouse_list_candidates("GH-404")
        assert len(candidates) == 3
        hired = [c for c in candidates if c["stage"] == "Hired"]
        assert len(hired) == 1

    def test_candidate_has_rating(self):
        candidates = greenhouse_list_candidates("GH-401")
        for c in candidates:
            assert 1 <= c["rating"] <= 5

    def test_candidate_has_enriched_data(self):
        """Verify candidates have enriched profiles (Phase 7)."""
        candidates = greenhouse_list_candidates("GH-401")
        for c in candidates:
            assert "skills" in c
            assert isinstance(c["skills"], list)
            assert len(c["skills"]) > 0
            assert "resume_summary" in c
            assert len(c["resume_summary"]) > 50
            assert "experience_years" in c
            assert "current_company" in c
            assert "education" in c


# ---------------------------------------------------------------------------
# Greenhouse — individual candidate lookup
# ---------------------------------------------------------------------------


class TestGreenhouseCandidateDetail:
    def test_get_candidate_by_id(self):
        candidate = greenhouse_get_candidate("C-202")
        assert candidate is not None
        assert candidate["name"] == "Mia Garcia"
        assert candidate["current_company"] == "Airbnb"

    def test_get_candidate_not_found(self):
        candidate = greenhouse_get_candidate("C-999")
        assert candidate is None

    def test_candidate_has_skills(self):
        candidate = greenhouse_get_candidate("C-201")
        assert "Python" in candidate["skills"]
        assert candidate["experience_years"] == 6


# ---------------------------------------------------------------------------
# Requisitions — enriched data
# ---------------------------------------------------------------------------


class TestRequisitionEnrichedData:
    def test_req_has_requirements(self):
        req = greenhouse_get_req("GH-401")
        assert "requirements" in req
        assert "Python" in req["requirements"]
        assert "description" in req
        assert len(req["description"]) > 50

    def test_req_has_nice_to_have(self):
        req = greenhouse_get_req("GH-401")
        assert "nice_to_have" in req
        assert isinstance(req["nice_to_have"], list)

    def test_req_has_experience_min(self):
        req = greenhouse_get_req("GH-401")
        assert "experience_min" in req
        assert req["experience_min"] == 5
