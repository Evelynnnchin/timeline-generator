import streamlit as st
import pandas as pd
import plotly.express as px

# =========================
# PAGE SETUP
# =========================
st.set_page_config(
    page_title="Master Timeline Generator",
    layout="wide"
)

st.title("📊 Master Project Timeline")
st.write("Upload your schedule file (.xlsx or .csv)")

# =========================
# FILE UPLOAD
# =========================
uploaded_file = st.file_uploader(
    "📂 Upload Schedule",
    type=["xlsx", "csv"]
)

if uploaded_file is not None:

    try:

        # =========================
        # READ FILE
        # =========================
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        # Clean column names
        df.columns = df.columns.str.strip()

        # Ensure required columns exist
        required_cols = ["Project", "Task", "Start", "Finish"]

        missing_cols = [c for c in required_cols if c not in df.columns]

        if missing_cols:
            st.error(
                f"Missing required columns: {', '.join(missing_cols)}"
            )
            st.stop()

        # =========================
        # CLEAN DATA
        # =========================

        # Convert dates
        df["Start"] = pd.to_datetime(
            df["Start"],
            errors="coerce"
        )

        df["Finish"] = pd.to_datetime(
            df["Finish"],
            errors="coerce"
        )

        # Remove project header rows
        df = df.dropna(
            subset=["Start", "Finish"]
        )

        # Remove blank tasks
        df = df.dropna(
            subset=["Task"]
        )

        # Sort by project then start date
        df = df.sort_values(
            ["Project", "Start"]
        )

        # =========================
        # CREATE TIMELINE
        # =========================

        fig = px.timeline(
            df,
            x_start="Start",
            x_end="Finish",
            y="Task",
            color="Project",
            facet_row="Project",
            hover_data={
                "Project": True,
                "Task": True,
                "Start": "|%d-%b-%Y",
                "Finish": "|%d-%b-%Y"
            }
        )

        # =========================
        # FORMAT FACET TITLES
        # =========================

        fig.for_each_annotation(
            lambda a: a.update(
                text=a.text.split("=")[-1],
                font=dict(size=14)
            )
        )

        # =========================
        # Y AXIS
        # =========================

        fig.update_yaxes(
            autorange="reversed",
            matches=None,
            title=""
        )

        # =========================
        # X AXIS MONTH LABELS
        # =========================

        min_date = df["Start"].min().replace(day=1)
        max_date = df["Finish"].max()

        all_months = pd.date_range(
            start=min_date,
            end=max_date,
            freq="MS"
        )

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
        tick_text = []

        for dt in all_months:

            tick_vals.append(dt)

            if dt.month == 6:
                tick_text.append(
                    f"{month_map[dt.month]}<br><b>{dt.year}</b>"
                )
            else:
                tick_text.append(
                    month_map[dt.month]
                )

        # =========================
        # CHART HEIGHT
        # =========================

        num_projects = df["Project"].nunique()

        chart_height = max(
            700,
            num_projects * 250
        )

        # =========================
        # LAYOUT
        # =========================

        fig.update_layout(
            height=chart_height,
            showlegend=False,
            margin=dict(
                l=20,
                r=20,
                t=50,
                b=50
            ),
            xaxis=dict(
                title="",
                tickmode="array",
                tickvals=tick_vals,
                ticktext=tick_text,
                tickangle=0,
                showgrid=False
            )
        )

        # =========================
        # MONTH GRIDLINES
        # =========================

        for dt in all_months:

            if dt.month == 1:
                fig.add_vline(
                    x=dt,
                    line_width=2,
                    line_color="black",
                    layer="below"
                )
            else:
                fig.add_vline(
                    x=dt,
                    line_width=1,
                    line_color="#DDDDDD",
                    layer="below"
                )

        # =========================
        # TODAY LINE
        # =========================

        today = pd.Timestamp.today()

        fig.add_vline(
            x=today,
            line_width=3,
            line_dash="dash",
            line_color="red",
            annotation_text="📍 TODAY",
            annotation_position="top right"
        )

        # =========================
        # DISPLAY
        # =========================

        st.success(
            f"Loaded {len(df)} activities across {num_projects} projects"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    except Exception as e:
        st.error(
            f"Error processing file: {e}"
        )
