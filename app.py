import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# =========================
# PAGE SETUP
# =========================
st.set_page_config(page_title="Master Timeline Generator", layout="wide")
st.title("📊 Master Project Timeline")

# =========================
# FILE FORMAT GUIDE
# =========================
st.write("### 📂 Required File Format")
st.write(
    "Please ensure your uploaded Excel or CSV file follows this exact structure for the timeline to generate correctly:"
)

format_data = {
    "Column A": ["Project Name (or empty)", "Project Name (or empty)"],
    "Column B": ["Task Name", "Task Name"],
    "Column C": ["Start Date (DD-MM-YY)", "Start Date (DD-MM-YY)"],
    "Column D": ["Finish Date (DD-MM-YY)", "Finish Date (DD-MM-YY)"],
}

st.table(pd.DataFrame(format_data))

st.write("---")

# =========================
# DATA LOADER
# =========================
@st.cache_data
def load_and_clean_data(file):

    if file.name.endswith(".csv"):
        df_raw = pd.read_csv(file, header=None, dtype=str)
    else:
        df_raw = pd.read_excel(file, header=None, dtype=str)

    df_raw[0] = df_raw[0].replace(r"^\s*$", np.nan, regex=True)
    df_raw[1] = df_raw[1].replace(r"^\s*$", np.nan, regex=True)

    # Remove header row if present
    if str(df_raw.iloc[0, 0]).strip().lower() == "project":
        df_raw = df_raw.iloc[1:].reset_index(drop=True)

    # Forward-fill project names
    df_raw["Extracted_Project"] = df_raw[0]
    df_raw["Extracted_Project"] = df_raw["Extracted_Project"].ffill()

    # Keep rows with task names
    task_mask = df_raw[1].notna()
    df = df_raw[task_mask].copy()

    df_clean = pd.DataFrame()

    df_clean["Project"] = df["Extracted_Project"].astype(str)
    df_clean["Task"] = df[1].astype(str)

    df_clean["Start"] = pd.to_datetime(df[2], errors="coerce")
    df_clean["Finish"] = pd.to_datetime(df[3], errors="coerce")

    df_clean = df_clean.dropna(subset=["Start", "Finish"])

    df_clean["Display_Task"] = (
        df_clean["Project"] + " : " + df_clean["Task"]
    )

    return df_clean


# =========================
# FILE UPLOAD
# =========================
uploaded_file = st.file_uploader(
    "📂 Upload Schedule (.xlsx or .csv)",
    type=["xlsx", "csv"]
)

