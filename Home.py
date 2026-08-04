import streamlit as st
from database.database import initialize_database

initialize_database()

st.set_page_config(
    page_title="Budgeting App"
)

# Pages
dashboard = st.Page(
    "pages/dashboard.py",
    title="Dashboard",
    default=True
)

budgets = st.Page(
    "pages/budgets.py",
    title="Budgets",
)

categories = st.Page(
    "pages/categories.py",
    title="Categories",
)

transactions = st.Page(
    "pages/transactions.py",
    title="Transactions",
)

assistant = st.Page(
    "pages/ai_assistant.py",
    title="AI Assistant",
)

upload = st.Page(
    "pages/upload.py",
    title="Upload",
)

income = st.Page(
    "pages/income.py",
    title="Income",
)

savings = st.Page(
    "pages/savings.py",
    title="Savings & Investments",
)

bills = st.Page(
    "pages/bills.py",
    title="Bills",
)

pg = st.navigation(
    {
        "Overview": [
            dashboard,
        ],
        "Cash Flow": [
            income,
            bills,
            savings,
        ],
        "Budgeting": [
            budgets,
            categories,
        ],
        "Activity": [
            transactions,
            upload,
        ],
        "Tools": [
            assistant,
        ],
    }
)

pg.run()