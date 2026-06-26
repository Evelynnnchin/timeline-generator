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

    # Remove empty-looking cells
    df_raw[0] = df_raw[0].replace(r"^\s*$", np.nan, regex=True)
    df_raw[1] = df_raw[1].replace(r"^\s*$", np.nan, regex=True)

    # Remove header row if uploaded file already has headers
    if str(df_raw.iloc[0, 0]).strip().lower() == "project":
        df_raw = df_raw.iloc[1:].reset_index(drop=True)

    # Forward fill project names
    df_raw["Extracted_Project"] = df_raw[0].ffill()

    # Only rows with task name are actual task rows
    task_mask = df_raw[1].notna()
    df = df_raw[task_mask].copy()

    df_clean = pd.DataFrame()
    df_clean["Project"] = df["Extracted_Project"].astype(str)
    df_clean["Task"] = df[1].astype(str)

    # Convert dates
    df_clean["Start"] = pd.to_datetime(df[2], errors="coerce", dayfirst=True)
    df_clean["Finish"] = pd.to_datetime(df[3], errors="coerce", dayfirst=True)

    # Remove rows without valid dates
    df_clean = df_clean.dropna(subset=["Start", "Finish"])

    # Display label on y-axis
    df_clean["Display_Task"] = df_clean["Project"] + " : " + df_clean["Task"]

    return df_clean


# =========================
# MAIN APP
# =========================
uploaded_file = st.file_uploader("📂 Upload Schedule (.xlsx or .csv)", type=["xlsx", "csv"])

if uploaded_file is not None:
    try:
        df_clean = load_and_clean_data(uploaded_file)

        # =========================
        # SIDEBAR SETTINGS
        # =========================
        st.sidebar.header("Settings")

        chart_title = st.sidebar.text_input(
            "Chart Title",
            value="Master Department Schedule: Grand View"
        )

        # =========================
        # PROJECT FILTERS - CHECKBOX VERSION
        # =========================
        st.sidebar.header("Filters")

        all_projects = sorted(df_clean["Project"].dropna().unique().tolist())

        select_all = st.sidebar.checkbox("Select All Projects", value=True)

        st.sidebar.write("Select Projects:")

        selected_projects = []

        for project in all_projects:
            checked = st.sidebar.checkbox(
                project,
                value=select_all,
                key=f"project_checkbox_{project}"
            )

            if checked:
                selected_projects.append(project)

        df_clean = df_clean[df_clean["Project"].isin(selected_projects)]

        if len(df_clean) == 0:
            st.warning("No projects selected.")
            st.stop()

        # =========================
        # BAR LABEL OPTIONS
        # =========================
        label_option = st.sidebar.selectbox(
            "Bar Labels",
            ["None", "Task", "Project", "Task + Project"]
        )

        if label_option == "Task":
            df_clean["Label"] = df_clean["Task"]
        elif label_option == "Project":
            df_clean["Label"] = df_clean["Project"]
        elif label_option == "Task + Project":
            df_clean["Label"] = df_clean["Project"] + "<br>" + df_clean["Task"]
        else:
            df_clean["Label"] = ""

        # =========================
        # CHART LOGIC
        # =========================
        fig = px.timeline(
            df_clean,
            x_start="Start",
            x_end="Finish",
            y="Display_Task",
            color="Task",
            text="Label" if label_option != "None" else None,
            title=f"<b>{chart_title}</b>",
            hover_data={
                "Display_Task": False,
                "Task": True,
                "Project": True,
                "Start": "|%B %d, %Y",
                "Finish": "|%B %d, %Y",
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
            tickfont=dict(color="black", size=13)
        )

        # =========================
        # AXIS DATES
        # =========================
        min_date = df_clean["Start"].min().replace(day=1)
        max_date = df_clean["Finish"].max()

        all_months = pd.date_range(start=min_date, end=max_date, freq="MS")

        month_map = {
            1: "J",
            2: "F",
            3: "M",
            4: "A",
            5: "M",
            6: "J",
            7: "J",
            8: "A",
            9: "S",
            10: "O",
            11: "N",
            12: "D"
        }

        tick_vals = []
        tick_text_bottom = []
        tick_text_top = []

        for dt in all_months:
            tick_vals.append(dt)

            if dt.month == 6:
                tick_text_bottom.append(f"{month_map[dt.month]}<br><b>{dt.year}</b>")
                tick_text_top.append(f"<b>{dt.year}</b><br>{month_map[dt.month]}")
            else:
                tick_text_bottom.append(f"{month_map[dt.month]}<br>&nbsp;")
                tick_text_top.append(f"&nbsp;<br>{month_map[dt.month]}")

        # =========================
        # PROJECT BACKGROUND COLOURS
        # =========================
        background_colours = [
            "rgba(100,149,237,0.20)",
            "rgba(143,188,143,0.25)",
            "rgba(244,164,96,0.25)",
            "rgba(216,191,216,0.30)",
            "rgba(255,160,122,0.25)"
        ]

        for i, proj in enumerate(df_clean["Project"].dropna().unique()):
            proj_tasks = df_clean[df_clean["Project"] == proj]["Display_Task"].unique().tolist()

            if proj_tasks:
                fig.add_hrect(
                    y0=unique_tasks.index(proj_tasks[0]) - 0.5,
                    y1=unique_tasks.index(proj_tasks[-1]) + 0.5,
                    fillcolor=background_colours[i % len(background_colours)],
                    layer="below",
                    line_width=0
                )

        # Invisible scatter to force top x-axis to appear
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
        # LAYOUT
        # =========================
        fig.update_layout(
            xaxis=dict(
                tickmode="array",
                tickvals=tick_vals,
                ticktext=tick_text_bottom,
                tickangle=0,
                showgrid=True,
                gridcolor="rgba(0,0,0,0.1)",
                gridwidth=1
            ),
            xaxis2=dict(
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
            height=max(600, len(unique_tasks) * 25),
            margin=dict(t=160, b=50, l=10, r=50)
        )

        # =========================
        # YEAR DIVIDER LINES
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
        # TODAY LINE
        # =========================
        fig.add_vline(
            x=pd.Timestamp.now().strftime("%Y-%m-%d"),
            line_width=3,
            line_dash="dash",
            line_color="red",
            annotation_text="📍 TODAY",
            annotation_position="top",
            annotation_font_color="red",
            annotation_font_weight="bold",
            annotation_yshift=40,
            layer="above"
        )

        # =========================
        # DISPLAY CHART
        # =========================
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "toImageButtonOptions": {
                    "format": "png",
                    "filename": "Master_Timeline_Visual",
                    "scale": 2
                },
                "displayModeBar": True
            }
        )

    except Exception as e:
        st.error(f"Error processing data: {e}")
