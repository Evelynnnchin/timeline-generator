import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from datetime import datetime
from zoneinfo import ZoneInfo


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
    "Please ensure your uploaded Excel or CSV file follows this structure:"
)

format_data = {
    "Column A": ["Project Name / Project Header / Empty", "Project Name / Project Header / Empty"],
    "Column B": ["Task Name", "Task Name"],
    "Column C": ["Start Date", "Start Date"],
    "Column D": ["Finish Date", "Finish Date"],
}

st.table(pd.DataFrame(format_data))
st.write("---")


# =========================
# DATE PARSER
# =========================
def parse_date_value(value):
    if pd.isna(value):
        return pd.NaT

    value = str(value).strip()

    if value == "" or value.lower() in ["nan", "nat", "none"]:
        return pd.NaT

    value = value.replace("\xa0", " ").strip()

    # Excel serial date
    try:
        numeric_value = float(value)
        if 20000 <= numeric_value <= 80000:
            return pd.to_datetime(numeric_value, unit="D", origin="1899-12-30")
    except Exception:
        pass

    return pd.to_datetime(value, errors="coerce", dayfirst=True)


# =========================
# DATA LOADER
# =========================
@st.cache_data
def load_and_clean_data(file):
    if file.name.lower().endswith(".csv"):
        df_raw = pd.read_csv(file, header=None, dtype=str)
    else:
        df_raw = pd.read_excel(file, header=None, dtype=str)

    # Make sure at least 4 columns exist
    while df_raw.shape[1] < 4:
        df_raw[df_raw.shape[1]] = np.nan

    # Only use first 4 columns
    df_raw = df_raw.iloc[:, :4].copy()
    df_raw.columns = ["Project_Raw", "Task_Raw", "Start_Raw", "Finish_Raw"]

    # Clean blank-looking cells
    for col in df_raw.columns:
        df_raw[col] = df_raw[col].replace(r"^\s*$", np.nan, regex=True)

    # Remove header row only if clearly header
    first_row = df_raw.iloc[0].astype(str).str.strip().str.lower().tolist()

    header_keywords = [
        "project",
        "project name",
        "task",
        "task name",
        "start",
        "start date",
        "finish",
        "finish date",
        "end",
        "end date",
    ]

    if any(cell in header_keywords for cell in first_row):
        df_raw = df_raw.iloc[1:].reset_index(drop=True)

    # Keep row number
    df_raw["Original_Row_No"] = df_raw.index + 1

    # Forward-fill project names from Column A
    df_raw["Project"] = df_raw["Project_Raw"].ffill()

    # Every non-empty Column B row becomes a task
    task_mask = df_raw["Task_Raw"].notna()
    df = df_raw[task_mask].copy()

    df["Project"] = df["Project"].fillna("No Project").astype(str).str.strip()
    df["Task"] = df["Task_Raw"].astype(str).str.strip()

    # Parse dates
    df["Start"] = df["Start_Raw"].apply(parse_date_value)
    df["Finish"] = df["Finish_Raw"].apply(parse_date_value)

    df["Has_Valid_Dates"] = df["Start"].notna() & df["Finish"].notna()

    # Swap if Finish is earlier than Start
    reversed_mask = df["Has_Valid_Dates"] & (df["Finish"] < df["Start"])

    temp_start = df.loc[reversed_mask, "Start"].copy()
    df.loc[reversed_mask, "Start"] = df.loc[reversed_mask, "Finish"]
    df.loc[reversed_mask, "Finish"] = temp_start

    # Placeholder dates for missing/invalid dates
    valid_rows = df[df["Has_Valid_Dates"]]

    if len(valid_rows) > 0:
        fallback_start = valid_rows["Start"].min()
    else:
        fallback_start = pd.Timestamp.today().normalize()

    fallback_finish = fallback_start + pd.Timedelta(days=7)

    df["Plot_Start"] = df["Start"]
    df["Plot_Finish"] = df["Finish"]

    df.loc[~df["Has_Valid_Dates"], "Plot_Start"] = fallback_start
    df.loc[~df["Has_Valid_Dates"], "Plot_Finish"] = fallback_finish

    # Make finish date inclusive
    valid_plot_mask = df["Has_Valid_Dates"]
    df.loc[valid_plot_mask, "Plot_Finish"] = (
        df.loc[valid_plot_mask, "Plot_Finish"] + pd.Timedelta(days=1)
    )

    # Prevent zero-width bars
    same_day_mask = df["Plot_Start"] >= df["Plot_Finish"]
    df.loc[same_day_mask, "Plot_Finish"] = (
        df.loc[same_day_mask, "Plot_Start"] + pd.Timedelta(days=1)
    )

    # Display labels
    df["Display_Task"] = df["Project"] + " : " + df["Task"]

    # Unique key for checking, not used as categorical y-axis anymore
    df["Row_Key"] = (
        df["Original_Row_No"].astype(str)
        + " | "
        + df["Project"]
        + " : "
        + df["Task"]
    )

    df["Date_Status"] = np.where(
        df["Has_Valid_Dates"],
        "Valid dates",
        "Missing / invalid dates",
    )

    df["Color_Group"] = np.where(
        df["Has_Valid_Dates"],
        df["Task"],
        "Missing / invalid dates",
    )

    df["Duration_Days"] = np.where(
        df["Has_Valid_Dates"],
        (df["Finish"] - df["Start"]).dt.days + 1,
        np.nan,
    )

    return df.reset_index(drop=True)


