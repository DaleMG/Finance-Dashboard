# Finance Dashboard

An AI-assisted personal finance and budgeting app built with Streamlit.

Users can upload bank CSV files, manually add transactions, manage categories and budgets, track income/bills/savings, and view spending through dashboards and charts. A Gemini-powered assistant answers finance questions using the app's own data, and can also help auto-categorize imported transactions.

## Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| Backend | Python |
| Data Handling | pandas |
| Database | SQLite |
| Charts | Plotly |
| AI | Google Gemini |
| App Structure | Multipage Streamlit app |

## Pages

| Page | Purpose |
|---|---|
| Dashboard | Spending summary, budget vs. actual, and category breakdown charts for a chosen timeframe |
| Transactions | View, add, edit, and delete transactions |
| Upload | Import a bank CSV, auto-detect columns, dedupe against existing transactions, and categorize via saved rules or AI |
| Categories | Manage the list of spending categories |
| Budgets | Set per-category monthly budgets |
| Income / Bills / Savings | Editable, autosaving monthly grids for cash flow, each with a bar chart |
| AI Assistant | Ask natural-language questions about your finances, answered using your own data |

## Features

- Upload CSV bank statements with auto-detected date/merchant/amount columns
- Add and edit transactions manually
- Prevent duplicate imports via a date + normalized-merchant + amount signature
- AI-assisted merchant categorization, with rules saved so repeat merchants skip the AI call
- Manage categories and per-category budgets
- View spending metrics and charts, with the Net figure colored green/red based on sign
- Track income, bills, and savings in autosaving, spreadsheet-like monthly grids
- Ask the AI assistant finance questions, answered from your own transaction and cash-flow data

## Setup

**Install dependencies:**

```bash
pip install -r requirements.txt
```

**Run the app:**

```bash
streamlit run home.py
```

There is no test suite, linter, or CI configuration in this repo.

## Optional AI Setup

To enable AI features, set your Gemini API key:

- `GEMINI_API_KEY`

You can set it in your shell, or in Streamlit secrets.
