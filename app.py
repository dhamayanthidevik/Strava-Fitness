import sqlite3
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from queries import CLEANING, ANALYSIS
import base64

st.set_page_config(page_title="Fitness Data Analytics Case Study", layout="wide",page_icon="🏃")


@st.cache_data
def get_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def set_background(path):
    b64 = get_base64(path)
    st.markdown(
    f"""
    <style>
    .stApp {{
        background-image: url("data:image/jpeg;base64,{b64}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
    [data-testid="stHeader"] {{ background: rgba(0,0,0,0); }}
    [data-testid="stSidebar"] {{ background: rgba(0,0,0,0.75); }}
    .block-container {{
        background: rgba(0,0,0,0.60);
        padding: 2rem 3rem;
        border-radius: 12px;
    }}

    /* white text everywhere */
    .stApp h1, .stApp h2, .stApp h3, .stApp h4,
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li,
    [data-testid="stMetricLabel"], [data-testid="stMetricValue"],
    [data-testid="stCaptionContainer"],
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p,
    [data-testid="stToolbar"] {{
        color: #ffffff !important;
    }}

    /* code blocks (your SQL): transparent, white border, white text */
    [data-testid="stCode"], [data-testid="stCode"] pre {{
        background: transparent !important;
    }}
    [data-testid="stCode"] {{
        border: 1px solid #ffffff;
        border-radius: 8px;
    }}
    [data-testid="stCode"] pre, [data-testid="stCode"] code,
    [data-testid="stCode"] span {{
        color: #ffffff !important;
    }}

    /* small inline `code` inside text */
    [data-testid="stMarkdownContainer"] code {{
        background: rgba(255,255,255,0.15) !important;
        color: #ffffff !important;
    }}

    /* expanders */
    [data-testid="stExpander"] details {{
        background: transparent !important;
        border: 1px solid #ffffff;
        border-radius: 8px;
    }}
    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] summary p,
    [data-testid="stExpander"] summary span {{
        background: transparent !important;
        color: #ffffff !important;
    }}
    [data-testid="stExpander"] summary svg {{ fill: #ffffff; color: #ffffff; }}

    /* select box */
    [data-baseweb="select"] > div {{
        background: transparent !important;
        border: 1px solid #ffffff !important;
    }}
    [data-baseweb="select"] * {{ color: #ffffff !important; }}
    [data-baseweb="select"] svg {{ fill: #ffffff !important; }}

    /* dropdown list (opens in its own layer, so keep it dark and readable) */
    [data-baseweb="popover"] > div,
    [data-baseweb="popover"] ul {{
        background: #1b1b1b !important;
    }}
    [data-baseweb="popover"] li, [data-baseweb="popover"] li * {{
        color: #ffffff !important;
    }}

    /* white borders around charts and tables */
    [data-testid="stPlotlyChart"], [data-testid="stDataFrame"] {{
        border: 1px solid #ffffff;
        border-radius: 8px;
    }}
    [data-testid="stDataFrame"] {{
    filter: invert(1) hue-rotate(180deg);
    mix-blend-mode: screen;
    border: 1px solid #000000;
   }}
    </style>
    """,
    unsafe_allow_html=True,
)
set_background("bg1.jpg")
def style_fig(fig):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="white",
        title_font_color="white",
        legend_font_color="white",
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.15)", linecolor="white")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.15)", linecolor="white")
    return fig
@st.cache_resource
def get_conn():
    return sqlite3.connect("fitbit.db", check_same_thread=False)


def q(sql: str) -> pd.DataFrame:
    return pd.read_sql(sql, get_conn())


def strip_num(df, col):  # "1 Mon" -> "Mon" for nicer axis labels
    df = df.copy()
    df[col] = df[col].str.replace(r"^\d\s", "", regex=True)
    return df


