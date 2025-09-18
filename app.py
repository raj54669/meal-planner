# -----------------------------
btn_curr_month = col2.button("Current Month")
btn_prev_week = col3.button("Previous Week")
btn_curr_week = col4.button("Current Week")


filtered_df = history_df.copy()
if history_df.empty:
st.info("History is empty.")
else:
if btn_prev_month:
today = date.today()
first_of_this = today.replace(day=1)
last_of_prev = first_of_this - timedelta(days=1)
first_of_prev = last_of_prev.replace(day=1)
filtered_df = history_df[(history_df["Date"].dt.date >= first_of_prev) & (history_df["Date"].dt.date <= last_of_prev)]
elif btn_curr_month:
today = date.today()
first = today.replace(day=1)
filtered_df = history_df[(history_df["Date"].dt.date >= first) & (history_df["Date"].dt.date <= today)]
elif btn_prev_week:
today = date.today()
start_this_week = today - timedelta(days=today.weekday())
prev_start = start_this_week - timedelta(days=7)
prev_end = start_this_week - timedelta(days=1)
filtered_df = history_df[(history_df["Date"].dt.date >= prev_start) & (history_df["Date"].dt.date <= prev_end)]
elif btn_curr_week:
today = date.today()
start_this_week = today - timedelta(days=today.weekday())
filtered_df = history_df[(history_df["Date"].dt.date >= start_this_week) & (history_df["Date"].dt.date <= today)]
else:
filtered_df = history_df.copy()


if not filtered_df.empty:
filtered_df = filtered_df.copy()
filtered_df["Days Ago"] = filtered_df["Date"].apply(lambda d: (date.today() - d.date()).days if pd.notna(d) else pd.NA)
display_cols = ["Date", "Recipe", "Item Type", "Days Ago"]
# format Date column to DD-MM-YYYY
df_display = filtered_df[display_cols].copy()
df_display["Date"] = pd.to_datetime(df_display["Date"]).dt.strftime("%d-%m-%Y")
st.dataframe(df_display.sort_values("Date", ascending=False).reset_index(drop=True), use_container_width=True)


if st.button("Remove Today's Entry (if exists)"):
new_hist = history_df[history_df["Date"].dt.date != date.today()].reset_index(drop=True)
try:
ok, new_history_sha = save_history(new_hist, GITHUB_REPO, GITHUB_TOKEN, branch=GITHUB_BRANCH, sha=history_sha)
if ok:
st.success("Removed today's entry from GitHub history.")
safe_rerun()
else:
new_hist.to_csv("history.csv", index=False)
st.success("Removed from local history.csv.")
safe_rerun()
except Exception as e:
st.error(f"Failed to update history: {e}")


# -----------------------------
# End of app.py
# -----------------------------
