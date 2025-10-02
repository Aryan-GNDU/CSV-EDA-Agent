import streamlit as st
import pandas as pd
from main import build_agent

st.set_page_config(page_title="CSV Agent", layout="wide")

st.title("📊 CSV Agent with LangChain + Groq")

# --- Upload CSV ---
uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])

if uploaded_file is not None:
    # Read CSV directly from memory (no saving to disk)
    try:
        df = pd.read_csv(uploaded_file)
        st.success(f"Uploaded `{uploaded_file.name}`")
        st.write("### Preview of data:")
        st.dataframe(df.head())
    except Exception as e:
        st.error(f"Error reading CSV: {e}")
        st.stop()

    # --- Build agent for this uploaded DataFrame ---
    ask_agent = build_agent(df)

    # --- Query Section ---
    query = st.text_area("Enter your query:", placeholder="e.g. Which columns have missing values?")

    if st.button("Ask Agent"):
        with st.spinner("Thinking..."):
            try:
                output = ask_agent(query)
                st.success("✅ Agent Response")
                st.write(output)
            except Exception as e:
                st.error(f"Error: {e}")
else:
    st.info("Please upload a CSV file to begin.")
