# app.py
import csv
from collections import Counter
from datetime import datetime, date
import streamlit as st

CSV_PATH = "Touchpoint - Sheet1.csv"

# ----------------------------
# Pure-Python Utilities (No Pandas/Numpy)
# ----------------------------
def parse_date(s):
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None

def load_rows():
    rows = []
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            r["Date Submitted Parsed"] = parse_date(r["Date Submitted"])
            r["Turnaround Float"] = float(r["Turnaround Time (Days)"]) if r["Turnaround Time (Days)"] else None
            rows.append(r)
    return rows

# ----------------------------
# Charts (Pure Python)
# ----------------------------
def show_bar_chart(items, title):
    counts = Counter(items)
    if counts:
        st.bar_chart({"Count": list(counts.values())}, x=list(counts.keys()))
    else:
        st.warning("No data for chart")

def show_turnaround_histogram(values, title):
    if values:
        # Simple binning without numpy
        bins = [0, 3, 7, 14, 30]
        hist = [0] * (len(bins)-1)
        for v in values:
            for i in range(len(bins)-1):
                if bins[i] <= v < bins[i+1]:
                    hist[i] += 1
        st.bar_chart({"Count": hist}, x=[f"{bins[i]}-{bins[i+1]} days" for i in range(len(hist))])
    else:
        st.warning("No turnaround data")

# ----------------------------
# Streamlit App
# ----------------------------
def main():
    st.set_page_config(layout="wide")
    st.title("Touchpoint Legal Dashboard")
    
    # Load data
    rows = load_rows()
    
    # Filters
    st.sidebar.header("Filters")
    date_min = min(r["Date Submitted Parsed"] for r in rows if r["Date Submitted Parsed"])
    date_max = max(r["Date Submitted Parsed"] for r in rows if r["Date Submitted Parsed"])
    date_range = st.sidebar.date_input("Date range", [date_min, date_max])
    
    # Filter rows
    filtered = [
        r for r in rows 
        if (r["Date Submitted Parsed"] and 
            date_range[0] <= r["Date Submitted Parsed"] <= date_range[1])
    ]
    
    # KPIs
    completed = [r for r in filtered if r["Status"].lower() in ("completed", "closed")]
    on_time = sum(1 for r in completed if r["Turnaround Float"] and r["Turnaround Float"] <= 7)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Requests", len(filtered))
    col2.metric("Completed", len(completed))
    col3.metric("On Time %", f"{(on_time/len(completed)*100 if completed else 0):.0f}%")
    
    # Charts
    tab1, tab2 = st.tabs(["Overview", "Details"])
    
    with tab1:
        show_bar_chart([r["Contract Type"] for r in filtered], "By Contract Type")
        show_bar_chart([r["Priority"] for r in filtered], "By Priority")
    
    with tab2:
        show_turnaround_histogram(
            [r["Turnaround Float"] for r in filtered if r["Turnaround Float"]], 
            "Turnaround Time"
        )
        st.dataframe(filtered)

if __name__ == "__main__":
    main()
