bruhhh make sure the code is not missing any task. every single thing on column b should appear. right now some are missing.
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

I’ll fix the export so the app gives two buttons: Download PNG and Download PDF. The safest fix is also to pin Kaleido to a version that does not need Chrome on Streamlit Cloud.

Thought for 34s

Ya, your error is because Kaleido v1 needs Chrome/Chromium installed. Plotly’s own docs say Kaleido v1 no longer bundles Chrome, but older Kaleido versions did.

For Streamlit Cloud, easiest fix: pin old Kaleido so you do not need Chrome.

Use this requirements.txt:

streamlit
pandas
numpy
openpyxl
plotly==5.24.1
kaleido==0.2.1

Then replace your PDF DOWNLOAD section with this:

# =========================
# EXPORT DOWNLOAD
# =========================
st.write("### 📄 Export Chart")

export_format = st.radio(
    "Choose export format:",
    ["PDF", "PNG"],
    horizontal=True
)

try:
    export_fig = deepcopy(fig)

    export_width = int(pdf_width)
    export_height = max(700, len(unique_rows) * int(pdf_height_per_task))
    export_scale = int(pdf_scale)

    export_fig.update_layout(
        width=export_width,
        height=export_height,
        margin=dict(t=180, b=80, l=40, r=80)
    )

    if export_format == "PDF":
        export_bytes = export_fig.to_image(
            format="pdf",
            width=export_width,
            height=export_height,
            scale=export_scale
        )

        st.download_button(
            label="📄 Download as PDF",
            data=export_bytes,
            file_name="Master_Timeline_Visual.pdf",
            mime="application/pdf"
        )

    else:
        export_bytes = export_fig.to_image(
            format="png",
            width=export_width,
            height=export_height,
            scale=export_scale
        )

        st.download_button(
            label="🖼️ Download as PNG",
            data=export_bytes,
            file_name="Master_Timeline_Visual.png",
            mime="image/png"
        )

except Exception as export_error:
    st.error(
        "Export failed. Use `plotly==5.24.1` and `kaleido==0.2.1` in requirements.txt, "
        "or install Chrome/Chromium if using latest Kaleido."
    )
    st.code(str(export_error))

Also make sure this import is at the top:

from copy import deepcopy

So your top imports should be:

import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from copy import deepcopy

Plotly can export PNG and PDF using static image export, but it needs Kaleido behind the scenes.

give me the full code
Thought for 11s

Use this full app.py:

import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from copy import deepcopy

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
    """
    Handles:
    - Excel serial dates
    - DD-MM-YY
    - DD/MM/YY
    - 11/Aug/21
    - 11-Aug-21
    - normal datetime values
    """
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
        "end date"
    ]

    if any(cell in header_keywords for cell in first_row):
        df_raw = df_raw.iloc[1:].reset_index(drop=True)

    # Keep original row number
    df_raw["Original_Row_No"] = df_raw.index + 1

    # Forward-fill project names from Column A
    df_raw["Project"] = df_raw["Project_Raw"].ffill()

    # IMPORTANT:
    # Every non-empty Column B row is treated as a task.
    task_mask = df_raw["Task_Raw"].notna()
    df = df_raw[task_mask].copy()

    df["Project"] = df["Project"].fillna("No Project").astype(str).str.strip()
    df["Task"] = df["Task_Raw"].astype(str).str.strip()

    # Parse dates
    df["Start"] = df["Start_Raw"].apply(parse_date_value)
    df["Finish"] = df["Finish_Raw"].apply(parse_date_value)

    # Check valid dates
    df["Has_Valid_Dates"] = df["Start"].notna() & df["Finish"].notna()

    # If finish is earlier than start, swap them
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

    # Dates used for plotting
    df["Plot_Start"] = df["Start"]
    df["Plot_Finish"] = df["Finish"]

    df.loc[~df["Has_Valid_Dates"], "Plot_Start"] = fallback_start
    df.loc[~df["Has_Valid_Dates"], "Plot_Finish"] = fallback_finish

    # Make finish date inclusive for chart display.
    # This also prevents same-day activities from disappearing.
    valid_plot_mask = df["Has_Valid_Dates"]
    df.loc[valid_plot_mask, "Plot_Finish"] = (
        df.loc[valid_plot_mask, "Plot_Finish"] + pd.Timedelta(days=1)
    )

    # For missing/invalid dates, make sure placeholder bar is visible
    same_day_mask = df["Plot_Start"] >= df["Plot_Finish"]
    df.loc[same_day_mask, "Plot_Finish"] = (
        df.loc[same_day_mask, "Plot_Start"] + pd.Timedelta(days=1)
    )

    # Display fields
    df["Display_Task"] = df["Project"] + " : " + df["Task"]

    # Unique y-axis key so duplicate task names do not collapse
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
        "Missing / invalid dates"
    )

    df["Color_Group"] = np.where(
        df["Has_Valid_Dates"],
        df["Task"],
        "Missing / invalid dates"
    )

    df["Duration_Days"] = np.where(
        df["Has_Valid_Dates"],
        (df["Finish"] - df["Start"]).dt.days + 1,
        np.nan
    )

    return df.reset_index(drop=True)


