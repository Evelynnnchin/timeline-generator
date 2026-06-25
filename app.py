import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# 1. Page Setup
st.set_page_config(page_title="Master Timeline Generator", layout="wide")
st.title("📊 Master Project Timeline")
st.write("Upload your raw grouped schedule to generate a stacked timeline.")

# 2. File Uploader (Now accepts both Excel and CSV!)
uploaded_file = st.file_uploader("📂 Upload Schedule (.xlsx or .csv)", type=['xlsx', 'csv'])

if uploaded_file is not None:
    try:
        # --- THE AUTO-CLEANER MAGIC ---
        
        # Read the file blindly without looking for standard column headers
        if uploaded_file.name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file, header=None)
        else:
            df_raw = pd.read_excel(uploaded_file, header=None)

        # Create a blank column at the end to hold our Project Names
        df_raw['Project'] = np.nan
        
        # DETECT HEADERS: We assume a row is a "Project Header" if the Task (Col 1) 
        # and Start Date (Col 3) are empty, but the first column has text.
        header_mask = df_raw[1].isna() & df_raw[3].isna() & df_raw[0].notna()
        
        # Move the project names into our new column
        df_raw.loc[header_mask, 'Project'] = df_raw[0]
        
        # Forward-fill the project name down to all the task rows below it!
        df_raw['Project'] = df_raw['Project'].ffill()
        
        # Delete the standalone header rows now that the tasks are tagged
        df = df_raw[~header_mask].copy()
        
        # Keep only the first 6 columns (to ignore stray data) and name them
        df = df.iloc[:, [0, 1, 2, 3, 4, 5]]
        df.columns = ['ID', 'Task', 'Duration', 'Start', 'Finish', 'Project']
        
        # Convert to dates. If a row has text (like table headers) or blanks, it turns to NaT (Not a Time)
        df['Start'] = pd.to_datetime(df['Start'], errors='coerce')
        df['Finish'] = pd.to_datetime(df['Finish'], errors='coerce')
        
        # Drop any invalid rows to leave us with perfectly clean task data
        df = df.dropna(subset=['Start', 'Finish'])


        # --- GENERATE THE CHART ---
        
        # Notice facet_row="Project". This is the magic that creates the visual headers!
        fig = px.timeline(
            df, x_start="Start", x_end="Finish", y="Task", color="Project",
            facet_row="Project", 
            hover_data={"Task": True, "Start": "|%B %d, %Y", "Finish": "|%B %d, %Y"} 
        )

        # 1. Clean up the facet headers (Removes the ugly default "Project=" text)
        fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1], font=dict(size=16, weight="bold")))
        
        # 2. Universal Task Sorting: This ensures every project automatically lists its tasks
        # from top to bottom exactly as they appear in the Excel sheet!
        fig.update_yaxes(matches=None, autorange="reversed", title="", showticklabels=True)

        # 3. Dynamic X-Axis (Month Letters & Centered Years)
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

        # 4. Dynamic Height: Automatically stretches the chart so things don't get 
        # squished if someone uploads a master file with 20 projects.
        num_projects = len(df['Project'].unique())
        chart_height = max(600, num_projects * 300) 

        fig.update_layout(
            xaxis=dict(
                title="", tickmode='array', tickvals=tick_vals,
                ticktext=tick_text, tickangle=0, showgrid=False
            ),
            showlegend=False, 
            height=chart_height,
            margin=dict(t=50, b=50, l=10, r=50) 
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
