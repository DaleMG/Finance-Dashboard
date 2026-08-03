import streamlit as st

from services.gemini_assistant import ask_gemini_assistant, build_finance_context, get_gemini_api_key

st.title("AI Assistant")
st.write("Ask questions about your spending, budgets, and categories.")

api_key = get_gemini_api_key(getattr(st, "secrets", None))

if not api_key:
    st.info("Set `GEMINI_API_KEY` in your environment or Streamlit secrets to enable the AI assistant.")

with st.form("gemini_assistant_form"):
    question = st.text_area(
        "Your question",
        placeholder="For example: How much did I spend on groceries last month?",
        height=120,
        key="gemini_assistant_question",
    )
    ask_button = st.form_submit_button("Ask AI")

if ask_button:
    cleaned_question = question.strip()

    if not cleaned_question:
        st.warning("Enter a question first.")
    elif not api_key:
        st.warning("Add your Gemini API key before asking the assistant.")
    else:
        finance_context = build_finance_context(cleaned_question)

        try:
            with st.spinner("Thinking..."):
                answer = ask_gemini_assistant(
                    question=cleaned_question,
                    finance_context=finance_context,
                    api_key=api_key,
                )
        except Exception as error:
            st.error(f"AI assistant request failed: {error}")
        else:
            st.subheader("Answer")
            st.write(answer)
