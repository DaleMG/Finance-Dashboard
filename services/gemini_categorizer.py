"""Gemini-based merchant categorization helpers."""

from __future__ import annotations

import json
import os
from typing import Any

from pydantic import BaseModel, Field

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")


def normalize_text(value: str) -> str:
    """Normalize text for stable merchant matching."""
    return " ".join(str(value).strip().lower().split())


class MerchantCategoryAssignment(BaseModel):
    """A single merchant-to-category suggestion from Gemini."""

    merchant: str = Field(description="Merchant name from the input list.")
    category: str | None = Field(
        default=None,
        description="One of the provided categories, or null if none fit.",
    )


class MerchantCategoryResponse(BaseModel):
    """Structured Gemini response for merchant categorization."""

    assignments: list[MerchantCategoryAssignment]


CATEGORIZATION_PROMPT = """
You are helping categorize bank merchants for a personal finance app.

Rules:
- Choose only from the provided category names.
- If a merchant does not clearly match any category, return null for that merchant.
- Return valid JSON only.
- Return an object with an assignments array.
- Each assignment must include merchant and category.
- Include one assignment for every merchant in the input list.
""".strip()


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


def _extract_json_object(text: str) -> dict[str, Any]:
    """Extract a JSON object from Gemini text output."""
    cleaned_text = text.strip()

    if cleaned_text.startswith("```"):
        cleaned_text = cleaned_text.strip("`")
        if cleaned_text.lower().startswith("json"):
            cleaned_text = cleaned_text[4:]

    try:
        parsed_output = json.loads(cleaned_text)
        if isinstance(parsed_output, dict):
            return parsed_output
    except json.JSONDecodeError:
        pass

    start_index = cleaned_text.find("{")
    end_index = cleaned_text.rfind("}")

    if start_index != -1 and end_index != -1 and end_index > start_index:
        parsed_output = json.loads(cleaned_text[start_index : end_index + 1])
        if isinstance(parsed_output, dict):
            return parsed_output

    raise ValueError("Gemini did not return valid JSON.")


def _suggest_merchant_categories_batch(
    merchants: list[str],
    categories: list[str],
    api_key: str,
    model: str,
) -> dict[str, str | None]:
    """Ask Gemini to assign a small batch of merchants to known categories."""
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError(
            "The google-genai package is not installed. Add it to requirements.txt and run pip install -r requirements.txt."
        ) from exc

    client = genai.Client(api_key=api_key)

    prompt = "\n\n".join(
        [
            CATEGORIZATION_PROMPT,
            "Categories:",
            json.dumps(categories, ensure_ascii=False),
            "Merchants:",
            json.dumps(merchants, ensure_ascii=False),
        ]
    )

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction="Return only valid JSON.",
            max_output_tokens=2048,
            response_mime_type="application/json",
            response_schema=MerchantCategoryResponse,
            temperature=0,
        ),
    )

    parsed_output = getattr(response, "parsed", None)
    if parsed_output is None:
        raw_text = (getattr(response, "text", None) or "").strip()
        if not raw_text:
            raise RuntimeError("The model returned no text response.")
        parsed_output = MerchantCategoryResponse.model_validate_json(raw_text)

    assignments = getattr(parsed_output, "assignments", None) or []
    allowed_categories = {category.lower(): category for category in categories}
    assignment_lookup = {
        normalize_text(assignment.merchant): assignment.category
        for assignment in assignments
    }

    batch_suggestions: dict[str, str | None] = {}
    for merchant in merchants:
        suggested_category = assignment_lookup.get(normalize_text(merchant))

        if suggested_category is None:
            batch_suggestions[merchant] = None
            continue

        normalized_category = str(suggested_category).strip().lower()
        batch_suggestions[merchant] = allowed_categories.get(normalized_category)

    return batch_suggestions


def _suggest_merchant_categories_with_retry(
    merchants: list[str],
    categories: list[str],
    api_key: str,
    model: str,
) -> dict[str, str | None]:
    """Ask Gemini to categorize merchants, splitting the batch when needed."""
    if not merchants:
        return {}

    try:
        return _suggest_merchant_categories_batch(
            merchants=merchants,
            categories=categories,
            api_key=api_key,
            model=model,
        )
    except Exception:
        if len(merchants) == 1:
            return {merchants[0]: None}

        midpoint = max(len(merchants) // 2, 1)
        left_batch = merchants[:midpoint]
        right_batch = merchants[midpoint:]

        combined_suggestions: dict[str, str | None] = {}
        combined_suggestions.update(
            _suggest_merchant_categories_with_retry(
                merchants=left_batch,
                categories=categories,
                api_key=api_key,
                model=model,
            )
        )
        combined_suggestions.update(
            _suggest_merchant_categories_with_retry(
                merchants=right_batch,
                categories=categories,
                api_key=api_key,
                model=model,
            )
        )
        return combined_suggestions


def suggest_merchant_categories(
    merchants: list[str],
    categories: list[str],
    api_key: str,
    model: str = DEFAULT_MODEL,
) -> dict[str, str | None]:
    """Ask Gemini to assign merchants to known categories."""
    if not merchants:
        return {}

    suggestions: dict[str, str | None] = {}
    batch_size = 10

    for start_index in range(0, len(merchants), batch_size):
        merchant_batch = merchants[start_index : start_index + batch_size]
        batch_suggestions = _suggest_merchant_categories_with_retry(
            merchants=merchant_batch,
            categories=categories,
            api_key=api_key,
            model=model,
        )
        suggestions.update(batch_suggestions)

    return suggestions
