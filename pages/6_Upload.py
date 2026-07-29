import io
from datetime import date

import pandas as pd
import streamlit as st

from database.database import (
    add_transactions,
    get_categories,
    get_merchant_rules,
    get_transaction_signatures,
    initialize_database,
    upsert_merchant_rule,
)
from services.gemini_categorizer import get_gemini_api_key, suggest_merchant_categories


def normalize_text(value):
    return " ".join(str(value).strip().lower().split())


def detect_header_row(file_text):
    lines = file_text.splitlines()

    for index, line in enumerate(lines):
        if line.count(",") < 2:
            continue

        normalized_line = line.strip().lower()

        if "date" in normalized_line and ("amount" in normalized_line or "balance" in normalized_line):
            return index

    for index, line in enumerate(lines):
        if line.count(",") >= 2:
            return index

    return 0


def suggest_column(columns, keywords):
    for column in columns:
        normalized_column = str(column).strip().lower()

        for keyword in keywords:
            if keyword in normalized_column:
                return column

    return columns[0]


def clean_optional_text(series):
    cleaned_series = series.fillna("").astype(str).str.strip()
    return cleaned_series.where(cleaned_series != "", None)


def clean_amount_series(series):
    """Convert messy amount text into numeric values."""
    cleaned_series = (
        series.fillna("")
        .astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.replace("(", "-", regex=False)
        .str.replace(")", "", regex=False)
        .str.strip()
    )

    return pd.to_numeric(cleaned_series, errors="coerce")


def parse_amount_value(value):
    """Convert a manual amount value into a float."""
    cleaned_value = (
        str(value)
        .replace("$", "")
        .replace(",", "")
        .replace("(", "-")
        .replace(")", "")
        .strip()
    )
    return pd.to_numeric(cleaned_value, errors="coerce")


def parse_dates(series):
    return pd.to_datetime(series, format="mixed", errors="coerce").dt.strftime("%Y-%m-%d")


def get_manual_blank_row(default_category):
    """Return a blank manual transaction row."""
    return {
        "Date": date.today(),
        "Merchant": "",
        "Amount": None,
        "Category": default_category,
    }


def is_manual_row_complete(row):
    """Return True when a manual transaction row has the required values."""
    merchant_value = str(row.get("Merchant", "")).strip()
    amount_value = row.get("Amount")
    row_date = row.get("Date")
    return bool(merchant_value) and row_date not in (None, "") and not pd.isna(amount_value)


def convert_manual_rows_to_transactions(rows, category_lookup):
    """Convert manual entry rows into transaction dictionaries ready for import."""
    transactions_to_insert = []
    skipped_partial_rows = 0

    for row in rows:
        merchant_name = str(row.get("Merchant", "")).strip()
        amount_value = row.get("Amount")
        row_date = row.get("Date")
        category_name = row.get("Category") or "Uncategorized"

        if not merchant_name and row_date in (None, "") and (amount_value in (None, "")):
            continue

        if not merchant_name or row_date in (None, "") or pd.isna(amount_value):
            skipped_partial_rows += 1
            continue

        numeric_amount = parse_amount_value(amount_value)
        if pd.isna(numeric_amount):
            skipped_partial_rows += 1
            continue

        if isinstance(row_date, date):
            transaction_date = row_date.isoformat()
        else:
            parsed_date = pd.to_datetime(row_date, errors="coerce")
            if pd.isna(parsed_date):
                skipped_partial_rows += 1
                continue
            transaction_date = parsed_date.date().isoformat()

        category_id = None if category_name == "Uncategorized" else category_lookup.get(category_name)
        normalized_amount = round(-abs(float(numeric_amount)), 2)

        transactions_to_insert.append(
            {
                "date": transaction_date,
                "merchant": merchant_name,
                "amount": normalized_amount,
                "category_id": category_id,
            }
        )

    return transactions_to_insert, skipped_partial_rows


