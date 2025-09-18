import streamlit as st
import pandas as pd
from datetime import datetime

def display_filtered_table(master_df, history_df):
    if master_df.empty:
        st.warning("⚠️ No recipes available")
        return

    df = master_df.copy()

    # Merge history for "Last Eaten" and "Days Ago"
    last_eaten = history_df.groupby("Recipe")["Date"].max().reset_index()
    df = df.merge(last_eaten, on="Recipe", how="left").rename(columns={"Date": "Last Eaten"})

    # Format Last Eaten date
    df["Last Eaten"] = df["Last Eaten"].apply(
        lambda x: datetime.strptime(str(x), "%d-%m-%Y").strftime("%d-%m-%Y") if pd.notna(x) else "-"
    )

    # Compute Days Ago
    def days_ago(date_str):
        if date_str == "-" or pd.isna(date_str):
            return "-"
        try:
            return (datetime.today() - datetime.strptime(date_str, "%d-%m-%Y")).days
        except:
            return "-"
    df["Days Ago"] = df["Last Eaten"].apply(days_ago)

    # Display table
    st.dataframe(
        df[["Recipe", "Item Type", "Calories", "Last Eaten", "Days Ago"]],
        use_container_width=True,
        hide_index=True
    )

def display_today_suggestions(suggestions, history_df):
    if suggestions.empty:
        st.info("ℹ️ No suggestions available")
        return

    df = suggestions.copy()

    # Merge history
    last_eaten = history_df.groupby("Recipe")["Date"].max().reset_index()
    df = df.merge(last_eaten, on="Recipe", how="left").rename(columns={"Date": "Last Eaten"})

    # Format Last Eaten date
    df["Last Eaten"] = df["Last Eaten"].apply(
        lambda x: datetime.strptime(str(x), "%d-%m-%Y").strftime("%d-%m-%Y") if pd.notna(x) else "-"
    )

    # Compute Days Ago
    def days_ago(date_str):
        if date_str == "-" or pd.isna(date_str):
            return "-"
        try:
            return (datetime.today() - datetime.strptime(date_str, "%d-%m-%Y")).days
        except:
            return "-"
    df["Days Ago"] = df["Last Eaten"].apply(days_ago)

    # Ensure Item Type beside Recipe
    st.dataframe(
        df[["Recipe", "Item Type", "Calories", "Last Eaten", "Days Ago"]],
        use_container_width=True,
        hide_index=True
    )
