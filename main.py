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

# ================== GLOBAL CSS ==================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&display=swap');

:root {
    --bg: #f7f5f2;
    --surface: #ffffff;
    --border: #e5e0d8;
    --text-primary: #1a1714;
    --text-secondary: #6b6560;
    --accent: #2d5a3d;
    --accent-light: #e8f0eb;
    --danger: #8b2635;
    --danger-light: #fdf0f1;
    --warning: #7a5c00;
    --warning-light: #fdf8e8;
    --radius: 8px;
    --shadow: 0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.04);
    --shadow-md: 0 4px 12px rgba(0,0,0,0.08);
}

html, body, [data-testid="stAppViewContainer"] {
    background-color: var(--bg) !important;
    font-family: 'DM Sans', sans-serif;
}

[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stSidebar"] { display: none !important; }

h1, h2, h3 {
    font-family: 'DM Serif Display', serif;
    color: var(--text-primary);
}

/* ---- LOGIN CARD ---- */
.login-wrapper {
    max-width: 420px;
    margin: 60px auto 0 auto;
    padding: 48px 40px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    box-shadow: var(--shadow-md);
}
.login-title {
    font-family: 'DM Serif Display', serif;
    font-size: 2rem;
    color: var(--text-primary);
    margin-bottom: 4px;
    text-align: center;
}
.login-subtitle {
    color: var(--text-secondary);
    font-size: 0.9rem;
    text-align: center;
    margin-bottom: 32px;
}

/* ---- TOP BAR ---- */
.topbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px 0 8px 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 32px;
}
.topbar-title {
    font-family: 'DM Serif Display', serif;
    font-size: 1.6rem;
    color: var(--text-primary);
    margin: 0;
}
.topbar-user {
    font-size: 0.85rem;
    color: var(--text-secondary);
    background: var(--accent-light);
    padding: 6px 14px;
    border-radius: 999px;
    border: 1px solid #c8dccf;
}

/* ---- METRICS ---- */
[data-testid="stMetric"] {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px 24px !important;
    box-shadow: var(--shadow);
}
[data-testid="stMetricLabel"] {
    font-size: 0.78rem !important;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-secondary) !important;
}
[data-testid="stMetricValue"] {
    font-family: 'DM Serif Display', serif;
    font-size: 1.7rem !important;
    color: var(--text-primary) !important;
}

/* ---- ALERTS ---- */
[data-testid="stAlert"] {
    border-radius: var(--radius) !important;
    border-left-width: 3px !important;
    font-size: 0.9rem;
}

/* ---- INPUTS ---- */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stSelectbox"] select,
[data-baseweb="select"] {
    border-radius: var(--radius) !important;
    border-color: var(--border) !important;
    font-family: 'DM Sans', sans-serif !important;
    background: var(--surface) !important;
}

/* ---- BUTTONS ---- */
[data-testid="stButton"] > button {
    background: var(--accent) !important;
    color: white !important;
    border: none !important;
    border-radius: var(--radius) !important;
    padding: 10px 24px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.9rem !important;
    letter-spacing: 0.02em !important;
    transition: opacity 0.15s ease !important;
    box-shadow: none !important;
}
[data-testid="stButton"] > button:hover {
    opacity: 0.88 !important;
}
.logout-btn [data-testid="stButton"] > button {
    background: transparent !important;
    color: var(--danger) !important;
    border: 1px solid var(--danger) !important;
    padding: 6px 16px !important;
    font-size: 0.82rem !important;
}

/* ---- TABS ---- */
[data-testid="stTabs"] [role="tablist"] {
    border-bottom: 2px solid var(--border);
    gap: 0;
}
[data-testid="stTabs"] [role="tab"] {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.88rem;
    font-weight: 500;
    color: var(--text-secondary);
    padding: 10px 20px;
    border-radius: 0;
    border-bottom: 2px solid transparent;
    margin-bottom: -2px;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom-color: var(--accent) !important;
    background: transparent !important;
}

/* ---- DATAFRAME ---- */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
}

