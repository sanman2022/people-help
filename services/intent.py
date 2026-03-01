import logging

from config import OPENAI_CHAT_MODEL
from services.rag import _get_openai

logger = logging.getLogger(__name__)

INTENT_ANSWER = "answer"
INTENT_CREATE_CASE = "create_case"
INTENT_START_WORKFLOW = "start_workflow"


async def classify_intent(user_input: str) -> str:
    try:
        client = _get_openai()
        system = """You classify the user's need into exactly one of:
- answer: they are asking a question that can be answered from knowledge/policy (e.g. "What is the PTO policy?", "How do I submit expenses?")
- create_case: they want to open a case or request (e.g. "I need help with my W2", "Something's wrong with my paycheck")
- start_workflow: they are about to start a process like onboarding or they mentioned offer/accepted/new hire (e.g. "I accepted the offer", "New hire onboarding")

Reply with only one word: answer, create_case, or start_workflow."""

        r = await client.chat.completions.create(
            model=OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_input},
            ],
            max_tokens=20,
        )
        raw = (r.choices[0].message.content or "").strip().lower()
        if "create_case" in raw or "create case" in raw:
            return INTENT_CREATE_CASE
        if "start_workflow" in raw or "start workflow" in raw or "workflow" in raw:
            return INTENT_START_WORKFLOW
        return INTENT_ANSWER
    except Exception as e:
        logger.error("Intent classification failed: %s", e)
        return INTENT_ANSWER
