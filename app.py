# app.py
import csv
from collections import Counter, defaultdict
from datetime import datetime, date
import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import calendar
from streamlit_tags import st_tags  # pip install streamlit-tags

CSV_PATH = "Touchpoint - Sheet1.csv"

# ----------------------------
# Utilities
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

def to_float(s):
    if s is None:
        return None
    try:
        return float(s)
    except (TypeError, ValueError):
        return None

def load_rows(csv_path):
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for r in reader:
            r = dict(r)
            r["Date Submitted Parsed"] = parse_date(r.get("Date Submitted", ""))
            r["Turnaround Float"] = to_float(r.get("Turnaround Time (Days)"))
            rows.append(r)
    return rows

def unique_values(rows, key):
    vals = sorted({(r.get(key) or "").strip() for r in rows if (r.get(key) or "").strip()})
    return vals

def filter_rows(rows, filters, date_range):
    start, end = date_range
    out = []
    for r in rows:
        ds = r.get("Date Submitted Parsed")
        if ds is None or ds < start or ds > end:
            continue
        keep = True
        for k, allowed in filters.items():
            if allowed:
                v = (r.get(k) or "").strip()
                if v not in allowed:
                    keep = False
                    break
        if keep:
            out.append(r)
    return out

# ----------------------------
# Enhanced KPIs
# ----------------------------
def kpi_values(rows):
    total = len(rows)
    completed = [r for r in rows if (r.get("Status") or "").strip().lower() in {"completed", "done", "closed"}]
    on_time = sum(1 for r in completed if r["Turnaround Float"] is not None and r["Turnaround Float"] <= 7)
    on_time_pct = (on_time / len(completed) * 100.0) if completed else 0.0
    turnaround_vals = [r["Turnaround Float"] for r in rows if r["Turnaround Float"] is not None]
    avg_turnaround = sum(turnaround_vals) / len(turnaround_vals) if turnaround_vals else 0.0
    counts = Counter([(r.get("Contract Type") or "").strip() for r in rows if (r.get("Contract Type") or "").strip()])
    most_common_ct = counts.most_common(1)[0][0] if counts else "—"
    
    # New KPIs
    high_priority = sum(1 for r in rows if (r.get("Priority") or "").lower() in {"high", "urgent"})
    high_priority_pct = (high_priority / total * 100) if total else 0
    overdue = sum(1 for r in rows if (r.get("Status") or "").lower() not in {"completed", "done", "closed"} 
                and r.get("Target Completion Date") 
                and parse_date(r.get("Target Completion Date")) 
                and parse_date(r.get("Target Completion Date")) < date.today())
    
    return {
        "total": total,
        "avg_turnaround": avg_turnaround,
        "on_time_pct": on_time_pct,
        "most_common_ct": most_common_ct,
        "high_priority_pct": high_priority_pct,
        "overdue": overdue
    }

# ----------------------------
# Enhanced Charts
# ----------------------------
def interactive_bar_chart(data, x, y, title, color=None):
    df = pd.DataFrame(data)
    fig = px.bar(df, x=x, y=y, title=title, color=color,
                 text=y, hover_data=[x, y])
    fig.update_traces(texttemplate='%{text:.2s}', textposition='outside')
    fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
    st.plotly_chart(fig, use_container_width=True)

def interactive_pie_chart(labels, values, title):
    fig = px.pie(names=labels, values=values, title=title,
                 hole=0.3, hover_data=[values])
    fig.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig, use_container_width=True)

def status_timeline_chart(rows):
    df = pd.DataFrame([
        {
            "Request": r.get("Request ID") or f"Request {i}",
            "Start": r["Date Submitted Parsed"],
            "Finish": parse_date(r.get("Actual Completion Date")) or date.today(),
            "Status": r.get("Status") or "Unknown",
            "Turnaround": r.get("Turnaround Float") or 0,
            "Priority": r.get("Priority") or "Normal"
        }
        for i, r in enumerate(rows) if r["Date Submitted Parsed"]
    ])
    
    if not df.empty:
        fig = px.timeline(df, x_start="Start", x_end="Finish", y="Request",
                          color="Status", title="Request Status Timeline",
                          hover_data=["Priority", "Turnaround"])
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No timeline data available.")

