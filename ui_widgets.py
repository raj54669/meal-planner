import streamlit as st

def display_table(df):
    """Custom table display with formatting"""
    if df.empty:
        st.info("No data available.")
        return

    # Apply CSS class to Days Ago column
    if "Days Ago" in df.columns:
        df_html = df.to_html(index=False, classes="dataframe", escape=False)
        df_html = df_html.replace(
            '<th>Days Ago</th>', '<th class="days-col">Days Ago</th>'
        ).replace(
            '<td>', '<td style="text-align:center;">'
        )
        st.markdown(df_html, unsafe_allow_html=True)
    else:
        st.dataframe(df, hide_index=True)
