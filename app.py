import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# 1. Page Setup
st.set_page_config(page_title="Master Timeline Generator", layout="wide")
st.title("📊 Master Project Timeline")
st.write("Upload your raw grouped schedule to generate a single, combined timeline.")

# 2. File Uploader
uploaded_file = st.file_uploader("📂 Upload Schedule (.xlsx or .csv)", type=['xlsx', 'csv'])

if uploaded_file is not None:
    try:
        # --- AUTO-CLEANER MAGIC (WITH BUG FIXES) ---
        
        # Read the file explicitly as strings to prevent float64 errors
        if uploaded_file.name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file, header=None, dtype=str)
        else:
            df_raw = pd.read_excel(uploaded_file, header=None, dtype=str)

        df_raw['Project'] = np.nan
        
        # DETECT HEADERS
        header_mask = df_raw[1].isna() & df_raw[3].isna() & df_raw[0].notna()
        df_raw.loc[header_mask, 'Project'] = df_raw[0]
        df_raw['Project'] = df_raw['Project'].ffill()
        
        df = df_raw[~header_mask].copy()
        df = df.iloc[:, [0, 1, 2, 3, 4, 5]]
        df.columns = ['ID', 'Task', 'Duration', 'Start', 'Finish', 'Project']
        
        # CRITICAL BUG FIX: Force object type so Plotly can read the text
        df['Project'] = df['Project'].astype(object)
        df['Task'] = df['Task'].astype(object)
        
        df['Start'] = pd.to_datetime(df['Start'], errors='coerce')
        df['Finish'] = pd.to_datetime(df['Finish'], errors='coerce')
        df = df.dropna(subset=['Start', 'Finish'])

        # Create a unique Y-axis label so tasks from different projects do not overlap
        df['Display_Task'] = df['Project'].astype(str) + " : " + df['Task'].astype(str)

        # --- GENERATE SINGLE GRAND VIEW CHART ---
        
        # facet_row is removed to put everything on ONE big plot
        fig = px.timeline(
            df, x_start="Start", x_end="Finish", y="Display_Task", color="Project",
            title="<b>Master Department Schedule: Grand View</b>",
            hover_data={"Display_Task": False, "Task": True, "Project": True, "Start": "|%B %d, %Y", "Finish": "|%B %d, %Y"} 
        )
        
        # Universal Task Sorting from top to bottom
        fig.update_yaxes(autorange="reversed", title="")

        # 3. Dynamic X-Axis
        min_date = df['Start'].min().replace(day=1)
        max_date = df['Finish'].max()
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
        # Scales smoothly based on the total number of tasks
        num_rows = len(df['Display_Task'].unique())
        chart_height = max(600, num_rows * 25) 

        fig.update_layout(
            xaxis=dict(
                title="", tickmode='array', tickvals=tick_vals,
                ticktext=tick_text, tickangle=0, showgrid=False
            ),
            showlegend=True, 
            legend_title="Projects",
            height=chart_height,
            margin=dict(t=80, b=50, l=10, r=50) 
        )

        # 5. Background Grid Lines
        for dt in all_months:
            if dt.month == 1:
                fig.add_vline(x=dt, line_width=2, line_color="black", layer="below")
            else:
                fig.add_vline(x=dt, line_width=1, line_color="#E5E5E5", layer="below")

        # 6. The "TODAY" Line
        today_str = pd.Timestamp.now().strftime('%Y-%m-%d')
        fig.add_vline(
            x=today_str, line_width=3, line_dash="dash", line_color="red",
            annotation_text=" 📍 TODAY", annotation_position="top right",
            annotation_font_color="red", annotation_font_weight="bold", layer="above"
        )

        # --- DISPLAY ---
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Oops! Something went wrong processing the data. Error details: {e}")