# =========================
# MAIN APP
# =========================
uploaded_file = st.file_uploader("📂 Upload Schedule (.xlsx or .csv)", type=["xlsx", "csv"])

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
            value="Master Department Schedule: Grand View"
        )

        show_undated_tasks = st.sidebar.checkbox(
            "Show tasks with missing / invalid dates",
            value=True
        )

        # =========================
        # EXPORT SETTINGS
        # =========================
        st.sidebar.header("Export Settings")

        export_width = st.sidebar.number_input(
            "Export Width",
            min_value=800,
            max_value=6000,
            value=2000,
            step=100
        )

        export_height_per_task = st.sidebar.number_input(
            "Export Height Per Task",
            min_value=20,
            max_value=100,
            value=36,
            step=2
        )

        export_scale = st.sidebar.number_input(
            "Export Scale",
            min_value=1,
            max_value=5,
            value=2,
            step=1
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
                key=f"project_checkbox_{project}"
            )

            if checked:
                selected_projects.append(project)

        df_view = df_clean[df_clean["Project"].isin(selected_projects)].copy()

        if not show_undated_tasks:
            df_view = df_view[df_view["Has_Valid_Dates"]].copy()

        if len(df_view) == 0:
            st.warning("No tasks to display based on current filters.")
            st.stop()

        # =========================
        # TASK CHECK
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
                        "Duration_Days"
                    ]
                ],
                use_container_width=True
            )

        # =========================
        # BAR LABEL OPTIONS
        # =========================
        label_option = st.sidebar.selectbox(
            "Bar Labels",
            ["None", "Task", "Project", "Task + Project", "Date Status"]
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
        # CHART
        # =========================
        fig = px.timeline(
            df_view,
            x_start="Plot_Start",
            x_end="Plot_Finish",
            y="Row_Key",
            color="Color_Group",
            text="Label" if label_option != "None" else None,
            title=f"<b>{chart_title}</b>",
            hover_data={
                "Row_Key": False,
                "Display_Task": True,
                "Task": True,
                "Project": True,
                "Start_Raw": True,
                "Finish_Raw": True,
                "Start": "|%B %d, %Y",
                "Finish": "|%B %d, %Y",
                "Date_Status": True,
                "Duration_Days": True,
            }
        )

        if label_option != "None":
            fig.update_traces(
                textposition="inside",
                insidetextanchor="middle"
            )

        # Preserve exact uploaded row order
        unique_rows = df_view["Row_Key"].tolist()
        tick_text = df_view["Display_Task"].tolist()

        fig.update_yaxes(
            autorange="reversed",
            title="",
            categoryorder="array",
            categoryarray=unique_rows,
            tickmode="array",
            tickvals=unique_rows,
            ticktext=tick_text,
            tickfont=dict(color="black", size=13)
        )

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
            "rgba(255,160,122,0.25)",
            "rgba(176,196,222,0.25)",
            "rgba(152,251,152,0.20)"
        ]

        visible_projects = df_view["Project"].dropna().unique().tolist()

        for i, proj in enumerate(visible_projects):
            proj_rows = df_view[df_view["Project"] == proj]["Row_Key"].tolist()

            if proj_rows:
                first_index = unique_rows.index(proj_rows[0])
                last_index = unique_rows.index(proj_rows[-1])

                fig.add_hrect(
                    y0=first_index - 0.5,
                    y1=last_index + 0.5,
                    fillcolor=background_colours[i % len(background_colours)],
                    layer="below",
                    line_width=0
                )

        # Invisible scatter to force top x-axis
        fig.add_scatter(
            x=[min_date],
            y=[unique_rows[0]],
            xaxis="x2",
            mode="markers",
            marker=dict(color="rgba(0,0,0,0)"),
            showlegend=False,
            hoverinfo="skip"
        )

        chart_height = max(650, len(unique_rows) * 32)

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
            height=chart_height,
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
        today = pd.Timestamp.now().normalize()

        fig.add_vline(
            x=today,
            line_width=3,
            line_dash="dash",
            line_color="red",
            annotation_text="📍 TODAY",
            annotation_position="top",
            annotation_font_color="red",
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

        # =========================
        # EXPORT BUTTONS
        # =========================
        st.write("### 📄 Export Chart")

        export_choice = st.radio(
            "Choose file type:",
            ["PDF", "PNG"],
            horizontal=True
        )

        try:
            export_fig = deepcopy(fig)

            final_export_width = int(export_width)
            final_export_height = max(
                700,
                len(unique_rows) * int(export_height_per_task)
            )
            final_export_scale = int(export_scale)

            export_fig.update_layout(
                width=final_export_width,
                height=final_export_height,
                margin=dict(t=180, b=80, l=40, r=80)
            )

            if export_choice == "PDF":
                pdf_bytes = export_fig.to_image(
                    format="pdf",
                    width=final_export_width,
                    height=final_export_height,
                    scale=final_export_scale
                )

                st.download_button(
                    label="📄 Download as PDF",
                    data=pdf_bytes,
                    file_name="Master_Timeline_Visual.pdf",
                    mime="application/pdf"
                )

            elif export_choice == "PNG":
                png_bytes = export_fig.to_image(
                    format="png",
                    width=final_export_width,
                    height=final_export_height,
                    scale=final_export_scale
                )

                st.download_button(
                    label="🖼️ Download as PNG",
                    data=png_bytes,
                    file_name="Master_Timeline_Visual.png",
                    mime="image/png"
                )

        except Exception as export_error:
            st.error(
                "Export failed. Use the pinned versions in requirements.txt below. "
                "This avoids the Chrome requirement from newer Kaleido versions."
            )
            st.code(str(export_error))

        # =========================
        # OPTIONAL HTML FALLBACK
        # =========================
        st.write("### 🌐 Backup Export")
        html_bytes = fig.to_html(include_plotlyjs="cdn").encode("utf-8")

        st.download_button(
            label="🌐 Download Interactive HTML Backup",
            data=html_bytes,
            file_name="Master_Timeline_Visual.html",
            mime="text/html"
        )

    except Exception as e:
        st.error(f"Error processing data: {e}")

Use this requirements.txt:

streamlit
pandas
numpy
openpyxl
plotly==5.24.1
kaleido==0.2.1

This gives you:

PDF export button
PNG export button
HTML backup export
Every non-empty Column B task shown
Same-day tasks still visible as bars
Missing/invalid date tasks still shown as placeholder bars
Pasted text(20).txt
Document
Pasted text (2)(1).txt
Document
i need the button to download as pdf pls. follow this code's format for the download as pdf 

Got it — I’ll switch the PDF export away from Plotly/Kaleido and follow your org-chart code style: reportlab generates the PDF bytes, then st.download_button downloads it. This means no Chrome/Kaleido issue.

Thought for 21s

Yes — use ReportLab PDF generation, same style as your other code. This does not use Kaleido, so it will not ask for Chrome.

Use this requirements.txt:

streamlit
pandas
numpy
plotly
openpyxl
reportlab

Full app.py:

import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import io
from datetime import datetime
from zoneinfo import ZoneInfo

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    from reportlab.pdfbase.pdfmetrics import stringWidth
    REPORTLAB_AVAILABLE = True
except ModuleNotFoundError:
    REPORTLAB_AVAILABLE = False


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

    while df_raw.shape[1] < 4:
        df_raw[df_raw.shape[1]] = np.nan

    df_raw = df_raw.iloc[:, :4].copy()
    df_raw.columns = ["Project_Raw", "Task_Raw", "Start_Raw", "Finish_Raw"]

    for col in df_raw.columns:
        df_raw[col] = df_raw[col].replace(r"^\s*$", np.nan, regex=True)

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
        "end date"
    ]

    if any(cell in header_keywords for cell in first_row):
        df_raw = df_raw.iloc[1:].reset_index(drop=True)

    df_raw["Original_Row_No"] = df_raw.index + 1

    df_raw["Project"] = df_raw["Project_Raw"].ffill()

    # Every non-empty Column B row becomes a task
    task_mask = df_raw["Task_Raw"].notna()
    df = df_raw[task_mask].copy()

    df["Project"] = df["Project"].fillna("No Project").astype(str).str.strip()
    df["Task"] = df["Task_Raw"].astype(str).str.strip()

    df["Start"] = df["Start_Raw"].apply(parse_date_value)
    df["Finish"] = df["Finish_Raw"].apply(parse_date_value)

    df["Has_Valid_Dates"] = df["Start"].notna() & df["Finish"].notna()

    # Swap wrong date order
    reversed_mask = df["Has_Valid_Dates"] & (df["Finish"] < df["Start"])

    temp_start = df.loc[reversed_mask, "Start"].copy()
    df.loc[reversed_mask, "Start"] = df.loc[reversed_mask, "Finish"]
    df.loc[reversed_mask, "Finish"] = temp_start

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

    # Finish date inclusive for visible chart bar
    valid_plot_mask = df["Has_Valid_Dates"]
    df.loc[valid_plot_mask, "Plot_Finish"] = (
        df.loc[valid_plot_mask, "Plot_Finish"] + pd.Timedelta(days=1)
    )

    # Prevent zero-width bars
    same_day_mask = df["Plot_Start"] >= df["Plot_Finish"]
    df.loc[same_day_mask, "Plot_Finish"] = (
        df.loc[same_day_mask, "Plot_Start"] + pd.Timedelta(days=1)
    )

    df["Display_Task"] = df["Project"] + " : " + df["Task"]

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
        "Missing / invalid dates"
    )

    df["Color_Group"] = np.where(
        df["Has_Valid_Dates"],
        df["Task"],
        "Missing / invalid dates"
    )

    df["Duration_Days"] = np.where(
        df["Has_Valid_Dates"],
        (df["Finish"] - df["Start"]).dt.days + 1,
        np.nan
    )

    return df.reset_index(drop=True)


