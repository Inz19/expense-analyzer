import firebase_admin
from firebase_admin import credentials, db
import streamlit as st
import pandas as pd
import os
from datetime import datetime
import calendar
import numpy as np
import jason

if not firebase_admin._apps:
    firebase_dict = json.loads(st.secrets["FIREBASE_KEY"])
    cred = credentials.Certificate(firebase_dict)

    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://expense-analyzer-db523-default-rtdb.asia-southeast1.firebasedatabase.app/"
    })

})
def save_data(username, data):
    ref = db.reference(f"users/{username}/expenses")
    ref.set(data.to_dict(orient="records"))
def load_data(username):
    ref = db.reference(f"users/{username}/expenses")
    data = ref.get()

    if data:
        return pd.DataFrame(data)
    else:
        return pd.DataFrame(columns=["Date", "Category", "Amount"])
# ================== CONFIG ==================
st.set_page_config(page_title="Expense Analyzer", layout="wide")
st.title("💰 Smart Expense Analyzer")

USERS_FILE = "users.csv"

# ================== INIT USERS ==================
if not os.path.exists(USERS_FILE):
    pd.DataFrame(columns=["username", "pin"]).to_csv(USERS_FILE, index=False)

# ================== USER LOGIN ==================
st.sidebar.header("👤 User")
username = st.sidebar.text_input("Enter username").strip()

if username == "":
    st.warning("Enter username")
    st.stop()

users_df = pd.read_csv(USERS_FILE, dtype={"pin": str})
user_row = users_df[users_df["username"] == username]

if not user_row.empty:
    pin = st.sidebar.text_input("Enter PIN", type="password").strip()

    if pin == "":
        st.info("Enter PIN")
        st.stop()

    stored_pin = str(user_row["pin"].values[0]).replace(".0", "")

    if pin != stored_pin:
        st.error("Wrong PIN")
        st.stop()
    if "data" not in st.session_state or st.session_state.get("user") != username:
        st.session_state.data = load_data(username)
        st.session_state.user = username

    st.success(f"Welcome {username}")

else:
    st.sidebar.subheader("New User")
    new_pin = st.sidebar.text_input("Set PIN", type="password").strip()

    if new_pin == "":
        st.warning("Set PIN")
        st.stop()

    new_user = pd.DataFrame([[username, new_pin]], columns=["username", "pin"])
    users_df = pd.concat([users_df, new_user], ignore_index=True)
    users_df.to_csv(USERS_FILE, index=False)

    st.success("Account created! Login again.")
    st.stop()

# ================== INCOME ==================
st.sidebar.subheader("💰 Income")

income_file = f"{username}_income.txt"

if os.path.exists(income_file):
    try:
        with open(income_file, "r") as f:
            income = float(f.read())
    except:
        income = 0.0
else:
    income = 0.0

if "income" not in st.session_state:
    st.session_state.income = income

new_income = st.sidebar.number_input("Monthly Income", min_value=0.0, value=st.session_state.income)

if st.sidebar.button("Save Income"):
    st.session_state.income = new_income
    with open(income_file, "w") as f:
        f.write(str(new_income))
    st.success("Income saved")
    st.rerun()

# ================== LOAD DATA ==================
file_name = f"{username}_expenses.csv"

if os.path.exists(file_name):
    data = load_data(username)
else:
    data = pd.DataFrame(columns=["Date", "Category", "Amount"])

if not data.empty:
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
data = data.dropna(subset=["Date"])

if "data" not in st.session_state:
    st.session_state.data = data.copy()

data = st.session_state.data

# ================== ADD EXPENSE ==================
st.header("➕ Add Expense")

date = st.date_input("Date")
category = st.selectbox("Category", ["Food", "Travel", "Shopping", "Entertainment", "Others"])
amount = st.number_input("Amount", min_value=0.0)

if st.button("Add Expense"):
    new_data = pd.DataFrame({
        "Date": [str(date)],
        "Category": [category],
        "Amount": [amount]
    })

    st.session_state.data = pd.concat([data, new_data], ignore_index=True)
    save_data(username, st.session_state.data)
    st.session_state.data.to_csv(file_name, index=False)

    st.success("Added!")
    st.rerun()

# ================== UNDO ==================
if st.button("Undo Last"):
    if len(data) > 0:
        st.session_state.data = data[:-1]
        st.session_state.data.to_csv(file_name, index=False)
        st.rerun()

# ================== BALANCE ==================
total_expense = data["Amount"].sum()
balance = st.session_state.income - total_expense

st.header("💼 Balance")

col1, col2 = st.columns(2)
col1.metric("Expense", f"{total_expense:.2f}")
col2.metric("Balance", f"{balance:.2f}")

# ================== SMART BUDGET ==================
# ================== SMART BUDGET ==================
today = datetime.today()
days_in_month = calendar.monthrange(today.year, today.month)[1]
days_left = days_in_month - today.day

st.subheader("🧠 Budget Advice")

# Ideal budget (full month)
ideal_daily = st.session_state.income / days_in_month

# Adjusted budget (remaining money)
if days_left > 0:
    adjusted_daily = balance / days_left
else:
    adjusted_daily = balance

st.info(f"💡 Ideal spending: ₹{ideal_daily:.2f}/day")

if balance < 0:
    st.error("⚠️ You have exceeded your budget!")
else:
    st.warning(f"⚠️ Adjusted spending: ₹{adjusted_daily:.2f}/day")

# ================== ALERT ==================
if not data.empty:
    avg_spend = data["Amount"].mean()

    if avg_spend > ideal_daily:
        st.warning("⚠️ You are spending more than ideal daily budget")

    if avg_spend > adjusted_daily:
        st.error("🚨 You are overspending even beyond safe limit!")
# ================== OVERVIEW ==================
st.header("📊 Overview")

if not data.empty:
    total = data["Amount"].sum()
    avg = data["Amount"].mean()
    median = data["Amount"].median()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total", f"{total:.2f}")
    c2.metric("Avg", f"{avg:.2f}")
    c3.metric("Median", f"{median:.2f}")

    st.subheader("Category Spending")
    st.bar_chart(data.groupby("Category")["Amount"].sum())

    st.subheader("Daily Spending")
    st.line_chart(data.groupby("Date")["Amount"].sum())

# ================== PREDICTION ==================
import numpy as np

if len(data) > 3:
    data_sorted = data.sort_values("Date")

    y = data_sorted["Amount"].values
    x = np.arange(len(y))

    # Fit a line (trend)
    slope, intercept = np.polyfit(x, y, 1)

    future_x = np.arange(len(y), len(y) + 7)
    predictions = slope * future_x + intercept

    st.line_chart(predictions)
else:
    st.info("Not enough data to predict yet")
