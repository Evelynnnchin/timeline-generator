import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# 1. Page Setup
st.set_page_config(page_title="Master Timeline Generator", layout="wide")
st.title("📊 Master Project Timeline")
st.write("Upload your formatted schedule (.xlsx or .csv) to generate a single, combined timeline.")

# --- PERFORMANCE CACHE ---
@st.cache_data
def load_and_clean_data(file):
    # Read without forcing string type so Pandas can naturally read Excel dates
    if file.name.endswith('.csv'):
        df_raw = pd.read_csv(file, header=None)
    else:
        df_raw = pd.read_excel(file, header=None)

    # Clean up empty spaces in the first two columns safely
    df_raw[0] = df_raw[0].astype(str).replace(r'^\s*$', np.nan, regex=True).replace('nan', np.nan)
    df_raw[1] = df_raw[1].astype(str).replace(r'^\s*$', np.nan, regex=True).replace('nan', np.nan)

    # Drop the actual text header row if it is in the file
    if str(df_raw.iloc[0, 0]).strip().lower() == 'project':
        df_raw = df_raw.iloc[1:].reset_index(drop=True)

    # Extract and forward-fill the Project names
    df_raw['Extracted_Project'] = df_raw[0].ffill()

    # Filter out rows that are ONLY project headers (where Task is blank)
    task_mask = df_raw[1].notna()
    df = df_raw[task_mask].copy()

    # Map to our final clean format
    df_clean = pd.DataFrame()
    df_clean['Project'] = df['Extracted_Project'].astype(str)
    df_clean['Task'] = df[1].astype(str)
    
    # Let Pandas natively parse the dates
    df_clean['Start'] = pd.to_datetime(df[2], errors='coerce')
    df_clean['Finish'] = pd.to_datetime(df[3], errors='coerce')

    # Drop any rows where dates could not be parsed
    df_clean = df_clean.dropna(subset=['Start', 'Finish'])

    # Create a unique Y-axis label so tasks from different projects do not overlap
    df_clean['Display_Task'] = df_clean['Project'] + " : " + df_clean['Task']
    
    return df_clean

# 2. File Uploader
uploaded_file = st.file_uploader("📂 Upload Schedule", type=['xlsx', 'csv'])

if uploaded_file is not None:
    try:
        # Load data using our fast cached function
        df_clean = load_and_clean_data(uploaded_file)

        # Safety Check: If the dataframe is empty after parsing, alert the user!
        if df_clean.empty:
            st.error("⚠️ No valid dates could be parsed. Please check that your Start and Finish columns contain valid date formats.")
            st.stop()

        # --- GENERATE THE CHART ---
        fig = px.timeline(
            df_clean, x_start="Start", x_end="Finish", y="Display_Task", color="Project",
            title="<b>Master Department Schedule: Grand View</b>",
            hover_data={"Display_Task": False, "Task": True, "Project": True, "Start": "|%B %d, %Y", "Finish": "|%B %d, %Y"}
        )
        
        # Ensures everything lists from top to bottom
        fig.update_yaxes(autorange="reversed", title="")

        # X-Axis Formatting
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

        # Automatically stretch chart height based on the number of tasks
        num_rows = len(df_clean['Display_Task'].unique())
        chart_height = max(600, num_rows * 25) 

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

        # Only manually draw the thick black year lines
        for dt in all_months:
            if dt.month == 1:
                fig.add_vline(x=dt, line_width=2, line_color="black", layer="below")

        today_str = pd.Timestamp.now().strftime('%Y-%m-%d')
        fig.add_vline(
            x=today_str, line_width=3, line_dash="dash", line_color="red",
            annotation_text=" 📍 TODAY", annotation_position="top right",
            annotation_font_color="red", annotation_font_weight="bold", layer="above"
        )

        # Plot the chart
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error processing the file. Details: {e}")
