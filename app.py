import streamlit as st
import pandas as pd
from data_manager import load_master_list, load_history, save_today_pick, save_new_recipe
from ui_widgets import format_table
from recommendations import get_today_suggestions

# Remove extra whitespace at top
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Sidebar Navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("",
    ["Pick Today's Recipe", "Master List", "History"]
)

master_list = load_master_list()
history = load_history()

if page == "Pick Today's Recipe":
    st.subheader("Choose option:")
    option = st.radio("", ["By Item Type", "Today's Suggestions"])

    if option == "By Item Type":
        item_types = master_list["Item Type"].dropna().unique()
        selected_type = st.selectbox("Select Item Type:", item_types)

        filtered_df = master_list[master_list["Item Type"] == selected_type].copy()

        # Merge with history to get last eaten
        last_eaten = history.groupby("Recipe")["Date"].max().reset_index()
        filtered_df = filtered_df.merge(last_eaten, on="Recipe", how="left").rename(
            columns={"Date": "Last Eaten"}
        )
        filtered_df["Days Ago"] = filtered_df["Last Eaten"].apply(
            lambda x: (pd.Timestamp.today() - pd.to_datetime(x)).days
            if pd.notnull(x) else None
        )

        st.dataframe(format_table(filtered_df))

        selected_recipe = st.radio(
            "Select recipe to save for today", filtered_df["Recipe"].tolist()
        )

        if st.button("Save Today's Pick (By Type)"):
            if save_today_pick(selected_recipe):
                st.success(f"Saved {selected_recipe} to history (GitHub).")
                st.rerun()
            else:
                st.error("Failed to save history.")

    elif option == "Today's Suggestions":
        suggestions = get_today_suggestions(master_list, history)
        st.dataframe(format_table(suggestions, show_item_type=True))

        selected_recipe = st.radio(
            "Select recipe to save for today", suggestions["Recipe"].tolist()
        )

        if st.button("Save Today's Pick (Suggestions)"):
            if save_today_pick(selected_recipe):
                st.success(f"Saved {selected_recipe} to history (GitHub).")
                st.rerun()
            else:
                st.error("Failed to save history.")

elif page == "Master List":
    st.subheader("Master Recipe List")
    st.dataframe(master_list)

    st.subheader("Add a new recipe")
    recipe = st.text_input("Recipe Name")
    item_type = st.selectbox("Item Type", ["Regular", "Occassional", "Rare"])

    if st.button("Add Recipe"):
        if recipe.strip():
            if save_new_recipe(recipe, item_type):
                st.success(f"Added {recipe} to master list.")
                st.rerun()
            else:
                st.error("Failed to add recipe.")
        else:
            st.warning("Please enter a recipe name.")

elif page == "History":
    st.subheader("Meal History")
    if not history.empty:
        history["Date"] = pd.to_datetime(history["Date"]).dt.strftime("%d-%m-%Y")
        st.dataframe(history.sort_values("Date", ascending=False).reset_index(drop=True))
    else:
        st.info("No history available.")
