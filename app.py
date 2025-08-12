# app.py
import csv
from collections import Counter, defaultdict
from datetime import datetime, date
import streamlit as st
import matplotlib.pyplot as plt
import numpy as np

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
# Charts (native)
# ----------------------------
def bar_chart_from_counter(counter_dict, title):
    labels, values = zip(*sorted(counter_dict.items(), key=lambda kv: (-kv[1], kv[0]))) if counter_dict else ([], [])
    st.subheader(title)
    if labels:
        st.bar_chart({"Count": list(values)}, x=list(labels))
    else:
        st.info("No data to display.")

def line_chart_counts(dates_list, title):
    counts = Counter(dates_list)
    sorted_dates = sorted(counts)
    values = [counts[d] for d in sorted_dates]
    st.subheader(title)
    if sorted_dates:
        st.line_chart({"Count": values}, x=[d.isoformat() for d in sorted_dates])
    else:
        st.info("No data to display.")

def histogram_turnaround(values, title):
    st.subheader(title)
    if values:
        fig, ax = plt.subplots()
        ax.hist(values, bins=min(20, len(set(values))), color='skyblue', edgecolor='black')
        ax.set_xlabel("Turnaround Time (Days)")
        ax.set_ylabel("Frequency")
        st.pyplot(fig)
    else:
        st.info("No turnaround time data.")

def calendar_heatmap(rows, title="Calendar Heatmap"):
    st.subheader(title)
    counts = Counter([r["Date Submitted Parsed"] for r in rows if r["Date Submitted Parsed"]])
    if not counts:
        st.info("No data for heatmap.")
        return

    weeks = sorted({d.isocalendar()[:2] for d in counts})
    week_idx = {w: i for i, w in enumerate(weeks)}
    heatmap = np.zeros((7, len(weeks)))

    for d, cnt in counts.items():
        year, week, weekday = d.isocalendar()
        weekday -= 1  # Monday=0
        heatmap[weekday, week_idx[(year, week)]] = cnt

    fig, ax = plt.subplots(figsize=(len(weeks) / 2, 2))
    c = ax.imshow(heatmap, cmap="Blues", aspect="auto")
    ax.set_yticks(range(7))
    ax.set_yticklabels(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
    ax.set_xticks(range(len(weeks)))
    ax.set_xticklabels([f"{y}-W{w}" for y, w in weeks], rotation=90, fontsize=8)
    fig.colorbar(c, ax=ax, orientation="vertical", label="Requests")
    st.pyplot(fig)

# ----------------------------
# App
# ----------------------------
st.set_page_config(page_title="Legal Intake Dashboard", layout="wide")
st.title("Legal Intake Dashboard (Native Streamlit)")

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

date_range = st.sidebar.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
contract_filter = st.sidebar.multiselect("Contract Type", options=all_contract_types, default=[])
priority_filter = st.sidebar.multiselect("Priority", options=all_priorities, default=[])
status_filter = st.sidebar.multiselect("Status", options=all_statuses, default=[])
counsel_filter = st.sidebar.multiselect("Assigned Counsel", options=all_counsels, default=[])

filters = {"Contract Type": contract_filter, "Priority": priority_filter, "Status": status_filter, "Assigned Counsel": counsel_filter}
rows = filter_rows(rows_all, filters, date_range)

# KPIs
total, avg_turnaround, on_time_pct, most_common_ct = kpi_values(rows)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Requests", f"{total}")
c2.metric("Average Turnaround", f"{avg_turnaround:.1f} days")
c3.metric("On-Time Completion", f"{on_time_pct:.0f}%")
c4.metric("Most Common Contract", most_common_ct)

# Tabs
tab1, tab2, tab3 = st.tabs(["Overview", "Performance", "Details"])

with tab1:
    bar_chart_from_counter(Counter([r.get("Contract Type", "") for r in rows]), "Most Common Contract Types")
    line_chart_counts([r["Date Submitted Parsed"] for r in rows if r["Date Submitted Parsed"]], "Requests Over Time")
    calendar_heatmap(rows, "Request Volume by Weekday & Week")

with tab2:
    bar_chart_from_counter(Counter([r.get("Priority", "") for r in rows]), "Requests by Priority")
    bar_chart_from_counter(Counter([r.get("Assigned Counsel", "") for r in rows]), "Requests by Assigned Counsel")
    histogram_turnaround([r["Turnaround Float"] for r in rows if r["Turnaround Float"] is not None], "Turnaround Time Distribution")

with tab3:
    st.subheader("Filtered Requests")
    if rows:
        cols = ["Request ID", "Request Name", "Requester", "Contract Type", "Priority", "Status", "Assigned Counsel",
                "Date Submitted", "Target Completion Date", "Actual Completion Date", "Turnaround Time (Days)"]
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
        st.download_button("Download filtered CSV", data=csv_bytes, file_name="filtered_requests.csv", mime="text/csv")
    else:
        st.info("No data in the selected filter range.")
