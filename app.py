import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# 1. Page Setup
st.set_page_config(page_title="Master Timeline Generator", layout="wide")
st.title("📊 Master Project Timeline")
st.write("Upload your formatted schedule to generate a filterable master timeline.")

# --- PERFORMANCE CACHE ---
@st.cache_data
def load_and_clean_data(file):
    if file.name.endswith('.csv'):
        df_raw = pd.read_csv(file, header=None)
    else:
        df_raw = pd.read_excel(file, header=None)

    df_raw[0] = df_raw[0].astype(str).replace(r'^\s*$', np.nan, regex=True).replace('nan', np.nan)
    df_raw[1] = df_raw[1].astype(str).replace(r'^\s*$', np.nan, regex=True).replace('nan', np.nan)

    if str(df_raw.iloc[0, 0]).strip().lower() == 'project':
        df_raw = df_raw.iloc[1:].reset_index(drop=True)

    df_raw['Extracted_Project'] = df_raw[0].ffill()

    task_mask = df_raw[1].notna()
    df = df_raw[task_mask].copy()

    df_clean = pd.DataFrame()
    df_clean['Project'] = df['Extracted_Project'].astype(str)
    df_clean['Task'] = df[1].astype(str)
    
    df_clean['Start'] = pd.to_datetime(df[2], errors='coerce')
    df_clean['Finish'] = pd.to_datetime(df[3], errors='coerce')

    df_clean = df_clean.dropna(subset=['Start', 'Finish'])

    # Combines Project and Task so you always see the project name on the Y-Axis
    df_clean['Display_Task'] = df_clean['Project'] + " : " + df_clean['Task']
    
    return df_clean

# 2. File Uploader
uploaded_file = st.file_uploader("📂 Upload Schedule", type=['xlsx', 'csv'])

if uploaded_file is not None:
    try:
        df_clean = load_and_clean_data(uploaded_file)

        if df_clean.empty:
            st.error("⚠️ No valid dates could be parsed. Please check that your Start and Finish columns contain valid date formats.")
            st.stop()

        # --- PROJECT FILTER WIDGET ---
        all_projects = df_clean['Project'].unique().tolist()
        selected_projects = st.multiselect(
            "🔎 Filter by Project(s):", 
            options=all_projects, 
            default=all_projects # Starts with all projects selected
        )
        
        # Apply the filter to the data
        df_filtered = df_clean[df_clean['Project'].isin(selected_projects)]
        
        if df_filtered.empty:
            st.warning("⚠️ Please select at least one project to view the timeline.")
            st.stop()

        # --- GENERATE THE CHART ---
        fig = px.timeline(
            df_filtered, x_start="Start", x_end="Finish", y="Display_Task", color="Project",
            title="<b>Master Department Schedule</b>",
            hover_data={"Display_Task": False, "Task": True, "Project": True, "Start": "|%B %d, %Y", "Finish": "|%B %d, %Y"}
        )
        
        fig.update_yaxes(autorange="reversed", title="")

        # X-Axis Formatting dynamically adjusts to the filtered data
        min_date = df_filtered['Start'].min().replace(day=1)
        max_date = df_filtered['Finish'].max()
        all_months = pd.date_range(start=min_date, end=max_date, freq='MS')

        month_map = {1:"J", 2:"F", 3:"M", 4:"A", 5:"M", 6:"J", 7:"J", 8:"A", 9:"S", 10:"O", 11:"N", 12:"D"}
        tick_vals, tick_text = [], []
        for dt in all_months:
            tick_vals.append(dt)
            if dt.month == 6:
                tick_text.append(f"{month_map[dt.month]}<br><b>{dt.year}</b>")
            else:
                tick_text.append(f"{month_map[dt.month]}")

        # Dynamic Height adjusts so the bars don't stretch weirdly when filtering
        num_rows = len(df_filtered['Display_Task'].unique())
        chart_height = max(400, num_rows * 25) 

        # --- SPEED OPTIMIZATION: Native Grid Lines ---
        fig.update_layout(
            xaxis=dict(
                title="", tickmode='array', tickvals=tick_vals,
                ticktext=tick_text, tickangle=0, 
                showgrid=True, gridcolor="#E5E5E5", gridwidth=1 
            ),
            showlegend=True, 
            legend_title="Projects",
            height=chart_height,
            margin=dict(t=80, b=50, l=10, r=50) 
        )

        for dt in all_months:
            if dt.month == 1:
                fig.add_vline(x=dt, line_width=2, line_color="black", layer="below")

        today_str = pd.Timestamp.now().strftime('%Y-%m-%d')
        fig.add_vline(
            x=today_str, line_width=3, line_dash="dash", line_color="red",
            annotation_text=" 📍 TODAY", annotation_position="top right",
            annotation_font_color="red", annotation_font_weight="bold", layer="above"
        )

        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error processing the file. Details: {e}")
