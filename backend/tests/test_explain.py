"""Tests for the LLM explanation service."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.explain import (
    ExplainError,
    ExplanationResult,
    explain_discrepancies,
    _format_discrepancy,
)

SAMPLE_DISCREPANCY = {
    "discrepancy_type": "missing_payment",
    "order_id": "ORD-001",
    "payment_ref": None,
    "expected_amount": 100.0,
    "actual_amount": None,
    "difference": 100.0,
    "notes": None,
}

SAMPLE_MULTIPLE = [
    SAMPLE_DISCREPANCY,
    {
        "discrepancy_type": "amount_mismatch",
        "order_id": "ORD-002",
        "payment_ref": "TXN-002",
        "expected_amount": 250.0,
        "actual_amount": 245.0,
        "difference": -5.0,
        "notes": "Fee deduction suspected",
    },
]


def _make_openai_mock(content: dict) -> AsyncMock:
    client = AsyncMock()
    message = MagicMock()
    message.content = json.dumps(content)
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    client.chat.completions.create = AsyncMock(return_value=response)
    return client


class TestExplainDiscrepancies:
    @pytest.mark.asyncio
    async def test_successful_single_explanation(self):
        mock_client = _make_openai_mock(
            {
                "explanation": "Payment is missing.",
                "recommended_action": "Check logs.",
                "severity": "high",
                "confidence": "medium",
            }
        )
        with patch("app.services.explain._get_client", return_value=mock_client):
            result = await explain_discrepancies([SAMPLE_DISCREPANCY])
        assert isinstance(result, ExplanationResult)
        assert result.explanation == "Payment is missing."
        assert result.severity == "high"

    @pytest.mark.asyncio
    async def test_successful_multiple(self):
        mock_client = _make_openai_mock(
            {
                "explanation": "Two issues.",
                "recommended_action": "Review.",
                "severity": "medium",
                "confidence": "high",
            }
        )
        with patch("app.services.explain._get_client", return_value=mock_client):
            await explain_discrepancies(SAMPLE_MULTIPLE)
        call_args = mock_client.chat.completions.create.call_args
        user_msg = call_args.kwargs["messages"][1]["content"]
        assert "ORD-001" in user_msg
        assert "2 discrepancies" in user_msg

    @pytest.mark.asyncio
    async def test_empty_discrepancies_raises(self):
        with pytest.raises(ExplainError, match="No discrepancies provided"):
            await explain_discrepancies([])

    @pytest.mark.asyncio
    async def test_missing_api_key_raises(self):
        with patch("app.services.explain._get_client", return_value=None):
            with pytest.raises(ExplainError, match="not configured"):
                await explain_discrepancies([SAMPLE_DISCREPANCY])

    @pytest.mark.asyncio
    async def test_openai_api_error_raises(self):
        from openai import OpenAIError

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=OpenAIError("rate limit exceeded")
        )
        with patch("app.services.explain._get_client", return_value=mock_client):
            with pytest.raises(ExplainError, match="API call failed"):
                await explain_discrepancies([SAMPLE_DISCREPANCY])

    @pytest.mark.asyncio
    async def test_malformed_json_raises(self):
        mock_client = AsyncMock()
        message = MagicMock()
        message.content = "not json"
        choice = MagicMock()
        choice.message = message
        response = MagicMock()
        response.choices = [choice]
        mock_client.chat.completions.create = AsyncMock(return_value=response)
        with patch("app.services.explain._get_client", return_value=mock_client):
            with pytest.raises(ExplainError, match="malformed"):
                await explain_discrepancies([SAMPLE_DISCREPANCY])

    @pytest.mark.asyncio
    async def test_empty_response_raises(self):
        mock_client = AsyncMock()
        message = MagicMock()
        message.content = ""
        choice = MagicMock()
        choice.message = message
        response = MagicMock()
        response.choices = [choice]
        mock_client.chat.completions.create = AsyncMock(return_value=response)
        with patch("app.services.explain._get_client", return_value=mock_client):
            with pytest.raises(ExplainError, match="empty response"):
                await explain_discrepancies([SAMPLE_DISCREPANCY])

    @pytest.mark.asyncio
    async def test_schema_validation_failure_raises(self):
        mock_client = _make_openai_mock({"explanation": "Only field."})
        with patch("app.services.explain._get_client", return_value=mock_client):
            with pytest.raises(ExplainError, match="did not match"):
                await explain_discrepancies([SAMPLE_DISCREPANCY])

    @pytest.mark.asyncio
    async def test_temperature_is_low(self):
        mock_client = _make_openai_mock(
            {"explanation": "T", "recommended_action": "T", "severity": "low", "confidence": "high"}
        )
        with patch("app.services.explain._get_client", return_value=mock_client):
            await explain_discrepancies([SAMPLE_DISCREPANCY])
        assert mock_client.chat.completions.create.call_args.kwargs["temperature"] == 0.2

    @pytest.mark.asyncio
    async def test_model_is_gpt4o_mini(self):
        mock_client = _make_openai_mock(
            {"explanation": "T", "recommended_action": "T", "severity": "low", "confidence": "high"}
        )
        with patch("app.services.explain._get_client", return_value=mock_client):
            await explain_discrepancies([SAMPLE_DISCREPANCY])
        assert mock_client.chat.completions.create.call_args.kwargs["model"] == "gpt-4o-mini"


class TestFormatDiscrepancy:
    def test_basic(self):
        result = _format_discrepancy(SAMPLE_DISCREPANCY, 0)
        assert "Discrepancy #1" in result
        assert "missing_payment" in result
        assert "ORD-001" in result

    def test_with_ref_and_notes(self):
        result = _format_discrepancy(SAMPLE_MULTIPLE[1], 1)
        assert "TXN-002" in result
        assert "Fee deduction suspected" in result
