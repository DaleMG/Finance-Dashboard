import streamlit as st
from database.database import initialize_database

initialize_database()

st.set_page_config(
    page_title="Budgeting App",
    page_icon="💰",
    layout="wide"
)

st.title("💰 Budgeting App")
st.write("Welcome to your personal budgeting dashboard.")