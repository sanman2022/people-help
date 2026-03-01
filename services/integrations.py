"""Mock integrations — Workday, Greenhouse, and connector health tracking."""

import logging
from datetime import datetime, timezone

from services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mock Workday data — employee profiles & org chart
# ---------------------------------------------------------------------------

MOCK_EMPLOYEES = [
    {
        "employee_id": "WD-1001",
        "name": "Alice Chen",
        "email": "alice.chen@company.com",
        "title": "Senior Software Engineer",
        "department": "Engineering",
        "manager": "Bob Martinez",
        "location": "San Francisco, CA",
        "start_date": "2022-03-15",
        "status": "active",
    },
    {
        "employee_id": "WD-1002",
        "name": "Bob Martinez",
        "email": "bob.martinez@company.com",
        "title": "Engineering Manager",
        "department": "Engineering",
        "manager": "Carol Williams",
        "location": "San Francisco, CA",
        "start_date": "2020-01-10",
        "status": "active",
    },
    {
        "employee_id": "WD-1003",
        "name": "Carol Williams",
        "email": "carol.williams@company.com",
        "title": "VP of Engineering",
        "department": "Engineering",
        "manager": "Diana Lee",
        "location": "New York, NY",
        "start_date": "2019-06-01",
        "status": "active",
    },
    {
        "employee_id": "WD-1004",
        "name": "Diana Lee",
        "email": "diana.lee@company.com",
        "title": "Chief People Officer",
        "department": "People",
        "manager": None,
        "location": "San Francisco, CA",
        "start_date": "2018-11-20",
        "status": "active",
    },
    {
        "employee_id": "WD-1005",
        "name": "Ethan Park",
        "email": "ethan.park@company.com",
        "title": "Recruiter",
        "department": "People",
        "manager": "Diana Lee",
        "location": "Austin, TX",
        "start_date": "2023-02-01",
        "status": "active",
    },
    {
        "employee_id": "WD-1006",
        "name": "Fatima Ahmed",
        "email": "fatima.ahmed@company.com",
        "title": "IT Support Specialist",
        "department": "IT",
        "manager": "George Kim",
        "location": "San Francisco, CA",
        "start_date": "2023-08-14",
        "status": "active",
    },
    {
        "employee_id": "WD-1007",
        "name": "George Kim",
        "email": "george.kim@company.com",
        "title": "IT Director",
        "department": "IT",
        "manager": "Carol Williams",
        "location": "San Francisco, CA",
        "start_date": "2021-04-05",
        "status": "active",
    },
    {
        "employee_id": "WD-1008",
        "name": "Hannah Nguyen",
        "email": "hannah.nguyen@company.com",
        "title": "Finance Analyst",
        "department": "Finance",
        "manager": "Isaac Brown",
        "location": "New York, NY",
        "start_date": "2024-01-08",
        "status": "active",
    },
    {
        "employee_id": "WD-1009",
        "name": "Isaac Brown",
        "email": "isaac.brown@company.com",
        "title": "Finance Director",
        "department": "Finance",
        "manager": "Diana Lee",
        "location": "New York, NY",
        "start_date": "2020-09-01",
        "status": "active",
    },
    {
        "employee_id": "WD-1010",
        "name": "Julia Torres",
        "email": "julia.torres@company.com",
        "title": "Product Designer",
        "department": "Design",
        "manager": "Bob Martinez",
        "location": "Austin, TX",
        "start_date": "2023-05-22",
        "status": "active",
    },
]


def workday_lookup_employee(query: str) -> list[dict]:
    """Mock Workday: search employees by name, email, or employee_id."""
    query_lower = query.lower()
    return [
        emp for emp in MOCK_EMPLOYEES
        if query_lower in emp["name"].lower()
        or query_lower in emp["email"].lower()
        or query_lower in emp["employee_id"].lower()
    ]


def workday_get_employee(employee_id: str) -> dict | None:
    """Mock Workday: get single employee by ID."""
    for emp in MOCK_EMPLOYEES:
        if emp["employee_id"] == employee_id:
            return emp
    return None


