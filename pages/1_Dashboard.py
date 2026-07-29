from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from database.database import (
    get_budgets,
    get_category_spending_by_date_range,
    get_dashboard_summary,
    get_transaction_date_bounds,
    initialize_database,
)

initialize_database()


def get_month_start(selected_date):
    """Return the first day of the month for a date."""
    return selected_date.replace(day=1)


def get_previous_month_range(selected_date):
    """Return the first and last day of the previous month."""
    current_month_start = get_month_start(selected_date)
    previous_month_end = current_month_start - timedelta(days=1)
    previous_month_start = get_month_start(previous_month_end)
    return previous_month_start, previous_month_end


def resolve_timeframe(option, current_month_start, today, date_bounds, custom_range):
    """Return the start and end dates for the selected dashboard timeframe."""
    if option == "Last 7 days":
        return today - timedelta(days=6), today

    if option == "Last month":
        return get_previous_month_range(today)

    if option == "All time":
        if date_bounds["start_date"] and date_bounds["end_date"]:
            return date.fromisoformat(date_bounds["start_date"]), date.fromisoformat(date_bounds["end_date"])
        return current_month_start, today

    if option == "Specific dates" and custom_range is not None:
        if isinstance(custom_range, tuple):
            start_date, end_date = custom_range
        else:
            start_date = end_date = custom_range

        if start_date > end_date:
            start_date, end_date = end_date, start_date

        return start_date, end_date

    return current_month_start, today


st.set_page_config(
    page_title="Dashboard | Budgeting App",
    page_icon="💰",
    layout="wide",
)

today = date.today()
current_month_start = get_month_start(today)
date_bounds = get_transaction_date_bounds()
overall_min_date = date.fromisoformat(date_bounds["start_date"]) if date_bounds["start_date"] else current_month_start
overall_max_date = date.fromisoformat(date_bounds["end_date"]) if date_bounds["end_date"] else today
specific_dates_default_start = max(current_month_start, overall_min_date)
specific_dates_default_end = min(today, overall_max_date)

if specific_dates_default_start > specific_dates_default_end:
    specific_dates_default_start = overall_min_date
    specific_dates_default_end = overall_max_date

if "specific_dates_range" not in st.session_state:
    st.session_state["specific_dates_range"] = (specific_dates_default_start, specific_dates_default_end)

st.title("Dashboard")
st.write("See your spending, budget totals, and category breakdown.")

with st.sidebar:
    st.header("Dashboard controls")
    timeframe_option = st.radio(
        "Timeframe",
        ["Current month", "Last 7 days", "Last month", "All time", "Specific dates"],
        index=0,
    )

    custom_range = None
    if timeframe_option == "Specific dates":
        with st.form("specific_dates_form"):
            custom_range = st.date_input(
                "Pick dates",
                value=st.session_state["specific_dates_range"],
                min_value=overall_min_date,
                max_value=overall_max_date,
                key="specific_dates_picker",
            )
            apply_dates = st.form_submit_button("Apply dates")

        if apply_dates:
            st.session_state["specific_dates_range"] = custom_range

        custom_range = st.session_state["specific_dates_range"]

start_date, end_date = resolve_timeframe(timeframe_option, current_month_start, today, date_bounds, custom_range)
is_current_month = start_date == current_month_start and end_date == today

selected_summary = get_dashboard_summary(start_date=start_date.isoformat(), end_date=end_date.isoformat())
category_spending = get_category_spending_by_date_range(start_date=start_date.isoformat(), end_date=end_date.isoformat())
budgets = get_budgets()

st.caption(f"Showing {timeframe_option.lower()} from {start_date.isoformat()} to {end_date.isoformat()}.")

if is_current_month:

    rem_budget = selected_summary['remaining_budget']

    if rem_budget >= 0:
        colored_value = f":green[${rem_budget:,.2f}]"
    else:
        colored_value = f":red[${rem_budget:,.2f}]"



    metric_col_1, metric_col_2, metric_col_3, metric_col_4 = st.columns(4)
    metric_col_1.metric("Total Spending", f"${selected_summary['total_spending']:.2f}")
    metric_col_2.metric("Total Budget", f"${selected_summary['total_budget']:.2f}")
    metric_col_3.metric("Remaining Budget", colored_value)   
    metric_col_4.metric("Transactions", selected_summary["transaction_count"])