# =========================
# MAIN APP
# =========================
if uploaded_file is not None:

    try:

        df_clean = load_and_clean_data(uploaded_file)

        # =========================
        # SIDEBAR FILTERS
        # =========================
        st.sidebar.header("Filters")

        all_projects = sorted(
            df_clean["Project"].dropna().unique().tolist()
        )

        selected_projects = st.sidebar.multiselect(
            "Select Projects",
            options=all_projects,
            default=all_projects
        )

        df_clean = df_clean[
            df_clean["Project"].isin(selected_projects)
        ]

        if len(df_clean) == 0:
            st.warning("No projects selected.")
            st.stop()

        # =========================
        # LABEL OPTIONS
        # =========================
        label_option = st.sidebar.selectbox(
            "Bar Labels",
            [
                "None",
                "Task",
                "Project",
                "Task + Project"
            ]
        )

        if label_option == "Task":
            df_clean["Label"] = df_clean["Task"]

        elif label_option == "Project":
            df_clean["Label"] = df_clean["Project"]

        elif label_option == "Task + Project":
            df_clean["Label"] = (
                df_clean["Project"]
                + "<br>"
                + df_clean["Task"]
            )

        else:
            df_clean["Label"] = ""

        # =========================
        # GANTT CHART
        # =========================
        fig = px.timeline(
            df_clean,
            x_start="Start",
            x_end="Finish",
            y="Display_Task",
            color="Task",
            text="Label" if label_option != "None" else None,
            title="<b>Master Department Schedule: Grand View</b>",
            hover_data={
                "Display_Task": False,
                "Task": True,
                "Project": True,
                "Start": "|%B %d, %Y",
                "Finish": "|%B %d, %Y"
            }
        )

        if label_option != "None":
            fig.update_traces(
                textposition="inside",
                insidetextanchor="middle"
            )

        unique_tasks = df_clean["Display_Task"].unique().tolist()

        fig.update_yaxes(
            autorange="reversed",
            title="",
            categoryorder="array",
            categoryarray=unique_tasks,
            tickfont=dict(
                color="black",
                size=13
            )
        )

        # =========================
        # X AXIS MONTHS
        # =========================
        min_date = df_clean["Start"].min().replace(day=1)
        max_date = df_clean["Finish"].max()

        all_months = pd.date_range(
            start=min_date,
            end=max_date,
            freq="MS"
        )

        month_map = {
            1: "J", 2: "F", 3: "M", 4: "A", 5: "M", 6: "J", 
            7: "J", 8: "A", 9: "S", 10: "O", 11: "N", 12: "D"
        }

        tick_vals = []
        tick_text_bottom = []
        tick_text_top = []

        for dt in all_months:
            tick_vals.append(dt)

            if dt.month == 6:
                # BOTTOM: Month on top of Year
                tick_text_bottom.append(f"{month_map[dt.month]}<br><b>{dt.year}</b>")
                # TOP: Year on top of Month
                tick_text_top.append(f"<b>{dt.year}</b><br>{month_map[dt.month]}")
            else:
                tick_text_bottom.append(f"{month_map[dt.month]}<br>&nbsp;")
                tick_text_top.append(f"&nbsp;<br>{month_map[dt.month]}")

        # =========================
        # CHART HEIGHT
        # =========================
        num_tasks = len(unique_tasks)
        chart_height = max(600, num_tasks * 25)

        # =========================
        # PROJECT BACKGROUNDS
        # =========================
        unique_projects = df_clean["Project"].dropna().unique().tolist()

        bg_colors = [
            "rgba(100,149,237,0.20)",
            "rgba(143,188,143,0.25)",
            "rgba(244,164,96,0.25)",
            "rgba(216,191,216,0.30)",
            "rgba(255,160,122,0.25)"
        ]

        for i, proj in enumerate(unique_projects):
            proj_tasks = df_clean[df_clean["Project"] == proj]["Display_Task"].unique().tolist()
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

        # =========================
        # FORCE TOP AXIS VISIBILITY
        # =========================
        fig.add_scatter(
            x=[min_date], 
            y=[unique_tasks[0]], 
            xaxis="x2", 
            mode="markers", 
            marker=dict(color="rgba(0,0,0,0)"), 
            showlegend=False, 
            hoverinfo="skip"
        )

        # =========================
        # LAYOUT (TOP & BOTTOM AXIS)
        # =========================
        fig.update_layout(
            xaxis=dict(
                title="",
                tickmode="array",
                tickvals=tick_vals,
                ticktext=tick_text_bottom,
                tickangle=0,
                showgrid=True,
                gridcolor="rgba(0,0,0,0.1)",
                gridwidth=1
            ),
            xaxis2=dict(
                title="",
                tickmode="array",
                tickvals=tick_vals,
                ticktext=tick_text_top,
                tickangle=0,
                showgrid=False, 
                overlaying="x",
                side="top",
                matches="x"
            ),
            showlegend=True,
            legend_title="Project Phases",
            height=chart_height,
            margin=dict(
                t=160, # Increased top margin so the TODAY text clears the title
                b=50,
                l=10,
                r=50
            )
        )

        # =========================
        # YEAR LINES
        # =========================
        for dt in all_months:
            if dt.month == 1:
                fig.add_vline(
                    x=dt,
                    line_width=2,
                    line_color="black",
                    layer="below"
                )

        # =========================
        # TODAY LINE & TEXT FIX
        # =========================
        today_str = pd.Timestamp.now().strftime("%Y-%m-%d")

        fig.add_vline(
            x=today_str,
            line_width=3,
            line_dash="dash",
            line_color="red",
            annotation_text="📍 TODAY",
            annotation_position="top",
            annotation_font_color="red",
            annotation_font_weight="bold",
            annotation_yshift=40, # Pushed even higher to sit clearly above the Year text
            layer="above"
        )

        # =========================
        # DISPLAY (HIGH-RES EXPORT)
        # =========================
        export_config = {
            'toImageButtonOptions': {
                'format': 'png', 
                'filename': 'Master_Timeline_Visual',
                'height': chart_height,
                'width': 1600,
                'scale': 2
            },
            'displayModeBar': True 
        }

        st.plotly_chart(
            fig,
            use_container_width=True,
            config=export_config
        )

    except Exception as e:
        st.error(
            f"Oops! Something went wrong processing the data. Error details: {e}"
        )
