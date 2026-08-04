"""Helpers for the Gemini assistant page."""

from __future__ import annotations

import json
import os
import re
from datetime import date, timedelta
from typing import Any

from database.database import (
    get_cash_flow_monthly_totals,
    get_cash_flow_records,
    get_budgets,
    get_categories,
    get_category_spending_by_date_range,
    get_dashboard_summary,
    get_transactions_for_rag,
)

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

SYSTEM_PROMPT = """
You are a careful personal finance assistant for a local-first budgeting app.

Rules:
- Use only the finance context provided below, including the retrieved SQLite records.
- The finance context may include cash flow records for income, bills, and savings.
- Do not invent transactions, categories, or budget values.
- For spending questions, treat negative amounts as spending and positive amounts as income or transfers.
- If the data is insufficient to answer exactly, say so clearly.
- Keep the answer concise, practical, and specific.
- Write in plain, natural, conversational sentences, like you're talking to a person.
- Do not use markdown, bullet points, asterisks, hashes, or other formatting symbols.
- Always write in complete sentences and make sure your response ends on a finished sentence.
""".strip()

STOP_WORDS = {
    "a",
    "about",
    "after",
    "all",
    "and",
    "any",
    "are",
    "around",
    "at",
    "before",
    "between",
    "but",
    "category",
    "categories",
    "current",
    "day",
    "days",
    "date",
    "dates",
    "did",
    "do",
    "does",
    "find",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "last",
    "me",
    "much",
    "many",
    "month",
    "months",
    "overall",
    "on",
    "or",
    "recent",
    "specific",
    "show",
    "spending",
    "spend",
    "spent",
    "time",
    "total",
    "the",
    "this",
    "transaction",
    "transactions",
    "your",
    "to",
    "today",
    "week",
    "weeks",
    "what",
    "when",
    "where",
    "which",
    "with",
    "yesterday",
    "year",
    "years",
}


def build_finance_context(question: str) -> dict[str, Any]:
    """Return a compact finance snapshot plus relevant SQLite retrieval results."""
    question = question.strip()
    start_date, end_date, date_label = infer_date_range(question)
    category_matches = find_matching_categories(question)
    search_terms = extract_search_terms(question)
    cash_flow_sections = infer_cash_flow_sections(question)

    summary = get_dashboard_summary(start_date=start_date, end_date=end_date)
    category_spending = get_category_spending_by_date_range(start_date=start_date, end_date=end_date)
    budgets = get_budgets()

    if category_matches:
        category_ids = [category["id"] for category in category_matches]
        relevant_budgets = [
            budget
            for budget in budgets
            if budget[3] in category_ids
        ]
    else:
        category_ids = []
        relevant_budgets = budgets

    relevant_transactions = get_transactions_for_rag(
        search_terms=search_terms or None,
        category_ids=category_ids or None,
        start_date=start_date,
        end_date=end_date,
        limit=25,
    )

    if not relevant_transactions:
        relevant_transactions = get_transactions_for_rag(
            start_date=start_date,
            end_date=end_date,
            limit=15,
        )

    cash_flow_context = {}
    for section_type in cash_flow_sections:
        records = get_cash_flow_records(section_type)
        cash_flow_context[section_type] = {
            "monthly_totals": [
                {
                    "month": month_key,
                    "total": float(total_amount),
                }
                for month_key, total_amount in get_cash_flow_monthly_totals(section_type)
            ],
            "recent_records": [
                {
                    "id": record[0],
                    "type": record[2],
                    "label": record[3],
                    "amount": float(record[4]),
                    "start_date": record[5],
                    "end_date": record[6],
                    "frequency": record[7],
                    "created_at": record[8],
                }
                for record in records[:15]
            ],
        }

    return {
        "retrieval": {
            "date_range": {
                "label": date_label,
                "start_date": start_date,
                "end_date": end_date,
            },
            "search_terms": search_terms,
            "matched_categories": category_matches,
        },
        "summary": {
            "transaction_count": int(summary["transaction_count"]),
            "total_income": float(summary["total_income"]),
            "total_spending": float(summary["total_spending"]),
            "net": float(summary["net"]),
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
            for budget in relevant_budgets
        ],
        "transactions": [
            {
                "id": transaction[0],
                "date": transaction[1],
                "merchant": transaction[2],
                "amount": float(transaction[3]),
                "category_id": transaction[4],
                "notes": transaction[5],
                "category": transaction[6],
            }
            for transaction in relevant_transactions
        ],
        "cash_flow": cash_flow_context,
        "question_focus": question.strip(),
    }


def normalize_question(question: str) -> str:
    """Normalize a question for lightweight keyword matching."""
    return re.sub(r"[^a-z0-9]+", " ", question.lower()).strip()


