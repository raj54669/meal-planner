import streamlit as st
import pandas as pd
import datetime
import io
from github import Github

# ---------- GitHub Setup ----------
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO_NAME = st.secrets["GITHUB_REPO"]     # updated here
BRANCH = st.secrets["GITHUB_BRANCH"]      # updated here

g = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_NAME)

# ---------- File Config ----------
MASTER_FILE = "master_meals.csv"
HISTORY_FILE = "meal_history.csv"

# ---------- Helper Functions ----------
def load_csv_from_repo(filename):
    try:
        file_content = repo.get_contents(filename, ref=BRANCH)
        return pd.read_csv(io.StringIO(file_content.decoded_content.decode()))
    except Exception:
        return pd.DataFrame()

def save_csv_to_repo(df, filename, message):
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    content = csv_buffer.getvalue()

    try:
        existing_file = repo.get_contents(filename, ref=BRANCH)
        repo.update_file(existing_file.path, message, content, existing_file.sha, branch=BRANCH)
    except Exception:
        repo.create_file(filename, message, content, branch=BRANCH)

# ---------- Load Data ----------
master_df = load_csv_from_repo(MASTER_FILE)
history_df = load_csv_from_repo(HISTORY_FILE)

# ---------- Streamlit UI ----------
st.title("🥗 Meal Planner with GitHub Storage")

# Show master meals
if not master_df.empty:
    st.subheader("Master Meal List")
    st.dataframe(master_df)
else:
    st.warning("No master meal list found!")

# Add new meal
with st.form("add_meal_form"):
    meal_name = st.text_input("Meal Name")
    calories = st.number_input("Calories", min_value=50, max_value=2000, step=50)
    submit = st.form_submit_button("Add Meal")

    if submit and meal_name:
        new_row = pd.DataFrame([[meal_name, calories]], columns=["Meal", "Calories"])
        master_df = pd.concat([master_df, new_row], ignore_index=True)
        save_csv_to_repo(master_df, MASTER_FILE, f"Added meal: {meal_name}")
        st.success(f"✅ {meal_name} added!")

# Log today's meal
st.subheader("Log Today's Meal")
if not master_df.empty:
    meal_choice = st.selectbox("Select a meal", master_df["Meal"].tolist())
    if st.button("Log Meal"):
        today = datetime.date.today()
        new_entry = pd.DataFrame([[today, meal_choice]], columns=["Date", "Meal"])
        history_df = pd.concat([history_df, new_entry], ignore_index=True)
        save_csv_to_repo(history_df, HISTORY_FILE, f"Logged meal: {meal_choice} on {today}")
        st.success(f"✅ Logged {meal_choice} for {today}")

# Show meal history
if not history_df.empty:
    st.subheader("Meal History")
    st.dataframe(history_df)
