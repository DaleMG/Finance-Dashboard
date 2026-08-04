# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A personal finance and budgeting web app built with Streamlit. Users upload bank CSV statements or add transactions manually, categorize spending (with optional Gemini-powered AI assistance), set per-category budgets, and view spending via dashboards/charts. A Gemini-powered chat assistant answers finance questions using the app's own SQLite data as retrieval context.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app (entry point is home.py, not Home.py despite the README)
streamlit run home.py
```

There is no test suite, linter, or CI configuration in this repo — don't assume `pytest`/`ruff`/etc. exist.

### AI features

AI categorization and the AI Assistant page require a Gemini API key, read from (in order) `st.secrets["GEMINI_API_KEY"]`/`st.secrets["GOOGLE_API_KEY"]` (`.streamlit/secrets.toml`, gitignored) or the `GEMINI_API_KEY`/`GOOGLE_API_KEY` env vars. Model defaults to `gemini-3.6-flash`, overridable via `GEMINI_MODEL`. Without a key, those features degrade gracefully (a warning is shown) rather than crashing — preserve that behavior in any changes.

## Architecture

**Multipage Streamlit app**, wired up in `home.py`: it calls `initialize_database()` once, then declares every page in `pages/` via `st.Page` and groups them into sections with `st.navigation`. To add a page, create `pages/<name>.py` and register it in `home.py`.

**Data layer — `database/database.py`**: the only module that touches SQLite (`database/budget.db`, gitignored). Every function opens its own `sqlite3.connect()`, does its work, and closes the connection — there's no shared connection/session object or ORM. Tables: `categories`, `transactions`, `budgets` (one row per category per `month`, currently always `"default"`), `merchant_rules` (persisted merchant→category mappings used to skip re-asking the AI), `cash_flow_entries` (legacy/simple), and `cash_flow_records` (income/bills/savings entries with `section_type` + `entry_kind`, used for the monthly cash-flow totals surfaced to the AI assistant). Page code calls these functions directly rather than going through a service layer.

**Pages import three kinds of dependencies**: `database.database` for persistence, `services/*` for Gemini calls, and occasionally `components/*` for shared UI. Most business logic (CSV parsing, dedup, date-range inference, prompt building) lives directly in `pages/*.py` or `services/*.py` as module-level functions — there's no separate model/controller split.

**`services/gemini_categorizer.py`**: batches unrecognized merchants (batch size 10) to Gemini with a Pydantic response schema (`MerchantCategoryResponse`), asking it to pick from the app's existing category names only. On a batch failure it recursively bisects the batch and retries the halves rather than failing the whole import.

**`services/gemini_assistant.py`**: implements a lightweight, keyword-based RAG layer (no embeddings/vector DB) — `build_finance_context()` infers a date range and matching categories/cash-flow sections from the question's keywords, pulls a bounded set of relevant rows via `get_transactions_for_rag`, serializes everything to JSON, and sends it to Gemini alongside a system prompt that forbids inventing figures.

**`pages/upload.py`** is the most complex page: it auto-detects the CSV header row, guesses date/merchant/amount columns by keyword, normalizes amounts (`$`, commas, parens-as-negative), applies saved `merchant_rules` before falling back to AI suggestions, and de-duplicates against existing transactions using a `(date, normalized_merchant, rounded_amount)` signature (see `get_transaction_signatures`). The same signature-based dedup applies to the manual-entry table below it.

**`components/cash_flow_page.py`** (`render_cash_flow_page`, used by `pages/income.py`, `pages/bills.py`, `pages/savings.py`) currently renders a session-local editable table seeded with zeros and a Plotly bar chart — it does **not** read/write the `cash_flow_records`/`cash_flow_entries` tables that `database.database` and the AI assistant already support. Data entered there is not persisted across reruns. Know this before assuming income/bills/savings data flows through to the database or the AI assistant's cash-flow context.

Amounts are stored as signed floats: negative = spending, positive = income/transfer. This convention is relied on throughout (`get_dashboard_summary`, `get_category_spending_by_date_range`, the AI system prompt).
