"""
LLM-powered discrepancy explanation service.

Calls the OpenAI API to produce plain-language explanations of discrepancies.
Uses structured output (response_format=json_schema) so the response shape
is predictable, then validates with Pydantic.

The LLM is ONLY used for explanation — it is never in the code path that
decides whether records match (see app/reconcile.py for deterministic logic).

Temperature: 0.2 — this is analytical/explanatory, not creative.  Low
temperature reduces hallucination and keeps outputs factual & consistent.

The API key is read exclusively from the OPENAI_API_KEY env var and is
never logged, cached, or returned to callers.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from openai import AsyncOpenAI, OpenAIError
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Structured output schema
# ---------------------------------------------------------------------------

EXPLANATION_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "discrepancy_explanation",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "explanation": {
                    "type": "string",
                    "description": (
                        "Plain-language explanation of what likely caused "
                        "this discrepancy, based only on the data provided."
                    ),
                },
                "recommended_action": {
                    "type": "string",
                    "description": (
                        "What someone should do to investigate or resolve "
                        "this discrepancy."
                    ),
                },
                "severity": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                },
                "confidence": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                },
            },
            "required": [
                "explanation",
                "recommended_action",
                "severity",
                "confidence",
            ],
            "additionalProperties": False,
        },
    },
}

SYSTEM_PROMPT = (
    "You are a financial reconciliation analyst. You will be given one or "
    "more discrepancies between orders and payments. For each, explain in "
    "plain language what likely happened and what someone should do about "
    "it. Base your explanation ONLY on the data provided — do not invent "
    "details. Keep responses concise and factual."
)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class ExplanationResult(BaseModel):
    """Validated explanation returned from the LLM."""

    explanation: str
    recommended_action: str
    severity: str
    confidence: str


class ExplainError(Exception):
    """Raised when explanation generation fails."""
    pass


# ---------------------------------------------------------------------------
# OpenAI client (lazy, cached)
# ---------------------------------------------------------------------------

_client: Optional[AsyncOpenAI] = None


def _get_client() -> Optional[AsyncOpenAI]:
    """Return a cached AsyncOpenAI client, or None if no key is configured."""
    global _client
    if _client is None and settings.OPENAI_API_KEY:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


def _format_discrepancy(d: dict, index: int) -> str:
    """Format a single discrepancy as a readable text block."""
    lines = [f"Discrepancy #{index + 1}:"]
    lines.append(f"  Type: {d.get('discrepancy_type', 'unknown')}")
    lines.append(f"  Order ID: {d.get('order_id', 'N/A')}")
    if d.get("payment_ref"):
        lines.append(f"  Payment Ref: {d['payment_ref']}")
    if d.get("expected_amount") is not None:
        lines.append(f"  Expected Amount: {d['expected_amount']}")
    if d.get("actual_amount") is not None:
        lines.append(f"  Actual Amount: {d['actual_amount']}")
    if d.get("difference") is not None:
        lines.append(f"  Difference: {d['difference']}")
    if d.get("notes"):
        lines.append(f"  Notes: {d['notes']}")
    return "\n".join(lines)


def _safe_error_message(error: OpenAIError) -> str:
    """Extract a safe error message without leaking sensitive details."""
    msg = str(error)
    if len(msg) > 200:
        msg = msg[:200] + "…"
    return msg


async def explain_discrepancies(
    discrepancies: list[dict],
) -> ExplanationResult:
    """Explain one or more discrepancies using the OpenAI API.

    Parameters
    ----------
    discrepancies:
        List of discrepancy dicts (as stored in the database).  Must contain
        at least one entry.

    Returns
    -------
    ExplanationResult
        Validated structured explanation.

    Raises
    ------
    ExplainError
        If the API key is missing, the call fails, or the response is
        malformed.
    """
    if not discrepancies:
        raise ExplainError("No discrepancies provided to explain.")

    client = _get_client()
    if client is None:
        raise ExplainError(
            "OpenAI API key is not configured. Set OPENAI_API_KEY in the "
            "backend environment."
        )

    # Build the user message from the discrepancy data.
    blocks = [_format_discrepancy(d, i) for i, d in enumerate(discrepancies)]
    user_content = "\n\n".join(blocks)

    if len(discrepancies) == 1:
        user_content += "\n\nExplain this discrepancy."
    else:
        user_content += (
            f"\n\nExplain each of these {len(discrepancies)} discrepancies."
        )

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            response_format=EXPLANATION_SCHEMA,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
        )
    except OpenAIError as e:
        logger.error("OpenAI API call failed: %s", _safe_error_message(e))
        raise ExplainError(
            f"OpenAI API call failed: {_safe_error_message(e)}"
        ) from e

    # Extract and parse the response content.
    content = response.choices[0].message.content
    if not content:
        raise ExplainError("OpenAI returned an empty response.")

    try:
        parsed = json.loads(content)
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(
            "OpenAI returned malformed JSON (truncated): %s",
            content[:200] if content else "<empty>",
        )
        raise ExplainError(
            "OpenAI returned a malformed response that could not be parsed."
        ) from e

    # Validate against the Pydantic schema.
    try:
        result = ExplanationResult(**parsed)
    except Exception as e:
        logger.error(
            "OpenAI response failed validation: %s | keys: %s",
            e,
            list(parsed.keys()) if isinstance(parsed, dict) else type(parsed).__name__,
        )
        raise ExplainError(
            "OpenAI returned a response that did not match the expected format."
        ) from e

    return result
