import streamlit as st
import pandas as pd
import datetime
import io
from github import Github

# ---------- GitHub Setup ----------
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO_NAME = st.secrets["REPO_NAME"]
g = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_NAME)

MASTER_FILE = "master_list.csv"
HISTORY_FILE = "history.csv"

# ---------- Utility: Load or Init CSV ----------
def load_or_init_csv(filename, columns):
    try:
        file_content = repo.get_contents(filename).decoded_content
        df = pd.read_csv(io.StringIO(file_content.decode("utf-8")))
        # Ensure required columns exist
        for col in columns:
            if col not in df.columns:
                df[col] = None
        return df
    except Exception:
        # Create an empty DataFrame with the right headers
        df = pd.DataFrame(columns=columns)
        save_csv(df, filename)
        return df

def save_csv(df, filename):
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    try:
        contents = repo.get_contents(filename)
        repo.update_file(contents.path, f"Update {filename}", csv_buffer.getvalue(), contents.sha)
    except Exception:
        repo.create_file(filename, f"Create {filename}", csv_buffer.getvalue())

# ---------- Load Data ----------
df_master = load_or_init_csv(MASTER_FILE, ["Recipe", "Item Type"])
df_history = load_or_init_csv(HISTORY_FILE, ["Recipe", "Item Type", "Last Eaten"])

# ---------- Streamlit UI ----------
st.set_page_config(page_title="NextBite – Meal Planner App", layout="wide")
st.title("🍴 NextBite – Meal Planner App")

# Navigation
page = st.sidebar.radio("Go to", ["Pick Today’s Recipe", "Master List", "History"])

# ---------- Page 1: Pick Today’s Recipe ----------
if page == "Pick Today’s Recipe":
    st.header("Pick Today’s Recipe")

    choice = st.radio("Choose option:", ["By Item Type", "Today’s Suggestions"])

    today = datetime.date.today().strftime("%Y-%m-%d")

    if choice == "By Item Type":
        if df_master.empty:
            st.warning("⚠️ No recipes in master list. Please add recipes first.")
        else:
            item_types = sorted(df_master["Item Type"].dropna().unique())
            if len(item_types) == 0:
                st.info("No item types available yet.")
            else:
                selected_type = st.selectbox("Select Item Type:", item_types)
                filtered = df_master[df_master["Item Type"] == selected_type]

                st.write("### Recipes")
                st.table(filtered)

                recipe_choice = st.selectbox("Select recipe to save for today:", filtered["Recipe"].tolist())

                if st.button("Save Today's Pick"):
                    if recipe_choice:
                        new_entry = pd.DataFrame([{
                            "Recipe": recipe_choice,
                            "Item Type": selected_type,
                            "Last Eaten": today
                        }])
                        df_history = pd.concat([df_history, new_entry], ignore_index=True)
                        save_csv(df_history, HISTORY_FILE)
                        st.success(f"✅ Saved {recipe_choice} as today’s meal!")

    elif choice == "Today’s Suggestions":
        if df_master.empty:
            st.warning("⚠️ No recipes in master list. Please add recipes first.")
        else:
            # Suggestions = recipes not eaten in last 7 days
            df_suggestions = df_master.copy()
            df_suggestions["Last Eaten"] = df_suggestions["Recipe"].map(
                df_history.set_index("Recipe")["Last Eaten"].to_dict()
            )
            df_suggestions["Days Ago"] = df_suggestions["Last Eaten"].apply(
                lambda x: (datetime.date.today() - datetime.date.fromisoformat(x)).days if pd.notnull(x) else "Never"
            )

            st.write("### Suggestions")
            st.table(df_suggestions[["Recipe", "Item Type", "Last Eaten", "Days Ago"]])

            recipe_choice = st.selectbox(
                "Select recipe to save for today:",
                df_suggestions["Recipe"].tolist() if not df_suggestions.empty else []
            )

            if st.button("Save Today's Pick"):
                if recipe_choice:
                    row = df_master[df_master["Recipe"] == recipe_choice]
                    if not row.empty:
                        item_type = row["Item Type"].values[0]
                    else:
                        item_type = "Unknown"

                    new_entry = pd.DataFrame([{
                        "Recipe": recipe_choice,
                        "Item Type": item_type,
                        "Last Eaten": today
                    }])
                    df_history = pd.concat([df_history, new_entry], ignore_index=True)
                    save_csv(df_history, HISTORY_FILE)
                    st.success(f"✅ Saved {recipe_choice} as today’s meal!")

# ---------- Page 2: Master List ----------
elif page == "Master List":
    st.header("Master Recipe List")

    if df_master.empty:
        st.info("No recipes in the master list yet. Add some below.")

    st.table(df_master)

    with st.expander("➕ Add New Recipe"):
        new_recipe = st.text_input("Recipe Name")
        new_type = st.text_input("Item Type")
        if st.button("Add Recipe"):
            if new_recipe and new_type:
                new_row = pd.DataFrame([{"Recipe": new_recipe, "Item Type": new_type}])
                df_master = pd.concat([df_master, new_row], ignore_index=True)
                save_csv(df_master, MASTER_FILE)
                st.success(f"✅ Added {new_recipe} to master list!")
            else:
                st.error("Please fill both fields.")

# ---------- Page 3: History ----------
elif page == "History":
    st.header("Meal History")

    if df_history.empty:
        st.info("No meals have been logged yet.")
    else:
        st.table(df_history)
