# app.py - Complete Working Version with Fixed Priority Matrix
import csv
from collections import Counter, defaultdict
from datetime import datetime, date, timedelta
import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

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
# KPIs
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
    return total, avg_turnaround, on_time_pct, most_common_ct

# ----------------------------
# Charts
# ----------------------------
def bar_chart_from_counter(counter_dict, title):
    st.subheader(title)
    if counter_dict:
        chart_data = {"Category": list(counter_dict.keys()), 
                     "Count": list(counter_dict.values())}
        st.bar_chart(chart_data, x="Category", y="Count")
    else:
        st.info("No data to display.")

def line_chart_counts(dates_list, title):
    st.subheader(title)
    if dates_list:
        date_counts = Counter(dates_list)
        chart_data = {"Date": [d.isoformat() for d in sorted(date_counts)],
                     "Count": [date_counts[d] for d in sorted(date_counts)]}
        st.line_chart(chart_data, x="Date", y="Count")
    else:
        st.info("No data to display.")

def histogram_turnaround(values, title):
    st.subheader(title)
    if values:
        bins = [0, 3, 7, 14, 30]
        hist = [0] * (len(bins)-1)
        for v in values:
            for i in range(len(bins)-1):
                if bins[i] <= v < bins[i+1]:
                    hist[i] += 1
        chart_data = {"Range": [f"{bins[i]}-{bins[i+1]} days" for i in range(len(hist))],
                     "Count": hist}
        st.bar_chart(chart_data, x="Range", y="Count")
    else:
        st.info("No turnaround time data.")

def calendar_heatmap(rows, title="Request Volume"):
    st.subheader(title)
    counts = Counter([r["Date Submitted Parsed"] for r in rows if r["Date Submitted Parsed"]])
    if not counts:
        st.info("No data for heatmap.")
        return

    colors = [(0.9, 0.95, 1), (0.6, 0.8, 1), (0.3, 0.6, 1), (0.1, 0.4, 0.8)]
    cmap = LinearSegmentedColormap.from_list("custom_blue", colors)
    cmap.set_under(color=(0.95, 0.97, 1, 0.5))

    dates = sorted(counts.keys())
    min_date = min(dates)
    max_date = max(dates)
    
    num_weeks = (max_date - min_date).days // 7 + 2
    heatmap = np.zeros((7, num_weeks))
    
    for d, cnt in counts.items():
        week_num = (d - min_date).days // 7
        day_of_week = d.weekday()
        heatmap[day_of_week, week_num] = cnt
    
    fig, ax = plt.subplots(figsize=(max(8, num_weeks*0.6), 2.2))
    fig.patch.set_alpha(0)
    
    c = ax.imshow(heatmap, cmap=cmap, aspect='auto', 
                 interpolation='none', vmin=0.1)
    
    ax.set_facecolor((0.95, 0.97, 1, 0.3))
    ax.set_xticks([])
    ax.set_yticks(range(7))
    ax.set_yticklabels(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], 
                      color='white', weight='bold')
    
    for spine in ax.spines.values():
        spine.set_visible(False)
    
    cbar = fig.colorbar(c, ax=ax, orientation='horizontal', pad=0.08)
    cbar.outline.set_visible(False)
    cbar.ax.tick_params(colors='white', labelsize=8)
    cbar.set_label('Requests', color='white', fontsize=10, weight='bold')
    cbar.ax.set_facecolor((0.95, 0.97, 1, 0.3))
    
    plt.tight_layout()
    st.pyplot(fig, transparent=True)

# ----------------------------
# New Features (with fixed Priority Matrix)
# ----------------------------
def show_priority_matrix(rows):
    """Fixed Priority Matrix visualization"""
    if not rows:
        st.warning("No data available for priority matrix")
        return
    
    st.subheader("Priority Matrix")
    
    categories = {
        "high_urgent": 0,
        "high_not_urgent": 0,
        "low_urgent": 0,
        "low_not_urgent": 0
    }
    
    for r in rows:
        try:
            priority = str(r.get("Priority", "")).lower()
            turnaround = float(r["Turnaround Float"]) if r.get("Turnaround Float") else None
            
            if turnaround is None:
                continue
                
            if priority in ["high", "urgent"]:
                key = "high_urgent" if turnaround <= 7 else "high_not_urgent"
            else:
                key = "low_urgent" if turnaround <= 7 else "low_not_urgent"
                
            categories[key] += 1
        except (ValueError, TypeError):
            continue
    
    # Prepare matrix data
    matrix_data = [
        [categories["high_urgent"], categories["high_not_urgent"]],
        [categories["low_urgent"], categories["low_not_urgent"]]
    ]
    
    if sum(sum(row) for row in matrix_data) == 0:
        st.warning("No valid priority/turnaround data available")
        return
    
    # Create visualization
    fig, ax = plt.subplots(figsize=(6, 6))
    c = ax.imshow(matrix_data, cmap="YlOrRd")
    
    # Add text labels
    for i in range(2):
        for j in range(2):
            ax.text(j, i, matrix_data[i][j],
                    ha="center", va="center", 
                    color="black", fontsize=14, fontweight='bold')
    
    # Configure axes
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(["High Priority", "Low Priority"])
    ax.set_yticklabels(["Urgent (≤7 days)", "Not Urgent (>7 days)"])
    ax.set_title("Work Priority Matrix", pad=20, fontweight='bold')
    
    # Add colorbar
    cbar = fig.colorbar(c, ax=ax, orientation='horizontal', pad=0.1)
    cbar.set_label('Number of Requests', fontweight='bold')
    
    st.pyplot(fig)