# =========================
# PDF HELPERS
# =========================
def safe_text(value):
    if pd.isna(value):
        return ""
    return str(value).replace("&amp;", "&").strip()


def draw_wrapped_text(c, text, x, y, max_width, font_name, font_size, max_lines=2):
    text = safe_text(text)

    if text == "":
        return

    words = text.split()
    lines = []
    current = ""

    for word in words:
        test = word if current == "" else current + " " + word

        if stringWidth(test, font_name, font_size) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    if len(lines) > max_lines:
        lines = lines[:max_lines]
        if len(lines[-1]) > 3:
            lines[-1] = lines[-1][:-3] + "..."

    line_height = font_size + 3

    for i, line in enumerate(lines):
        c.drawString(x, y - i * line_height, line)


def hex_to_reportlab_color(hex_code, fallback="#6699cc"):
    try:
        return colors.HexColor(hex_code)
    except Exception:
        return colors.HexColor(fallback)


def generate_color_map(tasks):
    palette = [
        "#4e79a7",
        "#59a14f",
        "#f28e2b",
        "#e15759",
        "#76b7b2",
        "#edc948",
        "#b07aa1",
        "#ff9da7",
        "#9c755f",
        "#bab0ab",
        "#86bc86",
        "#6b9ac4",
        "#d37295",
        "#fabfd2",
        "#b6992d",
        "#499894",
    ]

    color_map = {}

    for i, task in enumerate(tasks):
        color_map[task] = palette[i % len(palette)]

    color_map["Missing / invalid dates"] = "#9e9e9e"

    return color_map


