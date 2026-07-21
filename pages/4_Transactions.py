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
st.write("View, filter, edit, delete, and bulk update categories for your imported transactions.")


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


def clear_transaction_state():
    st.session_state["transactions_clear_selection"] = True
    for key in [
        "transactions_action",
        "transactions_selected_ids",
        "transactions_bulk_category",
    ]:
        st.session_state.pop(key, None)


if st.session_state.pop("transactions_clear_selection", False):
    st.session_state["transactions_table"] = {"selection": {"rows": []}}


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

    actions_container = st.container()
    table_event = st.dataframe(
        visible_transactions_dataframe,
        width="stretch",
        hide_index=True,
        on_select="rerun",
        selection_mode="multi-row",
        key="transactions_table",
    )

    selected_rows = get_selected_rows(table_event)
    if not selected_rows:
        selected_rows = get_selected_rows(st.session_state.get("transactions_table"))
    selected_transaction_ids = [transactions_dataframe.iloc[row_index]["ID"] for row_index in selected_rows]
    if not selected_transaction_ids:
        selected_transaction_ids = st.session_state.get("transactions_selected_ids", [])
    active_transactions = [
        transaction_lookup[transaction_id]
        for transaction_id in selected_transaction_ids
        if transaction_id in transaction_lookup
    ]

    if selected_transaction_ids and len(active_transactions) != len(selected_transaction_ids):
        clear_transaction_state()
        st.rerun()

    if selected_transaction_ids:
        st.session_state["transactions_selected_ids"] = selected_transaction_ids
    else:
        st.session_state.pop("transactions_selected_ids", None)

    action = st.session_state.get("transactions_action")
    single_selected_transaction = active_transactions[0] if len(active_transactions) == 1 else None

    with actions_container:
        if selected_transaction_ids:
            st.caption(f"Selected transactions: {len(selected_transaction_ids)}")

        action_col_1, action_col_2, action_col_3 = st.columns(3)

        if action_col_1.button("Edit Category"):
            if not selected_transaction_ids:
                st.warning("Select one or more transactions from the table first.")
            else:
                st.session_state["transactions_action"] = "bulk_category"
                st.rerun()

        if action_col_2.button("Edit selected"):
            if single_selected_transaction is None:
                st.warning("Select exactly one transaction to edit.")
            else:
                st.session_state["transactions_action"] = "edit"
                st.rerun()

        if action_col_3.button("Delete selected"):
            if single_selected_transaction is None:
                st.warning("Select exactly one transaction to delete.")
            else:
                st.session_state["transactions_action"] = "delete"
                st.rerun()

        if action == "bulk_category":
            st.subheader("Bulk Category Assignment")
            st.write(f"Apply a new category to {len(selected_transaction_ids)} selected transaction(s).")

            bulk_category_labels = list(edit_category_options.keys())
            default_bulk_index = 0
            selected_bulk_category_label = st.selectbox(
                "Category",
                bulk_category_labels,
                index=default_bulk_index,
                key="transactions_bulk_category",
            )

            confirm_col_1, confirm_col_2 = st.columns(2)

            if confirm_col_1.button("Confirm category change"):
                updated_category_id = edit_category_options[selected_bulk_category_label]

                for transaction in active_transactions:
                    update_transaction(
                        transaction_id=transaction[0],
                        date=transaction[1],
                        merchant=transaction[2],
                        amount=transaction[3],
                        category_id=updated_category_id,
                        notes=transaction[5],
                    )

                clear_transaction_state()
                st.success("Transactions updated.")
                st.rerun()

            if confirm_col_2.button("Cancel"):
                clear_transaction_state()
                st.rerun()

        if action == "edit" and single_selected_transaction is not None:
            transaction_id = single_selected_transaction[0]
            transaction_date = single_selected_transaction[1]
            transaction_merchant = single_selected_transaction[2]
            transaction_amount = float(single_selected_transaction[3])
            transaction_category_name = single_selected_transaction[6] if single_selected_transaction[6] is not None else "Uncategorized"
            edit_category_labels = list(edit_category_options.keys())
            selected_index = (
                edit_category_labels.index(transaction_category_name)
                if transaction_category_name in edit_category_labels
                else 0
            )

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
                        clear_transaction_state()
                        st.success("Transaction updated.")
                        st.rerun()

        if action == "delete" and single_selected_transaction is not None:
            st.subheader("Delete Selected Transaction")
            st.write(
                f"Delete `{single_selected_transaction[2]}` on `{single_selected_transaction[1]}` "
                f"for `${float(single_selected_transaction[3]):.2f}`?"
            )

            confirm_col_1, confirm_col_2 = st.columns(2)

            if confirm_col_1.button("Confirm delete"):
                delete_transaction(single_selected_transaction[0])
                clear_transaction_state()
                st.success("Transaction deleted.")
                st.rerun()

            if confirm_col_2.button("Cancel"):
                clear_transaction_state()
                st.rerun()
