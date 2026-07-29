import streamlit as st
from database.database import initialize_database

initialize_database()

st.set_page_config(
    page_title="Budgeting App"
)

st.title("Home")
st.write("Welcome to your personal budgeting dashboard.")

st.subheader("How to use the app")
st.markdown(
    """
    1. **Check Categories** to add or remove spending groups.
    2. **Set Budgets** for each category.
    3. **Upload** your CSV bank statement first.
    4. **Review Transactions** to edit, delete, or re-categorize entries.
    5. **Open the Dashboard** to see spending summaries and charts.
    6. **Use the AI Assistant** to ask questions about your finances.
    """
)
