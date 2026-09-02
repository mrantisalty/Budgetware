import json
import math
import os
import sqlite3
import tempfile
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Budgetware",
    layout="wide",
    initial_sidebar_state="collapsed",
)
px.defaults.template = "plotly_dark"

# Motion and fixed navigation styles.
st.markdown("""
<style>
:root { --bg: #09090b; --surface: #111113; --surface-raised: #18181b; --line: #2f2f35; --ink: #f4f4f5; --muted: #a1a1aa; --red: #ef3340; --red-dark: #b91c2b; --red-wash: #321419; }
html, body, #root { background: var(--bg) !important; color: var(--ink); }
[data-testid="stApp"] { position: relative !important; height: auto !important; min-height: 100vh; overflow: visible !important; }
[data-testid="stAppViewContainer"] {
    position: relative; color: var(--ink); overflow: visible !important;
    height: auto !important; min-height: 100vh;
    background-color: var(--bg) !important;
    background-image:
        linear-gradient(rgba(5,5,7,0.58), rgba(5,5,7,0.58)),
        radial-gradient(circle at 15% 25%, rgba(239,51,64,0.36), transparent 24%),
        radial-gradient(circle at 85% 72%, rgba(146,20,31,0.38), transparent 28%),
        radial-gradient(circle at 52% 48%, rgba(89,18,25,0.28), transparent 22%),
        repeating-linear-gradient(115deg, transparent 0 84px, rgba(239,51,64,0.06) 85px 87px) !important;
    background-size: auto, 160% 160%, 160% 160%, 150% 150%, 210% 210% !important;
    background-position: center, 0% 20%, 100% 80%, 50% 50%, 0% 0% !important;
    animation: background-shift 24s ease-in-out infinite alternate;
}
[data-testid="stMain"], [data-testid="stMainBlockContainer"], [data-testid="stAppViewBlockContainer"] {
    background-color: transparent !important; overflow: visible !important;
    height: auto !important; min-height: 0 !important;
    background-image: none !important;
}
[data-testid="stMain"], [data-testid="stHeader"] { position: relative; z-index: 2; background: transparent !important; height: auto !important; min-height: 100vh; }
.ambient-background {
    position: fixed; inset: 0; z-index: 0; pointer-events: none;
    background:
        linear-gradient(rgba(5,5,7,0.5), rgba(5,5,7,0.5)),
        radial-gradient(ellipse at 12% 18%, rgba(239,51,64,0.5), transparent 30%),
        radial-gradient(ellipse at 88% 78%, rgba(172,25,39,0.44), transparent 32%),
        repeating-linear-gradient(120deg, transparent 0 96px, rgba(239,51,64,0.1) 97px 99px);
    background-size: auto, 140% 140%, 140% 140%, 180% 180%;
    background-position: center, 0% 10%, 100% 90%, 0% 0%;
    animation: surface-shift 24s ease-in-out infinite alternate;
}
[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"] { display: none; }
[data-testid="stAppViewContainer"] { padding-top: 5.25rem; }
[data-testid="stMainBlockContainer"] { padding-bottom: 4rem; }
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li, label, h1, h2, h3, h4, h5, h6 { color: var(--ink); }
[data-testid="stCaptionContainer"] { color: var(--muted); }
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .navbar-anchor) {
    position: fixed; top: 0; left: 0; right: 0; z-index: 1000;
    padding: 0.7rem max(1rem, calc((100vw - 1400px) / 2));
    background: rgba(9,9,11,0.96); border-bottom: 1px solid rgba(239,51,64,0.3);
    box-shadow: 0 8px 24px rgba(0,0,0,0.35); backdrop-filter: blur(14px);
    animation: slide-down 420ms cubic-bezier(.2,.8,.2,1) both;
}
.navbar-anchor { display: none; }
.navbar-brand {
    color: var(--ink); font-size: 1.35rem; font-weight: 800; white-space: nowrap;
}
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .navbar-anchor) [data-testid="stButton"] button {
    min-height: 2.55rem; border: 1px solid transparent; border-radius: 0.7rem;
    color: var(--ink); background: transparent;
    transition: transform 180ms ease, background 180ms ease, color 180ms ease, box-shadow 180ms ease;
}
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .navbar-anchor) [data-testid="stButton"] button:hover { color: white; background: var(--red-wash); transform: translateY(-1px); }
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .navbar-anchor) [data-testid="stButton"] button:active { transform: translateY(1px) scale(0.97); }
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .navbar-anchor) [data-testid="stButton"] button[kind="primary"], [data-testid="stButton"] button[kind="primary"] { color: white; background: var(--red); border-color: var(--red); box-shadow: 0 5px 14px rgba(239,51,64,0.22); }
.sidebar-toggle-anchor { display: none; }
.sidebar-panel-anchor { display: none; }
[data-testid="stMarkdown"]:has(.sidebar-panel-anchor),
[data-testid="stMarkdown"]:has(.sidebar-panel-anchor) p,
[data-testid="stElementContainer"]:has(.sidebar-panel-anchor),
[data-testid="stLayoutWrapper"]:has(.sidebar-panel-anchor) {
    height: 0 !important; min-height: 0 !important; margin: 0 !important; padding: 0 !important;
}
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .sidebar-toggle-anchor) {
    position: fixed; top: 5.55rem; left: 1rem; z-index: 1100; width: 7rem;
    animation: slide-down 420ms cubic-bezier(.2,.8,.2,1) both;
}
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .sidebar-toggle-anchor) [data-testid="stButton"] button {
    color: var(--ink); background: var(--surface); border-color: var(--red);
    box-shadow: 0 8px 22px rgba(0,0,0,0.38);
}
[data-testid="stButton"] button { color: var(--ink); background: var(--surface-raised); border: 1px solid var(--line); border-radius: 0.7rem; transition: transform 180ms ease, border-color 180ms ease, background 180ms ease; }
[data-testid="stButton"] button:hover { color: white; border-color: var(--red); background: var(--red-wash); transform: translateY(-1px); }
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input, [data-testid="stSelectbox"] [role="combobox"], [data-baseweb="select"] > div { color: var(--ink); background: var(--surface-raised); border-color: var(--line); }
[data-testid="stNumberInput"] button, .modebar { display: none; }
[data-testid="stForm"], [data-testid="stMetric"] { background: var(--surface); border: 1px solid var(--line); border-radius: 0.8rem; padding: 1rem; }
[data-testid="stMetricValue"] { color: white; }
[data-testid="stProgressBar"] > div > div > div { background: var(--red); }
[data-testid="stAlert"] { background: var(--red-wash); border-color: var(--red-dark); }
.utility-sidebar { background: var(--surface); border: 1px solid var(--line); border-left: 4px solid var(--red); border-radius: 0.8rem; padding: 0.5rem 1rem 1rem; animation: slide-down 360ms cubic-bezier(.2,.8,.2,1) both; }
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .sidebar-panel-anchor) {
    position: fixed; top: 5.25rem; left: 0; z-index: 1050;
    width: min(23rem, calc(100vw - 1rem)); max-height: calc(100vh - 5.75rem);
    overflow-y: auto; padding: 1rem;
    box-sizing: border-box; background: rgba(17,17,19,0.98);
    border: 2px solid var(--red); border-radius: 0 0.9rem 0.9rem 0;
    box-shadow: 0 0 0 1px rgba(239,51,64,0.18), 14px 0 36px rgba(0,0,0,0.45);
    transform: translateX(-105%); visibility: hidden; pointer-events: none;
    transition: transform 360ms cubic-bezier(.2,.8,.2,1), visibility 0s linear 360ms;
}
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .sidebar-panel-anchor) [data-testid="stElementContainer"] { width: 100%; }
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .sidebar-panel-open) {
    transform: translateX(0); visibility: visible; pointer-events: auto;
    transition: transform 360ms cubic-bezier(.2,.8,.2,1), visibility 0s linear 0s;
}
[data-testid="stForm"], [data-testid="stAlert"], [data-testid="stMetric"] { animation: slide-down 420ms cubic-bezier(.2,.8,.2,1) both; }
[data-testid="stPlotlyChart"] { animation: slide-down 560ms 90ms cubic-bezier(.2,.8,.2,1) both; }
@keyframes slide-down { from { opacity: 0; transform: translateY(-16px); } to { opacity: 1; transform: translateY(0); } }
@keyframes background-drift { 0% { transform: translate3d(-3%, -2%, 0) scale(1); } 50% { transform: translate3d(2%, 3%, 0) scale(1.08); } 100% { transform: translate3d(4%, -1%, 0) scale(1.02); } }
@keyframes background-shift { from { background-position: center, 0% 20%, 100% 80%, 50% 50%, 0% 0%; } to { background-position: center, 65% 75%, 25% 15%, 80% 35%, 100% 100%; } }
@keyframes surface-shift { from { background-position: center, 0% 10%, 100% 90%, 0% 0%; } to { background-position: center, 70% 80%, 25% 15%, 100% 100%; } }
@media (max-width: 720px) { [data-testid="stAppViewContainer"] { padding-top: 8rem; } .navbar-brand { font-size: 1.1rem; } }
</style>
""", unsafe_allow_html=True)
st.markdown("<div class='ambient-background' aria-hidden='true'>&nbsp;</div>", unsafe_allow_html=True)

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
MONTH_INDEX = {name: idx for idx, name in enumerate(MONTHS)}
DB_PATH = "budgetware_data.db"
SAVES_FOLDER = "saves"
WIB = ZoneInfo("Asia/Jakarta")


