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
    return pd.DataFrame(data) if data else pd.DataFrame(columns=["Date", "Category", "Amount"])

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

    st.success(f"✅ Welcome back, {username}!")

else:
    st.sidebar.subheader("🆕 New User — Set PIN")
    new_pin = st.sidebar.text_input("Choose a PIN", type="password").strip()

    if new_pin == "":
        st.warning("Please set a PIN to create your account.")
        st.stop()

    save_user(username, new_pin)
    st.success("🎉 Account created! Please log in again.")
    st.stop()

# ================== INCOME ==================
st.sidebar.subheader("💰 Monthly Income")

if "income" not in st.session_state:
    st.session_state.income = load_income(username)

new_income = st.sidebar.number_input(
    "Monthly Income (₹)", min_value=0.0, value=st.session_state.income
)

if st.sidebar.button("Save Income"):
    st.session_state.income = new_income
    save_income(username, new_income)
    st.success("✅ Income saved!")
    st.rerun()

# ================== WORKING DATA ==================
data = st.session_state.data

if not data.empty:
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    data = data.dropna(subset=["Date"])
    st.session_state.data = data

# ================== ADD EXPENSE ==================
st.header("➕ Add Expense")

col_a, col_b, col_c = st.columns(3)
with col_a:
    date = st.date_input("Date")
with col_b:
    category = st.selectbox(
        "Category", ["Food", "Travel", "Shopping", "Entertainment", "Others"]
    )
with col_c:
    amount = st.number_input("Amount (₹)", min_value=0.0)

if st.button("Add Expense"):
    new_row = pd.DataFrame(
        {"Date": [str(date)], "Category": [category], "Amount": [amount]}
    )
    st.session_state.data = pd.concat(
        [st.session_state.data, new_row], ignore_index=True
    )
    save_expenses(username, st.session_state.data)
    st.success("✅ Expense added!")
    st.rerun()

if st.button("↩️ Undo Last Expense"):
    if len(st.session_state.data) > 0:
        st.session_state.data = st.session_state.data[:-1]
        save_expenses(username, st.session_state.data)
        st.success("Last expense removed.")
        st.rerun()

# ================== BALANCE ==================
data = st.session_state.data
total_expense = data["Amount"].sum() if not data.empty else 0.0
balance = st.session_state.income - total_expense

st.header("💼 Balance Summary")
col1, col2, col3 = st.columns(3)
col1.metric("Monthly Income", f"₹{st.session_state.income:.2f}")
col2.metric("Total Expenses", f"₹{total_expense:.2f}")
col3.metric("Remaining Balance", f"₹{balance:.2f}")

# ================== SMART BUDGET ==================
today = datetime.today()
days_in_month = calendar.monthrange(today.year, today.month)[1]
days_left = days_in_month - today.day

st.subheader("🧠 Smart Budget Advice")

ideal_daily = st.session_state.income / days_in_month if days_in_month > 0 else 0
adjusted_daily = balance / days_left if days_left > 0 else balance

st.info(f"💡 Ideal daily spending: ₹{ideal_daily:.2f}/day")

if balance < 0:
    st.error("⚠️ You have exceeded your monthly budget!")
else:
    st.warning(f"⚠️ Adjusted safe spending for remaining days: ₹{adjusted_daily:.2f}/day")

if not data.empty:
    avg_spend = data["Amount"].mean()
    if avg_spend > ideal_daily:
        st.warning("📊 Your average spend is above the ideal daily budget.")
    if avg_spend > adjusted_daily:
        st.error("🚨 You are overspending beyond the safe limit!")

# ================== OVERVIEW ==================
st.header("📊 Overview")

if not data.empty:
    total = data["Amount"].sum()
    avg = data["Amount"].mean()
    median = data["Amount"].median()
    std_dev = data["Amount"].std()
    variance = data["Amount"].var()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Spent", f"₹{total:.2f}")
    c2.metric("Mean (μ)", f"₹{avg:.2f}")
    c3.metric("Median", f"₹{median:.2f}")
    c4.metric("Std Dev (σ)", f"₹{std_dev:.2f}")
    c5.metric("Variance (σ²)", f"₹{variance:.2f}")

    st.subheader("🗂️ Spending by Category")
    st.bar_chart(data.groupby("Category")["Amount"].sum())

    st.subheader("📅 Daily Spending Trend")
    st.line_chart(data.groupby("Date")["Amount"].sum())

    # ================== PREDICTION ==================
    if len(data) > 3:
        st.subheader("🔮 7-Day Spending Forecast (Linear Regression)")
        st.caption("Uses least squares method: y = mx + c to predict future spending")
        data_sorted = data.sort_values("Date")
        y = data_sorted["Amount"].values
        x = np.arange(len(y))
        slope, intercept = np.polyfit(x, y, 1)
        future_x = np.arange(len(y), len(y) + 7)
        predictions = slope * future_x + intercept
        pred_df = pd.DataFrame(
            {"Day": [f"Day +{i+1}" for i in range(7)], "Predicted (₹)": predictions}
        ).set_index("Day")
        st.line_chart(pred_df)
        st.caption(f"Trend: slope = ₹{slope:.2f}/entry, intercept = ₹{intercept:.2f}")
    else:
        st.info("Add more than 3 expenses to see spending predictions.")