def workday_org_chart(employee_id: str) -> dict:
    """Mock Workday: get org chart for an employee (manager chain + direct reports)."""
    employee = workday_get_employee(employee_id)
    if not employee:
        return {"error": f"Employee {employee_id} not found"}

    # Find manager chain
    chain = []
    current = employee
    while current and current.get("manager"):
        manager = next((e for e in MOCK_EMPLOYEES if e["name"] == current["manager"]), None)
        if manager:
            chain.append({"name": manager["name"], "title": manager["title"], "employee_id": manager["employee_id"]})
            current = manager
        else:
            break

    # Find direct reports
    reports = [
        {"name": e["name"], "title": e["title"], "employee_id": e["employee_id"]}
        for e in MOCK_EMPLOYEES
        if e.get("manager") == employee["name"]
    ]

    return {
        "employee": {"name": employee["name"], "title": employee["title"], "employee_id": employee["employee_id"]},
        "manager_chain": chain,
        "direct_reports": reports,
    }


# ---------------------------------------------------------------------------
# Mock Greenhouse data — open requisitions & candidates
# ---------------------------------------------------------------------------

MOCK_REQUISITIONS = [
    {
        "req_id": "GH-401",
        "title": "Senior Backend Engineer",
        "department": "Engineering",
        "location": "San Francisco, CA",
        "hiring_manager": "Bob Martinez",
        "status": "open",
        "candidates": 3,
        "created_date": "2025-12-01",
        "description": "We are looking for a Senior Backend Engineer to design and build scalable APIs and data pipelines. You will work closely with the product and infrastructure teams to ship features that handle millions of requests per day.",
        "requirements": ["Python", "FastAPI or Django", "PostgreSQL", "Redis", "Docker", "CI/CD", "REST API design", "system design"],
        "nice_to_have": ["Kubernetes", "AWS/GCP", "GraphQL", "event-driven architecture"],
        "experience_min": 5,
    },
    {
        "req_id": "GH-402",
        "title": "Product Designer",
        "department": "Design",
        "location": "Remote",
        "hiring_manager": "Bob Martinez",
        "status": "open",
        "candidates": 3,
        "created_date": "2026-01-15",
        "description": "Join our Design team to craft intuitive, accessible user experiences for internal tools and employee-facing products. You will own end-to-end design from research through pixel-perfect handoff.",
        "requirements": ["Figma", "user research", "interaction design", "design systems", "prototyping", "accessibility (WCAG)"],
        "nice_to_have": ["motion design", "HTML/CSS", "data visualization", "Framer"],
        "experience_min": 3,
    },
    {
        "req_id": "GH-403",
        "title": "HR Business Partner",
        "department": "People",
        "location": "New York, NY",
        "hiring_manager": "Diana Lee",
        "status": "open",
        "candidates": 3,
        "created_date": "2026-02-01",
        "description": "Partner with business leaders to align people strategy with organizational goals. You will drive talent initiatives, performance management, and organizational design across multiple functions.",
        "requirements": ["HR business partnering", "performance management", "organizational design", "employee relations", "data-driven HR", "Workday"],
        "nice_to_have": ["change management", "M&A integration", "DEI programs", "people analytics"],
        "experience_min": 6,
    },
    {
        "req_id": "GH-404",
        "title": "Data Analyst",
        "department": "Finance",
        "location": "New York, NY",
        "hiring_manager": "Isaac Brown",
        "status": "closed",
        "candidates": 3,
        "created_date": "2025-10-10",
        "description": "Analyze financial data, build dashboards, and generate actionable insights for the Finance team. Work with stakeholders to translate business questions into data models.",
        "requirements": ["SQL", "Python", "Tableau or Looker", "financial modeling", "data storytelling"],
        "nice_to_have": ["dbt", "Snowflake", "Airflow", "statistical modeling"],
        "experience_min": 2,
    },
]

