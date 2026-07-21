import io

import pandas as pd
import streamlit as st

from database.database import add_transactions, initialize_database


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


def parse_dates(series):
    return pd.to_datetime(series, format="mixed", errors="coerce").dt.strftime("%Y-%m-%d")


st.title("Upload")
st.write("Upload a CSV file, choose the real header row, and map your transaction columns.")

initialize_database()

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
        st.subheader("Parsed Preview")
        st.dataframe(parsed_dataframe.head(20), width="stretch", hide_index=True)

        mapped_dataframe = parsed_dataframe.copy()
        mapped_dataframe.columns = [str(column).strip() for column in mapped_dataframe.columns]
        mapped_dataframe = mapped_dataframe.loc[:, ~mapped_dataframe.columns.duplicated()]
        mapped_dataframe = mapped_dataframe.replace("", pd.NA).dropna(how="all").reset_index(drop=True)

        if mapped_dataframe.empty:
            st.warning("No data rows were found after the detected header row.")
        else:
            available_columns = list(mapped_dataframe.columns)

            st.subheader("Column Mapping")

            date_column = st.selectbox(
                "Date column",
                available_columns,
                index=available_columns.index(suggest_column(available_columns, ["date"])),
            )
            merchant_column = st.selectbox(
                "Merchant or payee column",
                available_columns,
                index=available_columns.index(suggest_column(available_columns, ["payee", "merchant", "description", "details"])),
            )
            amount_column = st.selectbox(
                "Amount column",
                available_columns,
                index=available_columns.index(suggest_column(available_columns, ["amount", "debit", "credit", "value"])),
            )

            cleaned_dataframe = pd.DataFrame(
                {
                    "date": mapped_dataframe[date_column],
                    "merchant": mapped_dataframe[merchant_column],
                    "amount": mapped_dataframe[amount_column],
                }
            )

            cleaned_dataframe["date"] = parse_dates(cleaned_dataframe["date"])
            cleaned_dataframe["merchant"] = clean_optional_text(cleaned_dataframe["merchant"])
            cleaned_dataframe["amount"] = pd.to_numeric(cleaned_dataframe["amount"], errors="coerce")
            cleaned_dataframe = cleaned_dataframe.dropna(subset=["date", "merchant", "amount"]).reset_index(drop=True)

            st.subheader("Cleaned Preview")

            if cleaned_dataframe.empty:
                st.warning("No valid transaction rows remain after mapping and cleaning.")
            else:
                st.write(f"Cleaned rows: {len(cleaned_dataframe)}")
                st.dataframe(cleaned_dataframe.head(50), width="stretch", hide_index=True)

                if st.button("Import transactions"):
                    transactions_to_insert = cleaned_dataframe.where(pd.notna(cleaned_dataframe), None).to_dict(orient="records")
                    imported_count = add_transactions(transactions_to_insert)
                    st.success(f"Imported {imported_count} transactions.")
