# app.py - Complete Enhanced Version
import csv
from collections import Counter, defaultdict
from datetime import datetime, date, timedelta
import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

CSV_PATH = "Touchpoint - Sheet1.csv"

# ----------------------------
# Utilities (unchanged)
# ----------------------------
[... previous utility functions remain exactly the same ...]

# ----------------------------
# Enhanced Charts
# ----------------------------
[... previous chart functions including the improved calendar_heatmap ...]

# ----------------------------
# New Analytical Features
# ----------------------------
def show_priority_matrix(rows):
    """New Feature: 2x2 Priority Matrix"""
    if not rows:
        return
    
    st.subheader("Priority Matrix")
    
    # Categorize requests
    high_urgent = []
    high_not_urgent = []
    low_urgent = []
    low_not_urgent = []
    
    for r in rows:
        priority = r.get("Priority", "").lower()
        turnaround = r.get("Turnaround Float", float('inf'))
        
        if priority in ["high", "urgent"]:
            if turnaround <= 7:
                high_urgent.append(r)
            else:
                high_not_urgent.append(r)
        else:
            if turnaround <= 7:
                low_urgent.append(r)
            else:
                low_not_urgent.append(r)
    
    # Create matrix data
    matrix_data = {
        "Urgent": [len(high_urgent), len(low_urgent)],
        "Not Urgent": [len(high_not_urgent), len(low_not_urgent)]
    }
    
    # Visualize with colored matrix
    fig, ax = plt.subplots(figsize=(6, 6))
    c = ax.imshow([[len(high_urgent), len(high_not_urgent)], 
                  [len(low_urgent), len(low_not_urgent)]], 
                 cmap="YlOrRd")
    
    # Add text annotations
    for i in range(2):
        for j in range(2):
            ax.text(j, i, matrix_data[["Urgent", "Not Urgent"][j]][i],
                    ha="center", va="center", color="black", fontsize=14)
    
    # Customize appearance
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["High Priority", "Low Priority"])
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["Urgent", "Not Urgent"])
    ax.set_title("Work Priority Matrix", pad=20)
    plt.colorbar(c, ax=ax, label="Number of Requests")
    st.pyplot(fig)

def show_document_complexity(rows):
    """New Feature: Document Type Analysis"""
    if not rows:
        return
    
    st.subheader("Document Complexity Analysis")
    
    # Calculate metrics by document type
    doc_metrics = defaultdict(lambda: {"count": 0, "turnarounds": []})
    for r in rows:
        doc_type = r.get("Contract Type", "Other")
        if r["Turnaround Float"]:
            doc_metrics[doc_type]["count"] += 1
            doc_metrics[doc_type]["turnarounds"].append(r["Turnaround Float"])
    
    # Prepare data for display
    analysis_data = []
    for doc_type, metrics in doc_metrics.items():
        avg_time = sum(metrics["turnarounds"]) / len(metrics["turnarounds"]) if metrics["turnarounds"] else 0
        analysis_data.append({
            "Document Type": doc_type,
            "Count": metrics["count"],
            "Avg Turnaround": avg_time,
            "Complexity": "High" if avg_time > 7 else "Medium" if avg_time > 3 else "Low"
        })
    
    # Sort by complexity
    analysis_data.sort(key=lambda x: x["Avg Turnaround"], reverse=True)
    
    # Display with colored bars
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
# Updated App Layout with All Features
# ----------------------------
[... previous app setup code until the tabs section ...]

# Enhanced Tabs with All Features
tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Performance", "Analysis", "Insights"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        bar_chart_from_counter(Counter([r.get("Contract Type", "") for r in rows]), "Contracts by Type")
    with col2:
        line_chart_counts([r["Date Submitted Parsed"] for r in rows if r["Date Submitted Parsed"]], "Requests Over Time")
    calendar_heatmap(rows)

with tab2:
    col1, col2 = st.columns(2)
    with col1:
        bar_chart_from_counter(Counter([r.get("Priority", "") for r in rows]), "Requests by Priority")
    with col2:
        histogram_turnaround([r["Turnaround Float"] for r in rows if r["Turnaround Float"] is not None], "Turnaround Time")
    show_counsel_performance(rows)

with tab3:
    show_priority_matrix(rows)
    show_document_complexity(rows)
    
    # Additional analysis
    st.subheader("Status Transition Analysis")
    status_changes = defaultdict(Counter)
    for r in rows:
        if "Previous Status" in r:  # Assuming your data tracks status changes
            status_changes[r["Previous Status"]][r["Status"]] += 1
    if status_changes:
        st.write("How requests move between statuses:")
        st.dataframe(status_changes)

with tab4:
    show_completion_rate_trend(rows)
    show_upcoming_deadlines(rows)
    
    # Workload distribution
    st.subheader("Workload Distribution")
    status_counts = Counter([r.get("Status", "") for r in rows])
    if status_counts:
        fig, ax = plt.subplots()
        ax.pie(status_counts.values(), labels=status_counts.keys(),
              autopct='%1.1f%%', startangle=90, 
              colors=plt.cm.Blues(np.linspace(0.3, 0.8, len(status_counts))))
        ax.axis('equal')
        st.pyplot(fig)
