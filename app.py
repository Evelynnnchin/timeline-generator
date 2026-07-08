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
