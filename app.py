import csv
from collections import Counter, defaultdict
from datetime import datetime
import streamlit as st

# Load CSV data
data = []
with open("Touchpoint - Sheet1.csv", newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        data.append(row)

# Parse submission dates and filter valid turnaround times
submission_dates = []
contract_types = []
turnaround_times_by_contract = defaultdict(list)

for row in data:
    # Parse date submitted
    date_str = row.get("Date Submitted", "")
    try:
        date = datetime.strptime(date_str, "%d/%m/%Y")
        submission_dates.append(date)
    except:
        pass

    # Collect contract types
    contract_type = row.get("Contract Type", "").strip()
    if contract_type:
        contract_types.append(contract_type)

    # Collect turnaround times by contract type
    turnaround_str = row.get("Turnaround Time (Days)", "").strip()
    if turnaround_str and contract_type:
        try:
            turnaround = float(turnaround_str)
            turnaround_times_by_contract[contrac]()_