def make_timeline_pdf(
    df_view,
    chart_title,
    pdf_width=1800,
    row_height=26,
    left_margin=260,
    right_margin=60,
    top_margin=100,
    bottom_margin=70,
):
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("reportlab is not installed. Add reportlab to requirements.txt.")

    df_pdf = df_view.copy().reset_index(drop=True)

    if df_pdf.empty:
        raise ValueError("No tasks available to export.")

    # Date range
    min_date = df_pdf["Plot_Start"].min().replace(day=1)
    max_date = df_pdf["Plot_Finish"].max()

    if pd.isna(min_date) or pd.isna(max_date):
        min_date = pd.Timestamp.today().replace(day=1)
        max_date = min_date + pd.DateOffset(months=1)

    month_starts = pd.date_range(start=min_date, end=max_date, freq="MS")

    chart_left = left_margin
    chart_right = pdf_width - right_margin
    chart_width = chart_right - chart_left

    header_height = 60
    task_count = len(df_pdf)

    pdf_height = top_margin + header_height + task_count * row_height + bottom_margin
    pdf_height = max(pdf_height, 650)

    # ReportLab max page size guard
    max_page_size = 14400
    pdf_width = min(pdf_width, max_page_size)
    pdf_height = min(pdf_height, max_page_size)

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(pdf_width, pdf_height))

    # Title
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(40, pdf_height - 40, safe_text(chart_title))

    c.setFont("Helvetica", 9)
    exported_time = datetime.now(ZoneInfo("Asia/Singapore")).strftime("%d %b %Y, %I:%M %p SGT")
    c.drawString(40, pdf_height - 58, f"Exported: {exported_time}")

    # Helpers
    total_days = max((max_date - min_date).days, 1)

    def date_to_x(dt):
        dt = pd.Timestamp(dt)
        return chart_left + ((dt - min_date).days / total_days) * chart_width

    chart_top = pdf_height - top_margin - header_height
    chart_bottom = chart_top - task_count * row_height

    # Background
    c.setFillColor(colors.HexColor("#ffffff"))
    c.rect(0, 0, pdf_width, pdf_height, fill=1, stroke=0)

    # Month grid and labels
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

    c.setFont("Helvetica-Bold", 8)

    for dt in month_starts:
        x = date_to_x(dt)

        if dt.month == 1:
            c.setStrokeColor(colors.black)
            c.setLineWidth(1.4)
        else:
            c.setStrokeColor(colors.HexColor("#dddddd"))
            c.setLineWidth(0.5)

        c.line(x, chart_bottom, x, chart_top + 35)

        c.setFillColor(colors.black)
        c.drawCentredString(x + 8, chart_top + 18, month_map[dt.month])

        if dt.month == 1 or dt == month_starts[0]:
            c.setFont("Helvetica-Bold", 8)
            c.drawCentredString(x + 18, chart_top + 32, str(dt.year))

    # Today line
    today = pd.Timestamp(datetime.now(ZoneInfo("Asia/Singapore")).date())

    if min_date <= today <= max_date:
        today_x = date_to_x(today)
        c.setStrokeColor(colors.red)
        c.setLineWidth(1.5)
        c.setDash(4, 3)
        c.line(today_x, chart_bottom, today_x, chart_top + 40)
        c.setDash()

        c.setFillColor(colors.red)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(today_x, chart_top + 45, "TODAY")

    # Color map
    color_map = generate_color_map(df_pdf["Color_Group"].unique().tolist())

    # Project background bands
    background_colours = [
        colors.Color(100 / 255, 149 / 255, 237 / 255, alpha=0.12),
        colors.Color(143 / 255, 188 / 255, 143 / 255, alpha=0.16),
        colors.Color(244 / 255, 164 / 255, 96 / 255, alpha=0.15),
        colors.Color(216 / 255, 191 / 255, 216 / 255, alpha=0.18),
        colors.Color(255 / 255, 160 / 255, 122 / 255, alpha=0.15),
    ]

    projects = df_pdf["Project"].dropna().unique().tolist()

    for p_i, project in enumerate(projects):
        project_indexes = df_pdf.index[df_pdf["Project"] == project].tolist()

        if not project_indexes:
            continue

        y_top = chart_top - project_indexes[0] * row_height
        y_bottom = chart_top - (project_indexes[-1] + 1) * row_height

        c.setFillColor(background_colours[p_i % len(background_colours)])
        c.rect(0, y_bottom, pdf_width, y_top - y_bottom, fill=1, stroke=0)

    # Row lines, labels, bars
    bar_height = max(6, row_height * 0.48)
    label_font_size = 7 if task_count > 70 else 8

    for idx, row in df_pdf.iterrows():
        row_top = chart_top - idx * row_height
        row_mid = row_top - row_height / 2
        row_bottom = row_top - row_height

        # row separator
        c.setStrokeColor(colors.HexColor("#eeeeee"))
        c.setLineWidth(0.4)
        c.line(40, row_bottom, pdf_width - 40, row_bottom)

        # label
        c.setFillColor(colors.black)
        c.setFont("Helvetica", label_font_size)

        display_task = safe_text(row["Display_Task"])
        draw_wrapped_text(
            c,
            display_task,
            40,
            row_mid + 3,
            left_margin - 55,
            "Helvetica",
            label_font_size,
            max_lines=2,
        )

        # bar
        start = pd.Timestamp(row["Plot_Start"])
        finish = pd.Timestamp(row["Plot_Finish"])

        x1 = date_to_x(start)
        x2 = date_to_x(finish)

        if x2 <= x1:
            x2 = x1 + 2

        bar_width = max(x2 - x1, 2)

        color_key = safe_text(row["Color_Group"])
        bar_color = hex_to_reportlab_color(color_map.get(color_key, "#6699cc"))

        if not bool(row["Has_Valid_Dates"]):
            bar_color = colors.HexColor("#9e9e9e")

        c.setFillColor(bar_color)
        c.setStrokeColor(bar_color)
        c.roundRect(
            x1,
            row_mid - bar_height / 2,
            bar_width,
            bar_height,
            radius=2,
            fill=1,
            stroke=0,
        )

    # Border around timeline area
    c.setStrokeColor(colors.HexColor("#aaaaaa"))
    c.setLineWidth(0.8)
    c.rect(chart_left, chart_bottom, chart_width, task_count * row_height, fill=0, stroke=1)

    # Legend
    legend_y = 35
    legend_x = 40
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(colors.black)
    c.drawString(legend_x, legend_y + 14, "Legend:")

    c.setFont("Helvetica", 7)
    legend_items = list(color_map.items())[:12]

    x_pos = legend_x + 50

    for label, hex_color in legend_items:
        c.setFillColor(hex_to_reportlab_color(hex_color))
        c.rect(x_pos, legend_y + 8, 8, 8, fill=1, stroke=0)

        c.setFillColor(colors.black)
        c.drawString(x_pos + 12, legend_y + 8, safe_text(label)[:22])

        x_pos += 140

        if x_pos > pdf_width - 180:
            break

    c.showPage()
    c.save()
    buffer.seek(0)

    return buffer.getvalue()


