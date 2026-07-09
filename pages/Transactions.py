from datetime import date

import pandas as pd
import streamlit as st

from database.database import (
    delete_transaction,
    get_categories,
    get_transactions,
    initialize_database,
    update_transaction,
)

initialize_database()

st.title("Transactions")
st.write("View, filter, edit, and delete your imported transactions.")

categories = get_categories()
category_options = {"All": None, "Uncategorized": "uncategorized"}
edit_category_options = {"Uncategorized": None}

for category_id, category_name in categories:
    category_options[category_name] = category_id
    edit_category_options[category_name] = category_id

search_text = st.text_input("Search merchant")
selected_category_label = st.selectbox("Filter by category", list(category_options.keys()))
selected_category_id = category_options[selected_category_label]

transactions = get_transactions(search_text=search_text, category_id=selected_category_id)

if not transactions:
    st.info("No transactions match the current filters.")
else:
    transaction_rows = []
    transaction_lookup = {}

    for transaction in transactions:
        category_name = transaction[6] if transaction[6] is not None else "Uncategorized"
        transaction_rows.append(
            {
                "ID": transaction[0],
                "Date": transaction[1],
                "Merchant": transaction[2],
                "Amount": transaction[3],
                "Category": category_name,
            }
        )
        transaction_lookup[transaction[0]] = transaction

    transactions_dataframe = pd.DataFrame(transaction_rows)
    visible_transactions_dataframe = transactions_dataframe[["Date", "Merchant", "Amount", "Category"]]

    st.write(f"Transactions: {len(transactions_dataframe)}")
    table_event = st.dataframe(
        visible_transactions_dataframe,
        width="stretch",
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="transactions_table",
    )

    selected_rows = table_event.selection.rows
    selected_transaction = None

    if selected_rows:
        selected_row_index = selected_rows[0]
        selected_transaction_id = transactions_dataframe.iloc[selected_row_index]["ID"]
        selected_transaction = transaction_lookup[selected_transaction_id]

    action_col_1, action_col_2 = st.columns(2)

    if action_col_1.button("Edit selected"):
        if selected_transaction is None:
            st.warning("Select a transaction from the table first.")
        else:
            st.session_state["transactions_action"] = "edit"
            st.session_state["transactions_selected_id"] = selected_transaction[0]
            st.rerun()

    if action_col_2.button("Delete selected"):
        if selected_transaction is None:
            st.warning("Select a transaction from the table first.")
        else:
            st.session_state["transactions_action"] = "delete"
            st.session_state["transactions_selected_id"] = selected_transaction[0]
            st.rerun()

    action = st.session_state.get("transactions_action")
    selected_transaction_id = st.session_state.get("transactions_selected_id")
    active_transaction = transaction_lookup.get(selected_transaction_id)

    if action == "edit" and active_transaction is not None:
        transaction_id = active_transaction[0]
        transaction_date = active_transaction[1]
        transaction_merchant = active_transaction[2]
        transaction_amount = float(active_transaction[3])
        transaction_category_name = active_transaction[6] if active_transaction[6] is not None else "Uncategorized"
        edit_category_labels = list(edit_category_options.keys())
        selected_index = edit_category_labels.index(transaction_category_name) if transaction_category_name in edit_category_labels else 0

        st.subheader("Edit Selected Transaction")

        with st.form(f"edit_transaction_{transaction_id}"):
            edited_date = st.date_input("Date", value=date.fromisoformat(transaction_date))
            edited_merchant = st.text_input("Merchant", value=transaction_merchant)
            edited_amount = st.number_input(
                "Amount",
                value=transaction_amount,
                step=0.01,
                format="%.2f",
            )
            edited_category_label = st.selectbox(
                "Category",
                edit_category_labels,
                index=selected_index,
            )
            save_transaction = st.form_submit_button("Save changes")

            if save_transaction:
                cleaned_merchant = edited_merchant.strip()

                if not cleaned_merchant:
                    st.warning("Merchant cannot be empty.")
                else:
                    update_transaction(
                        transaction_id=transaction_id,
                        date=edited_date.isoformat(),
                        merchant=cleaned_merchant,
                        amount=edited_amount,
                        category_id=edit_category_options[edited_category_label],
                    )
                    st.session_state.pop("transactions_action", None)
                    st.session_state.pop("transactions_selected_id", None)
                    st.success("Transaction updated.")
                    st.rerun()

    if action == "delete" and active_transaction is not None:
        st.subheader("Delete Selected Transaction")
        st.write(
            f"Delete `{active_transaction[2]}` on `{active_transaction[1]}` "
            f"for `${float(active_transaction[3]):.2f}`?"
        )

        confirm_col_1, confirm_col_2 = st.columns(2)

        if confirm_col_1.button("Confirm delete"):
            delete_transaction(active_transaction[0])
            st.session_state.pop("transactions_action", None)
            st.session_state.pop("transactions_selected_id", None)
            st.success("Transaction deleted.")
            st.rerun()

        if confirm_col_2.button("Cancel"):
            st.session_state.pop("transactions_action", None)
            st.session_state.pop("transactions_selected_id", None)
            st.rerun()
