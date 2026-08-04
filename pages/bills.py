from components.cash_flow_page import render_cash_flow_page

render_cash_flow_page(
    page_title="Bills",
    row_names=[
        "Fixed Bills",
        "Variable Bills",
    ],
    section_type="bills",
    expense=True,
)