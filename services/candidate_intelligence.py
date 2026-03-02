"""Candidate Intelligence — AI-powered candidate-to-requisition matching and summarization.

Uses embeddings for similarity scoring and LLM for explanations.
Demonstrates decision-support AI for hiring managers.
"""

import logging

from config import OPENAI_CHAT_MODEL
from services.integrations import greenhouse_get_candidate, greenhouse_get_req, greenhouse_list_candidates
from services.rag import _get_openai, get_embedding

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Embedding-based match scoring
# ---------------------------------------------------------------------------


def _build_req_text(req: dict) -> str:
    """Build a text representation of a requisition for embedding."""
    parts = [
        f"Job Title: {req['title']}",
        f"Department: {req['department']}",
        f"Description: {req.get('description', '')}",
        f"Required skills: {', '.join(req.get('requirements', []))}",
        f"Nice to have: {', '.join(req.get('nice_to_have', []))}",
        f"Minimum experience: {req.get('experience_min', 0)} years",
    ]
    return "\n".join(parts)


def _build_candidate_text(candidate: dict) -> str:
    """Build a text representation of a candidate for embedding."""
    parts = [
        f"Name: {candidate['name']}",
        f"Current role: {candidate.get('current_title', 'N/A')} at {candidate.get('current_company', 'N/A')}",
        f"Experience: {candidate.get('experience_years', 0)} years",
        f"Skills: {', '.join(candidate.get('skills', []))}",
        f"Education: {candidate.get('education', 'N/A')}",
        f"Summary: {candidate.get('resume_summary', '')}",
    ]
    return "\n".join(parts)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


async def score_candidate_match(req: dict, candidate: dict) -> float:
    """Compute embedding similarity between a requisition and a candidate.
    Returns a score from 0.0 to 1.0."""
    try:
        req_text = _build_req_text(req)
        cand_text = _build_candidate_text(candidate)
        req_emb = await get_embedding(req_text)
        cand_emb = await get_embedding(cand_text)
        similarity = _cosine_similarity(req_emb, cand_emb)
        # Normalize from typical cosine range (0.7-0.95) to a more readable 0-100 scale
        normalized = max(0.0, min(1.0, (similarity - 0.65) / 0.30))
        return round(normalized, 3)
    except Exception as e:
        logger.error("Failed to score candidate %s: %s", candidate.get("candidate_id"), e)
        return 0.0


# ---------------------------------------------------------------------------
# LLM-based analysis
# ---------------------------------------------------------------------------


async def analyze_candidate_fit(req: dict, candidate: dict) -> dict:
    """Use LLM to analyze a candidate's fit for a requisition.
    Returns {score, strengths, gaps, recommendation}."""
    try:
        client = _get_openai()
        req_text = _build_req_text(req)
        cand_text = _build_candidate_text(candidate)

        prompt = f"""Analyze this candidate's fit for the job requisition.

REQUISITION:
{req_text}

CANDIDATE:
{cand_text}

Respond in this exact JSON format (no markdown):
{{
  "match_score": <number 1-100>,
  "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
  "gaps": ["<gap 1>", "<gap 2>"],
  "recommendation": "<one sentence: Strong Match / Good Match / Moderate Match / Weak Match with brief reason>"
}}"""

        r = await client.chat.completions.create(
            model=OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert technical recruiter analyzing candidate fit. Be objective and concise."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=300,
            temperature=0.2,
        )
        import json
        raw = (r.choices[0].message.content or "").strip()
        # Handle potential markdown code blocks
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return json.loads(raw)
    except Exception as e:
        logger.error("Failed to analyze candidate %s: %s", candidate.get("candidate_id"), e)
        return {
            "match_score": 0,
            "strengths": [],
            "gaps": ["Analysis unavailable"],
            "recommendation": "Unable to analyze — please review manually.",
        }


# ---------------------------------------------------------------------------
# High-level functions (used by agent tools and API)
# ---------------------------------------------------------------------------


async def rank_candidates_for_req(req_id: str) -> dict:
    """Rank all candidates for a requisition using embedding similarity.
    Returns {req, ranked_candidates: [{candidate, match_score}]}."""
    req = greenhouse_get_req(req_id)
    if not req:
        return {"error": f"Requisition {req_id} not found."}

    candidates = greenhouse_list_candidates(req_id)
    if not candidates:
        return {"error": f"No candidates found for {req_id}."}

    scored = []
    for cand in candidates:
        # Use pre-seeded demo scores when available (fast, deterministic);
        # fall back to live embedding scoring otherwise.
        if "demo_match_pct" in cand:
            score = cand["demo_match_pct"] / 100.0
        else:
            score = await score_candidate_match(req, cand)
        scored.append({
            "candidate": cand,
            "match_score": score,
            "match_pct": int(score * 100),
        })

    # Sort by score descending
    scored.sort(key=lambda x: x["match_score"], reverse=True)

    return {
        "req_id": req_id,
        "req_title": req["title"],
        "ranked_candidates": scored,
    }


async def get_candidate_analysis(req_id: str, candidate_id: str) -> dict:
    """Get detailed AI analysis of a candidate's fit for a specific requisition.
    Returns {candidate, req, analysis: {score, strengths, gaps, recommendation}}."""
    req = greenhouse_get_req(req_id)
    if not req:
        return {"error": f"Requisition {req_id} not found."}

    candidate = greenhouse_get_candidate(candidate_id)
    if not candidate:
        return {"error": f"Candidate {candidate_id} not found."}

    if candidate["req_id"] != req_id:
        return {"error": f"Candidate {candidate_id} is not applied to {req_id}."}

    analysis = await analyze_candidate_fit(req, candidate)
    embed_score = await score_candidate_match(req, candidate)

    return {
        "candidate": candidate,
        "requisition": {"req_id": req["req_id"], "title": req["title"]},
        "analysis": analysis,
        "embedding_similarity": round(embed_score, 3),
    }
