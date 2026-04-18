import json
import calendar
import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime
from scipy.stats import norm, poisson, binom
import firebase_admin
from firebase_admin import credentials, db

# ================== FIREBASE INIT ==================
if not firebase_admin._apps:
    firebase_key = st.secrets["FIREBASE_KEY"]
    firebase_dict = json.loads(firebase_key)
    cred = credentials.Certificate(firebase_dict)
    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://expense-analyzer-db523-default-rtdb.asia-southeast1.firebasedatabase.app/"
    })

# ================== FIREBASE HELPERS ==================
def save_expenses(username, data):
    ref = db.reference(f"users/{username}/expenses")
    ref.set(data.to_dict(orient="records"))

def load_expenses(username):
    ref = db.reference(f"users/{username}/expenses")
    data = ref.get()
    if data:
        df = pd.DataFrame(data)
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0.0)
        return df
    return pd.DataFrame(columns=["Date", "Category", "Amount"])

def save_user(username, pin):
    ref = db.reference(f"users/{username}/profile")
    ref.set({"pin": pin})

def load_user(username):
    ref = db.reference(f"users/{username}/profile")
    return ref.get()

def save_income(username, income):
    ref = db.reference(f"users/{username}/profile/income")
    ref.set(income)

def load_income(username):
    ref = db.reference(f"users/{username}/profile/income")
    val = ref.get()
    return float(val) if val else 0.0

# ================== CONFIG ==================
st.set_page_config(page_title="Smart Expense Analyzer", layout="wide")
st.title("💰 Smart Expense Analyzer")

# ================== USER LOGIN ==================
st.sidebar.header("👤 User")
username = st.sidebar.text_input("Enter username").strip()

if username == "":
    st.warning("Please enter a username to continue.")
    st.stop()

user_profile = load_user(username)

if user_profile:
    pin = st.sidebar.text_input("Enter PIN", type="password").strip()

    if pin == "":
        st.info("Please enter your PIN.")
        st.stop()

    if pin != str(user_profile.get("pin", "")):
        st.error("❌ Wrong PIN. Please try again.")
        st.stop()

    if "data" not in st.session_state or st.session_state.get("user") != username:
        st.session_state.data = load_expenses(username)
        st.session_state.user = username
        st.session_state.income = load_income(username)

    st.sidebar.success(f"✅ Welcome, {username}!")

else:
    st.sidebar.subheader("🆕 New User — Set PIN")
    new_pin = st.sidebar.text_input("Choose a PIN", type="password").strip()

    if new_pin == "":
        st.warning("Please set a PIN to create your account.")
        st.stop()

    save_user(username, new_pin)
    st.success("🎉 Account created! Please log in again.")
    st.stop()

# ================== INCOME SIDEBAR ==================
st.sidebar.subheader("💰 Monthly Income")

if "income" not in st.session_state:
    st.session_state.income = load_income(username)

new_income = st.sidebar.number_input(
    "Monthly Income (₹)", min_value=0.0, value=st.session_state.income
)

if st.sidebar.button("Save Income"):
    st.session_state.income = new_income
    save_income(username, new_income)
    st.sidebar.success("✅ Income saved!")
    st.rerun()

# ================== WORKING DATA ==================
data = st.session_state.data

if not data.empty:
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    data = data.dropna(subset=["Date"])
    data["Amount"] = pd.to_numeric(data["Amount"], errors="coerce").fillna(0.0)
    st.session_state.data = data

# ================== COMMON VARS ==================
today = datetime.today()
days_in_month = calendar.monthrange(today.year, today.month)[1]
days_left = max(days_in_month - today.day, 1)
total_expense = data["Amount"].sum() if not data.empty else 0.0
balance = st.session_state.income - total_expense
ideal_daily = st.session_state.income / days_in_month if days_in_month > 0 else 0
adjusted_daily = balance / days_left

# ================== TABS ==================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏠 Home", "➕ Add Expense", "📊 Overview", "🔮 Insights", "🎯 Smart Analysis"
])