def counsel_performance_chart(rows):
    counsel_data = defaultdict(list)
    for r in rows:
        counsel = (r.get("Assigned Counsel") or "Unassigned").strip()
        if counsel and r["Turnaround Float"] is not None:
            counsel_data[counsel].append(r["Turnaround Float"])
    
    if counsel_data:
        df = pd.DataFrame([
            {"Counsel": k, "Average Turnaround": sum(v)/len(v), "Cases": len(v)}
            for k, v in counsel_data.items()
        ])
        fig = px.scatter(df, x="Cases", y="Average Turnaround", 
                         size="Cases", color="Counsel",
                         title="Counsel Performance: Volume vs Turnaround",
                         hover_data=["Counsel", "Average Turnaround", "Cases"])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No counsel performance data available.")

def monthly_trend_chart(rows):
    month_counts = defaultdict(int)
    month_turnaround = defaultdict(list)
    
    for r in rows:
        if r["Date Submitted Parsed"]:
            month = r["Date Submitted Parsed"].strftime("%Y-%m")
            month_counts[month] += 1
            if r["Turnaround Float"] is not None:
                month_turnaround[month].append(r["Turnaround Float"])
    
    if month_counts:
        df = pd.DataFrame({
            "Month": list(month_counts.keys()),
            "Requests": list(month_counts.values()),
            "Avg Turnaround": [sum(month_turnaround[m])/len(month_turnaround[m]) 
                               if m in month_turnaround and month_turnaround[m] else 0 
                               for m in month_counts.keys()]
        })
        
        fig = px.line(df, x="Month", y="Requests", title="Monthly Request Trends",
                      markers=True)
        fig.add_bar(x=df["Month"], y=df["Avg Turnaround"], 
                   name="Avg Turnaround (days)", 
                   marker_color="rgba(255, 165, 0, 0.6)")
        fig.update_layout(barmode="overlay")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No monthly trend data available.")

# ----------------------------
# App Layout
# ----------------------------
st.set_page_config(page_title="Touchpoint Legal Dashboard", layout="wide", page_icon="⚖️")
st.title("⚖️ Touchpoint Legal Intake Dashboard")

# Custom CSS for better styling
st.markdown("""
<style>
    .metric-box {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }
    .metric-title {
        font-size: 14px;
        color: #6c757d;
        font-weight: 600;
    }
    .metric-value {
        font-size: 24px;
        color: #212529;
        font-weight: 700;
    }
    .stProgress > div > div > div > div {
        background-color: #2e86de;
    }
</style>
""", unsafe_allow_html=True)

rows_all = load_rows(CSV_PATH)

# Sidebar filters with improved layout
with st.sidebar:
    st.header("🔍 Filters")
    
    # Date range with improved defaults
    dates = [r["Date Submitted Parsed"] for r in rows_all if r["Date Submitted Parsed"]]
    min_date = min(dates) if dates else date(2025, 1, 1)
    max_date = max(dates) if dates else date(2025, 12, 31)
    
    date_range = st.date_input("📅 Date range", value=(min_date, max_date), 
                              min_value=min_date, max_value=max_date)
    
    # Collapsible filter sections
    with st.expander("📑 Contract Types", expanded=True):
        all_contract_types = unique_values(rows_all, "Contract Type")
        contract_filter = st.multiselect("Select contract types", 
                                       options=all_contract_types, 
                                       default=all_contract_types[:3] if all_contract_types else [])
    
    with st.expander("⚠️ Priorities", expanded=True):
        all_priorities = unique_values(rows_all, "Priority")
        priority_filter = st.multiselect("Select priorities", 
                                       options=all_priorities, 
                                       default=all_priorities)
    
    with st.expander("📊 Statuses", expanded=True):
        all_statuses = unique_values(rows_all, "Status")
        status_filter = st.multiselect("Select statuses", 
                                      options=all_statuses, 
                                      default=all_statuses)
    
    with st.expander("👨‍⚖️ Assigned Counsel", expanded=True):
        all_counsels = unique_values(rows_all, "Assigned Counsel")
        counsel_filter = st.multiselect("Select counsel", 
                                      options=all_counsels, 
                                      default=all_counsels)
    
    # Keyword search
    keywords = st_tags(label="🔍 Search keywords:",
                      text="Enter keywords to search",
                      value=[],
                      suggestions=["NDA", "Agreement", "Amendment", "Review"])

