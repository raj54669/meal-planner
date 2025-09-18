import streamlit as st
import pandas as pd
import os
from datetime import datetime

# ---------- Utility Functions ----------

def load_data():
    if os.path.exists("master.csv"):
        master = pd.read_csv("master.csv")
    else:
        master = pd.DataFrame(columns=["Recipe", "Item Type"])

    if os.path.exists("history.csv"):
        history = pd.read_csv("history.csv", parse_dates=["Date"])
    else:
        history = pd.DataFrame(columns=["Recipe", "Item Type", "Date"])

    return master, history


def save_data(master, history):
    master.to_csv("master.csv", index=False)
    history.to_csv("history.csv", index=False)


def format_table(df, suggestions=False):
    """Format table for display"""
    if df.empty:
        return df

    df = df.copy()

    # Format date column
    if "Last Eaten" in df.columns:
        df["Last Eaten"] = df["Last Eaten"].apply(
            lambda x: pd.to_datetime(x).strftime("%d-%m-%Y") if pd.notnull(x) else ""
        )

    # Reorder columns for suggestions
    if suggestions and "Item Type" in df.columns:
        cols = ["Recipe", "Item Type", "Last Eaten", "Days Ago"]
        df = df[cols]

    return df


def add_history(history, recipe, item_type):
    """Add a new history row using concat instead of append"""
    new_row = pd.DataFrame([{
        "Recipe": recipe,
        "Item Type": item_type,
        "Date": datetime.today().strftime("%Y-%m-%d")
    }])
    history = pd.concat([history, new_row], ignore_index=True)
    return history


def add_master(master, recipe, item_type):
    """Add a new recipe to master list using concat"""
    new_row = pd.DataFrame([{
        "Recipe": recipe.strip(),
        "Item Type": item_type.strip()
    }])
    master = pd.concat([master, new_row], ignore_index=True)
    return master


# ---------- UI Styling ----------
st.set_page_config(page_title="NextBite – Meal Planner", layout="wide")

# CSS to remove top white space and center align days column
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1rem;
    }
    table td:nth-child(3), table th:nth-child(3) {
        text-align: center !important;
        width: 80px !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------- Main App ----------

st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Pick Today’s Recipe", "Master List", "History"])

master, history = load_data()

if page == "Pick Today’s Recipe":
    st.title("🍴 NextBite – Meal Planner App")
    st.header("Pick Today’s Recipe")

    option = st.radio("Choose option:", ["By Item Type", "Today’s Suggestions"])

    if option == "By Item Type":
        item_types = master["Item Type"].unique()
        selected_type = st.selectbox("Select Item Type:", item_types)

        filtered = master[master["Item Type"] == selected_type].copy()
        if not filtered.empty:
            filtered["Last Eaten"] = filtered["Recipe"].map(
                lambda r: history.loc[history["Recipe"] == r, "Date"].max()
                if not history.loc[history["Recipe"] == r].empty else None
            )
            filtered["Days Ago"] = filtered["Last Eaten"].apply(
                lambda d: (datetime.today() - d).days if pd.notnull(d) else None
            )

            st.table(format_table(filtered))

            recipe_choice = st.radio("Select recipe to save for today", filtered["Recipe"])
            if st.button("Save Today's Pick (By Type)"):
                history = add_history(history, recipe_choice, selected_type)
                save_data(master, history)
                st.success(f"Saved {recipe_choice} for today!")

    else:  # Today's Suggestions
        # Get last eaten dates
        latest = history.groupby("Recipe")["Date"].max().reset_index()
        df = master.merge(latest, on="Recipe", how="left")
        df.rename(columns={"Date": "Last Eaten"}, inplace=True)

        df["Days Ago"] = df["Last Eaten"].apply(
            lambda d: (datetime.today() - d).days if pd.notnull(d) else None
        )

        st.table(format_table(df, suggestions=True))

        recipe_choice = st.radio("Select recipe to save for today", df["Recipe"])
        item_type = df.loc[df["Recipe"] == recipe_choice, "Item Type"].values[0]
        if st.button("Save Today's Pick (Suggestions)"):
            history = add_history(history, recipe_choice, item_type)
            save_data(master, history)
            st.success(f"Saved {recipe_choice} for today!")

elif page == "Master List":
    st.header("Master List")
    st.caption("Add / Edit / Delete recipes. Edit opens a popup modal.")

    new_name = st.text_input("Recipe Name")
    new_type = st.text_input("Item Type")
    if st.button("Add Recipe"):
        if new_name and new_type:
            master = add_master(master, new_name, new_type)
            save_data(master, history)
            st.success(f"Added {new_name} to master list!")

    st.table(master)

elif page == "History":
    st.header("History")
    if not history.empty:
        st.table(history)
    else:
        st.info("No history yet.")