def normalize_transaction_signature(transaction):
    """Build a duplicate-check signature for a transaction."""
    transaction_date = str(transaction["date"]).strip()
    merchant_name = normalize_text(transaction["merchant"])
    amount_value = round(float(transaction["amount"]), 2)
    return transaction_date, merchant_name, amount_value


def filter_duplicate_transactions(transactions, existing_signatures):
    """Remove transactions that already exist or repeat in the current batch."""
    unique_transactions = []
    skipped_duplicate_count = 0
    seen_signatures = set(existing_signatures)

    for transaction in transactions:
        signature = normalize_transaction_signature(transaction)

        if signature in seen_signatures:
            skipped_duplicate_count += 1
            continue

        seen_signatures.add(signature)
        unique_transactions.append(transaction)

    return unique_transactions, skipped_duplicate_count


st.title("Upload")
st.write("Upload a CSV file or add transactions manually. The app will detect the useful columns and categorize merchants.")

initialize_database()
existing_transaction_signatures = get_transaction_signatures()

uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])

if uploaded_file is None:
    st.info("Upload a CSV file to preview and map its contents.")
else:
    try:
        file_bytes = uploaded_file.getvalue()
        file_text = file_bytes.decode("utf-8-sig", errors="replace")
        detected_header_index = detect_header_row(file_text)
        parsed_dataframe = pd.read_csv(
            io.StringIO(file_text),
            skiprows=detected_header_index,
            dtype=str,
            keep_default_na=False,
        )
    except Exception as error:
        st.error(f"Unable to read the CSV file: {error}")
    else:
        mapped_dataframe = parsed_dataframe.copy()
        mapped_dataframe.columns = [str(column).strip() for column in mapped_dataframe.columns]
        mapped_dataframe = mapped_dataframe.loc[:, ~mapped_dataframe.columns.duplicated()]
        mapped_dataframe = mapped_dataframe.replace("", pd.NA).dropna(how="all").reset_index(drop=True)

        if mapped_dataframe.empty:
            st.warning("No data rows were found after the detected header row.")
        else:
            available_columns = list(mapped_dataframe.columns)
            categories = get_categories()
            if not categories:
                st.info("Add at least one category before using AI categorization.")
            else:
                date_column = suggest_column(available_columns, ["date"])
                merchant_column = suggest_column(available_columns, ["payee", "merchant", "description", "details"])
                amount_column = suggest_column(available_columns, ["amount", "debit", "credit", "value"])

                cleaned_dataframe = pd.DataFrame(
                    {
                        "date": mapped_dataframe[date_column],
                        "merchant": mapped_dataframe[merchant_column],
                        "amount": mapped_dataframe[amount_column],
                    }
                )

                cleaned_dataframe["date"] = parse_dates(cleaned_dataframe["date"])
                cleaned_dataframe["merchant"] = clean_optional_text(cleaned_dataframe["merchant"])
                cleaned_dataframe["amount"] = clean_amount_series(cleaned_dataframe["amount"])
                cleaned_dataframe = cleaned_dataframe.dropna(subset=["date", "merchant", "amount"]).reset_index(drop=True)

                if cleaned_dataframe.empty:
                    st.warning("No valid transaction rows remain after mapping and cleaning.")
                else:
                    category_lookup = {category_name: category_id for category_id, category_name in categories}
                    merchant_rules = get_merchant_rules()
                    saved_rule_lookup = {
                        normalize_text(merchant): category_name
                        for merchant, _, category_name in merchant_rules
                    }

                    api_key = get_gemini_api_key(getattr(st, "secrets", None))
                    use_ai_categorization = st.checkbox(
                        "Use AI to categorize merchants",
                        value=True,
                        help="Gemini will suggest categories for merchants that do not already have saved rules.",
                    )

                    unique_merchants = list(dict.fromkeys(cleaned_dataframe["merchant"].dropna().astype(str).str.strip()))
                    suggestions_signature = "|".join(unique_merchants) + "||" + "|".join(sorted(category_lookup.keys()))
                    cached_signature = st.session_state.get("upload_ai_suggestions_signature")
                    ai_suggestions = st.session_state.get("upload_ai_suggestions", {}) if cached_signature == suggestions_signature else {}

                    if use_ai_categorization:
                        ai_button_col_1, ai_button_col_2 = st.columns(2)

                        if ai_button_col_1.button("Generate AI suggestions"):
                            if not api_key:
                                st.warning("Add your Gemini API key to enable AI categorization.")
                            elif not unique_merchants:
                                st.info("No merchants available to categorize.")
                            else:
                                unknown_merchants = [
                                    merchant
                                    for merchant in unique_merchants
                                    if normalize_text(merchant) not in saved_rule_lookup
                                ]

                                if not unknown_merchants:
                                    st.success("All merchants already have saved rules.")
                                    st.session_state["upload_ai_suggestions"] = {}
                                    st.session_state["upload_ai_suggestions_signature"] = suggestions_signature
                                else:
                                    try:
                                        with st.spinner("Generating AI suggestions..."):
                                            generated_suggestions = suggest_merchant_categories(
                                                merchants=unknown_merchants,
                                                categories=list(category_lookup.keys()),
                                                api_key=api_key,
                                            )
                                    except Exception as error:
                                        st.warning(f"AI categorization skipped: {error}")
                                    else:
                                        st.session_state["upload_ai_suggestions"] = generated_suggestions
                                        st.session_state["upload_ai_suggestions_signature"] = suggestions_signature
                                        ai_suggestions = generated_suggestions
                                        st.success("AI suggestions generated.")

                        if ai_button_col_2.button("Clear AI suggestions"):
                            st.session_state.pop("upload_ai_suggestions", None)
                            st.session_state.pop("upload_ai_suggestions_signature", None)
                            ai_suggestions = {}
                            st.rerun()

                    preview_rows = []
                    final_category_ids = []

                    for _, row in cleaned_dataframe.iterrows():
                        merchant_name = str(row["merchant"]).strip()
                        normalized_merchant = normalize_text(merchant_name)
                        category_name = saved_rule_lookup.get(normalized_merchant)

                        if category_name is None and use_ai_categorization:
                            category_name = ai_suggestions.get(merchant_name)

                        category_id = category_lookup.get(category_name) if category_name is not None else None
                        final_category_ids.append(category_id)
                        preview_rows.append(
                            {
                                "Date": row["date"],
                                "Merchant": merchant_name,
                                "Amount": row["amount"],
                                "Suggested Category": category_name if category_name is not None else "Uncategorized",
                            }
                        )

                    preview_dataframe = pd.DataFrame(preview_rows)
                    cleaned_dataframe = cleaned_dataframe.copy()
                    cleaned_dataframe["category_id"] = final_category_ids

                    st.write(f"Cleaned rows: {len(cleaned_dataframe)}")
                    st.dataframe(preview_dataframe.head(50), width="stretch", hide_index=True)

                    if st.button("Import transactions"):
                        if use_ai_categorization and not ai_suggestions and api_key:
                            unknown_merchants = [
                                merchant
                                for merchant in unique_merchants
                                if normalize_text(merchant) not in saved_rule_lookup
                            ]

                            if unknown_merchants:
                                try:
                                    with st.spinner("Generating AI suggestions..."):
                                        ai_suggestions = suggest_merchant_categories(
                                            merchants=unknown_merchants,
                                            categories=list(category_lookup.keys()),
                                            api_key=api_key,
                                        )
                                except Exception as error:
                                    st.warning(f"AI categorization skipped: {error}")
                                else:
                                    st.session_state["upload_ai_suggestions"] = ai_suggestions
                                    st.session_state["upload_ai_suggestions_signature"] = suggestions_signature

                        transactions_to_insert = cleaned_dataframe[["date", "merchant", "amount", "category_id"]].where(
                            pd.notna(cleaned_dataframe[["date", "merchant", "amount", "category_id"]]),
                            None,
                        ).to_dict(orient="records")

                        if ai_suggestions:
                            for merchant_name, category_name in ai_suggestions.items():
                                if category_name is not None:
                                    upsert_merchant_rule(merchant_name, category_lookup[category_name])

                        transactions_to_insert, skipped_duplicate_count = filter_duplicate_transactions(
                            transactions_to_insert,
                            existing_transaction_signatures,
                        )

                        if not transactions_to_insert:
                            st.warning("All of the imported rows already exist in the database.")
                        else:
                            imported_count = add_transactions(transactions_to_insert)
                            existing_transaction_signatures.update(
                                normalize_transaction_signature(transaction) for transaction in transactions_to_insert
                            )
                            st.success(f"Imported {imported_count} transactions.")

                            if skipped_duplicate_count:
                                st.warning(f"Skipped {skipped_duplicate_count} duplicate row(s).")