# ══════════════════════════════════════════
# TAB 1 — HOME
# ══════════════════════════════════════════
with tab1:
    st.header("💼 Your Budget at a Glance")

    col1, col2, col3 = st.columns(3)
    col1.metric("Monthly Income", f"₹{st.session_state.income:.2f}")
    col2.metric("Total Spent", f"₹{total_expense:.2f}")
    col3.metric("Money Left", f"₹{balance:.2f}")

    st.subheader("🧠 Budget Advice")
    st.info(f"💡 You should ideally spend ₹{ideal_daily:.2f} per day to stay on track.")

    if balance < 0:
        st.error("⚠️ You've gone over your monthly budget!")
    else:
        st.warning(f"⚠️ To finish the month safely, keep your daily spending under ₹{adjusted_daily:.2f}.")

    if not data.empty:
        avg_spend = data["Amount"].mean()
        if avg_spend > adjusted_daily:
            st.error("🚨 Your recent spending is too high — you may run out of money before month end!")
        elif avg_spend > ideal_daily:
            st.warning("📊 You're spending a bit more than planned each day. Try to cut back a little.")
        else:
            st.success("✅ Great job! Your spending is well within budget.")

# ══════════════════════════════════════════
# TAB 2 — ADD EXPENSE
# ══════════════════════════════════════════
with tab2:
    st.header("➕ Add a New Expense")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        date = st.date_input("Date")
    with col_b:
        category = st.selectbox(
            "Category", ["Food", "Travel", "Shopping", "Entertainment", "Others"]
        )
    with col_c:
        amount = st.number_input("Amount (₹)", min_value=0.0, step=1.0)

    if st.button("Add Expense"):
        if amount <= 0:
            st.error("Please enter an amount greater than ₹0.")
        else:
            # FIX: ensure Amount column dtype is float before concat
            new_row = pd.DataFrame({
                "Date": [str(date)],
                "Category": [category],
                "Amount": [float(amount)]
            })
            current = st.session_state.data.copy()
            current["Amount"] = pd.to_numeric(current["Amount"], errors="coerce").fillna(0.0)
            st.session_state.data = pd.concat([current, new_row], ignore_index=True)
            save_expenses(username, st.session_state.data)
            st.success(f"✅ Added ₹{amount:.2f} for {category} on {date}!")
            st.rerun()

    if st.button("↩️ Undo Last Expense"):
        if len(st.session_state.data) > 0:
            st.session_state.data = st.session_state.data.iloc[:-1].reset_index(drop=True)
            save_expenses(username, st.session_state.data)
            st.success("Last expense removed.")
            st.rerun()
        else:
            st.info("No expenses to undo.")

    st.subheader("📋 All Expenses")
    if not data.empty:
        display_data = data.copy()
        display_data["Date"] = display_data["Date"].dt.strftime("%d %b %Y")
        display_data["Amount"] = display_data["Amount"].apply(lambda x: f"₹{x:.2f}")
        st.dataframe(display_data, use_container_width=True, hide_index=True)
    else:
        st.info("No expenses added yet.")

# ══════════════════════════════════════════
# TAB 3 — OVERVIEW
# ══════════════════════════════════════════
with tab3:
    st.header("📊 Spending Overview")

    if not data.empty:
        total = data["Amount"].sum()
        avg = data["Amount"].mean()
        median = data["Amount"].median()
        std_dev = data["Amount"].std()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Spent", f"₹{total:.2f}")
        c2.metric("Average per Expense", f"₹{avg:.2f}",
                  help="The typical amount you spend each time")
        c3.metric("Middle Expense Value", f"₹{median:.2f}",
                  help="Half your expenses are above this, half are below")
        c4.metric("How Much It Varies", f"₹{std_dev:.2f}",
                  help="How different your spending is day to day — lower means more consistent")

        st.subheader("🗂️ Where Your Money Goes")
        cat_totals = data.groupby("Category")["Amount"].sum()
        st.bar_chart(cat_totals)

        st.subheader("📅 Daily Spending Over Time")
        st.line_chart(data.groupby("Date")["Amount"].sum())

    else:
        st.info("No expenses recorded yet. Add some in the ➕ Add Expense tab!")

# ══════════════════════════════════════════
# TAB 4 — INSIGHTS (PREDICTION)
# ══════════════════════════════════════════
with tab4:
    st.header("🔮 Future Spending Forecast")

    if not data.empty and len(data) > 3:
        st.write("Based on your past spending, here's what the next 7 days might look like:")

        data_sorted = data.sort_values("Date")
        y = data_sorted["Amount"].values.astype(float)
        x = np.arange(len(y))
        slope, intercept = np.polyfit(x, y, 1)
        future_x = np.arange(len(y), len(y) + 7)
        predictions = slope * future_x + intercept

        pred_df = pd.DataFrame(
            {"Day": [f"Day +{i+1}" for i in range(7)], "Predicted Spend (₹)": predictions}
        ).set_index("Day")
        st.line_chart(pred_df)

        trend_msg = "going up 📈" if slope > 0 else "going down 📉"
        st.info(f"Your spending trend is {trend_msg} by about ₹{abs(slope):.2f} per entry.")

        total_predicted = predictions.sum()
        if total_predicted > balance:
            st.error(f"🚨 Your predicted spending for the next 7 days (₹{total_predicted:.2f}) could exceed your remaining balance (₹{balance:.2f})!")
        else:
            st.success(f"✅ Your predicted 7-day spend is ₹{total_predicted:.2f}, which fits within your remaining balance.")

    elif not data.empty:
        st.info("Add more than 3 expenses to see your spending forecast.")
    else:
        st.info("No expenses yet. Start adding expenses to see predictions!")

