# ui_widgets.py
def display_table(df):
    """Custom table display with formatting & compact widths"""
    import streamlit as st

    if df.empty:
        st.info("No data available.")
        return

    # Convert to HTML
    df_html = df.to_html(index=False, classes="custom-table", escape=False)

    # If Days Ago column exists → add CSS class
    if "Days Ago" in df.columns:
        df_html = df_html.replace(
            '<th>Days Ago</th>', '<th class="days-col">Days Ago</th>'
        ).replace(
            '<td>', '<td style="text-align:center;">'
        )

    # Inject CSS
    st.markdown(
        """
        <style>
        .custom-table th {
            text-align: center;
            padding: 6px;
        }
        .custom-table td {
            text-align: center;
            padding: 6px;
        }
        /* Column widths */
        .custom-table th:nth-child(1), .custom-table td:nth-child(1) { width: 30%; }  /* Recipe */
        .custom-table th:nth-child(2), .custom-table td:nth-child(2) { width: 20%; }  /* Item Type */
        .custom-table th:nth-child(3), .custom-table td:nth-child(3) { width: 25%; }  /* Last Eaten or Date */
        .custom-table th:nth-child(4), .custom-table td:nth-child(4) { width: 25%; }  /* Days Ago */
        
        /* Special Days Ago column styling */
        .custom-table th.days-col {
            text-align: center;
            white-space: nowrap;  /* keep "Days Ago" in one line */
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(df_html, unsafe_allow_html=True)