# =========================
# MAIN APP
# =========================
uploaded_file = st.file_uploader("📂 Upload Schedule (.xlsx or .csv)", type=["xlsx", "csv"])

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
            value="Master Department Schedule: Grand View"
        )

        show_undated_tasks = st.sidebar.checkbox(
            "Show tasks with missing / invalid dates",
            value=True
        )

        # =========================
        # PDF SETTINGS
        # =========================
        st.sidebar.header("PDF Settings")

        pdf_width = st.sidebar.slider(
            "PDF Width",
            min_value=1000,
            max_value=5000,
            value=2200,
            step=100
        )

        pdf_row_height = st.sidebar.slider(
            "PDF Row Height",
            min_value=18,
            max_value=50,
            value=28,
            step=1
        )

        pdf_left_margin = st.sidebar.slider(
            "PDF Task Label Width",
            min_value=180,
            max_value=600,
            value=320,
            step=20
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
                key=f"project_checkbox_{project}"
            )

            if checked:
                selected_projects.append(project)

        df_view = df_clean[df_clean["Project"].isin(selected_projects)].copy()

        if not show_undated_tasks:
            df_view = df_view[df_view["Has_Valid_Dates"]].copy()

        if len(df_view) == 0:
            st.warning("No tasks to display based on current filters.")
            st.stop()

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
                        "Duration_Days"
                    ]
                ],
                use_container_width=True
            )

        # =========================
        # BAR LABEL OPTIONS
        # =========================
        label_option = st.sidebar.selectbox(
            "Bar Labels",
            ["None", "Task", "Project", "Task + Project", "Date Status"]
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
        # CHART
        # =========================
        fig = px.timeline(
            df_view,
            x_start="Plot_Start",
            x_end="Plot_Finish",
            y="Row_Key",
            color="Color_Group",
            text="Label" if label_option != "None" else None,
            title=f"<b>{chart_title}</b>",
            hover_data={
                "Row_Key": False,
                "Display_Task": True,
                "Task": True,
                "Project": True,
                "Start_Raw": True,
                "Finish_Raw": True,
                "Plot_Start": "|%B %d, %Y",
                "Plot_Finish": "|%B %d, %Y",
                "Date_Status": True,
                "Duration_Days": True,
            }
        )

        if label_option != "None":
            fig.update_traces(
                textposition="inside",
                insidetextanchor="middle"
            )

        unique_rows = df_view["Row_Key"].tolist()
        tick_text = df_view["Display_Task"].tolist()

        fig.update_yaxes(
            autorange="reversed",
            title="",
            categoryorder="array",
            categoryarray=unique_rows,
            tickmode="array",
            tickvals=unique_rows,
            ticktext=tick_text,
            tickfont=dict(color="black", size=13)
        )

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
            "rgba(255,160,122,0.25)",
            "rgba(176,196,222,0.25)",
            "rgba(152,251,152,0.20)"
        ]

        visible_projects = df_view["Project"].dropna().unique().tolist()

        for i, proj in enumerate(visible_projects):
            proj_rows = df_view[df_view["Project"] == proj]["Row_Key"].tolist()

            if proj_rows:
                first_index = unique_rows.index(proj_rows[0])
                last_index = unique_rows.index(proj_rows[-1])

                fig.add_hrect(
                    y0=first_index - 0.5,
                    y1=last_index + 0.5,
                    fillcolor=background_colours[i % len(background_colours)],
                    layer="below",
                    line_width=0
                )

        # Invisible scatter to force top x-axis
        fig.add_scatter(
            x=[min_date],
            y=[unique_rows[0]],
            xaxis="x2",
            mode="markers",
            marker=dict(color="rgba(0,0,0,0)"),
            showlegend=False,
            hoverinfo="skip"
        )

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
            height=max(650, len(unique_rows) * 32),
            margin=dict(t=160, b=50, l=10, r=50)
        )

        for dt in all_months:
            if dt.month == 1:
                fig.add_vline(
                    x=dt,
                    line_width=2,
                    line_color="black",
                    layer="below"
                )

        today = pd.Timestamp(datetime.now(ZoneInfo("Asia/Singapore")).date())

        fig.add_vline(
            x=today,
            line_width=3,
            line_dash="dash",
            line_color="red",
            annotation_text="📍 TODAY",
            annotation_position="top",
            annotation_font_color="red",
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

        # =========================
        # REPORTLAB PDF DOWNLOAD
        # =========================
        st.markdown("### 📥 Download Full Timeline")

        if REPORTLAB_AVAILABLE:
            try:
                pdf_bytes = make_timeline_pdf(
                    df_view=df_view,
                    chart_title=chart_title,
                    pdf_width=int(pdf_width),
                    row_height=int(pdf_row_height),
                    left_margin=int(pdf_left_margin),
                )

                file_stamp = datetime.now(ZoneInfo("Asia/Singapore")).strftime("%Y%m%d_%H%M")

                st.download_button(
                    label="Download Timeline as PDF",
                    data=pdf_bytes,
                    file_name=f"Master_Timeline_Full_{file_stamp}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

                st.caption(
                    "This PDF is generated using ReportLab, so it does not need Kaleido or Chrome."
                )

            except Exception as e:
                st.error(f"Unable to generate PDF: {e}")

        else:
            st.error(
                "PDF download needs the reportlab package. Add `reportlab` to requirements.txt, then reboot the Streamlit app."
            )

    except Exception as e:
        st.error(f"Error processing data: {e}")

Main change: the PDF button now uses the same ReportLab-style st.download_button approach as your reference code, instead of fig.to_image().

there is big gap between top axis and first bar. 
Thought for 12s

Ya, the gap is because your chart height is forced to minimum 650px:

height=max(650, len(unique_rows) * 32)

When you only have a few tasks, Plotly stretches the y-axis too much, so the first bar becomes very far from the top axis.

Replace your layout section with this:

# =========================
# LAYOUT
# =========================

# Dynamic height: smaller when fewer tasks, bigger when many tasks
chart_height = max(280, len(unique_rows) * 34 + 160)

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
    height=chart_height,
    margin=dict(t=90, b=40, l=10, r=50)
)

Also change this part inside st.plotly_chart if your chart still feels too tall:

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

No need to change this one actually — the main fix is the chart_height.

Before:

height=max(650, len(unique_rows) * 32)

After:

chart_height = max(280, len(unique_rows) * 34 + 160)
height=chart_height

This will make 4 rows compact, but still expand automatically when you have many tasks.

can u give me the full 
Thought for 9s

Yes, here is the full updated code with the gap fixed. I kept your timeline logic and added the ReportLab PDF download style from your reference code.

Use this requirements.txt:

streamlit
pandas
numpy
plotly
openpyxl
reportlab

Full app.py:

import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import io
from datetime import datetime
from zoneinfo import ZoneInfo

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    from reportlab.pdfbase.pdfmetrics import stringWidth
    REPORTLAB_AVAILABLE = True
except ModuleNotFoundError:
    REPORTLAB_AVAILABLE = False


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

    while df_raw.shape[1] < 4:
        df_raw[df_raw.shape[1]] = np.nan

    df_raw = df_raw.iloc[:, :4].copy()
    df_raw.columns = ["Project_Raw", "Task_Raw", "Start_Raw", "Finish_Raw"]

    for col in df_raw.columns:
        df_raw[col] = df_raw[col].replace(r"^\s*$", np.nan, regex=True)

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

    df_raw["Original_Row_No"] = df_raw.index + 1
    df_raw["Project"] = df_raw["Project_Raw"].ffill()

    # Every non-empty Column B row becomes a task
    task_mask = df_raw["Task_Raw"].notna()
    df = df_raw[task_mask].copy()

    df["Project"] = df["Project"].fillna("No Project").astype(str).str.strip()
    df["Task"] = df["Task_Raw"].astype(str).str.strip()

    df["Start"] = df["Start_Raw"].apply(parse_date_value)
    df["Finish"] = df["Finish_Raw"].apply(parse_date_value)

    df["Has_Valid_Dates"] = df["Start"].notna() & df["Finish"].notna()

    # Swap if Finish is earlier than Start
    reversed_mask = df["Has_Valid_Dates"] & (df["Finish"] < df["Start"])

    temp_start = df.loc[reversed_mask, "Start"].copy()
    df.loc[reversed_mask, "Start"] = df.loc[reversed_mask, "Finish"]
    df.loc[reversed_mask, "Finish"] = temp_start

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

    df["Display_Task"] = df["Project"] + " : " + df["Task"]

    # Unique y-axis key so duplicate tasks do not collapse
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
# PDF HELPERS
# =========================
def safe_text(value):
    if pd.isna(value):
        return ""
    return str(value).replace("&amp;", "&").strip()


def draw_wrapped_text(c, text, x, y, max_width, font_name, font_size, max_lines=2):
    text = safe_text(text)

    if text == "":
        return

    words = text.split()
    lines = []
    current = ""

    for word in words:
        test = word if current == "" else current + " " + word

        if stringWidth(test, font_name, font_size) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    if len(lines) > max_lines:
        lines = lines[:max_lines]

        if len(lines[-1]) > 3:
            lines[-1] = lines[-1][:-3] + "..."

    line_height = font_size + 3

    for i, line in enumerate(lines):
        c.drawString(x, y - i * line_height, line)


def hex_to_reportlab_color(hex_code, fallback="#6699cc"):
    try:
        return colors.HexColor(hex_code)
    except Exception:
        return colors.HexColor(fallback)


def generate_color_map(tasks):
    palette = [
        "#4e79a7",
        "#59a14f",
        "#f28e2b",
        "#e15759",
        "#76b7b2",
        "#edc948",
        "#b07aa1",
        "#ff9da7",
        "#9c755f",
        "#bab0ab",
        "#86bc86",
        "#6b9ac4",
        "#d37295",
        "#fabfd2",
        "#b6992d",
        "#499894",
    ]

    color_map = {}

    for i, task in enumerate(tasks):
        color_map[task] = palette[i % len(palette)]

    color_map["Missing / invalid dates"] = "#9e9e9e"

    return color_map


def make_timeline_pdf(
    df_view,
    chart_title,
    pdf_width=2200,
    row_height=28,
    left_margin=320,
    right_margin=60,
    top_margin=100,
    bottom_margin=70,
):
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("reportlab is not installed. Add reportlab to requirements.txt.")

    df_pdf = df_view.copy().reset_index(drop=True)

    if df_pdf.empty:
        raise ValueError("No tasks available to export.")

    min_date = df_pdf["Plot_Start"].min().replace(day=1)
    max_date = df_pdf["Plot_Finish"].max()

    if pd.isna(min_date) or pd.isna(max_date):
        min_date = pd.Timestamp.today().replace(day=1)
        max_date = min_date + pd.DateOffset(months=1)

    month_starts = pd.date_range(start=min_date, end=max_date, freq="MS")

    chart_left = left_margin
    chart_right = pdf_width - right_margin
    chart_width = chart_right - chart_left

    header_height = 60
    task_count = len(df_pdf)

    pdf_height = top_margin + header_height + task_count * row_height + bottom_margin
    pdf_height = max(pdf_height, 650)

    max_page_size = 14400
    pdf_width = min(pdf_width, max_page_size)
    pdf_height = min(pdf_height, max_page_size)

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(pdf_width, pdf_height))

    c.setFillColor(colors.HexColor("#ffffff"))
    c.rect(0, 0, pdf_width, pdf_height, fill=1, stroke=0)

    # Title
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(40, pdf_height - 40, safe_text(chart_title))

    c.setFont("Helvetica", 9)
    exported_time = datetime.now(ZoneInfo("Asia/Singapore")).strftime("%d %b %Y, %I:%M %p SGT")
    c.drawString(40, pdf_height - 58, f"Exported: {exported_time}")

    total_days = max((max_date - min_date).days, 1)

    def date_to_x(dt):
        dt = pd.Timestamp(dt)
        return chart_left + ((dt - min_date).days / total_days) * chart_width

    chart_top = pdf_height - top_margin - header_height
    chart_bottom = chart_top - task_count * row_height

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

    # Month grid
    c.setFont("Helvetica-Bold", 8)

    for dt in month_starts:
        x = date_to_x(dt)

        if dt.month == 1:
            c.setStrokeColor(colors.black)
            c.setLineWidth(1.4)
        else:
            c.setStrokeColor(colors.HexColor("#dddddd"))
            c.setLineWidth(0.5)

        c.line(x, chart_bottom, x, chart_top + 35)

        c.setFillColor(colors.black)
        c.drawCentredString(x + 8, chart_top + 18, month_map[dt.month])

        if dt.month == 1 or dt == month_starts[0]:
            c.setFont("Helvetica-Bold", 8)
            c.drawCentredString(x + 18, chart_top + 32, str(dt.year))

    # Today line
    today = pd.Timestamp(datetime.now(ZoneInfo("Asia/Singapore")).date())

    if min_date <= today <= max_date:
        today_x = date_to_x(today)
        c.setStrokeColor(colors.red)
        c.setLineWidth(1.5)
        c.setDash(4, 3)
        c.line(today_x, chart_bottom, today_x, chart_top + 40)
        c.setDash()

        c.setFillColor(colors.red)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(today_x, chart_top + 45, "TODAY")

    color_map = generate_color_map(df_pdf["Color_Group"].unique().tolist())

    # Project background bands
    background_colours = [
        colors.Color(100 / 255, 149 / 255, 237 / 255, alpha=0.12),
        colors.Color(143 / 255, 188 / 255, 143 / 255, alpha=0.16),
        colors.Color(244 / 255, 164 / 255, 96 / 255, alpha=0.15),
        colors.Color(216 / 255, 191 / 255, 216 / 255, alpha=0.18),
        colors.Color(255 / 255, 160 / 255, 122 / 255, alpha=0.15),
    ]

    projects = df_pdf["Project"].dropna().unique().tolist()

    for p_i, project in enumerate(projects):
        project_indexes = df_pdf.index[df_pdf["Project"] == project].tolist()

        if not project_indexes:
            continue

        y_top = chart_top - project_indexes[0] * row_height
        y_bottom = chart_top - (project_indexes[-1] + 1) * row_height

        c.setFillColor(background_colours[p_i % len(background_colours)])
        c.rect(0, y_bottom, pdf_width, y_top - y_bottom, fill=1, stroke=0)

    bar_height = max(6, row_height * 0.48)
    label_font_size = 7 if task_count > 70 else 8

    for idx, row in df_pdf.iterrows():
        row_top = chart_top - idx * row_height
        row_mid = row_top - row_height / 2
        row_bottom = row_top - row_height

        # Row separator
        c.setStrokeColor(colors.HexColor("#eeeeee"))
        c.setLineWidth(0.4)
        c.line(40, row_bottom, pdf_width - 40, row_bottom)

        # Task label
        c.setFillColor(colors.black)
        c.setFont("Helvetica", label_font_size)

        draw_wrapped_text(
            c,
            row["Display_Task"],
            40,
            row_mid + 3,
            left_margin - 55,
            "Helvetica",
            label_font_size,
            max_lines=2,
        )

        # Timeline bar
        start = pd.Timestamp(row["Plot_Start"])
        finish = pd.Timestamp(row["Plot_Finish"])

        x1 = date_to_x(start)
        x2 = date_to_x(finish)

        if x2 <= x1:
            x2 = x1 + 2

        bar_width = max(x2 - x1, 2)

        color_key = safe_text(row["Color_Group"])
        bar_color = hex_to_reportlab_color(color_map.get(color_key, "#6699cc"))

        if not bool(row["Has_Valid_Dates"]):
            bar_color = colors.HexColor("#9e9e9e")

        c.setFillColor(bar_color)
        c.setStrokeColor(bar_color)
        c.roundRect(
            x1,
            row_mid - bar_height / 2,
            bar_width,
            bar_height,
            radius=2,
            fill=1,
            stroke=0,
        )

    # Border around chart
    c.setStrokeColor(colors.HexColor("#aaaaaa"))
    c.setLineWidth(0.8)
    c.rect(chart_left, chart_bottom, chart_width, task_count * row_height, fill=0, stroke=1)

    # Legend
    legend_y = 35
    legend_x = 40
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(colors.black)
    c.drawString(legend_x, legend_y + 14, "Legend:")

    c.setFont("Helvetica", 7)
    legend_items = list(color_map.items())[:12]

    x_pos = legend_x + 50

    for label, hex_color in legend_items:
        c.setFillColor(hex_to_reportlab_color(hex_color))
        c.rect(x_pos, legend_y + 8, 8, 8, fill=1, stroke=0)

        c.setFillColor(colors.black)
        c.drawString(x_pos + 12, legend_y + 8, safe_text(label)[:22])

        x_pos += 140

        if x_pos > pdf_width - 180:
            break

    c.showPage()
    c.save()
    buffer.seek(0)

    return buffer.getvalue()