filters = {
    "Contract Type": contract_filter, 
    "Priority": priority_filter, 
    "Status": status_filter, 
    "Assigned Counsel": counsel_filter
}

# Apply filters
rows = filter_rows(rows_all, filters, date_range)

# Apply keyword search if any keywords provided
if keywords:
    rows = [r for r in rows if any(kw.lower() in str(r).lower() for kw in keywords)]

# Enhanced KPIs with progress indicators
kpis = kpi_values(rows)

st.header("📊 Key Metrics")
col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.markdown(f"""
    <div class="metric-box">
        <div class="metric-title">Total Requests</div>
        <div class="metric-value">{kpis['total']}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-box">
        <div class="metric-title">Avg Turnaround</div>
        <div class="metric-value">{kpis['avg_turnaround']:.1f} days</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-box">
        <div class="metric-title">On-Time Completion</div>
        <div class="metric-value">{kpis['on_time_pct']:.0f}%</div>
    </div>
    """, unsafe_allow_html=True)
    st.progress(kpis['on_time_pct'] / 100)

with col4:
    st.markdown(f"""
    <div class="metric-box">
        <div class="metric-title">High Priority</div>
        <div class="metric-value">{kpis['high_priority_pct']:.0f}%</div>
    </div>
    """, unsafe_allow_html=True)
    st.progress(kpis['high_priority_pct'] / 100)

with col5:
    st.markdown(f"""
    <div class="metric-box">
        <div class="metric-title">Most Common Contract</div>
        <div class="metric-value">{kpis['most_common_ct']}</div>
    </div>
    """, unsafe_allow_html=True)

with col6:
    st.markdown(f"""
    <div class="metric-box">
        <div class="metric-title">Overdue Requests</div>
        <div class="metric-value">{kpis['overdue']}</div>
    </div>
    """, unsafe_allow_html=True)

# Tabs with enhanced content
tab1, tab2, tab3, tab4 = st.tabs(["📈 Overview", "⚡ Performance", "👨‍⚖️ Counsel", "📋 Details"])

with tab1:
    st.subheader("📈 Request Overview")
    
    c1, c2 = st.columns(2)
    with c1:
        contract_counts = Counter([r.get("Contract Type", "") for r in rows])
        interactive_bar_chart(
            {"Contract Type": list(contract_counts.keys()), "Count": list(contract_counts.values())},
            x="Contract Type", y="Count", title="Requests by Contract Type"
        )
    
    with c2:
        status_counts = Counter([r.get("Status", "") for r in rows])
        interactive_pie_chart(
            labels=list(status_counts.keys()),
            values=list(status_counts.values()),
            title="Request Status Distribution"
        )
    
    monthly_trend_chart(rows)
    status_timeline_chart(rows)

with tab2:
    st.subheader("⚡ Performance Metrics")
    
    c1, c2 = st.columns(2)
    with c1:
        priority_counts = Counter([r.get("Priority", "") for r in rows])
        interactive_bar_chart(
            {"Priority": list(priority_counts.keys()), "Count": list(priority_counts.values())},
            x="Priority", y="Count", title="Requests by Priority", color="Priority"
        )
    
    with c2:
        turnaround_vals = [r["Turnaround Float"] for r in rows if r["Turnaround Float"] is not None]
        if turnaround_vals:
            fig = px.histogram(x=turnaround_vals, nbins=20, 
                               title="Turnaround Time Distribution",
                               labels={"x": "Turnaround Time (Days)", "y": "Count"},
                               color_discrete_sequence=['#2e86de'])
            fig.update_layout(bargap=0.1)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No turnaround time data available.")
    
    counsel_performance_chart(rows)

