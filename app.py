# app.py (Enhanced Original)
import csv
from collections import Counter
from datetime import datetime, date
import streamlit as st
import matplotlib.pyplot as plt  # Only for heatmap

CSV_PATH = "Touchpoint - Sheet1.csv"

# ----------------------------
# Your Original Functions (Optimized)
# ----------------------------
def parse_date(s):
    """Safer date parsing with your preferred dd/mm/YYYY format first"""
    if not s or not isinstance(s, str):
        return None
    for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d"):  # Priority to dd/mm/Y
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None

def load_rows():
    """Faster CSV loading with error handling"""
    rows = []
    with open(CSV_PATH, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            try:
                r["Date Submitted Parsed"] = parse_date(r["Date Submitted"])
                r["Turnaround Float"] = float(r["Turnaround Time (Days)"]) if r["Turnaround Time (Days)"] else None
                rows.append(r)
            except (ValueError, KeyError) as e:
                st.warning(f"Skipping row due to error: {e}")
    return rows

# ----------------------------
# Enhanced Charts (No Pandas)
# ----------------------------
def bar_chart_simple(items, title):
    """Your original bar chart with sorted results"""
    counts = Counter(items)
    if counts:
        labels, values = zip(*sorted(counts.items(), key=lambda x: -x[1]))
        st.bar_chart({"Count": values}, x=labels)
    else:
        st.info("No data")

def show_completion_timeline(rows):
    """New: Visualize request status over time"""
    date_status = {}
    for r in rows:
        if r["Date Submitted Parsed"]:
            status = r.get("Status", "Unknown")
            date_status.setdefault(r["Date Submitted Parsed"], Counter())[status] += 1
    
    if date_status:
        st.subheader("Completion Timeline")
        for date, counts in sorted(date_status.items()):
            st.write(f"**{date.strftime('%Y-%m-%d')}**")
            cols = st.columns(len(counts))
            for (status, count), col in zip(counts.items(), cols):
                col.metric(status, count)

# ----------------------------
# App Layout (Your Original + Enhancements)
# ----------------------------
def main():
    st.set_page_config(layout="wide")
    st.title("Touchpoint Legal Dashboard")
    
    # Load data
    rows = load_rows()
    
    # Filters (Improved UI)
    with st.sidebar:
        st.header("Filters")
        date_options = sorted({r["Date Submitted Parsed"] for r in rows if r["Date Submitted Parsed"]})
        date_range = st.date_input(
            "Date range",
            value=(min(date_options), max(date_options)) if date_options else (date(2023,1,1), date.today())
        
        contract_types = sorted({r["Contract Type"] for r in rows if r["Contract Type"]})
        selected_types = st.multiselect("Contract Types", contract_types, default=contract_types[:3])
    
    # Apply filters
    filtered = [
        r for r in rows 
        if (r["Date Submitted Parsed"] and 
            date_range[0] <= r["Date Submitted Parsed"] <= date_range[1] and
            r.get("Contract Type") in selected_types)
    ]
    
    # KPIs (Your Original)
    completed = [r for r in filtered if r["Status"].lower() in ("completed", "closed")]
    on_time = sum(1 for r in completed if r["Turnaround Float"] and r["Turnaround Float"] <= 7)
    
    cols = st.columns(4)
    cols[0].metric("Total", len(filtered))
    cols[1].metric("Completed", len(completed))
    cols[2].metric("On Time", f"{on_time}/{len(completed)}" if completed else "0")
    cols[3].metric("Avg Days", 
                  f"{sum(r['Turnaround Float'] for r in completed if r['Turnaround Float']) / len(completed):.1f}" 
                  if completed else "N/A")
    
    # Tabs (Enhanced)
    tab1, tab2 = st.tabs(["Overview", "Details"])
    
    with tab1:
        bar_chart_simple([r["Contract Type"] for r in filtered], "Contracts by Type")
        bar_chart_simple([r["Priority"] for r in filtered], "By Priority")
        show_completion_timeline(filtered)
    
    with tab2:
        st.subheader("All Requests")
        st.dataframe([
            {
                "ID": r["Request ID"],
                "Type": r["Contract Type"],
                "Priority": r["Priority"],
                "Status": r["Status"],
                "Submitted": r["Date Submitted"],
                "Turnaround": r["Turnaround Time (Days)"]
            }
            for r in filtered
        ])

if __name__ == "__main__":
    main()