MOCK_CANDIDATES = [
    # GH-401 — Senior Backend Engineer
    {
        "candidate_id": "C-201",
        "name": "Liam Johnson",
        "req_id": "GH-401",
        "stage": "On-site Interview",
        "rating": 4,
        "email": "liam.johnson@email.com",
        "current_company": "Stripe",
        "current_title": "Backend Engineer",
        "experience_years": 6,
        "education": "B.S. Computer Science, UC Berkeley",
        "skills": ["Python", "Go", "PostgreSQL", "Redis", "Docker", "Kubernetes", "REST API design", "microservices"],
        "resume_summary": "6 years building payment processing APIs at Stripe. Led migration from monolith to microservices handling 50K+ requests/sec. Strong in Python, Go, and PostgreSQL. Built real-time event pipeline with Kafka. Experienced with Docker, Kubernetes, and CI/CD pipelines on AWS.",
    },
    {
        "candidate_id": "C-202",
        "name": "Mia Garcia",
        "req_id": "GH-401",
        "stage": "Offer",
        "rating": 5,
        "email": "mia.garcia@email.com",
        "current_company": "Airbnb",
        "current_title": "Senior Software Engineer",
        "experience_years": 8,
        "education": "M.S. Computer Science, Stanford",
        "skills": ["Python", "FastAPI", "PostgreSQL", "Redis", "Docker", "AWS", "system design", "CI/CD", "GraphQL", "event-driven architecture"],
        "resume_summary": "8 years of backend experience, currently at Airbnb building internal platform APIs with FastAPI and PostgreSQL. Designed the payments reconciliation service processing $2B+ annually. Expert in system design, event-driven architecture, and distributed systems. Previously at Google working on Cloud APIs.",
    },
    {
        "candidate_id": "C-203",
        "name": "Noah Smith",
        "req_id": "GH-401",
        "stage": "Phone Screen",
        "rating": 3,
        "email": "noah.smith@email.com",
        "current_company": "Acme Corp",
        "current_title": "Full Stack Developer",
        "experience_years": 4,
        "education": "B.S. Information Systems, NYU",
        "skills": ["JavaScript", "Node.js", "Python", "PostgreSQL", "React", "Docker", "REST APIs"],
        "resume_summary": "4 years as a full-stack developer at Acme Corp. Primarily focused on Node.js and React but has some Python experience. Built internal CRUD APIs and admin dashboards. Transitioning to backend-focused roles. Familiar with Docker but limited experience with CI/CD and system design at scale.",
    },

    # GH-402 — Product Designer
    {
        "candidate_id": "C-204",
        "name": "Olivia Davis",
        "req_id": "GH-402",
        "stage": "Portfolio Review",
        "rating": 4,
        "email": "olivia.davis@email.com",
        "current_company": "Spotify",
        "current_title": "Senior Product Designer",
        "experience_years": 5,
        "education": "BFA Graphic Design, RISD",
        "skills": ["Figma", "user research", "interaction design", "design systems", "prototyping", "accessibility (WCAG)", "motion design"],
        "resume_summary": "5 years designing consumer and internal tools at Spotify. Led redesign of creator analytics dashboard used by 1M+ artists. Expert in Figma, built Spotify's internal design system. Strong user research skills — ran 40+ usability studies. Passionate about accessibility; certified WCAG specialist.",
    },
    {
        "candidate_id": "C-205",
        "name": "Parker Wilson",
        "req_id": "GH-402",
        "stage": "On-site Interview",
        "rating": 4,
        "email": "parker.wilson@email.com",
        "current_company": "Meta",
        "current_title": "Product Designer",
        "experience_years": 4,
        "education": "M.Des. Interaction Design, CMU",
        "skills": ["Figma", "user research", "interaction design", "prototyping", "data visualization", "HTML/CSS", "Framer"],
        "resume_summary": "4 years designing enterprise tools at Meta. Designed the internal HR portal used by 80K+ employees. Strong in data visualization and prototyping. Proficient in HTML/CSS for dev handoff. Built interactive Framer prototypes for stakeholder demos. Experience with design systems and component libraries.",
    },
    {
        "candidate_id": "C-208",
        "name": "Sophia Martinez",
        "req_id": "GH-402",
        "stage": "Recruiter Screen",
        "rating": 3,
        "email": "sophia.martinez@email.com",
        "current_company": "Freelance",
        "current_title": "UX Designer",
        "experience_years": 3,
        "education": "B.A. Psychology, UCLA",
        "skills": ["Figma", "Sketch", "user research", "wireframing", "prototyping"],
        "resume_summary": "3 years of freelance UX design for small startups. Strong user research background from psychology degree. Experienced with Figma and Sketch. Primarily focused on mobile app design. Limited experience with design systems and accessibility. Portfolio shows consumer-focused work, no enterprise or internal tools experience.",
    },

    # GH-403 — HR Business Partner
    {
        "candidate_id": "C-206",
        "name": "Quinn Taylor",
        "req_id": "GH-403",
        "stage": "Phone Screen",
        "rating": 3,
        "email": "quinn.taylor@email.com",
        "current_company": "Deloitte",
        "current_title": "HR Consultant",
        "experience_years": 5,
        "education": "MBA, Wharton",
        "skills": ["HR consulting", "organizational design", "change management", "data-driven HR", "performance management"],
        "resume_summary": "5 years as an HR consultant at Deloitte advising Fortune 500 companies on org restructuring and performance management. Strong analytical skills and data-driven approach to people strategy. MBA from Wharton with HR concentration. Limited hands-on HRBP experience — mostly advisory roles. No direct Workday experience.",
    },
    {
        "candidate_id": "C-207",
        "name": "Riley Anderson",
        "req_id": "GH-403",
        "stage": "Recruiter Screen",
        "rating": 2,
        "email": "riley.anderson@email.com",
        "current_company": "StartupXYZ",
        "current_title": "HR Generalist",
        "experience_years": 3,
        "education": "B.A. Human Resources, Penn State",
        "skills": ["employee relations", "recruiting", "onboarding", "HRIS basics", "benefits administration"],
        "resume_summary": "3 years as an HR generalist at a 200-person startup. Handles recruiting, onboarding, and employee relations. Familiar with basic HRIS administration. No experience with organizational design, performance management frameworks, or strategic HR business partnering. Looking to step up to a more strategic role.",
    },
    {
        "candidate_id": "C-209",
        "name": "Jordan Kim",
        "req_id": "GH-403",
        "stage": "On-site Interview",
        "rating": 5,
        "email": "jordan.kim@email.com",
        "current_company": "Netflix",
        "current_title": "Senior HR Business Partner",
        "experience_years": 8,
        "education": "M.S. Industrial/Organizational Psychology, Columbia",
        "skills": ["HR business partnering", "performance management", "organizational design", "employee relations", "people analytics", "Workday", "change management", "DEI programs"],
        "resume_summary": "8 years in progressive HRBP roles, currently at Netflix supporting Engineering and Product (500+ employees). Led implementation of new performance management framework adopted company-wide. Expert in Workday, people analytics, and organizational design. Drove DEI initiatives that improved underrepresented hiring by 35%. Previously at Google as HRBP for Cloud division.",
    },

    # GH-404 — Data Analyst (closed)
    {
        "candidate_id": "C-210",
        "name": "Alex Rivera",
        "req_id": "GH-404",
        "stage": "Hired",
        "rating": 5,
        "email": "alex.rivera@email.com",
        "current_company": "Bloomberg",
        "current_title": "Data Analyst",
        "experience_years": 3,
        "education": "M.S. Statistics, Columbia",
        "skills": ["SQL", "Python", "Tableau", "financial modeling", "data storytelling", "dbt", "Snowflake"],
        "resume_summary": "3 years analyzing financial data at Bloomberg. Built executive dashboards in Tableau tracking $500M+ in revenue. Expert SQL and Python for data transformation. Experience with dbt and Snowflake. Strong statistical modeling background from Columbia. Excellent data storytelling — presented weekly to C-suite.",
    },
    {
        "candidate_id": "C-211",
        "name": "Priya Kapoor",
        "req_id": "GH-404",
        "stage": "Rejected",
        "rating": 3,
        "email": "priya.kapoor@email.com",
        "current_company": "Deloitte",
        "current_title": "Junior Analyst",
        "experience_years": 1,
        "education": "B.S. Economics, NYU",
        "skills": ["SQL", "Excel", "Tableau", "financial analysis"],
        "resume_summary": "1 year at Deloitte in advisory analytics. Proficient in SQL and Tableau for client reporting. Strong Excel skills for financial modeling. Economics background with coursework in statistics. Looking to transition into a dedicated data analyst role.",
    },
    {
        "candidate_id": "C-212",
        "name": "Marcus Chen",
        "req_id": "GH-404",
        "stage": "Rejected",
        "rating": 4,
        "email": "marcus.chen@email.com",
        "current_company": "JPMorgan Chase",
        "current_title": "Data Analyst",
        "experience_years": 2,
        "education": "M.S. Data Science, Georgia Tech",
        "skills": ["SQL", "Python", "Looker", "financial modeling", "Snowflake", "statistical modeling"],
        "resume_summary": "2 years in financial data analytics at JPMorgan Chase. Built Looker dashboards for risk reporting. Python for ETL pipelines and statistical modeling. Snowflake experience for large-scale data warehousing. Georgia Tech data science program included ML and advanced statistics.",
    },
]


