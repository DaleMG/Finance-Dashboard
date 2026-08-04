import sqlite3

import streamlit as st

from database.database import add_category, delete_category, get_categories, initialize_database

initialize_database()

st.title("Categories")
st.write("Manage your spending categories.")

with st.form("add_category_form", clear_on_submit=True):
    category_name = st.text_input("Category name")
    add_category_button = st.form_submit_button("Add category")

    if add_category_button:
        cleaned_name = category_name.strip()

        if not cleaned_name:
            st.warning("Please enter a category name.")
        else:
            try:
                add_category(cleaned_name)
            except sqlite3.IntegrityError:
                st.error("That category already exists.")
            else:
                st.success(f"Added category: {cleaned_name}")
                st.rerun()

categories = get_categories()

if not categories:
    st.info("No categories yet. Add your first category above.")
else:
    st.subheader("Existing categories")

    for category_id, category_name in categories:
        name_column, action_column = st.columns([4, 1])
        name_column.write(category_name)

        if action_column.button("Delete", key=f"delete_{category_id}"):
            delete_category(category_id)
            st.success(f"Deleted category: {category_name}")
            st.rerun()
