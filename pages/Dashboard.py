import pandas as pd
import plotly.express as px
import streamlit as st

from database.database import get_category_spending, get_dashboard_summary, initialize_database

initialize_database()

st.title("Dashboard")
st.write("See your spending, budget totals, and category breakdown.")

summary = get_dashboard_summary()

metric_col_1, metric_col_2, metric_col_3, metric_col_4 = st.columns(4)
metric_col_1.metric("Total Spending", f"${summary['total_spending']:.2f}")
metric_col_2.metric("Total Budget", f"${summary['total_budget']:.2f}")
metric_col_3.metric("Remaining Budget", f"${summary['remaining_budget']:.2f}")
metric_col_4.metric("Transactions", summary["transaction_count"])

category_spending = get_category_spending()

if not category_spending:
    st.info("No transactions available yet. Import some data to populate the dashboard.")
else:
    category_rows = []

    for category_name, total_spending in category_spending:
        category_rows.append(
            {
                "Category": category_name,
                "Total Spending": total_spending,
            }
        )

    category_dataframe = pd.DataFrame(category_rows)

    st.subheader("Spending by Category")
    st.dataframe(category_dataframe, width="stretch", hide_index=True)

    spending_chart = px.bar(
        category_dataframe,
        x="Category",
        y="Total Spending",
        title="Spending by Category",
    )
    st.plotly_chart(spending_chart, width="stretch")
