"""Helpers for the Gemini assistant page."""

from __future__ import annotations

import json
import os
from typing import Any

from database.database import get_budgets, get_category_spending, get_dashboard_summary

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

SYSTEM_PROMPT = """
You are a careful personal finance assistant for a local-first budgeting app.

Rules:
- Use only the finance context provided below.
- Do not invent transactions, categories, or budget values.
- For spending questions, treat negative amounts as spending and positive amounts as income or transfers.
- If the data is insufficient to answer exactly, say so clearly.
- Keep the answer concise, practical, and specific.
""".strip()


def build_finance_context(question: str) -> dict[str, Any]:
    """Return a compact snapshot of the current finances for the model."""
    summary = get_dashboard_summary()
    category_spending = get_category_spending()
    budgets = get_budgets()

    return {
        "summary": {
            "transaction_count": int(summary["transaction_count"]),
            "total_spending": float(summary["total_spending"]),
            "total_budget": float(summary["total_budget"]),
            "remaining_budget": float(summary["remaining_budget"]),
        },
        "category_spending": [
            {
                "category": category_name,
                "total_spending": float(total_spending),
            }
            for category_name, total_spending in category_spending
        ],
        "budgets": [
            {
                "category": budget[4],
                "budget_amount": float(budget[2]),
            }
            for budget in budgets
        ],
        "question_focus": question.strip(),
    }


def format_finance_context(finance_context: dict[str, Any]) -> str:
    """Serialize finance context for the prompt."""
    return json.dumps(finance_context, indent=2, ensure_ascii=False)


def get_gemini_api_key(secrets: Any | None = None) -> str | None:
    """Return the Gemini API key from Streamlit secrets or the environment."""
    if secrets is not None:
        try:
            if "GEMINI_API_KEY" in secrets:
                return secrets["GEMINI_API_KEY"]
            if "GOOGLE_API_KEY" in secrets:
                return secrets["GOOGLE_API_KEY"]
        except Exception:
            pass

    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def ask_gemini_assistant(
    question: str,
    finance_context: dict[str, Any],
    api_key: str | None = None,
    model: str = DEFAULT_MODEL,
) -> str:
    """Ask Gemini a finance question using the current app data."""
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError(
            "The google-genai package is not installed. Add it to requirements.txt and run pip install -r requirements.txt."
        ) from exc

    if api_key:
        client = genai.Client(api_key=api_key)
    else:
        client = genai.Client()

    prompt = "\n\n".join(
        [
            "Finance context:",
            format_finance_context(finance_context),
            "User question:",
            question.strip(),
        ]
    )

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            max_output_tokens=512,
        ),
    )

    answer = (getattr(response, "text", None) or "").strip()
    if not answer:
        raise RuntimeError("The model returned no text response.")

    return answer