# =========================
# MAIN APP
# =========================
uploaded_file = st.file_uploader("📂 Upload Schedule (.xlsx or .csv)", type=["xlsx", "csv"])

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
        # PDF SETTINGS
        # =========================
        st.sidebar.header("PDF Settings")

        pdf_width = st.sidebar.slider(
            "PDF Width",
            min_value=1000,
            max_value=5000,
            value=2200,
            step=100,
        )

        pdf_row_height = st.sidebar.slider(
            "PDF Row Height",
            min_value=18,
            max_value=50,
            value=28,
            step=1,
        )

        pdf_left_margin = st.sidebar.slider(
            "PDF Task Label Width",
            min_value=180,
            max_value=600,
            value=320,
            step=20,
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
        # CHART
        # =========================
        fig = px.timeline(
            df_view,
            x_start="Plot_Start",
            x_end="Plot_Finish",
            y="Row_Key",
            color="Color_Group",
            text="Label" if label_option != "None" else None,
            title=f"<b>{chart_title}</b>",
            hover_data={
                "Row_Key": False,
                "Display_Task": True,
                "Task": True,
                "Project": True,
                "Start_Raw": True,
                "Finish_Raw": True,
                "Plot_Start": "|%B %d, %Y",
                "Plot_Finish": "|%B %d, %Y",
                "Date_Status": True,
                "Duration_Days": True,
            },
        )

        if label_option != "None":
            fig.update_traces(
                textposition="inside",
                insidetextanchor="middle",
            )

        unique_rows = df_view["Row_Key"].tolist()
        tick_text = df_view["Display_Task"].tolist()

        fig.update_yaxes(
            autorange="reversed",
            title="",
            categoryorder="array",
            categoryarray=unique_rows,
            tickmode="array",
            tickvals=unique_rows,
            ticktext=tick_text,
            tickfont=dict(color="black", size=13),
        )

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
        # PROJECT BACKGROUND COLOURS
        # =========================
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
            proj_rows = df_view[df_view["Project"] == proj]["Row_Key"].tolist()

            if proj_rows:
                first_index = unique_rows.index(proj_rows[0])
                last_index = unique_rows.index(proj_rows[-1])

                fig.add_hrect(
                    y0=first_index - 0.5,
                    y1=last_index + 0.5,
                    fillcolor=background_colours[i % len(background_colours)],
                    layer="below",
                    line_width=0,
                )

        # Invisible scatter to force top x-axis
        fig.add_scatter(
            x=[min_date],
            y=[unique_rows[0]],
            xaxis="x2",
            mode="markers",
            marker=dict(color="rgba(0,0,0,0)"),
            showlegend=False,
            hoverinfo="skip",
        )

        # =========================
        # FIXED DYNAMIC HEIGHT
        # This removes the big gap between top axis and first bar.
        # =========================
        chart_height = max(280, len(unique_rows) * 34 + 160)

        fig.update_layout(
            xaxis=dict(
                tickmode="array",
                tickvals=tick_vals,
                ticktext=tick_text_bottom,
                tickangle=0,
                showgrid=True,
                gridcolor="rgba(0,0,0,0.1)",
                gridwidth=1,
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
            ),
            showlegend=True,
            height=chart_height,
            margin=dict(t=90, b=40, l=10, r=50),
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
            annotation_yshift=25,
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
            },
        )

        # =========================
        # REPORTLAB PDF DOWNLOAD
        # =========================
        st.markdown("### 📥 Download Full Timeline")

        if REPORTLAB_AVAILABLE:
            try:
                pdf_bytes = make_timeline_pdf(
                    df_view=df_view,
                    chart_title=chart_title,
                    pdf_width=int(pdf_width),
                    row_height=int(pdf_row_height),
                    left_margin=int(pdf_left_margin),
                )

                file_stamp = datetime.now(ZoneInfo("Asia/Singapore")).strftime("%Y%m%d_%H%M")

                st.download_button(
                    label="Download Timeline as PDF",
                    data=pdf_bytes,
                    file_name=f"Master_Timeline_Full_{file_stamp}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

                st.caption(
                    "This PDF is generated using ReportLab, so it does not need Kaleido or Chrome."
                )

            except Exception as e:
                st.error(f"Unable to generate PDF: {e}")

        else:
            st.error(
                "PDF download needs the reportlab package. Add `reportlab` to requirements.txt, then reboot the Streamlit app."
            )

    except Exception as e:
        st.error(f"Error processing data: {e}")

The main change is here:

chart_height = max(280, len(unique_rows) * 34 + 160)
margin=dict(t=90, b=40, l=10, r=50)

So when you only have a few bars, the chart becomes compact instead of leaving a huge blank space.

i dont need pdf
Thought for 10s

Got it — remove all PDF stuff. Use this clean version.

requirements.txt:

streamlit
pandas
numpy
plotly
openpyxl

Full app.py:

import streamlit as st
import pandas as pd
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

    # Unique y-axis key so duplicate task names do not collapse
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
        # CHART
        # =========================
        fig = px.timeline(
            df_view,
            x_start="Plot_Start",
            x_end="Plot_Finish",
            y="Row_Key",
            color="Color_Group",
            text="Label" if label_option != "None" else None,
            title=f"<b>{chart_title}</b>",
            hover_data={
                "Row_Key": False,
                "Display_Task": True,
                "Task": True,
                "Project": True,
                "Start_Raw": True,
                "Finish_Raw": True,
                "Plot_Start": "|%B %d, %Y",
                "Plot_Finish": "|%B %d, %Y",
                "Date_Status": True,
                "Duration_Days": True,
            },
        )

        if label_option != "None":
            fig.update_traces(
                textposition="inside",
                insidetextanchor="middle",
            )

        # Preserve uploaded row order
        unique_rows = df_view["Row_Key"].tolist()
        tick_text = df_view["Display_Task"].tolist()

        fig.update_yaxes(
            autorange="reversed",
            title="",
            categoryorder="array",
            categoryarray=unique_rows,
            tickmode="array",
            tickvals=unique_rows,
            ticktext=tick_text,
            tickfont=dict(color="black", size=13),
        )

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
        # PROJECT BACKGROUND COLOURS
        # =========================
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
            proj_rows = df_view[df_view["Project"] == proj]["Row_Key"].tolist()

            if proj_rows:
                first_index = unique_rows.index(proj_rows[0])
                last_index = unique_rows.index(proj_rows[-1])

                fig.add_hrect(
                    y0=first_index - 0.5,
                    y1=last_index + 0.5,
                    fillcolor=background_colours[i % len(background_colours)],
                    layer="below",
                    line_width=0,
                )

        # Invisible scatter to force top x-axis
        fig.add_scatter(
            x=[min_date],
            y=[unique_rows[0]],
            xaxis="x2",
            mode="markers",
            marker=dict(color="rgba(0,0,0,0)"),
            showlegend=False,
            hoverinfo="skip",
        )

        # =========================
        # DYNAMIC HEIGHT
        # Removes big gap between top axis and first bar
        # =========================
        chart_height = max(280, len(unique_rows) * 34 + 160)

        fig.update_layout(
            xaxis=dict(
                tickmode="array",
                tickvals=tick_vals,
                ticktext=tick_text_bottom,
                tickangle=0,
                showgrid=True,
                gridcolor="rgba(0,0,0,0.1)",
                gridwidth=1,
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
            ),
            showlegend=True,
            height=chart_height,
            margin=dict(t=90, b=40, l=10, r=50),
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
            annotation_yshift=25,
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
            },
        )

    except Exception as e:
        st.error(f"Error processing data: {e}")

