from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from services.rag import add_feedback, answer_with_rag, ingest_document, store_question_and_feedback
from templates_ctx import templates

router = APIRouter()


@router.get("", response_class=HTMLResponse)
async def knowledge_page(request: Request):
    return templates.TemplateResponse(
        request, "knowledge.html", {"answer": None, "sources": None, "question_id": None}
    )


@router.post("/ask", response_class=HTMLResponse)
async def knowledge_ask(request: Request):
    form = await request.form()
    query = (form.get("query") or "").strip()
    if not query:
        return RedirectResponse(url="/knowledge", status_code=302)
    answer, sources = await answer_with_rag(query)
    question_id = await store_question_and_feedback(query, answer, sources)
    return templates.TemplateResponse(
        request,
        "knowledge.html",
        {"answer": answer, "sources": sources, "question_id": question_id},
    )


@router.post("/feedback", response_class=RedirectResponse)
async def knowledge_feedback(request: Request):
    form = await request.form()
    question_id = form.get("question_id") or ""
    helpful = (form.get("helpful") or "").lower() == "true"
    if question_id:
        await add_feedback(question_id, helpful)
    return RedirectResponse(url="/knowledge", status_code=302)


@router.get("/seed", response_class=RedirectResponse)
@router.post("/seed")
async def knowledge_seed(request: Request):
    """Ingest 2-3 demo policy docs so RAG has content. Call once after deploying."""
    docs = [
        {
            "title": "PTO Policy",
            "content": """Paid Time Off (PTO) is accrued based on tenure. Full-time employees receive 15 days per year in their first two years, and 20 days after two years. PTO requests should be submitted at least two weeks in advance when possible, via the HR portal. Unused PTO may be carried over up to 5 days into the next year; the rest is paid out or forfeited per local policy.""",
        },
        {
            "title": "Expense Reimbursement",
            "content": """Expense reports must be submitted within 30 days of the expense. Use the approved expense tool and attach receipts for any expense over $25. Travel and meal guidelines: economy for flights under 4 hours; meals up to $50 per day when traveling. Reimbursement is typically processed within 10 business days after approval by your manager.""",
        },
        {
            "title": "New Hire Onboarding",
            "content": """New hires complete I-9 and tax forms on or before day one. IT provides laptop and access on day one. Benefits enrollment must be completed within 30 days of start date. Your manager will schedule a team intro and first 1:1 in the first week. Ask your onboarding buddy or People Help for any questions.""",
        },
        {
            "title": "Hiring and Recruiting Policy",
            "content": """All open positions must have a requisition approved by the hiring manager and their VP before recruiting begins. Job descriptions must be reviewed by the People team for inclusive language. Interview panels must include at least one cross-functional interviewer and one member trained in structured interviewing. Candidate evaluations should use the standard scorecard with ratings on technical skills, collaboration, and culture alignment. Offers require approval from the hiring manager and the compensation team. Background checks are completed before the start date. The target time-to-fill is 45 days for standard roles and 60 days for senior/specialized roles.""",
        },
        {
            "title": "Interview Guidelines",
            "content": """All interviewers must complete unconscious bias training before conducting interviews. Use structured interview guides with consistent questions for each role. Score candidates on a 1-5 scale using the standard rubric immediately after each interview — do not discuss scores with other interviewers before submitting. Debrief sessions should be scheduled within 24 hours of the final interview round. The hiring manager makes the final decision but must document the rationale. Candidate experience matters — respond to all applicants within 5 business days and provide constructive feedback to final-round candidates who are not selected.""",
        },
        {
            "title": "Compensation Philosophy",
            "content": """We target the 65th percentile of market compensation for all roles, benchmarked annually against peer companies using Radford and Mercer data. Total compensation includes base salary, annual bonus (target 10-20% depending on level), and equity for senior roles. Salary bands are published internally for transparency. Promotions include a minimum 8% salary increase. Off-cycle adjustments require VP and People team approval. We conduct pay equity audits annually. Relocation assistance is available for roles requiring geographic moves and is determined by the People team based on distance and level.""",
        },
        {
            "title": "Performance Review Process",
            "content": """Performance reviews are conducted semi-annually in March and September. Employees complete a self-review, and managers provide written feedback with ratings on Impact, Collaboration, and Growth. Calibration sessions ensure consistency across teams. Ratings are: Exceptional, Strong, Meets Expectations, Needs Improvement, and Below Expectations. Performance Improvement Plans (PIPs) are initiated for Below Expectations ratings and last 60 days. Managers must have regular 1:1 meetings (at least bi-weekly) and should document feedback throughout the cycle, not just during review periods.""",
        },
    ]
    ids = []
    for d in docs:
        doc_id = await ingest_document(d["title"], d["content"])
        if doc_id:
            ids.append(doc_id)
    if request.method == "GET":
        return RedirectResponse(url=f"/knowledge?seed={len(ids)}", status_code=302)
    return {"ingested": len(ids), "document_ids": ids}
