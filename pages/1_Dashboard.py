import pandas as pd
import plotly.express as px
import streamlit as st

from database.database import get_budgets, get_category_spending, get_dashboard_summary, initialize_database

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

    st.subheader("Actual Spending by Category")
    st.dataframe(category_dataframe, width="stretch", hide_index=True)

    spending_chart = px.bar(
        category_dataframe,
        x="Category",
        y="Total Spending",
        title="Actual Spending by Category",
    )
    st.plotly_chart(spending_chart, use_container_width=True)

budgets = get_budgets()

if budgets:
    budget_rows = []
    spending_rows = []

    for budget in budgets:
        budget_rows.append(
            {
                "Category": budget[4],
                "Budget Amount": float(budget[2]),
            }
        )

    for category_name, total_spending in category_spending:
        spending_rows.append(
            {
                "Category": category_name,
                "Actual Spending": float(total_spending),
            }
        )

    budgets_dataframe = pd.DataFrame(budget_rows)
    spending_dataframe = pd.DataFrame(spending_rows, columns=["Category", "Actual Spending"])

    budget_actual_dataframe = budgets_dataframe.merge(spending_dataframe, on="Category", how="left").fillna(
        {"Actual Spending": 0.0}
    )
    budget_actual_dataframe = budget_actual_dataframe.sort_values("Category").reset_index(drop=True)

    st.subheader("Budget vs Actual by Category")

    chart_columns = st.columns(2)

    for index, row in budget_actual_dataframe.iterrows():
        category_name = row["Category"]
        budget_amount = float(row["Budget Amount"])
        actual_spending = float(row["Actual Spending"])
        spent_within_budget = min(actual_spending, budget_amount)
        remaining_budget = max(budget_amount - actual_spending, 0.0)
        overspent_amount = max(actual_spending - budget_amount, 0.0)

        with chart_columns[index % 2]:
            if budget_amount <= 0:
                st.info("No budget set for this category.")
            else:
                pie_dataframe = pd.DataFrame(
                    {
                        "Status": ["Spent", "Remaining"],
                        "Amount": [spent_within_budget, remaining_budget],
                    }
                )

                pie_chart = px.pie(
                    pie_dataframe,
                    names="Status",
                    values="Amount",
                    hole=0.45,
                    title=category_name,
                )
                pie_chart.update_layout(legend_title_text="")
                st.plotly_chart(pie_chart, use_container_width=True)

                if overspent_amount > 0:
                    st.caption(f"Overspent by ${overspent_amount:.2f}")