def show_document_complexity(rows):
    """Document complexity analysis"""
    if not rows:
        return
    
    st.subheader("Document Complexity Analysis")
    
    doc_metrics = defaultdict(lambda: {"count": 0, "turnarounds": []})
    for r in rows:
        doc_type = r.get("Contract Type", "Other")
        if r["Turnaround Float"] is not None:
            try:
                turnaround = float(r["Turnaround Float"])
                doc_metrics[doc_type]["count"] += 1
                doc_metrics[doc_type]["turnarounds"].append(turnaround)
            except (ValueError, TypeError):
                continue
    
    analysis_data = []
    for doc_type, metrics in doc_metrics.items():
        if metrics["turnarounds"]:
            avg_time = sum(metrics["turnarounds"]) / len(metrics["turnarounds"])
            analysis_data.append({
                "Document Type": doc_type,
                "Count": metrics["count"],
                "Avg Turnaround": avg_time,
                "Complexity": "High" if avg_time > 7 else "Medium" if avg_time > 3 else "Low"
            })
    
    if not analysis_data:
        st.warning("No valid document complexity data available")
        return
    
    analysis_data.sort(key=lambda x: x["Avg Turnaround"], reverse=True)
    
    st.dataframe(
        analysis_data,
        column_config={
            "Avg Turnaround": st.column_config.ProgressColumn(
                "Avg Days",
                format="%.1f",
                min_value=0,
                max_value=max(item["Avg Turnaround"] for item in analysis_data) + 2
            ),
            "Complexity": st.column_config.SelectboxColumn(
                options=["High", "Medium", "Low"]
            )
        },
        hide_index=True,
        use_container_width=True
    )

# ----------------------------
# App Layout
# ----------------------------
st.set_page_config(page_title="Legal Intake Dashboard", layout="wide")
st.title("Legal Intake Dashboard")

rows_all = load_rows(CSV_PATH)

# Sidebar filters
st.sidebar.header("Filters")
all_contract_types = unique_values(rows_all, "Contract Type")
all_priorities = unique_values(rows_all, "Priority")
all_statuses = unique_values(rows_all, "Status")
all_counsels = unique_values(rows_all, "Assigned Counsel")

dates = [r["Date Submitted Parsed"] for r in rows_all if r["Date Submitted Parsed"]]
min_date = min(dates) if dates else date(2025, 1, 1)
max_date = max(dates) if dates else date(2025, 12, 31)

date_range = st.sidebar.date_input(
    "Date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

contract_filter = st.sidebar.multiselect("Contract Type", options=all_contract_types, default=[])
priority_filter = st.sidebar.multiselect("Priority", options=all_priorities, default=[])
status_filter = st.sidebar.multiselect("Status", options=all_statuses, default=[])
counsel_filter = st.sidebar.multiselect("Assigned Counsel", options=all_counsels, default=[])

filters = {
    "Contract Type": contract_filter,
    "Priority": priority_filter,
    "Status": status_filter,
    "Assigned Counsel": counsel_filter
}
rows = filter_rows(rows_all, filters, date_range)

# KPIs
total, avg_turnaround, on_time_pct, most_common_ct = kpi_values(rows)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Requests", f"{total}")
c2.metric("Average Turnaround", f"{avg_turnaround:.1f} days")
c3.metric("On-Time Completion", f"{on_time_pct:.0f}%")
c4.metric("Most Common Contract", most_common_ct)

# Tabs
tab1, tab2, tab3 = st.tabs(["Overview", "Analysis", "Details"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        bar_chart_from_counter(Counter([r.get("Contract Type", "") for r in rows]), "Contracts by Type")
    with col2:
        line_chart_counts([r["Date Submitted Parsed"] for r in rows if r["Date Submitted Parsed"]], "Requests Over Time")
    calendar_heatmap(rows)

with tab2:
    show_priority_matrix(rows)
    show_document_complexity(rows)

with tab3:
    st.subheader("Filtered Requests")
    if rows:
        cols = [
            "Request ID", "Request Name", "Requester",
            "Contract Type", "Priority", "Status",
            "Assigned Counsel", "Date Submitted",
            "Target Completion Date", "Actual Completion Date",
            "Turnaround Time (Days)"
        ]
        display_rows = [{c: r.get(c, "") for c in cols} for r in rows]
        st.dataframe(display_rows, use_container_width=True)

        def to_csv_string(dict_rows, headers):
            out = [",".join([f'"{h}"' for h in headers])]
            for d in dict_rows:
                row_vals = []
                for h in headers:
                    cell = d.get(h, "") or ""
                    cell = cell.replace('"', '""')
                    row_vals.append(f'"{cell}"')
                out.append(",".join(row_vals))
            return "\n".join(out)

        csv_bytes = to_csv_string(display_rows, cols).encode("utf-8")
        st.download_button(
            "Download filtered CSV",
            data=csv_bytes,
            file_name="filtered_requests.csv",
            mime="text/csv"
        )
    else:
        st.info("No data in the selected filter range.")