def greenhouse_get_candidate(candidate_id: str) -> dict | None:
    """Mock Greenhouse: get single candidate by ID."""
    return next((c for c in MOCK_CANDIDATES if c["candidate_id"] == candidate_id), None)


def greenhouse_list_reqs(status: str | None = None) -> list[dict]:
    """Mock Greenhouse: list requisitions, optionally filtered by status."""
    if status:
        return [r for r in MOCK_REQUISITIONS if r["status"] == status]
    return MOCK_REQUISITIONS


def greenhouse_get_req(req_id: str) -> dict | None:
    """Mock Greenhouse: get single requisition."""
    return next((r for r in MOCK_REQUISITIONS if r["req_id"] == req_id), None)


def greenhouse_list_candidates(req_id: str) -> list[dict]:
    """Mock Greenhouse: list candidates for a requisition."""
    return [c for c in MOCK_CANDIDATES if c["req_id"] == req_id]


# ---------------------------------------------------------------------------
# Webhook receiver — log incoming events
# ---------------------------------------------------------------------------


def process_webhook(source: str, payload: dict) -> str:
    """Process an incoming webhook. Logs to events table. Returns event ID."""
    try:
        sb = get_supabase()
        result = sb.table("events").insert({
            "event_type": f"webhook_{source}",
            "payload": {
                "source": source,
                "data": payload,
                "received_at": datetime.now(timezone.utc).isoformat(),
            },
        }).execute()
        event_id = str(result.data[0]["id"]) if result.data else "unknown"
        logger.info("Webhook received from %s: event %s", source, event_id)

        # Update connector last_seen
        _update_connector_health(source)

        return event_id
    except Exception as e:
        logger.error("Failed to process webhook from %s: %s", source, e)
        return ""