# ══════════════════════════════════════════
# TAB 5 — SMART ANALYSIS
# ══════════════════════════════════════════
with tab5:
    st.header("🎯 Smart Spending Analysis")

    if data.empty or len(data) < 5:
        st.info("⚠️ Add at least 5 expenses to unlock smart analysis.")
    else:
        daily = data.groupby("Date")["Amount"].sum().reset_index()
        daily.columns = ["Date", "DailyTotal"]
        amounts = daily["DailyTotal"].values.astype(float)

        mu = float(np.mean(amounts))
        sigma = float(np.std(amounts))
        n_days = len(amounts)
        skewness = float(pd.Series(amounts).skew())

        # ── SPENDING PERSONALITY ─────────────────────────────────
        st.subheader("🧬 Your Spending Personality")

        p1, p2, p3 = st.columns(3)
        p1.metric("Your Usual Daily Spend", f"₹{mu:.2f}",
                  help="The average amount you spend on a typical day")
        p2.metric("Day-to-Day Variation", f"₹{sigma:.2f}",
                  help="How much your daily spending jumps around — lower is more stable")
        p3.metric("Spending Pattern", 
                  "Spiky 🌋" if skewness > 0.5 else ("Heavy starter 🏋️" if skewness < -0.5 else "Steady 🟢"),
                  help="Spiky = occasional big days. Heavy starter = you spend more early. Steady = consistent.")

        if skewness > 0.5:
            st.info("📈 You have a few days where you spend a lot more than usual — things like shopping trips or outings.")
        elif skewness < -0.5:
            st.info("📉 You tend to spend heavily early in the month and slow down later.")
        else:
            st.success("✅ Your spending is pretty consistent — you're a steady spender!")

        st.divider()

        # ── OVERSPENDING RISK ────────────────────────────────────
        st.subheader("🔔 Overspending Risk Check")
        st.write("Set a daily limit and see how often you're likely to go over it.")

        if sigma == 0:
            st.warning("All your daily expenses are the same — can't calculate risk.")
        else:
            oc1, oc2 = st.columns(2)

            with oc1:
                threshold = st.number_input(
                    "Your daily spending limit (₹)",
                    min_value=0.0,
                    value=float(round(mu * 1.2, 2)),
                    key="nd_threshold",
                )

            with oc2:
                z_score = (threshold - mu) / sigma
                prob_exceed = float(1 - norm.cdf(z_score))
                st.metric("Chance of going over your limit", f"{prob_exceed*100:.1f}%")
                st.metric("Chance of staying within limit", f"{(1-prob_exceed)*100:.1f}%")

            st.markdown(
                f"""
                Based on your past spending (usual daily: ₹{mu:.2f}, variation: ₹{sigma:.2f}):
                - 68% of your days, you spend between **₹{mu-sigma:.2f}** and **₹{mu+sigma:.2f}**
                - 95% of your days, you spend between **₹{mu-2*sigma:.2f}** and **₹{mu+2*sigma:.2f}**
                """
            )

            if prob_exceed > 0.5:
                st.error(f"🚨 You cross ₹{threshold:.0f} more than half the time — consider raising your budget or cutting back.")
            elif prob_exceed > 0.25:
                st.warning(f"⚠️ You have a 1 in 4 chance of exceeding ₹{threshold:.0f} on any given day.")
            else:
                st.success(f"✅ You rarely go over ₹{threshold:.0f}. You're in good control!")

        st.divider()

        # ── BIG SPENDING DAYS ────────────────────────────────────
        st.subheader("☄️ How Often Do You Have a Big Spending Day?")
        st.write("A 'big spending day' is when you spend more than your usual amount by a significant margin.")

        bd1, bd2 = st.columns(2)

        with bd1:
            large_threshold = st.number_input(
                "What counts as a 'big spending day'? (₹)",
                min_value=0.0,
                value=float(round(mu + sigma, 2)),
                key="poisson_threshold",
            )
            target_days = st.number_input(
                "How many big spending days are you expecting this month?",
                min_value=0, max_value=30, value=3, key="poisson_target"
            )

        with bd2:
            large_days = int(np.sum(amounts > large_threshold))
            m = max((large_days / n_days) * days_in_month, 0.01)
            px = float(poisson.pmf(target_days, m))
            p_at_least_one = float(1 - poisson.pmf(0, m))

            st.metric("Expected big-spend days this month", f"{m:.1f} days")
            st.metric(f"Chance of exactly {target_days} big days", f"{px*100:.2f}%")
            st.metric("Chance of at least 1 big day", f"{p_at_least_one*100:.1f}%")

        st.markdown("**Probability breakdown for this month:**")
        poisson_table = pd.DataFrame({
            "Number of big-spend days": list(range(8)),
            "Chance of exactly this many": [f"{poisson.pmf(x, m)*100:.2f}%" for x in range(8)],
            "Chance of this many or fewer": [f"{poisson.cdf(x, m)*100:.2f}%" for x in range(8)],
        })
        st.dataframe(poisson_table, use_container_width=True, hide_index=True)

        st.divider()

        # ── BUDGET SUCCESS STREAK ────────────────────────────────
        st.subheader("🎯 Will You Stay Under Budget?")
        st.write("Based on your history, what are the chances you stick to your daily budget for most of the month?")

        bs1, bs2 = st.columns(2)

        with bs1:
            n_trials = st.number_input(
                "Days in this month", min_value=1, max_value=31,
                value=int(days_in_month), key="binom_n"
            )
            success_days = st.number_input(
                "How many days do you want to stay under budget?",
                min_value=0, max_value=int(n_trials),
                value=int(n_trials * 0.7), key="binom_k"
            )

        with bs2:
            if ideal_daily > 0 and n_days > 0:
                under_budget_days = int(np.sum(amounts <= ideal_daily))
                p_success = max(0.01, min(0.99, under_budget_days / n_days))
            else:
                under_budget_days = 0
                p_success = 0.5

            q_fail = 1 - p_success
            mean_binom = n_trials * p_success
            p_at_least = float(1 - binom.cdf(success_days - 1, n_trials, p_success))
            p_exact = float(binom.pmf(success_days, n_trials, p_success))

            st.metric("Your daily budget success rate", f"{p_success*100:.1f}%",
                      help="How often you've stayed under your ideal daily budget in the past")
            st.metric(f"Chance of staying under budget for {success_days}+ days", f"{p_at_least*100:.1f}%")
            st.metric("On average, you'll stay under budget for", f"{mean_binom:.0f} days")

        if p_at_least > 0.7:
            st.success(f"✅ Great! There's a strong {p_at_least*100:.0f}% chance you'll stay on budget for {success_days}+ days.")
        elif p_at_least > 0.4:
            st.warning(f"⚠️ It's possible but not certain — {p_at_least*100:.0f}% chance of {success_days}+ good days.")
        else:
            st.error(f"🚨 Only {p_at_least*100:.0f}% chance. You might want to cut back to hit {success_days} budget-friendly days.")

        st.markdown("**Day-by-day success probability:**")
        rows = list(range(min(n_trials + 1, 16)))
        binom_table = pd.DataFrame({
            "Good budget days": rows,
            "Chance of exactly this many": [f"{binom.pmf(x, n_trials, p_success)*100:.2f}%" for x in rows],
            "Chance of this many or fewer": [f"{binom.cdf(x, n_trials, p_success)*100:.2f}%" for x in rows],
            "Chance of this many or more": [f"{(1-binom.cdf(x-1, n_trials, p_success))*100:.2f}%" for x in rows],
        })
        st.dataframe(binom_table, use_container_width=True, hide_index=True)

        st.divider()

        # ── CATEGORY PROBABILITY ─────────────────────────────────
        st.subheader("🎲 What Do You Usually Spend On?")
        st.write("Based on your past transactions, here's how likely you are to spend in each category next time:")

        cat_counts = data.groupby("Category")["Amount"].count()
        total_txns = cat_counts.sum()
        cat_probs = (cat_counts / total_txns * 100).round(2)

        prob_df = pd.DataFrame({
            "Category": cat_probs.index,
            "Times you spent here": cat_counts.values,
            "Likelihood of next expense": [f"{p:.1f}%" for p in cat_probs.values],
        })

        st.dataframe(prob_df, use_container_width=True, hide_index=True)

        most_likely = cat_probs.idxmax()
        st.info(f"🎯 Your most common spending category is **{most_likely}** — you spend here {cat_probs[most_likely]:.1f}% of the time.")
