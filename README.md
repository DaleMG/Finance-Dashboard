# Finance Dashboard

An AI-assisted personal finance and budgeting app built with Streamlit.

Users can upload bank CSV files, manually add transactions, manage categories and budgets, and track spending with dashboards and charts. The app also includes a Gemini-powered assistant for finance questions and merchant categorization.

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

## Features

- Upload CSV bank statements
- Add transactions manually
- Prevent duplicate imports
- Auto-detect transaction columns
- AI-assisted merchant categorization
- Manage categories and budgets
- View spending metrics and charts
- Ask questions through the AI assistant

## Setup

**Install dependencies:**

```bash
pip install -r requirements.txt
```

**Run the app:**

```bash
streamlit run Home.py
```

## Optional AI Setup

To enable AI features, set one of these environment variables:

- `GEMINI_API_KEY`

You can set it in your shell or in Streamlit secrets.
