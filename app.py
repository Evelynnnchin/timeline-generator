import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Page Setup
st.set_page_config(page_title="Department Timeline Generator", layout="wide")
st.title("📊 Project Timeline Generator")
st.write("Enter your project details and upload the schedule to generate an interactive timeline.")

# 2. User Inputs
project_title = st.text_input("📝 Enter Project Title:", value="Official Project Schedule")
uploaded_file = st.file_uploader("📂 Upload Excel File (.xlsx)", type=['xlsx'])

if uploaded_file is not None:
    try:
        # 3. Read the uploaded Excel file
        df = pd.read_excel(uploaded_file)
        
        # Ensure dates are in the correct format
        df['Start'] = pd.to_datetime(df['Start'])
        df['Finish'] = pd.to_datetime(df['Finish'])

        # 4. Generate the Chart
        ordered_tasks = [
            "Defect Liability Period", "Test Running", "ITC", "STC", 
            "Installation", "OSIT", "Software Development", 
            "PMF,Delivery", "Design", "General"
        ]

        # Added custom hover data so the interactive tooltips look super clean!
        fig = px.timeline(
            df, x_start="Start", x_end="Finish", y="Task", color="Task",
            title=f"<b>{project_title}</b>",
            hover_data={"Task": True, "Start": "|%B %d, %Y", "Finish": "|%B %d, %Y"} 
        )

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

        fig.update_yaxes(categoryorder="array", categoryarray=ordered_tasks)
        fig.update_layout(
            xaxis=dict(
                title="", tickmode='array', tickvals=tick_vals,
                ticktext=tick_text, tickangle=0, showgrid=False
            ),
            yaxis_title="Project Phases", showlegend=False, font=dict(size=12),
            height=600 
        )

        for dt in all_months:
            if dt.month == 1:
                fig.add_vline(x=dt, line_width=2, line_color="black", layer="below")
            else:
                fig.add_vline(x=dt, line_width=1, line_color="#E5E5E5", layer="below")

        # 5. Add "Time Now" Line (Using your exact styling!)
        # We grab the current time and format it as a standard date string so Plotly doesn't crash
        today_str = pd.Timestamp.now().strftime('%Y-%m-%d')
        
        fig.add_vline(
            x=today_str,
            line_width=3,
            line_dash="dash",
            line_color="red",
            annotation_text="Time Now",
            annotation_position="top",
            annotation_font_color="red",
            annotation_font_weight="bold"
        )

        # 6. Display the interactive chart!
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Oops! Something went wrong reading the file. Please ensure it has 'Task', 'Start', and 'Finish' columns. Error details: {e}")