def extract_search_terms(question: str) -> list[str]:
    """Extract lightweight retrieval terms from a question."""
    normalized_question = normalize_question(question)
    terms = []
    seen_terms = set()

    for token in normalized_question.split():
        if len(token) < 3:
            continue
        if token in STOP_WORDS:
            continue
        if token.isdigit():
            continue
        if token not in seen_terms:
            seen_terms.add(token)
            terms.append(token)

    return terms


def infer_date_range(question: str) -> tuple[str | None, str | None, str]:
    """Infer a useful date range from the user's question."""
    normalized_question = normalize_question(question)
    today = date.today()

    if "today" in normalized_question:
        return today.isoformat(), today.isoformat(), "today"

    if "yesterday" in normalized_question:
        yesterday = today - timedelta(days=1)
        return yesterday.isoformat(), yesterday.isoformat(), "yesterday"

    if "last 7 days" in normalized_question or "past 7 days" in normalized_question:
        start_date = today - timedelta(days=6)
        return start_date.isoformat(), today.isoformat(), "last 7 days"

    if "this week" in normalized_question:
        start_date = today - timedelta(days=today.weekday())
        return start_date.isoformat(), today.isoformat(), "this week"

    if "last week" in normalized_question:
        this_week_start = today - timedelta(days=today.weekday())
        last_week_end = this_week_start - timedelta(days=1)
        last_week_start = last_week_end - timedelta(days=6)
        return last_week_start.isoformat(), last_week_end.isoformat(), "last week"

    if "last month" in normalized_question:
        current_month_start = today.replace(day=1)
        last_month_end = current_month_start - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        return last_month_start.isoformat(), last_month_end.isoformat(), "last month"

    if "this month" in normalized_question or "current month" in normalized_question:
        current_month_start = today.replace(day=1)
        return current_month_start.isoformat(), today.isoformat(), "this month"

    if "all time" in normalized_question:
        return None, None, "all time"

    return None, None, "all time"


def find_matching_categories(question: str) -> list[dict[str, Any]]:
    """Return categories whose names appear in the question."""
    normalized_question = normalize_question(question)
    question_terms = set(normalized_question.split())
    matched_categories = []

    for category_id, category_name in get_categories():
        normalized_category = normalize_question(category_name)

        if not normalized_category:
            continue

        category_terms = normalized_category.split()

        if normalized_category in normalized_question or any(
            len(category_term) >= 4 and category_term in normalized_question
            for category_term in category_terms
        ) or any(category_term in question_terms for category_term in category_terms):
            matched_categories.append(
                {
                    "id": category_id,
                    "name": category_name,
                }
            )

    return matched_categories


def infer_cash_flow_sections(question: str) -> list[str]:
    """Return the cash-flow sections that are most relevant to the question."""
    normalized_question = normalize_question(question)

    section_keywords = {
        "income": ["income", "salary", "wage", "paycheck", "pay", "revenue", "job"],
        "bills": ["bill", "bills", "rent", "utilities", "utility", "power", "water", "internet", "phone"],
        "savings": ["saving", "savings", "investment", "investments", "invest", "emergency fund", "contribution"],
    }

    matched_sections = []
    for section_type, keywords in section_keywords.items():
        if any(keyword in normalized_question for keyword in keywords):
            matched_sections.append(section_type)

    if matched_sections:
        return matched_sections

    return ["income", "bills", "savings"]


def format_finance_context(finance_context: dict[str, Any]) -> str:
    """Serialize finance context for the prompt."""
    return json.dumps(finance_context, indent=2, ensure_ascii=False)


SENTENCE_END_CHARACTERS = (".", "!", "?", '"', "'")


def clean_answer_text(answer: str) -> str:
    """Strip markdown symbols and trim any dangling, unfinished final sentence."""
    text = answer.strip()

    # Drop common markdown formatting characters.
    text = re.sub(r"[*_#`]+", "", text)
    # Collapse leading list markers like "- " or "1. " at line starts.
    text = re.sub(r"(?m)^\s*(?:[-•]|\d+\.)\s+", "", text)
    # Normalize excess blank lines/whitespace left behind.
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    if text and not text.endswith(SENTENCE_END_CHARACTERS):
        last_end = max(text.rfind(char) for char in SENTENCE_END_CHARACTERS)
        if last_end != -1:
            text = text[: last_end + 1].strip()

    return text


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
            max_output_tokens=1024,
        ),
    )

    answer = (getattr(response, "text", None) or "").strip()
    if not answer:
        raise RuntimeError("The model returned no text response.")

    return clean_answer_text(answer)