def wib_now():
    return datetime.now(WIB)


def format_idr(amount):
    return f"IDR {float(amount or 0):,.0f}"


def ensure_item_ids(items):
    normalized = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        clean = dict(item)
        clean["id"] = clean.get("id") or uuid.uuid4().hex
        normalized.append(clean)
    return normalized


def remove_item_by_id(items, item_id):
    for index, item in enumerate(items):
        if item.get("id") == item_id:
            items.pop(index)
            return True
    return False


def normalize_goal(goal, fallback_monthly_savings=0.0):
    if not isinstance(goal, dict):
        goal = {}

    normalized = dict(goal)
    normalized["name"] = normalized.get("name") or "Goal"
    normalized["target_amount"] = float(normalized.get("target_amount", 0) or 0)
    normalized["current_savings"] = float(normalized.get("current_savings", normalized.get("balance", 0)) or 0)
    normalized["balance"] = normalized["current_savings"]
    normalized["monthly_savings"] = float(normalized.get("monthly_savings", fallback_monthly_savings) or fallback_monthly_savings)
    if "deadline" not in normalized or not normalized["deadline"]:
        normalized["deadline"] = wib_now().date() + timedelta(days=365)
    return normalized

def normalize_saving(saving):
    if not isinstance(saving, dict):
        saving = {}
    return {
        "id": saving.get("id") or uuid.uuid4().hex,
        "name": saving.get("name") or "Saving",
        "amount": float(saving.get("amount", 0) or 0),
        "start_month": saving.get("start_month") or MONTHS[wib_now().month - 1],
        "start_year": int(saving.get("start_year", wib_now().year) or wib_now().year),
    }


