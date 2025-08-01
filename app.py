import csv
from collections import Counter, defaultdict
from datetime import datetime
import streamlit as st

def safe_get_strip(row, key):
    val = row.get(key)
    if val is None:
        return ""
    else:
        return val.strip()

# Load CSV data
data = []
with open("Touchpoint - Sheet1.csv", newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        data.append(row)

# Prepare lists and dicts to store processed data
submission_dates = []
contract_types = []
turnaround_times_by_contract = defaultdict(list)

for row in data:
    date_str = safe_get_strip(row, "Date Submitted")
    try:
        date = datetime.strptime(date_str, "%d/%m/%Y")
        submission_dates.append(date)
    except:
        pass

    contract_type = safe_get_strip(row, "Contract Type")
    turnaround_str = safe_get_strip(row, "Turnaround Time (Days)")

    if contract_type:
        contract_types.append(contract_type)

    if turnaround_str and contract_type:
        try:
            turnaround = float(turnaround_str)
            turnaround_times_by_contract[contract_type].append(turnaround)
        except:
            pass

# Aggregate data for charts

# Most common contract types
contract_counts = Counter(contract_types)

# Requests submitted over time
date_counts = Counter(submission_dates)
dates_sorted = sorted(date_counts.keys())
date_labels = [d.strftime("%Y-%m-%d") for d in dates_sorted]
date_values = [date_counts[d] for d in dates_sorted]

# Average turnaround time by contract type
avg_turnaround = {
    ct: sum(times) / len(times) for ct, times in turnaround_times_by_contract.items()
}

# Streamlit UI
st.title("Legal Intake Data Dashboard")

st.subheader("Most Common Contract Types")
st.bar_chart(contract_counts)

st.subheader("Requests Submitted Over Time")
st.line_chart(dict(zip(date_labels, date_values)))

st.subheader("Average Turnaround Time by Contract Type")
st.bar_chart(avg_turnaround)