with tab3:
    st.subheader("👨‍⚖️ Counsel Performance")
    
    counsel_counts = Counter([r.get("Assigned Counsel", "") for r in rows])
    if counsel_counts:
        df = pd.DataFrame({
            "Counsel": list(counsel_counts.keys()),
            "Cases": list(counsel_counts.values())
        })
        
        c1, c2 = st.columns(2)
        with c1:
            fig = px.bar(df, x="Counsel", y="Cases", 
                         title="Case Load by Counsel",
                         color="Counsel")
            st.plotly_chart(fig, use_container_width=True)
        
        with c2:
            fig = px.pie(df, names="Counsel", values="Cases",
                         title="Case Distribution Among Counsel",
                         hole=0.3)
            st.plotly_chart(fig, use_container_width=True)
        
        # Detailed counsel stats
        st.subheader("Detailed Counsel Metrics")
        counsel_stats = []
        for counsel in counsel_counts:
            counsel_rows = [r for r in rows if (r.get("Assigned Counsel") or "").strip() == counsel]
            turnaround = [r["Turnaround Float"] for r in counsel_rows if r["Turnaround Float"] is not None]
            avg_turnaround = sum(turnaround)/len(turnaround) if turnaround else 0
            completed = sum(1 for r in counsel_rows if (r.get("Status") or "").lower() in {"completed", "done", "closed"})
            completion_pct = (completed / len(counsel_rows)) * 100 if counsel_rows else 0
            counsel_stats.append({
                "Counsel": counsel,
                "Total Cases": len(counsel_rows),
                "Avg Turnaround": avg_turnaround,
                "Completion %": completion_pct,
                "Overdue": sum(1 for r in counsel_rows if (r.get("Status") or "").lower() not in {"completed", "done", "closed"} 
                              and r.get("Target Completion Date") 
                              and parse_date(r.get("Target Completion Date")) 
                              and parse_date(r.get("Target Completion Date")) < date.today())
            })
        
        st.dataframe(pd.DataFrame(counsel_stats).sort_values("Avg Turnaround"), 
                     use_container_width=True)
    else:
        st.info("No counsel data available.")

with tab4:
    st.subheader("📋 Request Details")
    
    if rows:
        cols = ["Request ID", "Request Name", "Requester", "Contract Type", "Priority", 
                "Status", "Assigned Counsel", "Date Submitted", "Target Completion Date", 
                "Actual Completion Date", "Turnaround Time (Days)"]
        display_rows = [{c: r.get(c, "") for c in cols} for r in rows]
        df = pd.DataFrame(display_rows)
        
        # Add filtering
        with st.expander("🔍 Advanced Filtering", expanded=False):
            filter_cols = st.columns(3)
            with filter_cols[0]:
                status_filter = st.multiselect("Filter by Status", options=df["Status"].unique(), default=df["Status"].unique())
            with filter_cols[1]:
                priority_filter = st.multiselect("Filter by Priority", options=df["Priority"].unique(), default=df["Priority"].unique())
            with filter_cols[2]:
                counsel_filter = st.multiselect("Filter by Counsel", options=df["Assigned Counsel"].unique(), default=df["Assigned Counsel"].unique())
            
            df = df[
                (df["Status"].isin(status_filter)) &
                (df["Priority"].isin(priority_filter)) &
                (df["Assigned Counsel"].isin(counsel_filter))
            ]
        
        st.dataframe(df, use_container_width=True, height=600)
        
        # Download options
        st.download_button(
            label="📥 Download as CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="touchpoint_legal_requests.csv",
            mime="text/csv"
        )
    else:
        st.info("No data in the selected filter range.")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #6c757d; font-size: 12px;">
    Touchpoint Legal Dashboard • Last updated: {date} • v1.1.0
</div>
""".format(date=date.today().strftime("%Y-%m-%d")), unsafe_allow_html=True)
