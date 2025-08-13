# app.py (Fixed Hybrid Version)
import csv
from collections import Counter, defaultdict
from datetime import datetime, date
import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

CSV_PATH = "Touchpoint - Sheet1.csv"

# ----------------------------
# Utilities (Keep your working version)
# ----------------------------
def parse_date(s):
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    # Prioritize dd/mm/YYYY format first since that's what your CSV uses
    for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None

def to_float(s):
    if s is None or str(s).strip() == "":
        return None
    try:
        return float(s)
    except (TypeError, ValueError):
        return None

def load_rows(csv_path):
    # Use pandas for more robust CSV reading
    df = pd.read_csv(csv_path)
    rows = df.to_dict('records')
    for r in rows:
        r["Date Submitted Parsed"] = parse_date(r.get("Date Submitted", ""))
        r["Turnaround Float"] = to_float(r.get("Turnaround Time (Days)"))
        # Handle empty completion dates
        r["Actual Completion Date Parsed"] = parse_date(r.get("Actual Completion Date", ""))
    return rows

# ----------------------------
# KPIs (Enhanced but safer)
# ----------------------------
def kpi_values(rows):
    total = len(rows)
    
    # Safer completed detection
    completed = [r for r in rows 
                if str(r.get("Status", "")).strip().lower() in {"completed", "done", "closed"}
                and r.get("Actual Completion Date Parsed")]
    
    # On-time calculation (within 7 days)
    on_time = 0
    for r in completed:
        if r["Turnaround Float"] is not None:
            if r["Turnaround Float"] <= 7:
                on_time += 1
            elif r["Actual Completion Date Parsed"] and r["Date Submitted Parsed"]:
                actual_days = (r["Actual Completion Date Parsed"] - r["Date Submitted Parsed"]).days
                if actual_days <= 7:
                    on_time += 1
    
    on_time_pct = (on_time / len(completed) * 100 if completed else 0
    
    # Turnaround calculation
    turnaround_vals = []
    for r in rows:
        if r["Turnaround Float"] is not None:
            turnaround_vals.append(r["Turnaround Float"])
        elif r["Actual Completion Date Parsed"] and r["Date Submitted Parsed"]:
            turnaround_vals.append(
                (r["Actual Completion Date Parsed"] - r["Date Submitted Parsed"]).days
            )
    
    avg_turnaround = sum(turnaround_vals) / len(turnaround_vals) if turnaround_vals else 0
    
    # Contract type analysis
    contract_types = [str(r.get("Contract Type", "")).strip() for r in rows]
    most_common_ct = max(set(contract_types), key=contract_types.count) if contract_types else "N/A"
    
    return {
        "total": total,
        "avg_turnaround": avg_turnaround,
        "on_time_pct": on_time_pct,
        "most_common_ct": most_common_ct
    }

# ----------------------------
# Enhanced UI (But safer)
# ----------------------------
def main():
    st.set_page_config(page_title="Legal Intake Dashboard", layout="wide")
    st.title("Legal Intake Dashboard")
    
    rows_all = load_rows(CSV_PATH)
    
    # Debug: Uncomment to see raw data
    # st.write("Sample row:", rows_all[0] if rows_all else "No data")
    
    # Sidebar filters
    st.sidebar.header("Filters")
    
    # Date range handling
    dates = [r["Date Submitted Parsed"] for r in rows_all if r["Date Submitted Parsed"]]
    min_date = min(dates) if dates else date(2025, 1, 1)
    max_date = max(dates) if dates else date(2025, 12, 31)
    
    date_range = st.sidebar.date_input("Date range", 
                                     value=(min_date, max_date), 
                                     min_value=min_date, 
                                     max_value=max_date)
    
    # Dynamic filter options
    filter_options = {
        "Contract Type": sorted({r.get("Contract Type", "") for r in rows_all}),
        "Priority": sorted({r.get("Priority", "") for r in rows_all}),
        "Status": sorted({r.get("Status", "") for r in rows_all}),
        "Assigned Counsel": sorted({r.get("Assigned Counsel", "") for r in rows_all})
    }
    
    filters = {}
    for key, options in filter_options.items():
        filters[key] = st.sidebar.multiselect(key, options=options, default=options)
    
    # Apply filters
    filtered_rows = []
    for r in rows_all:
        if not (r["Date Submitted Parsed"] and date_range[0] <= r["Date Submitted Parsed"] <= date_range[1]):
            continue
        
        include = True
        for key, selected in filters.items():
            if selected and str(r.get(key, "")).strip() not in selected:
                include = False
                break
                
        if include:
            filtered_rows.append(r)
    
    # KPIs
    kpis = kpi_values(filtered_rows)
    
    cols = st.columns(4)
    cols[0].metric("Total Requests", kpis["total"])
    cols[1].metric("Avg Turnaround", f"{kpis['avg_turnaround']:.1f} days")
    cols[2].metric("On-Time Rate", f"{kpis['on_time_pct']:.0f}%")
    cols[3].metric("Top Contract", kpis["most_common_ct"])
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["Overview", "Performance", "Details"])
    
    with tab1:
        st.subheader("Request Volume")
        if filtered_rows:
            # Daily volume line chart
            date_counts = Counter(r["Date Submitted Parsed"] for r in filtered_rows if r["Date Submitted Parsed"])
            dates_sorted = sorted(date_counts.keys())
            st.line_chart({
                "Requests": [date_counts[d] for d in dates_sorted]
            }, x=dates_sorted)
            
            # Contract type distribution
            contract_counts = Counter(r.get("Contract Type", "Unknown") for r in filtered_rows)
            st.bar_chart(contract_counts)
    
    with tab2:
        st.subheader("Performance Metrics")
        if filtered_rows:
            # Priority distribution
            priority_counts = Counter(r.get("Priority", "Unknown") for r in filtered_rows)
            st.bar_chart(priority_counts)
            
            # Turnaround time histogram
            turnaround_data = [
                r["Turnaround Float"] for r in filtered_rows 
                if r["Turnaround Float"] is not None
            ]
            if turnaround_data:
                st.subheader("Turnaround Time (Days)")
                st.bar_chart(turnaround_data)
    
    with tab3:
        st.subheader("Request Details")
        if filtered_rows:
            # Display as dataframe
            df = pd.DataFrame(filtered_rows)
            display_cols = [
                "Request ID", "Request Name", "Requester", 
                "Contract Type", "Priority", "Status",
                "Assigned Counsel", "Date Submitted",
                "Target Completion Date", "Actual Completion Date",
                "Turnaround Time (Days)"
            ]
            st.dataframe(df[display_cols], use_container_width=True)
            
            # Download button
            csv = df[display_cols].to_csv(index=False)
            st.download_button(
                "Download CSV",
                data=csv,
                file_name="legal_requests.csv",
                mime="text/csv"
            )

if __name__ == "__main__":
    main()
