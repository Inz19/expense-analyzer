import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
st.set_page_config(page_title="Expense Analyzer", page_icon="📊", layout="wide")

# Title
st.title("📊 Smart Expense Analyzer & Predictor")

# Load dataset
data = pd.read_csv("expenses.csv")

# Clean data
data = data[['Date', 'Category', 'Amount']]
data['Date'] = pd.to_datetime(data['Date'], dayfirst=True)

# =========================
# 🔹 SECTION 1: OVERVIEW
# =========================
st.header("Overview")

total = data['Amount'].sum()
avg = data['Amount'].mean()
median = data['Amount'].median()

st.write(f"Total Expense: ₹{total}")
st.write(f"Average Expense: ₹{avg:.2f}")
st.write(f"Median Expense: ₹{median}")

# =========================
# 🔹 SECTION 2: CATEGORY ANALYSIS
# =========================
st.header("Category Analysis")

category_sum = data.groupby('Category')['Amount'].sum()

st.write(category_sum)

fig1, ax1 = plt.subplots()
category_sum.plot(kind='bar', ax=ax1)
ax1.set_title("Spending by Category")
st.pyplot(fig1)

highest = category_sum.idxmax()
st.write(f"Highest Spending Category: {highest}")

# =========================
# 🔹 SECTION 3: DAILY TREND
# =========================
st.header("Daily Expense Trend")

daily = data.groupby('Date')['Amount'].sum()

fig2, ax2 = plt.subplots()
daily.plot(ax=ax2)
ax2.set_title("Daily Expenses")
st.pyplot(fig2)

# =========================
# 🔹 SECTION 4: SIMPLE PREDICTION
# =========================
st.header("Prediction")

# Simple prediction (average-based)
predicted = avg * 7

st.write(f"Predicted Expense for Next 7 Days: ₹{predicted:.2f}")

# =========================
# 🔹 SECTION 5: ALERT
# =========================
st.header("Budget Alert")

budget = st.number_input("Enter your weekly budget:", value=3000)

if predicted > budget:
    st.error("⚠️ You may overspend!")
else:
    st.success("✅ You are within budget")
    from sklearn.linear_model import LinearRegression
import numpy as np

# Prepare data
daily = data.groupby('Date')['Amount'].sum().reset_index()

# Convert dates to numbers
daily['Day'] = np.arange(len(daily))

X = daily[['Day']]
y = daily['Amount']

# Train model
model = LinearRegression()
model.fit(X, y)

# Predict next 7 days
future_days = pd.DataFrame({
    'Day': np.arange(len(daily), len(daily) + 7)
})
predictions = model.predict(future_days)

predicted = predictions.sum()

st.write(f"Predicted Expense for Next 7 Days: ₹{predicted:.2f}")