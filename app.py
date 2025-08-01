import streamlit as st
import pandas as pd
import plotly.express as px

# Load data
df = pd.read_csv("Touchpoint - Sheet1.csv")

# Parse submission dates
df["Date Submitted"] = pd.to_datetime(df["Date Submitted"], format="%d/%m/%Y", errors="coerce")

# Filter rows with valid turnaround time
df_turnaround = df.dropna(subset=["Turnaround Time (Days)", "Contract Type"])

# Prepare data for most common contract types
common_contracts = df["Contract Type"].value_counts().reset_index()
common_contracts.columns = ["Contract Type", "Count"]

# Prepare data for submissions over time
submissions_by_date = df["Date Submitted"].value_counts().sort_index().reset_index()
submissions_by_date.columns = ["Date", "Count"]

# Prepare average turnaround time by contract type
avg_turnaround = df_turnaround.groupby("Contract Type")["Turnaround Time (Days)"].mean().reset_index()

# Streamlit layout
st.title("Legal Intake Data Dashboard")
st.markdown("This dashboard displays summary visualizations based on data exported from Airtable.")

# Chart 1: Most common contract types
st.subheader("Most Common Contract Types")
fig1 = px.bar(common_contracts, x="Contract Type", y="Count", color="Contract Type", text="Count")
st.plotly_chart(fig1, use_container_width=True)

# Chart 2: Requests submitted over time
st.subheader("Requests Submitted Over Time")
fig2 = px.line(submissions_by_date, x="Date", y="Count", markers=True)
st.plotly_chart(fig2, use_container_width=True)

# Chart 3: Average turnaround time by contract type
st.subheader("Average Turnaround Time by Contract Type")
fig3 = px.bar(avg_turnaround, x="Contract Type", y="Turnaround Time (Days)", color="Contract Type", text_auto=True)
st.plotly_chart(fig3, use_container_width=True)
