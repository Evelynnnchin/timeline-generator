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
st.write("Upload an Excel schedule to generate a master timeline.")

# =========================
# FILE UPLOADER
# =========================
uploaded_file = st.file_uploader(
    "📂 Upload Schedule (.xlsx)",
    type=["xlsx"]
)

if uploaded_file is not None:

    try:

        # =========================
        # READ EXCEL
        # =========================
        df = pd.read_excel(uploaded_file)

        # Clean column names
        df.columns = df.columns.str.strip()

        # Check required columns
        required_cols = ["Project", "Task", "Start", "Finish"]

        missing_cols = [
            col for col in required_cols
            if col not in df.columns
        ]

        if missing_cols:
            st.error(
                f"Missing required columns: {', '.join(missing_cols)}"
            )
            st.write("Detected columns:")
            st.write(list(df.columns))
            st.stop()

        # =========================
        # DATA CLEANING
        # =========================

        df["Start"] = pd.to_datetime(
            df["Start"],
            errors="coerce"
        )

        df["Finish"] = pd.to_datetime(
            df["Finish"],
            errors="coerce"
        )

        # Remove separator rows
        df = df.dropna(
            subset=["Start", "Finish"]
        )

        # Remove blank tasks
        df = df.dropna(
            subset=["Task"]
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

        # Clean facet titles
        fig.for_each_annotation(
            lambda a: a.update(
                text=a.text.split("=")[-1],
                font=dict(size=16)
            )
        )

        # Reverse task order
        fig.update_yaxes(
            matches=None,
            autorange="reversed",
            title="",
            showticklabels=True
        )

        # =========================
        # X AXIS
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
        # HEIGHT
        # =========================

        num_projects = df["Project"].nunique()

        chart_height = max(
            800,
            num_projects * 250
        )

        # =========================
        # LAYOUT
        # =========================

        fig.update_layout(
            showlegend=False,
            height=chart_height,
            margin=dict(
                t=50,
                b=50,
                l=20,
                r=20
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
        # GRIDLINES
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
        st.error(f"Error processing file: {e}")