Now there is no PDF section, no ReportLab, no Kaleido, and no Chrome issue. The chart still has the built-in Plotly PNG download button in the top-right toolbar.

Pasted text(21).txt
Document
the gap between first bar and top axis is too big bruhh
Thought for 44s

Ya, the earlier fix only reduced chart height, but Plotly still keeps 0.5 category padding above the first row. I changed it properly now by forcing the y-axis range closer to the first category and making the bars thicker. This follows your current uploaded code structure.

Use this full code:

import streamlit as st
import pandas as pd
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

    # Unique y-axis key so duplicate task names do not collapse
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

        top_gap = st.sidebar.slider(
            "Gap Between Top Axis and First Bar",
            min_value=0.02,
            max_value=0.50,
            value=0.08,
            step=0.01,
        )

        bar_thickness = st.sidebar.slider(
            "Bar Thickness",
            min_value=0.40,
            max_value=1.00,
            value=0.85,
            step=0.05,
        )

        top_margin = st.sidebar.slider(
            "Top Margin",
            min_value=40,
            max_value=120,
            value=70,
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
        # CHART
        # =========================
        fig = px.timeline(
            df_view,
            x_start="Plot_Start",
            x_end="Plot_Finish",
            y="Row_Key",
            color="Color_Group",
            text="Label" if label_option != "None" else None,
            title=f"<b>{chart_title}</b>",
            hover_data={
                "Row_Key": False,
                "Display_Task": True,
                "Task": True,
                "Project": True,
                "Start_Raw": True,
                "Finish_Raw": True,
                "Plot_Start": "|%B %d, %Y",
                "Plot_Finish": "|%B %d, %Y",
                "Date_Status": True,
                "Duration_Days": True,
            },
        )

        if label_option != "None":
            fig.update_traces(
                textposition="inside",
                insidetextanchor="middle",
            )

        # Make bars thicker so they sit closer visually
        fig.update_traces(width=bar_thickness)

        # Preserve uploaded row order
        unique_rows = df_view["Row_Key"].tolist()
        tick_text = df_view["Display_Task"].tolist()

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
        # PROJECT BACKGROUND COLOURS
        # =========================
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
            proj_rows = df_view[df_view["Project"] == proj]["Row_Key"].tolist()

            if proj_rows:
                first_index = unique_rows.index(proj_rows[0])
                last_index = unique_rows.index(proj_rows[-1])

                fig.add_hrect(
                    y0=first_index - 0.5,
                    y1=last_index + 0.5,
                    fillcolor=background_colours[i % len(background_colours)],
                    layer="below",
                    line_width=0,
                )

        # Invisible scatter to force top x-axis
        fig.add_scatter(
            x=[min_date],
            y=[unique_rows[0]],
            xaxis="x2",
            mode="markers",
            marker=dict(color="rgba(0,0,0,0)"),
            showlegend=False,
            hoverinfo="skip",
        )

        # =========================
        # IMPORTANT GAP FIX
        # Plotly category axes normally keep 0.5 category padding.
        # This manual range reduces the padding above the first bar.
        # =========================
        n_rows = len(unique_rows)

        if n_rows == 1:
            y_axis_range = [0.60, -float(top_gap)]
        else:
            y_axis_range = [n_rows - 0.55, -float(top_gap)]

        fig.update_yaxes(
            autorange=False,
            range=y_axis_range,
            title="",
            categoryorder="array",
            categoryarray=unique_rows,
            tickmode="array",
            tickvals=unique_rows,
            ticktext=tick_text,
            tickfont=dict(color="black", size=13),
            fixedrange=False,
        )

        # =========================
        # COMPACT DYNAMIC HEIGHT
        # =========================
        chart_height = max(210, n_rows * int(chart_row_height) + 120)

        fig.update_layout(
            xaxis=dict(
                tickmode="array",
                tickvals=tick_vals,
                ticktext=tick_text_bottom,
                tickangle=0,
                showgrid=True,
                gridcolor="rgba(0,0,0,0.1)",
                gridwidth=1,
                fixedrange=False,
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
                fixedrange=False,
            ),
            showlegend=True,
            height=chart_height,
            margin=dict(t=int(top_margin), b=35, l=10, r=50),
            bargap=0.05,
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
            annotation_yshift=18,
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

The key fix is this part:

y_axis_range = [n_rows - 0.55, -float(top_gap)]

fig.update_yaxes(
    autorange=False,
    range=y_axis_range,
)

Your sidebar will now have “Gap Between Top Axis and First Bar”. Lower it to around 0.02–0.08 if you want the first bar even closer.
