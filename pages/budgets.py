import pandas as pd
import streamlit as st

from database.database import add_budget, delete_budget, get_budgets, get_categories, initialize_database

initialize_database()

st.title("Budgets")
st.write("Set and manage a budget for each category.")


def get_selected_rows(selection_state):
    """Return the selected dataframe row indexes from a dataframe event."""
    if selection_state is None:
        return []

    try:
        return list(selection_state.selection.rows)
    except Exception:
        pass

    try:
        return list(selection_state["selection"]["rows"])
    except Exception:
        return []


def clear_budget_state():
    st.session_state["budgets_clear_selection"] = True
    for key in [
        "budgets_action",
        "budgets_selected_id",
    ]:
        st.session_state.pop(key, None)


if st.session_state.pop("budgets_clear_selection", False):
    st.session_state["budgets_table"] = {"selection": {"rows": []}}


categories = get_categories()

if not categories:
    st.info("Add at least one category before creating budgets.")
else:
    category_options = {category_name: category_id for category_id, category_name in categories}

    with st.form("add_budget_form", clear_on_submit=True):
        selected_category_name = st.selectbox("Category", list(category_options.keys()))
        budget_amount = st.number_input("Budget amount", min_value=0.0, step=0.01, format="%.2f")
        save_budget_button = st.form_submit_button("Save budget")

        if save_budget_button:
            add_budget(category_options[selected_category_name], budget_amount)
            st.success(f"Saved budget for {selected_category_name}.")
            st.rerun()

    budgets = get_budgets()

    if not budgets:
        st.info("No budgets saved yet.")
    else:
        budget_rows = []
        budget_lookup = {}

        for budget in budgets:
            budget_rows.append(
                {
                    "Budget ID": budget[0],
                    "Category": budget[4],
                    "Budget Amount": budget[2],
                }
            )
            budget_lookup[budget[0]] = budget

        budgets_dataframe = pd.DataFrame(budget_rows)
        actions_container = st.container()

        table_event = st.dataframe(
            budgets_dataframe[["Category", "Budget Amount"]],
            width="stretch",
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="budgets_table",
        )

        selected_rows = get_selected_rows(table_event)
        if not selected_rows:
            selected_rows = get_selected_rows(st.session_state.get("budgets_table"))
        if selected_rows:
            selected_row_index = selected_rows[0]
            selected_budget_id = budgets_dataframe.iloc[selected_row_index]["Budget ID"]
            st.session_state["budgets_selected_id"] = selected_budget_id

        selected_budget_id = st.session_state.get("budgets_selected_id")
        action = st.session_state.get("budgets_action")
        active_budget = budget_lookup.get(selected_budget_id)

        if selected_budget_id is not None and active_budget is None:
            clear_budget_state()
            action = None

        if selected_budget_id is not None and active_budget is not None:
            st.caption(f"Selected budget: {active_budget[4]} | ${float(active_budget[2]):.2f}")

        with actions_container:
            action_col_1, action_col_2 = st.columns(2)

            if action_col_1.button("Edit selected"):
                if active_budget is None:
                    st.warning("Select a budget from the table first.")
                else:
                    st.session_state["budgets_action"] = "edit"
                    st.rerun()

            if action_col_2.button("Delete selected"):
                if active_budget is None:
                    st.warning("Select a budget from the table first.")
                else:
                    st.session_state["budgets_action"] = "delete"
                    st.rerun()

            if action == "edit" and active_budget is not None:
                st.subheader("Edit Selected Budget")

                with st.form(f"edit_budget_{active_budget[0]}"):
                    edited_amount = st.number_input(
                        f"Budget for {active_budget[4]}",
                        min_value=0.0,
                        value=float(active_budget[2]),
                        step=0.01,
                        format="%.2f",
                    )
                    save_budget_changes = st.form_submit_button("Save changes")

                    if save_budget_changes:
                        add_budget(active_budget[3], edited_amount)
                        clear_budget_state()
                        st.success("Budget updated.")
                        st.rerun()

            if action == "delete" and active_budget is not None:
                st.subheader("Delete Selected Budget")
                st.write(f"Delete budget for `{active_budget[4]}` set to `${float(active_budget[2]):.2f}`?")

                confirm_col_1, confirm_col_2 = st.columns(2)

                if confirm_col_1.button("Confirm delete"):
                    delete_budget(active_budget[0])
                    clear_budget_state()
                    st.success("Budget deleted.")
                    st.rerun()

                if confirm_col_2.button("Cancel"):
                    clear_budget_state()
                    st.rerun()
