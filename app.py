import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# 1. Page Setup
st.set_page_config(page_title="Master Timeline Generator", layout="wide")
st.title("📊 Master Project Timeline")
st.write("Upload your formatted schedule (.xlsx or .csv) to generate a combined, color-coded timeline.")

# --- PERFORMANCE CACHE ---
@st.cache_data
def load_and_clean_data(file):
    if file.name.endswith('.csv'):
        df_raw = pd.read_csv(file, header=None, dtype=str)
    else:
        df_raw = pd.read_excel(file, header=None, dtype=str)

    df_raw[0] = df_raw[0].replace(r'^\s*$', np.nan, regex=True)
    df_raw[1] = df_raw[1].replace(r'^\s*$', np.nan, regex=True)

    if str(df_raw.iloc[0, 0]).strip().lower() == 'project':
        df_raw = df_raw.iloc[1:].reset_index(drop=True)

    df_raw['Extracted_Project'] = df_raw[0]
    df_raw['Extracted_Project'] = df_raw['Extracted_Project'].ffill()

    task_mask = df_raw[1].notna()
    df = df_raw[task_mask].copy()

    df_clean = pd.DataFrame()
    df_clean['Project'] = df['Extracted_Project'].astype(object)
    df_clean['Task'] = df[1].astype(object)
    df_clean['Start'] = pd.to_datetime(df[2], errors='coerce')
    df_clean['Finish'] = pd.to_datetime(df[3], errors='coerce')

    df_clean = df_clean.dropna(subset=['Start', 'Finish'])
    df_clean['Display_Task'] = df_clean['Project'].astype(str) + " : " + df_clean['Task'].astype(str)
    
    return df_clean

# 2. File Uploader
uploaded_file = st.file_uploader("📂 Upload Schedule", type=['xlsx', 'csv'])

if uploaded_file is not None:
    try:
        df_clean = load_and_clean_data(uploaded_file)

        # --- GENERATE THE CHART ---
        fig = px.timeline(
            df_clean, x_start="Start", x_end="Finish", y="Display_Task", color="Task", 
            title="<b>Master Department Schedule: Grand View</b>",
            hover_data={"Display_Task": False, "Task": True, "Project": True, "Start": "|%B %d, %Y", "Finish": "|%B %d, %Y"} 
        )
        
        unique_tasks = df_clean['Display_Task'].unique().tolist()
        
        # [NEW] Added tickfont to make Y-Axis labels solid black and slightly larger
        fig.update_yaxes(
            autorange="reversed", 
            title="",
            categoryorder="array",
            categoryarray=unique_tasks,
            tickfont=dict(color="black", size=13) 
        )

        # 3. Dynamic X-Axis 
        min_date = df_clean['Start'].min().replace(day=1)
        max_date = df_clean['Finish'].max()
        all_months = pd.date_range(start=min_date, end=max_date, freq='MS')

        month_map = {1:"J", 2:"F", 3:"M", 4:"A", 5:"M", 6:"J", 7:"J", 8:"A", 9:"S", 10:"O", 11:"N", 12:"D"}
        tick_vals, tick_text = [], []
        for dt in all_months:
            tick_vals.append(dt)
            if dt.month == 6:
                tick_text.append(f"{month_map[dt.month]}<br><b>{dt.year}</b>")
            else:
                tick_text.append(f"{month_map[dt.month]}")

        # 4. Dynamic Height
        num_tasks = len(unique_tasks)
        chart_height = max(600, num_tasks * 25) 

        # --- DRAW PROJECT BACKGROUND BANDS [UPDATED] ---
        unique_projects = df_clean['Project'].unique().tolist()
        
        # [NEW] Richer, distinct colors with higher opacity (0.2 to 0.3)
        bg_colors = [
            "rgba(100, 149, 237, 0.2)",   # Cornflower Blue
            "rgba(143, 188, 143, 0.25)",  # Dark Sea Green
            "rgba(244, 164, 96, 0.25)",   # Sandy Brown
            "rgba(216, 191, 216, 0.3)",   # Thistle Purple
            "rgba(255, 160, 122, 0.25)"   # Light Salmon
        ]
        
        for i, proj in enumerate(unique_projects):
            proj_tasks = df_clean[df_clean['Project'] == proj]['Display_Task'].unique().tolist()
            if not proj_tasks:
                continue
                
            first_idx = unique_tasks.index(proj_tasks[0])
            last_idx = unique_tasks.index(proj_tasks[-1])
            
            fig.add_hrect(
                y0=first_idx - 0.5, 
                y1=last_idx + 0.5, 
                fillcolor=bg_colors[i % len(bg_colors)], 
                layer="below", 
                line_width=0
            )

        # 5. Speed Optimized Layout & Grid Lines
        fig.update_layout(
            xaxis=dict(
                title="", tickmode='array', tickvals=tick_vals,
                ticktext=tick_text, tickangle=0, 
                showgrid=True, gridcolor="rgba(0,0,0,0.1)", gridwidth=1 
            ),
            showlegend=True, 
            legend_title="Project Phases",
            height=chart_height,
            margin=dict(t=50, b=50, l=10, r=50) 
        )

        for dt in all_months:
            if dt.month == 1:
                fig.add_vline(x=dt, line_width=2, line_color="black", layer="below")

        # 6. The "TODAY" Line
        today_str = pd.Timestamp.now().strftime('%Y-%m-%d')
        fig.add_vline(
            x=today_str, line_width=3, line_dash="dash", line_color="red",
            annotation_text=" 📍 TODAY", annotation_position="top",
            annotation_font_color="red", annotation_font_weight="bold", layer="above"
        )

        # --- DISPLAY ---
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Oops! Something went wrong processing the data. Error details: {e}")