st.divider()
st.subheader("Manual transaction loading")
st.write("Add transactions directly without uploading a CSV file.")

manual_categories = get_categories()
manual_category_lookup = {category_name: category_id for category_id, category_name in manual_categories}
manual_category_labels = ["Uncategorized"] + [category_name for _, category_name in manual_categories]

if "manual_transaction_rows" not in st.session_state:
    st.session_state["manual_transaction_rows"] = [get_manual_blank_row(manual_category_labels[0])]

if st.session_state.pop("manual_transaction_reset", False):
    st.session_state.pop("manual_transaction_editor", None)
    st.session_state["manual_transaction_rows"] = [get_manual_blank_row(manual_category_labels[0])]

manual_editor_dataframe = pd.DataFrame(st.session_state["manual_transaction_rows"])
edited_manual_dataframe = st.data_editor(
    manual_editor_dataframe,
    width="stretch",
    hide_index=True,
    num_rows="dynamic",
    column_config={
        "Date": st.column_config.DateColumn("Date", required=True),
        "Merchant": st.column_config.TextColumn("Merchant", required=True),
        "Amount": st.column_config.NumberColumn("Amount", required=True, step=0.01, format="%.2f"),
        "Category": st.column_config.SelectboxColumn("Category", options=manual_category_labels),
    },
    key="manual_transaction_editor",
)