# =========================
# COLOUR HELPER
# =========================
def make_color_map(values):
    palette = (
        px.colors.qualitative.Plotly
        + px.colors.qualitative.Set3
        + px.colors.qualitative.Dark24
    )

    color_map = {}

    for i, value in enumerate(values):
        color_map[value] = palette[i % len(palette)]

    color_map["Missing / invalid dates"] = "#9E9E9E"

    return color_map


# =========================
# MAIN APP
# =========================
uploaded_file = st.file_uploader(
    "📂 Upload Schedule (.xlsx or .csv)",
    type=["xlsx", "csv"]
)

if uploaded_file is not None:
    try:
        df_clean = load_and_clean_data(uploaded_file)

        if len(df_clean) == 0:
            st.error("No tasks found. Please make sure Column B contains task names.")
            st.stop()

        # =========================
        # SIDEBAR SETTINGS
        # =========================
        st.sidebar.header("Settings")

        chart_title = st.sidebar.text_input(
            "Chart Title",
            value="Master Department Schedule: Grand View",
        )

        show_undated_tasks = st.sidebar.checkbox(
            "Show tasks with missing / invalid dates",
            value=True,
        )

        # =========================
        # CHART SPACING SETTINGS
        # =========================
        st.sidebar.header("Chart Spacing")

        chart_row_height = st.sidebar.slider(
            "Row Height",
            min_value=24,
            max_value=60,
            value=34,
            step=2,
        )

        bar_thickness = st.sidebar.slider(
            "Bar Thickness",
            min_value=0.40,
            max_value=1.00,
            value=0.90,
            step=0.05,
        )

        gap_above_first_bar = st.sidebar.slider(
            "Gap Above First Bar",
            min_value=0.00,
            max_value=0.30,
            value=0.02,
            step=0.01,
        )

        top_margin = st.sidebar.slider(
            "Top Margin",
            min_value=35,
            max_value=100,
            value=55,
            step=5,
        )

        # =========================
        # FILTERS
        # =========================
        st.sidebar.header("Filters")

        all_projects = sorted(df_clean["Project"].dropna().unique().tolist())

        select_all = st.sidebar.checkbox("Select All Projects", value=True)

        selected_projects = []

        st.sidebar.write("Select Projects:")

        for project in all_projects:
            checked = st.sidebar.checkbox(
                project,
                value=select_all,
                key=f"project_checkbox_{project}",
            )

            if checked:
                selected_projects.append(project)

        df_view = df_clean[df_clean["Project"].isin(selected_projects)].copy()

        if not show_undated_tasks:
            df_view = df_view[df_view["Has_Valid_Dates"]].copy()

        if len(df_view) == 0:
            st.warning("No tasks to display based on current filters.")
            st.stop()

        # Preserve uploaded row order
        df_view = df_view.reset_index(drop=True)
        df_view["Y_Pos"] = df_view.index

        # =========================
        # TASK COUNT CHECK
        # =========================
        st.write("### ✅ Column B Task Check")
        st.write(
            f"Total Column B tasks found: **{len(df_clean)}** | "
            f"Shown in current chart: **{len(df_view)}**"
        )

        missing_date_rows = df_clean[~df_clean["Has_Valid_Dates"]].copy()

        if len(missing_date_rows) > 0:
            st.warning(
                f"{len(missing_date_rows)} task(s) have missing or invalid dates. "
                "They are still shown as placeholder bars."
            )

        with st.expander("Show every detected Column B task"):
            st.dataframe(
                df_clean[
                    [
                        "Original_Row_No",
                        "Project",
                        "Task",
                        "Start_Raw",
                        "Finish_Raw",
                        "Start",
                        "Finish",
                        "Date_Status",
                        "Duration_Days",
                    ]
                ],
                use_container_width=True,
            )

        # =========================
        # BAR LABEL OPTIONS
        # =========================
        label_option = st.sidebar.selectbox(
            "Bar Labels",
            ["None", "Task", "Project", "Task + Project", "Date Status"],
        )

        if label_option == "Task":
            df_view["Label"] = df_view["Task"]
        elif label_option == "Project":
            df_view["Label"] = df_view["Project"]
        elif label_option == "Task + Project":
            df_view["Label"] = df_view["Project"] + "<br>" + df_view["Task"]
        elif label_option == "Date Status":
            df_view["Label"] = df_view["Date_Status"]
        else:
            df_view["Label"] = ""

        # =========================
        # AXIS DATES
        # =========================
        min_date = df_view["Plot_Start"].min().replace(day=1)
        max_date = df_view["Plot_Finish"].max()

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
            12: "D",
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
        # CUSTOM NUMERIC-Y GANTT CHART
        # This removes the big top gap.
        # =========================
        fig = go.Figure()

        color_groups = df_view["Color_Group"].dropna().unique().tolist()
        color_map = make_color_map(color_groups)

        # Project background colours
        background_colours = [
            "rgba(100,149,237,0.20)",
            "rgba(143,188,143,0.25)",
            "rgba(244,164,96,0.25)",
            "rgba(216,191,216,0.30)",
            "rgba(255,160,122,0.25)",
            "rgba(176,196,222,0.25)",
            "rgba(152,251,152,0.20)",
        ]

        visible_projects = df_view["Project"].dropna().unique().tolist()

        for i, proj in enumerate(visible_projects):
            project_indexes = df_view.index[df_view["Project"] == proj].tolist()

            if project_indexes:
                fig.add_hrect(
                    y0=project_indexes[0] - 0.5,
                    y1=project_indexes[-1] + 0.5,
                    fillcolor=background_colours[i % len(background_colours)],
                    layer="below",
                    line_width=0,
                )

        # Add bars grouped by colour group so legend works
        for group in color_groups:
            group_df = df_view[df_view["Color_Group"] == group].copy()

            duration_ms = (
                group_df["Plot_Finish"] - group_df["Plot_Start"]
            ).dt.total_seconds() * 1000

            custom_data = np.stack(
                [
                    group_df["Display_Task"].astype(str),
                    group_df["Project"].astype(str),
                    group_df["Task"].astype(str),
                    group_df["Start"].dt.strftime("%d %b %Y").fillna("Invalid date"),
                    group_df["Finish"].dt.strftime("%d %b %Y").fillna("Invalid date"),
                    group_df["Date_Status"].astype(str),
                    group_df["Duration_Days"].fillna("").astype(str),
                ],
                axis=-1,
            )

            fig.add_trace(
                go.Bar(
                    x=duration_ms,
                    y=group_df["Y_Pos"],
                    base=group_df["Plot_Start"],
                    orientation="h",
                    width=float(bar_thickness),
                    name=str(group),
                    marker=dict(
                        color=color_map.get(group, "#1f77b4"),
                        line=dict(width=0),
                    ),
                    text=group_df["Label"] if label_option != "None" else None,
                    textposition="inside",
                    insidetextanchor="middle",
                    customdata=custom_data,
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        "Project: %{customdata[1]}<br>"
                        "Task: %{customdata[2]}<br>"
                        "Start: %{customdata[3]}<br>"
                        "Finish: %{customdata[4]}<br>"
                        "Status: %{customdata[5]}<br>"
                        "Duration: %{customdata[6]} days"
                        "<extra></extra>"
                    ),
                )
            )

        # Invisible scatter to force top x-axis
        fig.add_scatter(
            x=[min_date],
            y=[0],
            xaxis="x2",
            mode="markers",
            marker=dict(color="rgba(0,0,0,0)"),
            showlegend=False,
            hoverinfo="skip",
        )

        # =========================
        # Y-AXIS REAL GAP FIX
        # =========================
        n_rows = len(df_view)

        top_range = -(float(bar_thickness) / 2 + float(gap_above_first_bar))
        bottom_range = (n_rows - 1) + (float(bar_thickness) / 2) + 0.25

        y_axis_range = [bottom_range, top_range]

        # =========================
        # COMPACT HEIGHT
        # =========================
        chart_height = max(180, n_rows * int(chart_row_height) + 90)

        fig.update_yaxes(
            range=y_axis_range,
            autorange=False,
            tickmode="array",
            tickvals=df_view["Y_Pos"].tolist(),
            ticktext=df_view["Display_Task"].tolist(),
            title="",
            tickfont=dict(color="black", size=13),
            fixedrange=False,
        )

        fig.update_layout(
            title=f"<b>{chart_title}</b>",
            xaxis=dict(
                tickmode="array",
                tickvals=tick_vals,
                ticktext=tick_text_bottom,
                tickangle=0,
                showgrid=True,
                gridcolor="rgba(0,0,0,0.1)",
                gridwidth=1,
                type="date",
            ),
            xaxis2=dict(
                tickmode="array",
                tickvals=tick_vals,
                ticktext=tick_text_top,
                tickangle=0,
                showgrid=False,
                overlaying="x",
                side="top",
                matches="x",
                type="date",
            ),
            barmode="overlay",
            bargap=0.02,
            showlegend=True,
            height=chart_height,
            margin=dict(t=int(top_margin), b=35, l=10, r=50),
            legend=dict(
                title="Color_Group",
                orientation="v",
            ),
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
                    layer="below",
                )

        # =========================
        # TODAY LINE
        # =========================
        today = pd.Timestamp(datetime.now(ZoneInfo("Asia/Singapore")).date())

        fig.add_vline(
            x=today,
            line_width=3,
            line_dash="dash",
            line_color="red",
            annotation_text="📍 TODAY",
            annotation_position="top",
            annotation_font_color="red",
            annotation_yshift=-5,
            layer="above",
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
                    "scale": 2,
                },
                "displayModeBar": True,
                "scrollZoom": True,
            },
        )

    except Exception as e:
        st.error(f"Error processing data: {e}")