# ---------------------------------------------------------------------------
# Connector health tracking
# ---------------------------------------------------------------------------

DEFAULT_CONNECTORS = [
    {"name": "workday", "label": "Workday (Mock)", "type": "hris", "status": "connected"},
    {"name": "greenhouse", "label": "Greenhouse (Mock)", "type": "ats", "status": "connected"},
    {"name": "slack", "label": "Slack (Stub)", "type": "messaging", "status": "not_configured"},
    {"name": "okta", "label": "Okta (Stub)", "type": "identity", "status": "not_configured"},
]


def get_connectors() -> list[dict]:
    """Return all connectors with health status."""
    try:
        sb = get_supabase()
        result = sb.table("connectors").select("*").order("name").execute()
        connectors = result.data or []
        if not connectors:
            # Seed on first access
            for c in DEFAULT_CONNECTORS:
                sb.table("connectors").insert(c).execute()
            result = sb.table("connectors").select("*").order("name").execute()
            connectors = result.data or []
        return connectors
    except Exception as e:
        logger.error("Failed to load connectors: %s", e)
        return DEFAULT_CONNECTORS  # Fallback to in-memory defaults


def _update_connector_health(source: str) -> None:
    """Update last_event_at for a connector after receiving a webhook."""
    try:
        sb = get_supabase()
        now = datetime.now(timezone.utc).isoformat()
        sb.table("connectors").update({
            "last_event_at": now,
            "status": "connected",
        }).eq("name", source).execute()
    except Exception as e:
        logger.error("Failed to update connector health for %s: %s", source, e)