def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS monthly_data (
            id INTEGER PRIMARY KEY,
            month TEXT,
            year INTEGER,
            income_items TEXT DEFAULT '[]',
            expense_items TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(month, year)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS recurring_savings (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            amount REAL NOT NULL DEFAULT 0,
            start_month TEXT NOT NULL,
            start_year INTEGER NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def save_monthly_data(month, year, income_items, expense_items):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO monthly_data (month, year, income_items, expense_items)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(month, year) DO UPDATE SET
            income_items = excluded.income_items,
            expense_items = excluded.expense_items,
            updated_at = CURRENT_TIMESTAMP
        """,
        (month, year, json.dumps(income_items), json.dumps(expense_items)),
    )
    conn.commit()
    conn.close()


def load_monthly_data(month, year):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT income_items, expense_items FROM monthly_data WHERE month = ? AND year = ?",
        (month, year),
    )
    result = cursor.fetchone()
    conn.close()
    if result:
        return {
            "income_items": json.loads(result[0]) if result[0] else [],
            "expense_items": json.loads(result[1]) if result[1] else [],
        }
    return {"income_items": [], "expense_items": []}


def list_monthly_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT month, year, income_items, expense_items FROM monthly_data ORDER BY year, month")
    rows = cursor.fetchall()
    conn.close()
    collected = []
    for month, year, income_items, expense_items in rows:
        collected.append(
            {
                "month": month,
                "year": year,
                "income_items": json.loads(income_items) if income_items else [],
                "expense_items": json.loads(expense_items) if expense_items else [],
            }
        )
    return collected

def list_recurring_savings():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, amount, start_month, start_year FROM recurring_savings ORDER BY name")
    rows = cursor.fetchall()
    conn.close()
    return [
        normalize_saving({"id": row[0], "name": row[1], "amount": row[2], "start_month": row[3], "start_year": row[4]})
        for row in rows
    ]

def save_recurring_saving(saving):
    normalized = normalize_saving(saving)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        INSERT INTO recurring_savings (id, name, amount, start_month, start_year)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            amount = excluded.amount,
            start_month = excluded.start_month,
            start_year = excluded.start_year
        """,
        (normalized["id"], normalized["name"], normalized["amount"], normalized["start_month"], normalized["start_year"]),
    )
    conn.commit()
    conn.close()

def delete_recurring_saving(saving_id):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM recurring_savings WHERE id = ?", (saving_id,))
    conn.commit()
    conn.close()

def saving_months_applied(saving, selected_month, selected_year):
    start_key = month_sort_key(saving["start_month"], saving["start_year"])
    selected_key = month_sort_key(selected_month, selected_year)
    if start_key > selected_key:
        return 0
    return (int(selected_year) - saving["start_year"]) * 12 + MONTH_INDEX[selected_month] - MONTH_INDEX[saving["start_month"]] + 1

def recurring_savings_total(selected_month, selected_year):
    return sum(
        saving["amount"]
        for saving in list_recurring_savings()
        if saving_months_applied(saving, selected_month, selected_year) > 0
    )


def calculate_month_totals(income_items, expense_items):
    income_total = sum(float(item.get("amount", 0) or 0) for item in income_items)
    expense_total = sum(float(item.get("amount", 0) or 0) for item in expense_items)
    net = income_total - expense_total
    return income_total, expense_total, net


def month_sort_key(month_name, year):
    return (int(year), MONTH_INDEX.get(month_name, 0))


def get_profile_balance(selected_month, selected_year):
    running_balance = 0.0
    for record in list_monthly_data():
        record_month = record["month"]
        record_year = int(record["year"])
        if month_sort_key(record_month, record_year) <= month_sort_key(selected_month, selected_year):
            _, _, monthly_net = calculate_month_totals(record["income_items"], record["expense_items"])
            running_balance += monthly_net
    return running_balance - sum(
        saving["amount"] * saving_months_applied(saving, selected_month, selected_year)
        for saving in list_recurring_savings()
    )


def ensure_saves_folder():
    if not os.path.exists(SAVES_FOLDER):
        os.makedirs(SAVES_FOLDER)


def export_data(filename=None):
    ensure_saves_folder()
    if file_name := filename:
        filepath = os.path.join(SAVES_FOLDER, file_name)
    else:
        filepath = os.path.join(SAVES_FOLDER, f"budget_backup_{wib_now().strftime('%Y%m%d_%H%M%S')}.json")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT month, year, income_items, expense_items FROM monthly_data ORDER BY year, month")
    rows = cursor.fetchall()
    conn.close()

    payload = {"exported_at": wib_now().isoformat(), "monthly_data": []}
    for month, year, income_items, expense_items in rows:
        payload["monthly_data"].append(
            {
                "month": month,
                "year": year,
                "income_items": json.loads(income_items) if income_items else [],
                "expense_items": json.loads(expense_items) if expense_items else [],
            }
        )

    if "goals" in st.session_state:
        payload["goals"] = []
        for goal in st.session_state.goals:
            goal_copy = dict(goal)
            if hasattr(goal_copy.get("deadline"), "isoformat"):
                goal_copy["deadline"] = goal_copy["deadline"].isoformat()
            payload["goals"].append(goal_copy)
    payload["recurring_savings"] = list_recurring_savings()

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return filepath


def import_data(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            payload = json.load(f)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM monthly_data")
        conn.commit()
        conn.close()

        for month_data in payload.get("monthly_data", []):
            save_monthly_data(
                month_data.get("month"),
                month_data.get("year"),
                month_data.get("income_items", []),
                month_data.get("expense_items", []),
            )

        if "goals" in payload:
            imported_goals = []
            for goal in payload["goals"]:
                goal_copy = dict(goal)
                if isinstance(goal_copy.get("deadline"), str):
                    try:
                        goal_copy["deadline"] = datetime.fromisoformat(goal_copy["deadline"]).date()
                    except ValueError:
                        pass
                imported_goals.append(normalize_goal(goal_copy))
            st.session_state.goals = imported_goals

        conn = sqlite3.connect(DB_PATH)
        conn.execute("DELETE FROM recurring_savings")
        conn.commit()
        conn.close()
        for saving in payload.get("recurring_savings", []):
            save_recurring_saving(saving)

        return True, "Data imported successfully."
    except Exception as exc:
        return False, f"Error importing data: {exc}"


init_database()

today = wib_now()
if "current_month" not in st.session_state:
    st.session_state.current_month = MONTHS[today.month - 1]
if "current_year" not in st.session_state:
    st.session_state.current_year = today.year
if "goals" not in st.session_state:
    st.session_state.goals = []
if "current_page" not in st.session_state:
    st.session_state.current_page = "Monthly"
st.session_state.setdefault("show_menu", False)
st.session_state.setdefault("editing_goal", None)

# FIXED TOP NAVBAR
with st.container():
    st.markdown("<span class='navbar-anchor'></span>", unsafe_allow_html=True)
    navbar_col1, navbar_col2 = st.columns([1, 5])

    with navbar_col1:
        st.markdown("<div class='navbar-brand'>Budgetware</div>", unsafe_allow_html=True)

    with navbar_col2:
        nav_col1, nav_col2, nav_col3, nav_col4, nav_col5 = st.columns(5)

        with nav_col1:
            if st.button("Monthly", key="nav_monthly", width="stretch"):
                st.session_state.current_page = "Monthly"
        with nav_col2:
            if st.button("Yearly", key="nav_yearly", width="stretch"):
                st.session_state.current_page = "Yearly"
        with nav_col3:
            if st.button("Lifetime", key="nav_lifetime", width="stretch"):
                st.session_state.current_page = "Lifetime"
        with nav_col4:
            if st.button("Goals", key="nav_goals", width="stretch"):
                st.session_state.current_page = "Savings Goals"
        with nav_col5:
            if st.button("Savings", key="nav_savings", width="stretch"):
                st.session_state.current_page = "Savings"

with st.container():
    st.markdown("<span class='sidebar-toggle-anchor'></span>", unsafe_allow_html=True)
    if st.button("Menu", key="hamburger_btn", help="Open sidebar", width="stretch"):
        st.session_state.show_menu = not st.session_state.get("show_menu", False)

# ALWAYS-MOUNTED SIDEBAR OVERLAY
sidebar_marker = "sidebar-panel-anchor sidebar-panel-open" if st.session_state.show_menu else "sidebar-panel-anchor"
with st.container():
    st.markdown(f"<span class='{sidebar_marker}'></span>", unsafe_allow_html=True)

    menu_col1, menu_col2 = st.columns(2)

    with menu_col1:
        st.markdown("**Month**")
        previous_month = st.session_state.current_month
        previous_year = st.session_state.current_year
        selected_month = st.selectbox(
            "Select Month",
            MONTHS,
            index=MONTH_INDEX[st.session_state.current_month],
            key="month_select",
        )

    with menu_col2:
        st.markdown("**Year**")
        year_options = [wib_now().year - 1, wib_now().year, wib_now().year + 1]
        selected_year = st.selectbox(
            "Select Year",
            year_options,
            index=year_options.index(st.session_state.current_year) if st.session_state.current_year in year_options else 1,
            key="year_select",
        )

    if selected_month != previous_month or selected_year != previous_year:
        save_monthly_data(
            previous_month,
            previous_year,
            st.session_state.get("current_income_items", []),
            st.session_state.get("current_expense_items", []),
        )
        loaded = load_monthly_data(selected_month, selected_year)
        st.session_state.current_month = selected_month
        st.session_state.current_year = selected_year
        st.session_state.current_income_items = ensure_item_ids(loaded.get("income_items", []))
        st.session_state.current_expense_items = ensure_item_ids(loaded.get("expense_items", []))
        st.rerun()

    st.markdown("---")
    st.markdown("**Backup**")

    backup_col1, backup_col2 = st.columns(2)

    with backup_col1:
        if st.button("Save backup", type="primary", width="stretch"):
            save_monthly_data(
                st.session_state.current_month,
                st.session_state.current_year,
                st.session_state.get("current_income_items", []),
                st.session_state.get("current_expense_items", []),
            )
            filepath = export_data()
            st.toast(f"Saved {os.path.basename(filepath)}")

    with backup_col2:
        uploaded_file = st.file_uploader("Import backup", type="json", key="import_backup")
        if uploaded_file is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name
            success, message = import_data(tmp_path)
            os.remove(tmp_path)
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    ensure_saves_folder()
    backups = sorted(f for f in os.listdir(SAVES_FOLDER) if f.endswith(".json"))
    if backups:
        st.markdown("**Download**")
        backup_choice = st.selectbox("Backup file", backups, key="backup_choice")
        if st.button("Download JSON", width="stretch"):
            filepath = os.path.join(SAVES_FOLDER, backup_choice)
            with open(filepath, "rb") as f:
                st.download_button(
                    label=" Download",
                    data=f.read(),
                    file_name=backup_choice,
                    mime="application/json",
                    width="stretch",
                )

st.markdown("---")

# LOAD DATA
if "current_income_items" not in st.session_state:
    loaded = load_monthly_data(st.session_state.current_month, st.session_state.current_year)
    st.session_state.current_income_items = ensure_item_ids(loaded.get("income_items", []))
if "current_expense_items" not in st.session_state:
    loaded = load_monthly_data(st.session_state.current_month, st.session_state.current_year)
    st.session_state.current_expense_items = ensure_item_ids(loaded.get("expense_items", []))

st.session_state.current_income_items = ensure_item_ids(st.session_state.current_income_items)
st.session_state.current_expense_items = ensure_item_ids(st.session_state.current_expense_items)

income_total, expense_total, monthly_balance = calculate_month_totals(
    st.session_state.current_income_items,
    st.session_state.current_expense_items,
)
profile_balance = get_profile_balance(st.session_state.current_month, st.session_state.current_year)
monthly_savings_total = recurring_savings_total(st.session_state.current_month, st.session_state.current_year)
safe_monthly_balance = monthly_balance - monthly_savings_total

save_monthly_data(
    st.session_state.current_month,
    st.session_state.current_year,
    st.session_state.current_income_items,
    st.session_state.current_expense_items,
)

# PAGE CONTENT
page = st.session_state.current_page

if page == "Monthly":
    st.subheader(f" Monthly Budget - {st.session_state.current_month} {st.session_state.current_year}")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Income")
        for item in st.session_state.current_income_items:
            st.write(f"{item['name']}: {format_idr(item.get('amount', 0))}")

        with st.form("income_form", clear_on_submit=True):
            income_name = st.text_input("Income name", placeholder="Salary, Freelance, Bonus")
            income_amount = st.number_input("Amount (IDR)", min_value=0, step=1000, format="%d")
            if st.form_submit_button("Add income", use_container_width=True):
                if income_name and income_amount > 0:
                    st.session_state.current_income_items.append({
                        "id": uuid.uuid4().hex,
                        "name": income_name,
                        "amount": float(income_amount),
                    })
                    save_monthly_data(
                        st.session_state.current_month,
                        st.session_state.current_year,
                        st.session_state.current_income_items,
                        st.session_state.current_expense_items,
                    )
                    st.rerun()
                else:
                    st.error("Please enter a name and amount greater than zero.")

        if st.session_state.current_income_items:
            with st.form("delete_income_form", clear_on_submit=True):
                income_choice = st.selectbox(
                    "Delete income item",
                    options=[item["id"] for item in st.session_state.current_income_items],
                    format_func=lambda item_id: next((f"{item['name']} - {format_idr(item['amount'])}" for item in st.session_state.current_income_items if item.get("id") == item_id), "Select item"),
                )
                if st.form_submit_button("Delete Income", use_container_width=True):
                    remove_item_by_id(st.session_state.current_income_items, income_choice)
                    save_monthly_data(
                        st.session_state.current_month,
                        st.session_state.current_year,
                        st.session_state.current_income_items,
                        st.session_state.current_expense_items,
                    )
                    st.rerun()

    with col2:
        st.markdown("### Expenses")
        for item in st.session_state.current_expense_items:
            st.write(f"{item['name']}: {format_idr(item.get('amount', 0))}")

        with st.form("expense_form", clear_on_submit=True):
            expense_name = st.text_input("Expense name", placeholder="Rent, Groceries, Bills")
            expense_amount = st.number_input("Amount (IDR)", min_value=0, step=1000, format="%d", key="expense_amount_input")
            if st.form_submit_button("Add expense", use_container_width=True):
                if expense_name and expense_amount > 0:
                    st.session_state.current_expense_items.append({
                        "id": uuid.uuid4().hex,
                        "name": expense_name,
                        "amount": float(expense_amount),
                    })
                    save_monthly_data(
                        st.session_state.current_month,
                        st.session_state.current_year,
                        st.session_state.current_income_items,
                        st.session_state.current_expense_items,
                    )
                    st.rerun()
                else:
                    st.error("Please enter a name and amount greater than zero.")

        if st.session_state.current_expense_items:
            with st.form("delete_expense_form", clear_on_submit=True):
                expense_choice = st.selectbox(
                    "Delete expense item",
                    options=[item["id"] for item in st.session_state.current_expense_items],
                    format_func=lambda item_id: next((f"{item['name']} - {format_idr(item['amount'])}" for item in st.session_state.current_expense_items if item.get("id") == item_id), "Select item"),
                )
                if st.form_submit_button("Delete Expense", use_container_width=True):
                    remove_item_by_id(st.session_state.current_expense_items, expense_choice)
                    save_monthly_data(
                        st.session_state.current_month,
                        st.session_state.current_year,
                        st.session_state.current_income_items,
                        st.session_state.current_expense_items,
                    )
                    st.rerun()

    st.markdown("---")
    metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
    metrics_col1.metric("Monthly Income", format_idr(income_total))
    metrics_col2.metric("Monthly Expenses", format_idr(expense_total))
    metrics_col3.metric("Monthly Balance", format_idr(monthly_balance))
    metrics_col4.metric("Profile Balance", format_idr(profile_balance))

    st.markdown("---")
    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        if st.session_state.current_expense_items:
            expense_df = pd.DataFrame(st.session_state.current_expense_items)
            fig = px.pie(expense_df, names="name", values="amount", hole=0.5)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Add expenses to see the chart.")
    with chart_col2:
        if st.session_state.current_income_items:
            income_df = pd.DataFrame(st.session_state.current_income_items)
            fig = px.bar(income_df, x="name", y="amount", text_auto=True)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Add income to see the chart.")

elif page == "Yearly":
    st.subheader(f"Yearly Summary - {st.session_state.current_year}")
    yearly_balance = profile_balance * 12
    y1, y2, y3 = st.columns(3)
    y1.metric("Yearly Income", format_idr(income_total * 12))
    y2.metric("Yearly Expenses", format_idr(expense_total * 12))
    y3.metric("Yearly Balance", format_idr(yearly_balance))

    st.markdown("---")
    if st.session_state.current_expense_items:
        yearly_df = pd.DataFrame({
            "Category": [item["name"] for item in st.session_state.current_expense_items],
            "Amount": [item["amount"] * 12 for item in st.session_state.current_expense_items],
        })
        fig = px.pie(yearly_df, names="Category", values="Amount", hole=0.5)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No expense data for yearly chart.")

elif page == "Lifetime":
    st.subheader("Lifetime Summary")
    lifetime_years = st.slider("Lifetime period (years)", min_value=1, max_value=50, value=10)
    lifetime_balance = profile_balance * lifetime_years
    l1, l2, l3 = st.columns(3)
    l1.metric("Lifetime Income", format_idr(income_total * 12 * lifetime_years))
    l2.metric("Lifetime Expenses", format_idr(expense_total * 12 * lifetime_years))
    l3.metric("Lifetime Balance", format_idr(lifetime_balance))

    st.markdown("---")
    years_list = list(range(1, lifetime_years + 1))
    lifetime_df = pd.DataFrame({
        "Year": years_list,
        "Accumulated Balance": [profile_balance * year for year in years_list],
    })
    fig = px.line(lifetime_df, x="Year", y="Accumulated Balance", markers=True)
    st.plotly_chart(fig, use_container_width=True)

elif page == "Savings Goals":
    st.subheader("Savings Goals")
    with st.form("add_goal_form", clear_on_submit=True):
        goal_name = st.text_input("Goal name", placeholder="Vacation, Emergency Fund, Car")
        goal_target = st.number_input("Target amount (IDR)", min_value=0, step=1000, format="%d")
        goal_saved = st.number_input("Current saved amount (IDR)", min_value=0, step=1000, format="%d")
        goal_deadline = st.date_input("Target deadline", value=wib_now().date() + timedelta(days=365))
        if st.form_submit_button("Add goal", use_container_width=True):
            if goal_name and goal_target > 0:
                st.session_state.goals.append(
                    normalize_goal(
                        {
                            "name": goal_name,
                            "target_amount": float(goal_target),
                            "current_savings": float(goal_saved),
                            "balance": float(goal_saved),
                            "deadline": goal_deadline,
                        },
                        fallback_monthly_savings=max(0.0, monthly_balance),
                    )
                )
                st.rerun()
            else:
                st.error("Please enter a goal name and target amount greater than zero.")

    st.markdown("---")
    if st.session_state.goals:
        for idx, goal in enumerate(st.session_state.goals):
            normalized_goal = normalize_goal(goal, fallback_monthly_savings=max(0.0, profile_balance))
            progress = min(normalized_goal["current_savings"] / normalized_goal["target_amount"], 1.0) if normalized_goal["target_amount"] > 0 else 0
            amount_left = max(0.0, normalized_goal["target_amount"] - normalized_goal["current_savings"])
            days_left = (normalized_goal["deadline"] - wib_now().date()).days
            months_left = max(1, days_left // 30)
            required_per_month = amount_left / months_left if amount_left > 0 else 0
            projected_monthly = max(0.0, monthly_balance)
            projected_months = math.ceil(amount_left / projected_monthly) if projected_monthly > 0 and amount_left > 0 else None
            projected_date = wib_now().date() + timedelta(days=projected_months * 30) if projected_months else None
            is_on_track = amount_left <= 0 or (projected_monthly > 0 and projected_monthly >= required_per_month)

            st.markdown(f"### {normalized_goal['name']}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Target", format_idr(normalized_goal["target_amount"]))
            c2.metric("Saved", format_idr(normalized_goal["current_savings"]))
            c3.metric("Needed / month", format_idr(required_per_month))
            st.progress(progress, text=f"{progress * 100:.1f}% complete")
            if amount_left <= 0:
                st.success("Goal reached.")
            elif projected_date:
                track_label = "On track" if is_on_track else "Behind schedule"
                st.write(f"Estimated completion: {projected_date.strftime('%B %Y')} | {track_label}")
                st.caption(f"Projection uses current monthly surplus of {format_idr(projected_monthly)}.")
            else:
                st.warning("Completion date unavailable while monthly surplus is zero or negative.")

            action_col1, action_col2 = st.columns(2)
            with action_col1:
                if st.button("Edit goal", key=f"edit_goal_{idx}", width="stretch"):
                    st.session_state.editing_goal = idx
                    st.rerun()
            with action_col2:
                if st.button("Delete goal", key=f"delete_goal_{idx}", width="stretch"):
                    st.session_state.goals.pop(idx)
                    st.session_state.editing_goal = None
                    st.rerun()

            if st.session_state.editing_goal == idx:
                with st.form(f"edit_goal_form_{idx}"):
                    edited_name = st.text_input("Goal name", value=normalized_goal["name"])
                    edit_col1, edit_col2 = st.columns(2)
                    with edit_col1:
                        edited_target = st.number_input(
                            "Target amount (IDR)",
                            min_value=0.0,
                            value=float(normalized_goal["target_amount"]),
                            step=1000.0,
                            format="%.0f",
                        )
                        edited_saved = st.number_input(
                            "Current saved amount (IDR)",
                            min_value=0.0,
                            value=float(normalized_goal["current_savings"]),
                            step=1000.0,
                            format="%.0f",
                        )
                    with edit_col2:
                        edited_deadline = st.date_input("Target deadline", value=normalized_goal["deadline"])
                    save_col, cancel_col = st.columns(2)
                    with save_col:
                        save_goal = st.form_submit_button("Save goal", type="primary", width="stretch")
                    with cancel_col:
                        cancel_edit = st.form_submit_button("Cancel", width="stretch")

                    if save_goal:
                        if edited_name and edited_target > 0:
                            st.session_state.goals[idx] = normalize_goal(
                                {
                                    **normalized_goal,
                                    "name": edited_name,
                                    "target_amount": float(edited_target),
                                    "current_savings": float(edited_saved),
                                    "balance": float(edited_saved),
                                    "deadline": edited_deadline,
                                },
                                fallback_monthly_savings=max(0.0, monthly_balance),
                            )
                            st.session_state.editing_goal = None
                            st.rerun()
                        st.error("Please enter a goal name and target amount greater than zero.")
                    if cancel_edit:
                        st.session_state.editing_goal = None
                        st.rerun()

            st.divider()
    else:
        st.info("No savings goals yet.")

elif page == "Savings":
    st.subheader("Savings")
    st.write("Set aside a fixed amount each month before deciding what money is safe to use.")

    savings_col1, savings_col2, savings_col3 = st.columns(3)
    savings_col1.metric("Profile balance", format_idr(profile_balance))
    savings_col2.metric("Saved this month", format_idr(monthly_savings_total))
    savings_col3.metric("Safe to use this month", format_idr(safe_monthly_balance))

    with st.form("add_saving_form", clear_on_submit=True):
        saving_name = st.text_input("Saving name", placeholder="Emergency fund, House deposit, Travel")
        saving_amount = st.number_input("Monthly amount (IDR)", min_value=0, step=1000, format="%d")
        saving_start_month = st.selectbox("Start month", MONTHS, index=MONTH_INDEX[st.session_state.current_month])
        saving_start_year = st.number_input(
            "Start year",
            min_value=wib_now().year - 10,
            max_value=wib_now().year + 50,
            value=st.session_state.current_year,
            step=1,
        )
        if st.form_submit_button("Add saving", width="stretch"):
            if saving_name and saving_amount > 0:
                save_recurring_saving(
                    {
                        "name": saving_name,
                        "amount": float(saving_amount),
                        "start_month": saving_start_month,
                        "start_year": int(saving_start_year),
                    }
                )
                st.toast(f"Added {saving_name}")
                st.rerun()
            else:
                st.error("Please enter a saving name and an amount greater than zero.")

    st.markdown("---")
    st.markdown("**Recurring savings**")
    recurring_savings = list_recurring_savings()
    if recurring_savings:
        for saving in recurring_savings:
            savings_item_col1, savings_item_col2, savings_item_col3 = st.columns([2, 2, 1])
            with savings_item_col1:
                st.write(saving["name"])
            with savings_item_col2:
                st.write(f"{format_idr(saving['amount'])} per month from {saving['start_month']} {saving['start_year']}")
            with savings_item_col3:
                if st.button("Delete", key=f"delete_saving_{saving['id']}", width="stretch"):
                    delete_recurring_saving(saving["id"])
                    st.rerun()
    else:
        st.info("No recurring savings yet.")

save_monthly_data(
    st.session_state.current_month,
    st.session_state.current_year,
    st.session_state.current_income_items,
    st.session_state.current_expense_items,
)