st.caption("Tip: you can type a new row directly in the table and then save it.")

manual_save_col_1, manual_save_col_2 = st.columns(2)

if manual_save_col_1.button("Save manual transactions"):
    transactions_to_insert, skipped_partial_rows = convert_manual_rows_to_transactions(
        edited_manual_dataframe.to_dict(orient="records"),
        manual_category_lookup,
    )

    if not transactions_to_insert:
        st.warning("Add at least one complete transaction before saving.")
    else:
        transactions_to_insert, skipped_duplicate_count = filter_duplicate_transactions(
            transactions_to_insert,
            existing_transaction_signatures,
        )

        if not transactions_to_insert:
            st.warning("All of the manual rows already exist in the database.")
        else:
            imported_count = add_transactions(transactions_to_insert)
            existing_transaction_signatures.update(
                normalize_transaction_signature(transaction) for transaction in transactions_to_insert
            )
            st.session_state["manual_transaction_reset"] = True

            if skipped_partial_rows:
                st.warning(f"Skipped {skipped_partial_rows} incomplete row(s).")

            if skipped_duplicate_count:
                st.warning(f"Skipped {skipped_duplicate_count} duplicate row(s).")

            st.success(f"Imported {imported_count} manual transaction(s).")
            st.rerun()

if manual_save_col_2.button("Clear manual rows"):
    st.session_state["manual_transaction_reset"] = True
    st.rerun()