# page = st.sidebar.radio("Go to", ["Overview", "Data & Cleaning", "SQL Analysis", "Visual Insights", "Recommendations"])
page = st.sidebar.radio("Go to", [
    "🏠 Overview",
    "🧹 Data & Cleaning",
    "🔍 SQL Analysis",
    "📊 Visual Insights",
    "💡 Recommendations",
])

# ---------------------------------------------------------------- Overview
if page == "🏠 Overview":
    st.title("Fitness Data Analytics Case Study")
    st.caption("Bellabeat (Fitbit tracker data, Apr 12 - May 12, 2016)")
    st.subheader("Business task")
    st.write("How are consumers using their smart devices, and what can that tell Bellabeat's marketing team "
             "about where to focus? Stakeholders: Urska Srsen (co-founder, CCO), Sando Mur (co-founder), "
             "and the Bellabeat marketing analytics team.")
    k = q("""SELECT COUNT(DISTINCT Id) AS users, ROUND(AVG(TotalSteps)) AS steps, ROUND(AVG(Calories)) AS cal,
                    ROUND(100.0 * AVG(SedentaryMinutes) / 1440, 1) AS sed FROM daily_clean""").iloc[0]
    c = st.columns(4)
    c[0].metric("👥 Users", int(k.users))
    c[1].metric("🏃 Avg daily steps", f"{int(k.steps):,}")
    c[2].metric("🔥 Avg daily calories", f"{int(k.cal):,}")
    c[3].metric("😴 Share of day sedentary", f"{k.sed}%")
    st.subheader("Data sources")
    st.write("Fitbit Fitness Tracker Data (Kaggle, CC0): daily activity, hourly steps / calories / intensity, "
             "sleep and weight logs. The daily calories, steps and intensities files duplicate columns already "
             "in `dailyActivity`, so they are not loaded separately. Minute-level files were reviewed but not "
             "needed for the daily and hourly questions.")
    st.warning("Limitations: only 33 users, one month, no age / gender / profession, data from 2016, "
               "and it is not specific to women.")

# ---------------------------------------------------------------- Cleaning
elif page == "🧹 Data & Cleaning":
    st.title("Data integrity and cleaning")
    st.markdown("""
**Steps applied in `build_db.py`**
1. Converted all date columns from `M/D/YYYY` text to ISO dates and split hourly timestamps into date and hour.
2. Removed 3 duplicate rows from the sleep table.
3. Merged hourly steps, calories and intensity into one table.
4. Flagged **non-wear days** (1440 sedentary minutes) and excluded them in the `daily_clean` view.
5. Left the `Fat` column as is: it is almost entirely empty, so it is not used in the analysis.
""")
    for name, sql in CLEANING.items():
        with st.expander("🧹 " +name, expanded=False):
            st.code(sql.strip(), language="sql")
            st.dataframe(q(sql), use_container_width=True)

# ---------------------------------------------------------------- SQL analysis
elif page == "🔍 SQL Analysis":
    st.title("SQL analysis")
    name = st.selectbox("Choose an analysis", list(ANALYSIS))
    sql = ANALYSIS[name]
    st.code(sql.strip(), language="sql")
    df = q(sql)
    st.dataframe(df, use_container_width=True)
    num_cols = df.select_dtypes("number").columns.tolist()
    if len(df) > 1 and num_cols:
        y = st.selectbox("Chart column", num_cols, index=0)
        st.plotly_chart(style_fig(px.bar(strip_num(df, df.columns[0]), x=df.columns[0], y=y)), use_container_width=True,theme=None)
    st.divider()
    st.subheader("Try your own query")
    custom = st.text_area("SELECT statement (tables: daily_clean, daily_activity, hourly, sleep_day, weight_log)",
                          "SELECT * FROM daily_clean LIMIT 10")
    if st.button("Run"):
        if custom.strip().lower().startswith("select"):
            try:
                st.dataframe(q(custom), use_container_width=True)
            except Exception as e:
                st.error(e)
        else:
            st.error("Only SELECT queries are allowed.")