else:
    st.info("No expenses recorded yet. Start adding your expenses above!")


# ================================================================
# 📐 PROBABILITY & STATISTICS ANALYSIS  (Module 1 & Module 2)
# ================================================================

st.divider()
st.header("📐 Probability & Statistical Analysis")
st.caption(
    "Applying Module 2 concepts: Normal Distribution, Poisson Distribution, "
    "Binomial Distribution, Conditional Probability & Descriptive Statistics"
)

if data.empty or len(data) < 5:
    st.info(
        "⚠️ Add at least 5 expense entries to unlock the probability analysis features."
    )
else:
    # --- Aggregate to daily totals ---
    daily = data.groupby("Date")["Amount"].sum().reset_index()
    daily.columns = ["Date", "DailyTotal"]
    amounts = daily["DailyTotal"].values

    mu = float(np.mean(amounts))
    sigma = float(np.std(amounts))
    n_days = len(amounts)

    # ── DESCRIPTIVE STATS RECAP ──────────────────────────────────
    st.subheader("📊 Descriptive Statistics of Daily Spending")
    st.caption("Module 1: Mean, Variance, Standard Deviation, Skewness")

    skewness = float(pd.Series(amounts).skew())
    desc_col1, desc_col2, desc_col3, desc_col4 = st.columns(4)
    desc_col1.metric("Mean (μ)", f"₹{mu:.2f}")
    desc_col2.metric("Std Dev (σ)", f"₹{sigma:.2f}")
    desc_col3.metric("Variance (σ²)", f"₹{sigma**2:.2f}")
    desc_col4.metric("Skewness", f"{skewness:.3f}")

    if skewness > 0.5:
        st.info("📈 Positively skewed — occasional large expense spikes detected.")
    elif skewness < -0.5:
        st.info("📉 Negatively skewed — most days you spend heavily.")
    else:
        st.success("✅ Roughly symmetric spending — consistent daily habits.")

    st.divider()

    # ════════════════════════════════════════════════════════════
    # FEATURE 1 — NORMAL DISTRIBUTION
    # ════════════════════════════════════════════════════════════
    st.subheader("🔔 Feature 1: Normal Distribution — Overspending Probability")
    st.caption(
        "Module 2: Normal/Gaussian Distribution | Formula: Z = (X - μ) / σ | "
        "P(X > threshold) = 1 - Φ(Z)"
    )

    with st.expander("📖 What is Normal Distribution?", expanded=False):
        st.markdown(
            """
            A continuous random variable X follows **Normal Distribution** N(μ, σ²) if:

            **PDF:** f(x) = (1 / σ√2π) × e^[-(x-μ)²/2σ²]

            - **μ (mean):** Centre of the bell curve
            - **σ (std dev):** How spread out the data is
            - **Z-score:** Z = (X - μ) / σ  standardises X to N(0,1)

            We use the **Standard Normal Table** to find P(X > threshold).
            """
        )

    if sigma == 0:
        st.warning("All daily expenses are identical — cannot compute normal distribution.")
    else:
        nd_col1, nd_col2 = st.columns(2)

        with nd_col1:
            threshold = st.number_input(
                "Set daily spending threshold (₹)",
                min_value=0.0,
                value=float(round(mu * 1.2, 2)),
                key="nd_threshold",
            )

        with nd_col2:
            z_score = (threshold - mu) / sigma
            prob_exceed = float(1 - norm.cdf(z_score))

            st.metric("Z-score", f"{z_score:.4f}")
            st.metric("P(Spending > threshold)", f"{prob_exceed*100:.2f}%")

        st.markdown(
            f"""
            **Step-by-step working (Module 2):**
            - μ = ₹{mu:.2f} | σ = ₹{sigma:.2f} | Threshold = ₹{threshold:.2f}
            - Z = (X - μ) / σ = ({threshold:.2f} - {mu:.2f}) / {sigma:.2f} = **{z_score:.4f}**
            - P(X > {threshold:.2f}) = 1 - Φ({z_score:.4f}) = **{prob_exceed*100:.2f}%**

            **Normal Curve Area Properties:**
            - μ ± 1σ covers 68.26% → ₹{mu-sigma:.2f} to ₹{mu+sigma:.2f}
            - μ ± 2σ covers 95.44% → ₹{mu-2*sigma:.2f} to ₹{mu+2*sigma:.2f}
            - μ ± 3σ covers 99.74% → ₹{mu-3*sigma:.2f} to ₹{mu+3*sigma:.2f}
            """
        )

        if prob_exceed > 0.5:
            st.error(f"🚨 High risk! {prob_exceed*100:.1f}% chance tomorrow exceeds ₹{threshold:.0f}.")
        elif prob_exceed > 0.25:
            st.warning(f"⚠️ Moderate risk. {prob_exceed*100:.1f}% chance of exceeding ₹{threshold:.0f}.")
        else:
            st.success(f"✅ Low risk. Only {prob_exceed*100:.1f}% chance of exceeding ₹{threshold:.0f}.")

    st.divider()

    # ════════════════════════════════════════════════════════════
    # FEATURE 2 — POISSON DISTRIBUTION
    # ════════════════════════════════════════════════════════════
    st.subheader("☄️ Feature 2: Poisson Distribution — Large Expense Day Prediction")
    st.caption(
        "Module 2: Poisson Distribution | Formula: P(X = x) = (e⁻ᵐ × mˣ) / x! | "
        "Mean = Variance = m"
    )

    with st.expander("📖 What is Poisson Distribution?", expanded=False):
        st.markdown(
            """
            **Poisson Distribution** models how many times a rare event occurs in a fixed interval.

            **PMF:** P(X = x) = (e⁻ᵐ × mˣ) / x!

            **Conditions (Module 2):** n → ∞, p → 0, np = m (finite)

            Mean = Variance = m

            **Here:** A "large expense day" is the rare event. We predict how many will happen this month.
            """
        )

    pd_col1, pd_col2 = st.columns(2)

    with pd_col1:
        large_threshold = st.number_input(
            "Define 'large expense day' threshold (₹)",
            min_value=0.0,
            value=float(round(mu + sigma, 2)),
            key="poisson_threshold",
        )
        target_days = st.number_input(
            "Find P(exactly X large-expense days this month)",
            min_value=0, max_value=30, value=3, key="poisson_target"
        )

    with pd_col2:
        large_days = int(np.sum(amounts > large_threshold))
        m = max((large_days / n_days) * days_in_month, 0.01)

        px = float(poisson.pmf(target_days, m))
        p_at_least_one = float(1 - poisson.pmf(0, m))

        st.metric("λ (m) — Expected large-expense days/month", f"{m:.2f}")
        st.metric(f"P(X = {target_days})", f"{px*100:.4f}%")
        st.metric("P(At least 1 large-expense day)", f"{p_at_least_one*100:.2f}%")

    st.markdown(
        f"""
        **Step-by-step working (Module 2):**
        - Threshold = ₹{large_threshold:.2f}
        - Large-expense days in data = {large_days} / {n_days}
        - Rate per day = {large_days/n_days:.4f}
        - m = rate × days_in_month = {large_days/n_days:.4f} × {days_in_month} = **{m:.4f}**
        - P(X = {target_days}) = (e⁻{m:.4f} × {m:.4f}^{target_days}) / {target_days}! = **{px*100:.4f}%**
        - P(X ≥ 1) = 1 - e⁻{m:.4f} = **{p_at_least_one*100:.2f}%**
        """
    )

    st.markdown("**Poisson Probability Table:**")
    poisson_table = pd.DataFrame({
        "X (large-expense days)": list(range(8)),
        "P(X = x)": [f"{poisson.pmf(x, m)*100:.4f}%" for x in range(8)],
        "P(X ≤ x)  [CDF]": [f"{poisson.cdf(x, m)*100:.4f}%" for x in range(8)],
    })
    st.dataframe(poisson_table, use_container_width=True, hide_index=True)

    st.divider()

    # ════════════════════════════════════════════════════════════
    # FEATURE 3 — BINOMIAL DISTRIBUTION
    # ════════════════════════════════════════════════════════════
    st.subheader("🎯 Feature 3: Binomial Distribution — Monthly Budget Success")
    st.caption(
        "Module 2: Binomial Distribution | Formula: P(X = x) = ⁿCₓ pˣ qⁿ⁻ˣ | "
        "Mean = np | Variance = npq"
    )

    with st.expander("📖 What is Binomial Distribution?", expanded=False):
        st.markdown(
            """
            **Binomial Distribution** gives probability of x successes in n independent trials.

            **PMF:** P(X = x) = ⁿCₓ × pˣ × qⁿ⁻ˣ  where q = 1 - p

            **Conditions (Module 2):** Fixed n, independent trials, constant p, success/failure only.

            **Mean = np | Variance = npq | SD = √npq**

            **Here:** Each day = 1 trial. Success = spending ≤ ideal daily budget.
            """
        )

    binom_col1, binom_col2 = st.columns(2)

    with binom_col1:
        n_trials = st.number_input(
            "Number of days (n)", min_value=1, max_value=31,
            value=int(days_in_month), key="binom_n"
        )
        success_days = st.number_input(
            "Minimum success days to find probability for",
            min_value=0, max_value=int(n_trials),
            value=int(n_trials * 0.7), key="binom_k"
        )

    with binom_col2:
        if ideal_daily > 0 and n_days > 0:
            under_budget_days = int(np.sum(amounts <= ideal_daily))
            p_success = max(0.01, min(0.99, under_budget_days / n_days))
        else:
            under_budget_days = 0
            p_success = 0.5

        q_fail = 1 - p_success
        mean_binom = n_trials * p_success
        var_binom = n_trials * p_success * q_fail
        sd_binom = float(np.sqrt(var_binom))

        p_at_least = float(1 - binom.cdf(success_days - 1, n_trials, p_success))
        p_exact = float(binom.pmf(success_days, n_trials, p_success))

        st.metric("p (daily budget success rate)", f"{p_success*100:.2f}%")
        st.metric("q = 1 - p", f"{q_fail*100:.2f}%")
        st.metric(f"P(X ≥ {success_days} budget-success days)", f"{p_at_least*100:.2f}%")

    st.markdown(
        f"""
        **Step-by-step working (Module 2):**
        - n = {n_trials} | p = {p_success:.4f} | q = {q_fail:.4f}
        - Days under budget = {under_budget_days} / {n_days}
        - **Mean = np = {n_trials} × {p_success:.4f} = {mean_binom:.2f}**
        - **Variance = npq = {n_trials} × {p_success:.4f} × {q_fail:.4f} = {var_binom:.4f}**
        - **SD = √npq = {sd_binom:.4f}**
        - P(X = {success_days}) = ⁿCₓ pˣ qⁿ⁻ˣ = **{p_exact*100:.4f}%**
        - P(X ≥ {success_days}) = 1 - P(X ≤ {success_days-1}) = **{p_at_least*100:.2f}%**
        """
    )

    if p_at_least > 0.7:
        st.success(f"✅ {p_at_least*100:.1f}% chance of staying under budget for {success_days}+ days!")
    elif p_at_least > 0.4:
        st.warning(f"⚠️ {p_at_least*100:.1f}% chance of {success_days}+ budget-success days.")
    else:
        st.error(f"🚨 Only {p_at_least*100:.1f}% chance of {success_days}+ days under budget.")

    st.markdown(f"**Binomial Probability Table (n={n_trials}, p={p_success:.4f}):**")
    rows = list(range(min(n_trials + 1, 16)))
    binom_table = pd.DataFrame({
        "X (success days)": rows,
        "P(X = x)": [f"{binom.pmf(x, n_trials, p_success)*100:.4f}%" for x in rows],
        "P(X ≤ x) [CDF]": [f"{binom.cdf(x, n_trials, p_success)*100:.4f}%" for x in rows],
        "P(X ≥ x)": [f"{(1-binom.cdf(x-1, n_trials, p_success))*100:.4f}%" for x in rows],
    })
    st.dataframe(binom_table, use_container_width=True, hide_index=True)

    st.divider()

    # ════════════════════════════════════════════════════════════
    # BONUS — CATEGORY PROBABILITY (Classical / Relative Frequency)
    # ════════════════════════════════════════════════════════════
    st.subheader("🎲 Bonus: Category Spending Probability")
    st.caption(
        "Module 2: Classical & Relative Frequency Definition | P(E) = n(E) / n(S)"
    )

    cat_counts = data.groupby("Category")["Amount"].count()
    total_txns = cat_counts.sum()
    cat_probs = (cat_counts / total_txns * 100).round(2)

    prob_df = pd.DataFrame({
        "Category": cat_probs.index,
        "Transactions n(E)": cat_counts.values,
        "Total n(S)": total_txns,
        "P(E) = n(E)/n(S)": [f"{p:.2f}%" for p in cat_probs.values],
    })

    st.markdown(
        f"Based on your {total_txns} transactions, probability the next expense belongs to each category:"
    )
    st.dataframe(prob_df, use_container_width=True, hide_index=True)

    most_likely = cat_probs.idxmax()
    st.info(
        f"🎯 Most likely next category: **{most_likely}** ({cat_probs[most_likely]:.1f}%)"
    )

    st.divider()
    st.caption(
        "📚 All calculations are based on your Statistics & Probability module — "
        "Normal Distribution (Z = (X-μ)/σ), Poisson PMF (e⁻ᵐmˣ/x!), "
        "Binomial PMF (ⁿCₓpˣqⁿ⁻ˣ), Descriptive Stats (μ, σ, σ², skewness), "
        "and Classical Probability P(E) = n(E)/n(S)."
    )