else:
    metric_col_1, metric_col_2 = st.columns(2)
    metric_col_1.metric("Total Spending", f"${selected_summary['total_spending']:.2f}")
    metric_col_2.metric("Transactions", selected_summary["transaction_count"])

if is_current_month:
    category_rows = []
    budget_rows = []
    spending_rows = []

    for category_name, total_spending in category_spending:
        spending_rows.append(
            {
                "Category": category_name,
                "Total Spending": float(total_spending),
            }
        )

    for budget in budgets:
        budget_rows.append(
            {
                "Category": budget[4],
                "Budget": float(budget[2]),
            }
        )

    spending_dataframe = pd.DataFrame(spending_rows)
    budget_dataframe = pd.DataFrame(budget_rows)

    if not budget_dataframe.empty and not spending_dataframe.empty:
        category_dataframe = budget_dataframe.merge(spending_dataframe, on="Category", how="outer").fillna(0.0)
    elif not budget_dataframe.empty:
        category_dataframe = budget_dataframe.copy()
        category_dataframe["Total Spending"] = 0.0
    elif not spending_dataframe.empty:
        category_dataframe = spending_dataframe.copy()
        category_dataframe["Budget"] = 0.0
    else:
        category_dataframe = pd.DataFrame(columns=["Category", "Budget", "Total Spending"])

    category_dataframe = category_dataframe[["Category", "Budget", "Total Spending"]].sort_values(
        "Category"
    ).reset_index(drop=True)

    if category_dataframe.empty:
        st.info("No transactions available for the current month.")
    else:
        st.subheader("Total Spending by Category")
        chart_columns = px.bar(
            category_dataframe,
            x="Category",
            y= "Total Spending",
            color="Category"
        )
        st.plotly_chart(chart_columns, width="stretch")

        st.subheader("Budget vs Spending")
        st.dataframe(category_dataframe, width="stretch", hide_index=True)

        chart_columns = st.columns(2)

        for index, row in category_dataframe.iterrows():
            category_name = row["Category"]
            budget_amount = float(row["Budget"])
            actual_spending = float(row["Total Spending"])

            with chart_columns[index % 2]:
                if budget_amount <= 0 and actual_spending <= 0:
                    st.info(f"No data for {category_name}.")
                elif budget_amount <= 0:
                    pie_dataframe = pd.DataFrame(
                        {
                            "Status": ["Budget", "Spent"],
                            "Amount": [actual_spending, 0.0],
                        }
                    )

                    pie_chart = px.pie(
                        pie_dataframe,
                        names="Status",
                        values="Amount",
                        hole=0.45,
                        title=category_name,
                        color_discrete_sequence=["#22c55e", "#ef4444"],
                    )
                    st.plotly_chart(pie_chart, width="stretch")
                    st.caption("No budget set for this category.")
                else:
                    pie_dataframe = pd.DataFrame(
                        {
                            "Status": ["Budget", "Spent"],
                            "Amount": [budget_amount, actual_spending],
                        }
                    )

                    pie_chart = px.pie(
                        pie_dataframe,
                        names="Status",
                        values="Amount",
                        hole=0.45,
                        title=category_name,
                        color_discrete_sequence=["#22c55e", "#ef4444"],
                    )
                    st.plotly_chart(pie_chart, width="stretch")
else:
    if not category_spending:
        st.info("No transactions available for the selected timeframe.")
    else:
        category_rows = []

        for category_name, total_spending in category_spending:
            category_rows.append(
                {
                    "Category": category_name,
                    "Total Spending": float(total_spending),
                }
            )

        category_dataframe = pd.DataFrame(category_rows)

        pie_chart = px.pie(
            category_dataframe,
            names="Category",
            values="Total Spending",
            title="Category Spend Share",
        )
        st.plotly_chart(pie_chart, width="stretch")
