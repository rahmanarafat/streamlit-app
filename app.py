"""
1-4-7 Revision Technique Study Tracker
---------------------------------------
A cloud-persistent study planner using the spaced repetition 1-4-7 method.
Author: Senior Full-Stack Engineer
Tech: Streamlit + Google Sheets API
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date, timedelta
import uuid
import io

# ======================================================
# PAGE CONFIGURATION
# ======================================================
st.set_page_config(
    page_title="1-4-7 Study Tracker",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ======================================================
# CUSTOM CSS — Modern Dark Mode SaaS UI
# ======================================================
CUSTOM_CSS = """
<style>
    /* Global */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: #e2e8f0;
    }
    /* Headings */
    h1, h2, h3, h4 {
        color: #f8fafc !important;
        font-family: 'Segoe UI', sans-serif;
        font-weight: 700;
    }
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #0b1220 !important;
        border-right: 1px solid #1e293b;
    }
    /* Metric Cards */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    div[data-testid="stMetricValue"] {
        color: #38bdf8 !important;
        font-size: 2rem !important;
    }
    /* Buttons */
    .stButton>button {
        background: linear-gradient(90deg, #3b82f6, #8b5cf6);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 10px 22px;
        font-weight: 600;
        transition: transform 0.15s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(139,92,246,0.4);
    }
    /* Badges */
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 6px;
    }
    .badge-r1 { background:#10b981; color:white; }
    .badge-r2 { background:#f59e0b; color:white; }
    .badge-r3 { background:#ef4444; color:white; }
    .badge-done { background:#64748b; color:white; }
    /* Topic Card */
    .topic-card {
        background: #1e293b;
        border-left: 4px solid #3b82f6;
        padding: 14px 18px;
        border-radius: 10px;
        margin-bottom: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.25);
    }
    /* Input fields */
    .stTextInput input, .stDateInput input {
        background-color: #1e293b !important;
        color: #e2e8f0 !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
    }
    /* Hide Streamlit footer */
    #MainMenu, footer {visibility: hidden;}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ======================================================
# GOOGLE SHEETS CONNECTION
# ======================================================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
SHEET_NAME = "StudyTrackerDB"
WORKSHEET_NAME = "Revisions"
HEADERS = [
    "ID", "Timestamp", "Topic", "StudyDate",
    "Rev1_Date", "Rev1_Done",
    "Rev2_Date", "Rev2_Done",
    "Rev3_Date", "Rev3_Done",
    "Notes",
]


@st.cache_resource(show_spinner=False)
def get_gspread_client():
    """Authenticate using Streamlit secrets and return gspread client."""
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Google Sheets authentication failed: {e}")
        st.stop()


def get_worksheet():
    """Open or create the worksheet; ensure headers exist."""
    client = get_gspread_client()
    try:
        sh = client.open(SHEET_NAME)
    except gspread.SpreadsheetNotFound:
        sh = client.create(SHEET_NAME)
        # Share with the service account's user if needed (manual step)
    try:
        ws = sh.worksheet(WORKSHEET_NAME)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=WORKSHEET_NAME, rows=1000, cols=20)
        ws.append_row(HEADERS)

    # Verify headers
    existing = ws.row_values(1)
    if existing != HEADERS:
        ws.clear()
        ws.append_row(HEADERS)
    return ws


# ======================================================
# DATA OPERATIONS
# ======================================================
def fetch_all_data() -> pd.DataFrame:
    """Fetch all rows from the sheet as a DataFrame."""
    try:
        ws = get_worksheet()
        records = ws.get_all_records()
        df = pd.DataFrame(records)
        if df.empty:
            return pd.DataFrame(columns=HEADERS)
        # Parse dates
        for col in ["StudyDate", "Rev1_Date", "Rev2_Date", "Rev3_Date"]:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
        for col in ["Rev1_Done", "Rev2_Done", "Rev3_Done"]:
            df[col] = df[col].astype(str).str.upper().map(
                {"TRUE": True, "FALSE": False}
            ).fillna(False)
        return df
    except Exception as e:
        st.error(f"⚠️ Failed to fetch data: {e}")
        return pd.DataFrame(columns=HEADERS)


def add_topic(topic: str, study_date: date, notes: str = ""):
    """Insert a new study topic with auto-generated 1-4-7 revision dates."""
    ws = get_worksheet()
    rev1 = study_date + timedelta(days=1)
    rev2 = study_date + timedelta(days=4)
    rev3 = study_date + timedelta(days=7)
    row = [
        str(uuid.uuid4())[:8],
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        topic.strip(),
        study_date.isoformat(),
        rev1.isoformat(), "FALSE",
        rev2.isoformat(), "FALSE",
        rev3.isoformat(), "FALSE",
        notes.strip(),
    ]
    ws.append_row(row)


def update_revision_status(row_id: str, rev_num: int, done: bool):
    """Update a specific revision's completion status."""
    ws = get_worksheet()
    cell = ws.find(row_id)
    if cell:
        # Rev1_Done=col6, Rev2_Done=col8, Rev3_Done=col10
        col_map = {1: 6, 2: 8, 3: 10}
        ws.update_cell(cell.row, col_map[rev_num], "TRUE" if done else "FALSE")


def delete_topic(row_id: str):
    """Delete a topic row by ID."""
    ws = get_worksheet()
    cell = ws.find(row_id)
    if cell:
        ws.delete_rows(cell.row)


# ======================================================
# HELPER: Build a long-form revision task list
# ======================================================
def build_task_list(df: pd.DataFrame) -> pd.DataFrame:
    """Transform wide df into long-form list of individual revision tasks."""
    if df.empty:
        return pd.DataFrame()
    rows = []
    for _, r in df.iterrows():
        for i in [1, 2, 3]:
            rows.append({
                "ID": r["ID"],
                "Topic": r["Topic"],
                "StudyDate": r["StudyDate"],
                "RevisionNum": i,
                "RevisionDate": r[f"Rev{i}_Date"],
                "Done": r[f"Rev{i}_Done"],
                "Notes": r.get("Notes", ""),
            })
    return pd.DataFrame(rows)


def badge_html(rev_num: int, done: bool) -> str:
    if done:
        return '<span class="badge badge-done">✓ Completed</span>'
    colors = {1: "badge-r1", 2: "badge-r2", 3: "badge-r3"}
    labels = {1: "Day +1", 2: "Day +4", 3: "Day +7"}
    return f'<span class="badge {colors[rev_num]}">R{rev_num} — {labels[rev_num]}</span>'


# ======================================================
# SIDEBAR — Input Form
# ======================================================
def render_sidebar():
    with st.sidebar:
        st.markdown("## 📘 Add New Topic")
        st.caption("Applies the **1-4-7 Spaced Repetition** method automatically.")
        with st.form("add_topic_form", clear_on_submit=True):
            topic = st.text_input("Topic Name", placeholder="e.g., Integration by Parts")
            study_date = st.date_input("Study Date", value=date.today())
            notes = st.text_area("Notes (optional)", placeholder="Key formulas, page refs...")
            submitted = st.form_submit_button("➕ Add Topic")
            if submitted:
                if not topic.strip():
                    st.warning("Please enter a topic name.")
                else:
                    with st.spinner("Saving to cloud..."):
                        add_topic(topic, study_date, notes)
                    st.success(f"✅ '{topic}' added! Revisions scheduled.")
                    st.cache_data.clear()

        st.markdown("---")
        st.markdown("### 🔍 Filter")
        search = st.text_input("Search topic", key="search_box")
        st.markdown("---")
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()
        return search


# ======================================================
# DASHBOARD SECTIONS
# ======================================================
def render_metrics(df: pd.DataFrame, tasks: pd.DataFrame):
    today = date.today()
    total_topics = len(df)
    due_today = len(tasks[(tasks["RevisionDate"] == today) & (~tasks["Done"])]) if not tasks.empty else 0
    completed = len(tasks[tasks["Done"]]) if not tasks.empty else 0
    pending = len(tasks[~tasks["Done"]]) if not tasks.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📚 Total Topics", total_topics)
    c2.metric("🎯 Due Today", due_today)
    c3.metric("✅ Completed", completed)
    c4.metric("⏳ Pending", pending)


def render_today_focus(tasks: pd.DataFrame):
    st.markdown("## 🎯 Today's Focus")
    today = date.today()
    if tasks.empty:
        st.info("No topics yet — add one from the sidebar to begin.")
        return

    due = tasks[(tasks["RevisionDate"] == today) & (~tasks["Done"])]
    overdue = tasks[(tasks["RevisionDate"] < today) & (~tasks["Done"])]

    if due.empty and overdue.empty:
        st.success("🎉 You're all caught up! No revisions due today.")
        return

    if not overdue.empty:
        st.warning(f"⚠️ {len(overdue)} overdue revision(s)")
        for _, t in overdue.iterrows():
            render_task_card(t, overdue=True)

    for _, t in due.iterrows():
        render_task_card(t)


def render_task_card(task, overdue=False):
    col1, col2 = st.columns([5, 1])
    with col1:
        badge = badge_html(task["RevisionNum"], task["Done"])
        overdue_tag = (
            '<span class="badge badge-r3">OVERDUE</span>' if overdue else ""
        )
        st.markdown(
            f"""
            <div class="topic-card">
                <h4 style="margin:0;color:#f8fafc;">{task['Topic']}</h4>
                <p style="margin:6px 0;color:#94a3b8;font-size:0.85rem;">
                    Studied: {task['StudyDate']} • Scheduled: {task['RevisionDate']}
                </p>
                {badge} {overdue_tag}
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        key = f"done_{task['ID']}_{task['RevisionNum']}"
        if st.checkbox("Done", value=task["Done"], key=key):
            if not task["Done"]:
                update_revision_status(task["ID"], task["RevisionNum"], True)
                st.cache_data.clear()
                st.rerun()
        else:
            if task["Done"]:
                update_revision_status(task["ID"], task["RevisionNum"], False)
                st.cache_data.clear()
                st.rerun()


def render_upcoming(tasks: pd.DataFrame):
    st.markdown("## 📅 Upcoming Schedule")
    if tasks.empty:
        return
    today = date.today()
    upcoming = tasks[(tasks["RevisionDate"] > today) & (~tasks["Done"])].sort_values("RevisionDate")
    if upcoming.empty:
        st.info("No upcoming revisions scheduled.")
        return
    for _, t in upcoming.head(15).iterrows():
        days_left = (t["RevisionDate"] - today).days
        st.markdown(
            f"""
            <div class="topic-card" style="border-left-color:#8b5cf6;">
                <strong>{t['Topic']}</strong> {badge_html(t['RevisionNum'], False)}
                <span style="float:right;color:#94a3b8;">in {days_left} day(s) — {t['RevisionDate']}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_progress_chart(tasks: pd.DataFrame):
    st.markdown("## 📊 Progress Analytics")
    if tasks.empty:
        st.info("Add topics to see analytics.")
        return
    col1, col2 = st.columns(2)
    with col1:
        status_counts = tasks["Done"].map({True: "Completed", False: "Pending"}).value_counts().reset_index()
        status_counts.columns = ["Status", "Count"]
        fig = px.pie(
            status_counts, values="Count", names="Status",
            color="Status", color_discrete_map={"Completed": "#10b981", "Pending": "#f59e0b"},
            hole=0.5, title="Revision Completion",
        )
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#e2e8f0")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        rev_counts = tasks.groupby("RevisionNum")["Done"].agg(["sum", "count"]).reset_index()
        rev_counts["Pending"] = rev_counts["count"] - rev_counts["sum"]
        rev_counts["Label"] = rev_counts["RevisionNum"].map({1: "R1 (Day+1)", 2: "R2 (Day+4)", 3: "R3 (Day+7)"})
        fig2 = px.bar(
            rev_counts, x="Label", y=["sum", "Pending"],
            title="Revision Stage Breakdown",
            labels={"value": "Count", "Label": "Stage"},
            color_discrete_sequence=["#10b981", "#ef4444"],
        )
        fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#e2e8f0")
        st.plotly_chart(fig2, use_container_width=True)


def render_all_topics(df: pd.DataFrame, search: str):
    st.markdown("## 📋 All Topics")
    if df.empty:
        return
    filtered = df.copy()
    if search:
        filtered = filtered[filtered["Topic"].str.contains(search, case=False, na=False)]
    if filtered.empty:
        st.info("No topics match your search.")
        return

    for _, r in filtered.sort_values("StudyDate", ascending=False).iterrows():
        with st.expander(f"📖 {r['Topic']} — Studied {r['StudyDate']}"):
            st.write(f"**ID:** `{r['ID']}`")
            if r.get("Notes"):
                st.write(f"**Notes:** {r['Notes']}")
            for i in [1, 2, 3]:
                done = r[f"Rev{i}_Done"]
                st.markdown(
                    f"- **Revision {i}** ({r[f'Rev{i}_Date']}) — "
                    f"{'✅ Done' if done else '⏳ Pending'}",
                    unsafe_allow_html=True,
                )
            if st.button(f"🗑️ Delete", key=f"del_{r['ID']}"):
                delete_topic(r["ID"])
                st.cache_data.clear()
                st.rerun()


def render_export(df: pd.DataFrame):
    st.markdown("## 💾 Export Data")
    if df.empty:
        return
    col1, col2 = st.columns(2)
    with col1:
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Download CSV", data=csv,
            file_name=f"study_tracker_{date.today()}.csv",
            mime="text/csv",
        )
    with col2:
        # Simple text report
        buf = io.StringIO()
        buf.write("1-4-7 STUDY TRACKER REPORT\n")
        buf.write(f"Generated: {datetime.now()}\n\n")
        for _, r in df.iterrows():
            buf.write(f"Topic: {r['Topic']} | Studied: {r['StudyDate']}\n")
            for i in [1, 2, 3]:
                s = "✓" if r[f"Rev{i}_Done"] else "✗"
                buf.write(f"  R{i} ({r[f'Rev{i}_Date']}): {s}\n")
            buf.write("\n")
        st.download_button(
            "📄 Download Report (TXT)", data=buf.getvalue(),
            file_name=f"study_report_{date.today()}.txt",
            mime="text/plain",
        )


# ======================================================
# MAIN APP
# ======================================================
def main():
    st.markdown("# 📚 1-4-7 Revision Study Tracker")
    st.caption("Master any topic with scientifically-backed spaced repetition. All data persisted to Google Sheets ☁️")

    search = render_sidebar()

    with st.spinner("Loading your data from the cloud..."):
        df = fetch_all_data()
        tasks = build_task_list(df)

    render_metrics(df, tasks)
    st.markdown("---")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["🎯 Today", "📅 Upcoming", "📊 Analytics", "📋 All Topics", "💾 Export"]
    )
    with tab1:
        render_today_focus(tasks)
    with tab2:
        render_upcoming(tasks)
    with tab3:
        render_progress_chart(tasks)
    with tab4:
        render_all_topics(df, search)
    with tab5:
        render_export(df)


if __name__ == "__main__":
    main()