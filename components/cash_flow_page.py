"""Shared UI for Income, Bills and Savings pages."""

from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from database.database import get_cash_flow_grid, save_cash_flow_entry


MONTHS = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]


def _save_edited_cells(
    editor_key: str,
    row_names: list[str],
    section_type: str,
    current_year: int,
    expense: bool,
) -> None:
    edited_rows = st.session_state[editor_key].get("edited_rows", {})

    for row_index, changes in edited_rows.items():
        entry_kind = row_names[row_index]

        for month_name, raw_value in changes.items():
            if month_name not in MONTHS:
                continue

            month_number = MONTHS.index(month_name) + 1
            raw_amount = float(raw_value or 0.0)
            signed_amount = -abs(raw_amount) if expense else abs(raw_amount)

            save_cash_flow_entry(
                section_type=section_type,
                entry_kind=entry_kind,
                year=current_year,
                month=month_number,
                amount=signed_amount,
            )


def render_cash_flow_page(
    page_title: str,
    row_names: list[str],
    section_type: str,
    expense: bool = False,
) -> None:

    st.title(page_title)

    current_year = date.today().year
    editor_key = f"{section_type}_cash_flow_editor"

    # -------------------------
    # Create editable table, prefilled with saved amounts
    # -------------------------

    saved_grid = get_cash_flow_grid(section_type, current_year)

    table = {"Type": row_names}

    for month_number, month_name in enumerate(MONTHS, start=1):
        table[month_name] = [
            abs(saved_grid.get((row_name, month_number), 0.0))
            for row_name in row_names
        ]

    df = pd.DataFrame(table)

    st.subheader("Monthly Overview")
    st.caption("Edits save automatically — press Enter or click away to commit a cell.")

    edited_df = st.data_editor(
        df,
        hide_index=True,
        use_container_width=True,
        num_rows="fixed",
        column_config={
            "Type": st.column_config.TextColumn("Type", disabled=True),
        },
        key=editor_key,
        on_change=_save_edited_cells,
        args=(editor_key, row_names, section_type, current_year, expense),
    )

    st.divider()

    # -------------------------
    # Build chart data
    # -------------------------

    chart_rows = []

    for month in MONTHS:

        for _, row in edited_df.iterrows():

            chart_rows.append(
                {
                    "Month": month,
                    "Type": row["Type"],
                    "Amount": row[month],
                }
            )

    chart_df = pd.DataFrame(chart_rows)

    fig = px.bar(
        chart_df,
        x="Month",
        y="Amount",
        color="Type",
        barmode="group",
        title=f"{page_title} by Month",
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )
