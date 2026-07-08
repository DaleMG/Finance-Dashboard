import pandas as pd
import streamlit as st

from database.database import get_transactions, initialize_database

initialize_database()

st.title("Transactions")
st.write("View your imported transactions.")

transactions = get_transactions()

if not transactions:
    st.info("No transactions found yet. Import a CSV from the Upload page first.")
else:
    transaction_rows = []

    for transaction in transactions:
        transaction_rows.append(
            {
                "ID": transaction[0],
                "Date": transaction[1],
                "Merchant": transaction[2],
                "Amount": transaction[3],
                "Category ID": transaction[4] if transaction[4] is not None else "Uncategorized",
            }
        )

    transactions_dataframe = pd.DataFrame(transaction_rows)

    st.write(f"Transactions: {len(transactions_dataframe)}")
    st.dataframe(transactions_dataframe, width="stretch", hide_index=True)
