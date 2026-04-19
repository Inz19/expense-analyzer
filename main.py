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
    records = data.copy()
    records["Date"] = records["Date"].astype(str)
    records["Amount"] = records["Amount"].astype(float)
    ref.set(records.to_dict(orient="records"))

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

# Only hide sidebar — no other CSS overrides that break inputs
st.markdown("""
<style>
[data-testid="stSidebar"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ================== SESSION STATE ==================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = None

# ================== LOGIN SCREEN ==================
if not st.session_state.logged_in:

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align:center'>Smart Expense Analyzer</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; opacity:0.6'>Track, understand, and improve your spending</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    col_l, col_c, col_r = st.columns([1, 1.2, 1])
    with col_c:
        username = st.text_input("Username", placeholder="Enter your username")
        pin      = st.text_input("PIN", type="password", placeholder="Enter your PIN")
        st.markdown("<br>", unsafe_allow_html=True)
        b1, b2 = st.columns(2)
        with b1:
            login_btn    = st.button("Sign In", use_container_width=True)
        with b2:
            register_btn = st.button("Create Account", use_container_width=True)

        if login_btn:
            if not username.strip() or not pin.strip():
                st.error("Please enter both username and PIN.")
            else:
                profile = load_user(username.strip())
                if not profile:
                    st.error("Account not found. Please create one.")
                elif pin.strip() != str(profile.get("pin", "")):
                    st.error("Incorrect PIN.")
                else:
                    st.session_state.logged_in = True
                    st.session_state.user      = username.strip()
                    st.session_state.data      = load_expenses(username.strip())
                    st.session_state.income    = load_income(username.strip())
                    st.rerun()

        if register_btn:
            if not username.strip() or not pin.strip():
                st.error("Please enter both a username and PIN.")
            else:
                if load_user(username.strip()):
                    st.error("Username already taken. Please sign in.")
                else:
                    save_user(username.strip(), pin.strip())
                    st.success("Account created. You can now sign in.")

    st.stop()

# ================== LOGGED-IN SETUP ==================
username = st.session_state.user
data     = st.session_state.data

if not data.empty:
    data["Date"]   = pd.to_datetime(data["Date"], errors="coerce")
    data           = data.dropna(subset=["Date"])
    data["Amount"] = pd.to_numeric(data["Amount"], errors="coerce").fillna(0.0)
    st.session_state.data = data

today          = datetime.today()
days_in_month  = calendar.monthrange(today.year, today.month)[1]
days_left      = max(days_in_month - today.day, 1)
total_expense  = data["Amount"].sum() if not data.empty else 0.0
balance        = st.session_state.income - total_expense
ideal_daily    = st.session_state.income / days_in_month if days_in_month > 0 else 0
adjusted_daily = balance / days_left

# ---- Top bar ----
col_t, col_u = st.columns([6, 1])
with col_t:
    st.title("Smart Expense Analyzer")
    st.caption(f"Signed in as **{username}**")
with col_u:
    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("Sign Out"):
        for k in ["logged_in", "user", "data", "income"]:
            st.session_state.pop(k, None)
        st.rerun()

st.divider()

# ================== TABS ==================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Home", "Add Expense", "Overview", "Forecast", "Smart Analysis"
])

# ══════════════════════════════════════════
# TAB 1 — HOME
# ══════════════════════════════════════════
with tab1:
    st.header("Your Budget at a Glance")

    inc_col, save_col = st.columns([3, 1])
    with inc_col:
        new_income = st.number_input(
            "Monthly Income (INR)", min_value=0.0,
            value=st.session_state.income
        )
    with save_col:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Save Income"):
            st.session_state.income = new_income
            save_income(username, new_income)
            st.rerun()

    st.markdown("")
    col1, col2, col3 = st.columns(3)
    col1.metric("Monthly Income", f"INR {st.session_state.income:,.2f}")
    col2.metric("Total Spent",    f"INR {total_expense:,.2f}")
    col3.metric("Money Left",     f"INR {balance:,.2f}")

    st.subheader("Budget Advice")
    st.info(f"Ideal daily spend to stay on track: INR {ideal_daily:,.2f}")

    if balance < 0:
        st.error("You have exceeded your monthly budget.")
    else:
        st.warning(f"To finish the month safely, keep daily spending under INR {adjusted_daily:,.2f}.")

    if not data.empty:
        avg_spend = data["Amount"].mean()
        if avg_spend > adjusted_daily:
            st.error("Your recent spending is too high — you may run out of money before month end.")
        elif avg_spend > ideal_daily:
            st.warning("You are spending a bit more than planned each day. Try to cut back a little.")
        else:
            st.success("Great job! Your spending is well within budget.")

# ══════════════════════════════════════════
# TAB 2 — ADD EXPENSE
# ══════════════════════════════════════════
with tab2:
    st.header("Add a New Expense")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        date = st.date_input("Date")
    with col_b:
        category = st.selectbox(
            "Category", ["Food", "Travel", "Shopping", "Entertainment", "Others"]
        )
    with col_c:
        amount = st.number_input("Amount (INR)", min_value=0.0, step=1.0)

    btn1, btn2, _ = st.columns([1, 1, 3])
    with btn1:
        if st.button("Add Expense", use_container_width=True):
            if amount <= 0:
                st.error("Please enter an amount greater than INR 0.")
            else:
                new_row = pd.DataFrame({
                    "Date":     [str(date)],
                    "Category": [category],
                    "Amount":   [float(amount)]
                })
                current = st.session_state.data.copy()
                current["Amount"] = pd.to_numeric(current["Amount"], errors="coerce").fillna(0.0)
                st.session_state.data = pd.concat([current, new_row], ignore_index=True)
                save_expenses(username, st.session_state.data)
                st.success(f"Added INR {amount:,.2f} for {category} on {date}.")
                st.rerun()

    with btn2:
        if st.button("Undo Last", use_container_width=True):
            if len(st.session_state.data) > 0:
                st.session_state.data = st.session_state.data.iloc[:-1].reset_index(drop=True)
                save_expenses(username, st.session_state.data)
                st.success("Last expense removed.")
                st.rerun()
            else:
                st.info("No expenses to undo.")

    st.subheader("All Expenses")
    if not data.empty:
        display_data = data.copy()
        display_data["Date"]   = display_data["Date"].dt.strftime("%d %b %Y")
        display_data["Amount"] = display_data["Amount"].apply(lambda x: f"INR {x:,.2f}")
        st.dataframe(display_data, use_container_width=True, hide_index=True)
    else:
        st.info("No expenses added yet.")

# ══════════════════════════════════════════
# TAB 3 — OVERVIEW
# ══════════════════════════════════════════
with tab3:
    st.header("Spending Overview")

    if not data.empty:
        total   = data["Amount"].sum()
        avg     = data["Amount"].mean()
        median  = data["Amount"].median()
        std_dev = data["Amount"].std()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Spent",         f"INR {total:,.2f}")
        c2.metric("Average per Expense", f"INR {avg:,.2f}",
                  help="The typical amount you spend each time")
        c3.metric("Median Expense",      f"INR {median:,.2f}",
                  help="Half your expenses are above this, half are below")
        c4.metric("Std Deviation",       f"INR {std_dev:,.2f}",
                  help="How different your spending is day to day")

        st.subheader("Spending by Category")
        st.bar_chart(data.groupby("Category")["Amount"].sum())

        st.subheader("Daily Spending Over Time")
        st.line_chart(data.groupby("Date")["Amount"].sum())
    else:
        st.info("No expenses recorded yet. Add some in the Add Expense tab.")

# ══════════════════════════════════════════
# TAB 4 — FORECAST
# ══════════════════════════════════════════
with tab4:
    st.header("7-Day Spending Forecast")

    if not data.empty and len(data) > 3:
        st.write("Based on your past spending, here is what the next 7 days might look like:")

        data_sorted      = data.sort_values("Date")
        y                = data_sorted["Amount"].values.astype(float)
        x                = np.arange(len(y))
        slope, intercept = np.polyfit(x, y, 1)
        future_x         = np.arange(len(y), len(y) + 7)
        predictions      = slope * future_x + intercept

        pred_df = pd.DataFrame(
            {"Day": [f"Day +{i+1}" for i in range(7)], "Predicted Spend (INR)": predictions}
        ).set_index("Day")
        st.line_chart(pred_df)

        direction = "increasing" if slope > 0 else "decreasing"
        st.info(f"Your spending trend is {direction} by about INR {abs(slope):,.2f} per entry.")

        total_predicted = predictions.sum()
        if total_predicted > balance:
            st.error(
                f"Your predicted 7-day spend (INR {total_predicted:,.2f}) may exceed "
                f"your remaining balance (INR {balance:,.2f})."
            )
        else:
            st.success(
                f"Your predicted 7-day spend is INR {total_predicted:,.2f}, "
                f"which fits within your remaining balance."
            )

    elif not data.empty:
        st.info("Add more than 3 expenses to see your spending forecast.")
    else:
        st.info("No expenses yet. Start adding to see predictions.")

# ══════════════════════════════════════════
# TAB 5 — SMART ANALYSIS
# ══════════════════════════════════════════
with tab5:
    st.header("Smart Spending Analysis")

    if data.empty or len(data) < 5:
        st.info("Add at least 5 expenses to unlock smart analysis.")
    else:
        daily    = data.groupby("Date")["Amount"].sum().reset_index()
        daily.columns = ["Date", "DailyTotal"]
        amounts  = daily["DailyTotal"].values.astype(float)
        mu       = float(np.mean(amounts))
        sigma    = float(np.std(amounts))
        n_days   = len(amounts)
        skewness = float(pd.Series(amounts).skew())

        # ── SPENDING PERSONALITY ─────────────────────────────────
        st.subheader("Your Spending Personality")

        p1, p2, p3 = st.columns(3)
        p1.metric("Usual Daily Spend",    f"INR {mu:,.2f}",
                  help="The average amount you spend on a typical day")
        p2.metric("Day-to-Day Variation", f"INR {sigma:,.2f}",
                  help="How much your daily spending jumps around")
        pattern = "Spiky" if skewness > 0.5 else ("Heavy starter" if skewness < -0.5 else "Steady")
        p3.metric("Spending Pattern", pattern,
                  help="Spiky = occasional big days. Heavy starter = spend more early. Steady = consistent.")

        if skewness > 0.5:
            st.info("You have a few days where you spend a lot more than usual — like shopping trips or outings.")
        elif skewness < -0.5:
            st.info("You tend to spend heavily early in the month and slow down later.")
        else:
            st.success("Your spending is pretty consistent — you are a steady spender.")

        st.divider()

        # ── OVERSPENDING RISK ────────────────────────────────────
        st.subheader("Overspending Risk Check")
        st.write("Set a daily limit and see how often you are likely to go over it.")

        if sigma == 0:
            st.warning("All your daily expenses are the same — risk calculation not available.")
        else:
            oc1, oc2 = st.columns(2)
            with oc1:
                threshold = st.number_input(
                    "Your daily spending limit (INR)",
                    min_value=0.0,
                    value=float(round(mu * 1.2, 2)),
                    key="nd_threshold",
                )
            with oc2:
                z_score     = (threshold - mu) / sigma
                prob_exceed = float(1 - norm.cdf(z_score))
                st.metric("Chance of going over limit",     f"{prob_exceed*100:.1f}%")
                st.metric("Chance of staying within limit", f"{(1-prob_exceed)*100:.1f}%")

            st.markdown(
                f"""
                Based on your past spending (avg: INR {mu:,.2f}, variation: INR {sigma:,.2f}):
                - 68% of days you spend between **INR {mu-sigma:,.2f}** and **INR {mu+sigma:,.2f}**
                - 95% of days you spend between **INR {mu-2*sigma:,.2f}** and **INR {mu+2*sigma:,.2f}**
                """
            )

            if prob_exceed > 0.5:
                st.error(f"You cross INR {threshold:,.0f} more than half the time — consider raising your budget or cutting back.")
            elif prob_exceed > 0.25:
                st.warning(f"You have roughly a 1 in 4 chance of exceeding INR {threshold:,.0f} on any given day.")
            else:
                st.success(f"You rarely go over INR {threshold:,.0f}. You are in good control.")

        st.divider()

        # ── BIG SPENDING DAYS ────────────────────────────────────
        st.subheader("How Often Do You Have a High-Spend Day?")
        st.write("A high-spend day is when you spend significantly more than your usual amount.")

        bd1, bd2 = st.columns(2)
        with bd1:
            large_threshold = st.number_input(
                "Define a high-spend day (INR)",
                min_value=0.0,
                value=float(round(mu + sigma, 2)),
                key="poisson_threshold",
            )
            target_days = st.number_input(
                "Expected high-spend days this month",
                min_value=0, max_value=30, value=3, key="poisson_target"
            )
        with bd2:
            large_days     = int(np.sum(amounts > large_threshold))
            m              = max((large_days / n_days) * days_in_month, 0.01)
            px             = float(poisson.pmf(target_days, m))
            p_at_least_one = float(1 - poisson.pmf(0, m))
            st.metric("Expected high-spend days this month",        f"{m:.1f}")
            st.metric(f"Chance of exactly {target_days} such days", f"{px*100:.2f}%")
            st.metric("Chance of at least one",                     f"{p_at_least_one*100:.1f}%")

        st.markdown("**Probability breakdown for this month:**")
        poisson_table = pd.DataFrame({
            "Number of high-spend days":    list(range(8)),
            "Chance of exactly this many":  [f"{poisson.pmf(x, m)*100:.2f}%" for x in range(8)],
            "Chance of this many or fewer": [f"{poisson.cdf(x, m)*100:.2f}%" for x in range(8)],
        })
        st.dataframe(poisson_table, use_container_width=True, hide_index=True)

        st.divider()

        # ── BUDGET SUCCESS ────────────────────────────────────────
        st.subheader("Will You Stay Under Budget?")
        st.write("Based on your history, what are the chances you stick to your daily budget for most of the month?")

        bs1, bs2 = st.columns(2)
        with bs1:
            n_trials = st.number_input(
                "Days in this month", min_value=1, max_value=31,
                value=int(days_in_month), key="binom_n"
            )
            success_days = st.number_input(
                "Target days within budget",
                min_value=0, max_value=int(n_trials),
                value=int(n_trials * 0.7), key="binom_k"
            )
        with bs2:
            if ideal_daily > 0 and n_days > 0:
                under_budget_days = int(np.sum(amounts <= ideal_daily))
                p_success         = max(0.01, min(0.99, under_budget_days / n_days))
            else:
                p_success = 0.5

            mean_binom = n_trials * p_success
            p_at_least = float(1 - binom.cdf(success_days - 1, n_trials, p_success))
            st.metric("Daily budget success rate",                  f"{p_success*100:.1f}%",
                      help="How often you have stayed under your ideal daily budget")
            st.metric(f"Chance of {success_days}+ days within budget", f"{p_at_least*100:.1f}%")
            st.metric("Average on-budget days expected",            f"{mean_binom:.0f}")

        if p_at_least > 0.7:
            st.success(f"There is a strong {p_at_least*100:.0f}% chance you will stay on budget for {success_days}+ days.")
        elif p_at_least > 0.4:
            st.warning(f"It is possible but not certain — {p_at_least*100:.0f}% chance of {success_days}+ good days.")
        else:
            st.error(f"Only {p_at_least*100:.0f}% chance. You may want to cut back to hit {success_days} budget-friendly days.")

        st.markdown("**Day-by-day success probability:**")
        rows = list(range(min(n_trials + 1, 16)))
        binom_table = pd.DataFrame({
            "On-budget days":               rows,
            "Chance of exactly this many":  [f"{binom.pmf(x, n_trials, p_success)*100:.2f}%" for x in rows],
            "Chance of this many or fewer": [f"{binom.cdf(x, n_trials, p_success)*100:.2f}%" for x in rows],
            "Chance of this many or more":  [f"{(1-binom.cdf(x-1, n_trials, p_success))*100:.2f}%" for x in rows],
        })
        st.dataframe(binom_table, use_container_width=True, hide_index=True)

        st.divider()

        # ── CATEGORY PROBABILITY ─────────────────────────────────
        st.subheader("What Do You Usually Spend On?")
        st.write("Based on your past transactions, here is how likely you are to spend in each category next time:")

        cat_counts = data.groupby("Category")["Amount"].count()
        total_txns = cat_counts.sum()
        cat_probs  = (cat_counts / total_txns * 100).round(2)

        prob_df = pd.DataFrame({
            "Category":                   cat_probs.index,
            "Times you spent here":       cat_counts.values,
            "Likelihood of next expense": [f"{p:.1f}%" for p in cat_probs.values],
        })
        st.dataframe(prob_df, use_container_width=True, hide_index=True)

        most_likely = cat_probs.idxmax()
        st.info(
            f"Your most common spending category is {most_likely} — "
            f"you spend here {cat_probs[most_likely]:.1f}% of the time."
        )