/* ---- DIVIDER ---- */
hr {
    border-color: var(--border) !important;
    margin: 24px 0 !important;
}

/* ---- SECTION LABEL ---- */
.section-label {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-secondary);
    margin-bottom: 16px;
}

/* ---- INCOME CARD ---- */
.income-card {
    background: var(--accent-light);
    border: 1px solid #c8dccf;
    border-radius: var(--radius);
    padding: 20px 24px;
    margin-bottom: 24px;
}
</style>
""", unsafe_allow_html=True)


# ================== SESSION STATE INIT ==================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = None


# ================== LOGIN / REGISTER SCREEN ==================
if not st.session_state.logged_in:
    st.markdown("""
        <div class="login-wrapper">
            <div class="login-title">Expense Analyzer</div>
            <div class="login-subtitle">Track, understand, and improve your spending</div>
        </div>
    """, unsafe_allow_html=True)

    # Center the form using columns
    col_left, col_center, col_right = st.columns([1, 2, 1])
    with col_center:
        username = st.text_input("Username", placeholder="Enter your username")
        pin = st.text_input("PIN", type="password", placeholder="Enter your PIN")

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            login_btn = st.button("Sign In", use_container_width=True)
        with col_btn2:
            register_btn = st.button("Create Account", use_container_width=True)

        if login_btn:
            if not username.strip() or not pin.strip():
                st.error("Please enter both username and PIN.")
            else:
                user_profile = load_user(username.strip())
                if not user_profile:
                    st.error("Account not found. Please create one.")
                elif pin.strip() != str(user_profile.get("pin", "")):
                    st.error("Incorrect PIN. Please try again.")
                else:
                    st.session_state.logged_in = True
                    st.session_state.user = username.strip()
                    st.session_state.data = load_expenses(username.strip())
                    st.session_state.income = load_income(username.strip())
                    st.rerun()

        if register_btn:
            if not username.strip() or not pin.strip():
                st.error("Please enter both a username and PIN.")
            else:
                existing = load_user(username.strip())
                if existing:
                    st.error("That username is already taken. Please sign in or choose another.")
                else:
                    save_user(username.strip(), pin.strip())
                    st.success("Account created. You can now sign in.")

    st.stop()


# ================== LOGGED-IN STATE ==================
username = st.session_state.user
data = st.session_state.data

if not data.empty:
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    data = data.dropna(subset=["Date"])
    data["Amount"] = pd.to_numeric(data["Amount"], errors="coerce").fillna(0.0)
    st.session_state.data = data

today = datetime.today()
days_in_month = calendar.monthrange(today.year, today.month)[1]
days_left = max(days_in_month - today.day, 1)
total_expense = data["Amount"].sum() if not data.empty else 0.0
balance = st.session_state.income - total_expense
ideal_daily = st.session_state.income / days_in_month if days_in_month > 0 else 0
adjusted_daily = balance / days_left

# ---- TOP BAR with logout ----
col_title, col_user, col_logout = st.columns([5, 2, 1])
with col_title:
    st.markdown('<p class="topbar-title">Expense Analyzer</p>', unsafe_allow_html=True)
with col_user:
    st.markdown(f'<div style="padding-top:18px; text-align:right"><span class="topbar-user">{username}</span></div>', unsafe_allow_html=True)
with col_logout:
    st.markdown('<div class="logout-btn" style="padding-top:14px">', unsafe_allow_html=True)
    if st.button("Sign Out"):
        for key in ["logged_in", "user", "data", "income"]:
            st.session_state.pop(key, None)
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ================== TABS ==================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Overview", "Add Expense", "Breakdown", "Forecast", "Smart Analysis"
])

# ══════════════════════════════════════════
# TAB 1 — OVERVIEW (Home)
# ══════════════════════════════════════════
with tab1:
    # Income row
    inc_col, _, save_col = st.columns([3, 1, 1])
    with inc_col:
        new_income = st.number_input(
            "Monthly Income (INR)", min_value=0.0,
            value=st.session_state.income, label_visibility="visible"
        )
    with save_col:
        st.markdown("<div style='padding-top:28px'>", unsafe_allow_html=True)
        if st.button("Save Income"):
            st.session_state.income = new_income
            save_income(username, new_income)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Monthly Income", f"INR {st.session_state.income:,.2f}")
    c2.metric("Total Spent", f"INR {total_expense:,.2f}")
    c3.metric("Remaining", f"INR {balance:,.2f}")

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    st.markdown('<p class="section-label">Budget Guidance</p>', unsafe_allow_html=True)
    st.info(f"Ideal daily spend to stay on track: INR {ideal_daily:,.2f}")

    if balance < 0:
        st.error("You have exceeded your monthly budget.")
    else:
        st.warning(f"To finish the month within budget, keep daily spending under INR {adjusted_daily:,.2f}.")

    if not data.empty:
        avg_spend = data["Amount"].mean()
        if avg_spend > adjusted_daily:
            st.error("Your average expense exceeds the safe daily limit. Consider reducing discretionary spending.")
        elif avg_spend > ideal_daily:
            st.warning("Your average expense is slightly above the ideal daily amount.")
        else:
            st.success("Your spending is within budget. Keep it up.")


# ══════════════════════════════════════════
# TAB 2 — ADD EXPENSE
# ══════════════════════════════════════════
with tab2:
    st.markdown('<p class="section-label">New Expense</p>', unsafe_allow_html=True)

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
                st.error("Please enter an amount greater than zero.")
            else:
                new_row = pd.DataFrame({
                    "Date": [str(date)],
                    "Category": [category],
                    "Amount": [float(amount)]
                })
                current = st.session_state.data.copy()
                current["Amount"] = pd.to_numeric(current["Amount"], errors="coerce").fillna(0.0)
                st.session_state.data = pd.concat([current, new_row], ignore_index=True)
                save_expenses(username, st.session_state.data)
                st.success(f"Added INR {amount:,.2f} under {category} for {date}.")
                st.rerun()

    with btn2:
        if st.button("Undo Last", use_container_width=True):
            if len(st.session_state.data) > 0:
                st.session_state.data = st.session_state.data.iloc[:-1].reset_index(drop=True)
                save_expenses(username, st.session_state.data)
                st.success("Last expense removed.")
                st.rerun()
            else:
                st.info("No expenses to remove.")

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    st.markdown('<p class="section-label">All Expenses</p>', unsafe_allow_html=True)

    if not data.empty:
        display_data = data.copy()
        display_data["Date"] = display_data["Date"].dt.strftime("%d %b %Y")
        display_data["Amount"] = display_data["Amount"].apply(lambda x: f"INR {x:,.2f}")
        st.dataframe(display_data, use_container_width=True, hide_index=True)
    else:
        st.info("No expenses recorded yet.")


# ══════════════════════════════════════════
# TAB 3 — BREAKDOWN (Overview)
# ══════════════════════════════════════════
with tab3:
    if not data.empty:
        total = data["Amount"].sum()
        avg = data["Amount"].mean()
        median = data["Amount"].median()
        std_dev = data["Amount"].std()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Spent", f"INR {total:,.2f}")
        c2.metric("Avg per Expense", f"INR {avg:,.2f}")
        c3.metric("Median Expense", f"INR {median:,.2f}")
        c4.metric("Std Deviation", f"INR {std_dev:,.2f}")

        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
        st.markdown('<p class="section-label">Spending by Category</p>', unsafe_allow_html=True)
        cat_totals = data.groupby("Category")["Amount"].sum()
        st.bar_chart(cat_totals)

        st.markdown('<p class="section-label">Daily Spending</p>', unsafe_allow_html=True)
        st.line_chart(data.groupby("Date")["Amount"].sum())

    else:
        st.info("No expenses recorded yet. Add some in the Add Expense tab.")


# ══════════════════════════════════════════
# TAB 4 — FORECAST
# ══════════════════════════════════════════
with tab4:
    if not data.empty and len(data) > 3:
        st.markdown('<p class="section-label">7-Day Spending Forecast</p>', unsafe_allow_html=True)
        st.write("Based on your historical data, here is a projection for the next 7 days.")

        data_sorted = data.sort_values("Date")
        y = data_sorted["Amount"].values.astype(float)
        x = np.arange(len(y))
        slope, intercept = np.polyfit(x, y, 1)
        future_x = np.arange(len(y), len(y) + 7)
        predictions = slope * future_x + intercept

        pred_df = pd.DataFrame(
            {"Day": [f"Day +{i+1}" for i in range(7)], "Predicted Spend (INR)": predictions}
        ).set_index("Day")
        st.line_chart(pred_df)

        direction = "increasing" if slope > 0 else "decreasing"
        st.info(f"Your spending trend is {direction} by approximately INR {abs(slope):,.2f} per entry.")

        total_predicted = predictions.sum()
        if total_predicted > balance:
            st.error(
                f"Your projected 7-day spend of INR {total_predicted:,.2f} may exceed your "
                f"remaining balance of INR {balance:,.2f}."
            )
        else:
            st.success(
                f"Your projected 7-day spend of INR {total_predicted:,.2f} is within "
                f"your remaining balance."
            )

    elif not data.empty:
        st.info("Add more than 3 expenses to unlock the forecast.")
    else:
        st.info("No expenses recorded yet.")


# ══════════════════════════════════════════
# TAB 5 — SMART ANALYSIS
# ══════════════════════════════════════════
with tab5:
    if data.empty or len(data) < 5:
        st.info("Add at least 5 expenses to unlock smart analysis.")
    else:
        daily = data.groupby("Date")["Amount"].sum().reset_index()
        daily.columns = ["Date", "DailyTotal"]
        amounts = daily["DailyTotal"].values.astype(float)

        mu = float(np.mean(amounts))
        sigma = float(np.std(amounts))
        n_days = len(amounts)
        skewness = float(pd.Series(amounts).skew())

        # ── SPENDING PROFILE ────────────────────────────────────
        st.markdown('<p class="section-label">Spending Profile</p>', unsafe_allow_html=True)

        p1, p2, p3 = st.columns(3)
        p1.metric("Avg Daily Spend", f"INR {mu:,.2f}",
                  help="The average amount spent on a typical day")
        p2.metric("Day-to-Day Variation", f"INR {sigma:,.2f}",
                  help="How much your daily spending fluctuates")
        pattern = "Variable" if skewness > 0.5 else ("Front-loaded" if skewness < -0.5 else "Consistent")
        p3.metric("Spending Pattern", pattern)

        if skewness > 0.5:
            st.info("Your spending has occasional high-cost days, such as shopping or outings.")
        elif skewness < -0.5:
            st.info("You tend to spend more at the start of the month and slow down toward the end.")
        else:
            st.success("Your spending is consistent across the month.")

        st.divider()

        # ── OVERSPENDING RISK ────────────────────────────────────
        st.markdown('<p class="section-label">Overspending Risk</p>', unsafe_allow_html=True)

        if sigma == 0:
            st.warning("All daily expenses are identical — risk calculation is not available.")
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
                z_score = (threshold - mu) / sigma
                prob_exceed = float(1 - norm.cdf(z_score))
                st.metric("Probability of exceeding limit", f"{prob_exceed*100:.1f}%")
                st.metric("Probability of staying within limit", f"{(1-prob_exceed)*100:.1f}%")

            st.markdown(
                f"""
                Based on your past spending (avg: INR {mu:,.2f}, variation: INR {sigma:,.2f}):
                - 68% of days you spend between **INR {mu-sigma:,.2f}** and **INR {mu+sigma:,.2f}**
                - 95% of days you spend between **INR {mu-2*sigma:,.2f}** and **INR {mu+2*sigma:,.2f}**
                """
            )

            if prob_exceed > 0.5:
                st.error(f"You exceed INR {threshold:,.0f} more than half the time. Consider revising your budget.")
            elif prob_exceed > 0.25:
                st.warning(f"There is roughly a 1 in 4 chance of exceeding INR {threshold:,.0f} on any given day.")
            else:
                st.success(f"You rarely exceed INR {threshold:,.0f}. Your spending is well controlled.")

        st.divider()

        # ── HIGH-SPEND DAYS ──────────────────────────────────────
        st.markdown('<p class="section-label">High-Spend Day Frequency</p>', unsafe_allow_html=True)

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
            large_days = int(np.sum(amounts > large_threshold))
            m = max((large_days / n_days) * days_in_month, 0.01)
            px = float(poisson.pmf(target_days, m))
            p_at_least_one = float(1 - poisson.pmf(0, m))

            st.metric("Expected high-spend days this month", f"{m:.1f}")
            st.metric(f"Chance of exactly {target_days} such days", f"{px*100:.2f}%")
            st.metric("Chance of at least one", f"{p_at_least_one*100:.1f}%")

        st.markdown('<p class="section-label">Monthly Probability Table</p>', unsafe_allow_html=True)
        poisson_table = pd.DataFrame({
            "High-spend days": list(range(8)),
            "Probability (exact)": [f"{poisson.pmf(x, m)*100:.2f}%" for x in range(8)],
            "Probability (up to)": [f"{poisson.cdf(x, m)*100:.2f}%" for x in range(8)],
        })
        st.dataframe(poisson_table, use_container_width=True, hide_index=True)

        st.divider()

        # ── BUDGET SUCCESS ────────────────────────────────────────
        st.markdown('<p class="section-label">Budget Adherence Forecast</p>', unsafe_allow_html=True)

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
                p_success = max(0.01, min(0.99, under_budget_days / n_days))
            else:
                under_budget_days = 0
                p_success = 0.5

            mean_binom = n_trials * p_success
            p_at_least = float(1 - binom.cdf(success_days - 1, n_trials, p_success))

            st.metric("Historical budget success rate", f"{p_success*100:.1f}%")
            st.metric(f"Chance of {success_days}+ days within budget", f"{p_at_least*100:.1f}%")
            st.metric("Expected on-budget days", f"{mean_binom:.0f}")

        if p_at_least > 0.7:
            st.success(f"There is a strong {p_at_least*100:.0f}% chance you will meet your target of {success_days} days.")
        elif p_at_least > 0.4:
            st.warning(f"It is possible but uncertain — {p_at_least*100:.0f}% chance of reaching {success_days} days.")
        else:
            st.error(f"Only a {p_at_least*100:.0f}% chance of hitting {success_days} days. Consider a more modest target.")

        st.markdown('<p class="section-label">Adherence Probability Table</p>', unsafe_allow_html=True)
        rows = list(range(min(n_trials + 1, 16)))
        binom_table = pd.DataFrame({
            "On-budget days": rows,
            "Probability (exact)": [f"{binom.pmf(x, n_trials, p_success)*100:.2f}%" for x in rows],
            "Probability (up to)": [f"{binom.cdf(x, n_trials, p_success)*100:.2f}%" for x in rows],
            "Probability (at least)": [f"{(1-binom.cdf(x-1, n_trials, p_success))*100:.2f}%" for x in rows],
        })
        st.dataframe(binom_table, use_container_width=True, hide_index=True)

        st.divider()

        # ── CATEGORY BREAKDOWN ────────────────────────────────────
        st.markdown('<p class="section-label">Spending Category Distribution</p>', unsafe_allow_html=True)

        cat_counts = data.groupby("Category")["Amount"].count()
        total_txns = cat_counts.sum()
        cat_probs = (cat_counts / total_txns * 100).round(2)

        prob_df = pd.DataFrame({
            "Category": cat_probs.index,
            "Transactions": cat_counts.values,
            "Share of spending": [f"{p:.1f}%" for p in cat_probs.values],
        })
        st.dataframe(prob_df, use_container_width=True, hide_index=True)

        most_likely = cat_probs.idxmax()
        st.info(
            f"Your most frequent spending category is {most_likely}, "
            f"accounting for {cat_probs[most_likely]:.1f}% of all transactions."
        )