# ---------------------------------------------------------------- Visuals
elif page == "📊 Visual Insights":
    st.title("Visual insights")
    a, b = st.columns(2)
    d = strip_num(q(ANALYSIS["1. Average activity by weekday"]), "weekday")
    a.plotly_chart(style_fig(px.bar(d, x="weekday", y="avg_steps", title="Average steps by weekday")), use_container_width=True, theme=None)
    s = strip_num(q(ANALYSIS["2. User segments by average daily steps"]), "segment")
    b.plotly_chart(style_fig(px.pie(s, names="segment", values="users", title="Users by activity segment")), use_container_width=True, theme=None)

    h = q(ANALYSIS["5. Average steps by hour of day"])
    st.plotly_chart(style_fig(px.line(h, x="Hour", y="avg_steps", markers=True, title="Average steps by hour of day")), use_container_width=True, theme=None)

    a, b = st.columns(2)
    df = q("SELECT TotalSteps, Calories FROM daily_clean")
    fig = px.scatter(df, x="TotalSteps", y="Calories", opacity=0.5, title="Steps vs calories")
    m, c0 = np.polyfit(df.TotalSteps, df.Calories, 1)
    xs = np.array([df.TotalSteps.min(), df.TotalSteps.max()])
    fig.add_scatter(x=xs, y=m * xs + c0, mode="lines", name="trend")
    a.plotly_chart(style_fig(fig), use_container_width=True)
    a.caption(f"Correlation between steps and calories: {df.TotalSteps.corr(df.Calories):.2f}")
    sl = strip_num(q(ANALYSIS["6. Sleep summary by weekday"]), "weekday")
    b.plotly_chart(style_fig(px.bar(sl, x="weekday", y=["avg_hours_asleep", "avg_hours_in_bed"], barmode="group",
                          title="Sleep by weekday (hours)")), use_container_width=True,theme=None)

    mins = q(ANALYSIS["3. Share of the day in each activity level"]).iloc[0]
    act = pd.DataFrame({"level": ["Sedentary", "Lightly active", "Fairly active", "Very active"],
                        "minutes": [mins.sedentary_min, mins.light_min, mins.fair_min, mins.very_min]})
    st.plotly_chart(style_fig(px.bar(act, x="level", y="minutes", title="Average minutes per day by activity level")), use_container_width=True, theme=None)

# ---------------------------------------------------------------- Recommendations
else:
    st.title("Findings and recommendations")
    st.subheader("Key findings")
    st.markdown("""
- Users are sedentary for about **66% of the day** (roughly 950 of 1,440 minutes), and only **7 of 33** average 10,000+ steps.
- Activity peaks around **12:00-14:00 and 17:00-19:00**; Sunday has the fewest steps, Tuesday and Saturday the most.
- Steps and calories are positively related (correlation about 0.57), and days above 10k steps burn far more calories.
- Average sleep is about 7 hours, longest on Sunday (about 7.5 h) and shortest on Thursday (about 6.7 h).
- Engagement drops over the month: **33 users wore the tracker in week 1, 27 in week 5**.
- Only **24 of 33** users track sleep, and only **8** log weight (5 of the 8 entered it manually).
""")
    st.subheader("Recommendations for Bellabeat marketing")
    st.markdown("""
1. **Target sedentary time.** Position the Bellabeat app and wearables (Leaf, Time) around gentle "move" reminders and
   small, personalised step goals by segment, rather than one-size-fits-all 10k goals.
2. **Time messages to daily rhythm.** Send nudges and challenges at lunchtime and early evening, and add a
   Sunday motivation campaign.
3. **Keep users engaged and expand feature use.** Add streaks and rewards to reduce wear drop-off, and promote
   sleep tracking and connected-scale weight logging inside the membership.
""")
    st.info("These conclusions come from 33 users over one month, so validate them with a larger, more recent dataset before acting.")
