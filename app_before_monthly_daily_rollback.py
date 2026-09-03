import json
import math
import os
import sqlite3
import tempfile
import uuid
from calendar import monthrange
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
@media (max-width: 720px) {
    [data-testid="stAppViewContainer"] { padding-top: 8rem; }
    .navbar-brand { font-size: 1.1rem; }
    [data-testid="stMetricValue"] { font-size: 1.2rem; line-height: 1.2; overflow-wrap: anywhere; }
    [data-testid="stMetricLabel"] { white-space: normal; overflow-wrap: anywhere; }
}
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
        clean["balance_type"] = clean.get("balance_type") or "Account balance"
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
    normalized["monthly_savings_history"] = [
        {
            "month": entry.get("month") or MONTHS[wib_now().month - 1],
            "year": int(entry.get("year", wib_now().year) or wib_now().year),
            "amount": float(entry.get("amount", 0) or 0),
        }
        for entry in normalized.get("monthly_savings_history", [])
        if isinstance(entry, dict)
    ]
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


def normalize_daily_transaction(transaction):
    if not isinstance(transaction, dict):
        transaction = {}
    return {
        "id": transaction.get("id") or uuid.uuid4().hex,
        "date": transaction.get("date") or wib_now().date().isoformat(),
        "name": transaction.get("name") or "Transaction",
        "balance_type": transaction.get("balance_type") or "Account balance",
        "income": float(transaction.get("income", 0) or 0),
        "expenses": float(transaction.get("expenses", 0) or 0),
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
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            data TEXT NOT NULL DEFAULT '[]'
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS profile_balances (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            cash_balance REAL NOT NULL DEFAULT 0,
            account_balance REAL NOT NULL DEFAULT 0
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_transactions (
            id TEXT PRIMARY KEY,
            transaction_date TEXT NOT NULL,
            name TEXT NOT NULL,
            balance_type TEXT NOT NULL,
            income REAL NOT NULL DEFAULT 0,
            expenses REAL NOT NULL DEFAULT 0
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


def save_goals(goals):
    serialized_goals = []
    for goal in goals:
        goal_copy = dict(goal)
        if hasattr(goal_copy.get("deadline"), "isoformat"):
            goal_copy["deadline"] = goal_copy["deadline"].isoformat()
        serialized_goals.append(goal_copy)

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO goals (id, data) VALUES (1, ?) ON CONFLICT(id) DO UPDATE SET data = excluded.data",
        (json.dumps(serialized_goals),),
    )
    conn.commit()
    conn.close()


def load_goals():
    conn = sqlite3.connect(DB_PATH)
    result = conn.execute("SELECT data FROM goals WHERE id = 1").fetchone()
    conn.close()
    if not result:
        return []

    goals = []
    for goal in json.loads(result[0]):
        goal_copy = dict(goal)
        if isinstance(goal_copy.get("deadline"), str):
            try:
                goal_copy["deadline"] = datetime.fromisoformat(goal_copy["deadline"]).date()
            except ValueError:
                pass
        goals.append(normalize_goal(goal_copy))
    return goals


def save_profile_balances(cash_balance, account_balance):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO profile_balances (id, cash_balance, account_balance) VALUES (1, ?, ?) ON CONFLICT(id) DO UPDATE SET cash_balance = excluded.cash_balance, account_balance = excluded.account_balance",
        (float(cash_balance), float(account_balance)),
    )
    conn.commit()
    conn.close()


def load_profile_balances():
    conn = sqlite3.connect(DB_PATH)
    result = conn.execute("SELECT cash_balance, account_balance FROM profile_balances WHERE id = 1").fetchone()
    conn.close()
    return (float(result[0]), float(result[1])) if result else None


def save_daily_transaction(transaction):
    normalized = normalize_daily_transaction(transaction)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        INSERT INTO daily_transactions (id, transaction_date, name, balance_type, income, expenses)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            transaction_date = excluded.transaction_date,
            name = excluded.name,
            balance_type = excluded.balance_type,
            income = excluded.income,
            expenses = excluded.expenses
        """,
        (normalized["id"], normalized["date"], normalized["name"], normalized["balance_type"], normalized["income"], normalized["expenses"]),
    )
    conn.commit()
    conn.close()


def list_daily_transactions():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, transaction_date, name, balance_type, income, expenses FROM daily_transactions ORDER BY transaction_date, id"
    ).fetchall()
    conn.close()
    return [
        normalize_daily_transaction({"id": row[0], "date": row[1], "name": row[2], "balance_type": row[3], "income": row[4], "expenses": row[5]})
        for row in rows
    ]


def delete_daily_transaction(transaction_id):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM daily_transactions WHERE id = ?", (transaction_id,))
    conn.commit()
    conn.close()


def transfer_balance(from_balance, to_balance, amount):
    amount = float(amount)
    if from_balance == to_balance:
        return False, "Choose two different balances."
    if amount <= 0:
        return False, "Enter an amount greater than zero."
    if from_balance == "Cash balance" and amount > st.session_state.cash_balance:
        return False, "Transfer amount is greater than your cash balance."
    if from_balance == "Account balance" and amount > st.session_state.account_balance:
        return False, "Transfer amount is greater than your account balance."

    if from_balance == "Cash balance":
        st.session_state.cash_balance -= amount
        st.session_state.account_balance += amount
    else:
        st.session_state.account_balance -= amount
        st.session_state.cash_balance += amount
    save_profile_balances(st.session_state.cash_balance, st.session_state.account_balance)
    return True, "Transfer completed."


def adjust_balance(balance_type, amount):
    if balance_type == "Cash balance":
        st.session_state.cash_balance += float(amount)
    else:
        st.session_state.account_balance += float(amount)


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


def goal_required_monthly(goal):
    normalized_goal = normalize_goal(goal)
    logged_savings = sum(entry["amount"] for entry in normalized_goal["monthly_savings_history"])
    amount_left = max(0.0, normalized_goal["target_amount"] - normalized_goal["current_savings"] - logged_savings)
    days_left = (normalized_goal["deadline"] - wib_now().date()).days
    months_left = max(1, days_left // 30)
    return amount_left / months_left if amount_left > 0 else 0.0


def goal_savings_summary(goal):
    history = normalize_goal(goal)["monthly_savings_history"]
    total_saved = sum(entry["amount"] for entry in history)
    average_monthly = total_saved / len(history) if history else 0.0
    return total_saved, average_monthly


def get_profile_balance(selected_month, selected_year):
    running_balance = 0.0
    for record in list_monthly_data():
        record_month = record["month"]
        record_year = int(record["year"])
        if month_sort_key(record_month, record_year) <= month_sort_key(selected_month, selected_year):
            _, _, monthly_net = calculate_month_totals(record["income_items"], record["expense_items"])
            running_balance += monthly_net
    return running_balance


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
    payload["profile_balances"] = {
        "cash_balance": st.session_state.get("cash_balance", 0.0),
        "account_balance": st.session_state.get("account_balance", 0.0),
    }
    payload["daily_transactions"] = list_daily_transactions()
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
            save_goals(st.session_state.goals)

        if "profile_balances" in payload:
            imported_balances = payload["profile_balances"]
            st.session_state.cash_balance = float(imported_balances.get("cash_balance", 0) or 0)
            st.session_state.account_balance = float(imported_balances.get("account_balance", 0) or 0)
            save_profile_balances(st.session_state.cash_balance, st.session_state.account_balance)

        conn = sqlite3.connect(DB_PATH)
        conn.execute("DELETE FROM daily_transactions")
        conn.commit()
        conn.close()
        for transaction in payload.get("daily_transactions", []):
            save_daily_transaction(transaction)

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
    st.session_state.goals = load_goals()
if "cash_balance" not in st.session_state or "account_balance" not in st.session_state:
    stored_balances = load_profile_balances()
    if stored_balances is None:
        st.session_state.cash_balance = 0.0
        st.session_state.account_balance = get_profile_balance(
            st.session_state.current_month,
            st.session_state.current_year,
        )
        save_profile_balances(st.session_state.cash_balance, st.session_state.account_balance)
    else:
        st.session_state.cash_balance, st.session_state.account_balance = stored_balances
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
        nav_col1, nav_col2, nav_col3, nav_col4, nav_col5, nav_col6, nav_col7 = st.columns(7)

        with nav_col1:
            if st.button("Overview", key="nav_overview", width="stretch"):
                st.session_state.current_page = "Overview"
        with nav_col2:
            if st.button("Monthly", key="nav_monthly", width="stretch"):
                st.session_state.current_page = "Monthly"
        with nav_col3:
            if st.button("Daily", key="nav_daily", width="stretch"):
                st.session_state.current_page = "Daily"
        with nav_col4:
            if st.button("Yearly", key="nav_yearly", width="stretch"):
                st.session_state.current_page = "Yearly"
        with nav_col5:
            if st.button("Lifetime", key="nav_lifetime", width="stretch"):
                st.session_state.current_page = "Lifetime"
        with nav_col6:
            if st.button("Goals", key="nav_goals", width="stretch"):
                st.session_state.current_page = "Savings Goals"
        with nav_col7:
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
profile_balance = st.session_state.cash_balance + st.session_state.account_balance
monthly_savings_total = recurring_savings_total(st.session_state.current_month, st.session_state.current_year)
safe_monthly_balance = profile_balance - monthly_savings_total

save_monthly_data(
    st.session_state.current_month,
    st.session_state.current_year,
    st.session_state.current_income_items,
    st.session_state.current_expense_items,
)

# PAGE CONTENT
page = st.session_state.current_page

if page == "Overview":
    st.subheader("Overview")
    overview_records = [
        record for record in list_monthly_data()
        if record["income_items"] or record["expense_items"]
    ]
    overview_records.sort(key=lambda record: month_sort_key(record["month"], record["year"]))
    all_time_income = sum(
        calculate_month_totals(record["income_items"], record["expense_items"])[0]
        for record in overview_records
    )
    all_time_expenses = sum(
        calculate_month_totals(record["income_items"], record["expense_items"])[1]
        for record in overview_records
    )

    overview_metric_col1, overview_metric_col2, overview_metric_col3 = st.columns(3)
    overview_metric_col4, overview_metric_col5 = st.columns(2)
    overview_metric_col1.metric("Current profile balance", format_idr(profile_balance))
    overview_metric_col2.metric("Monthly income rate", format_idr(income_total))
    overview_metric_col3.metric("Monthly expenses rate", format_idr(expense_total))
    overview_metric_col4.metric("All-time income", format_idr(all_time_income))
    overview_metric_col5.metric("All-time expenses", format_idr(all_time_expenses))

    balance_col1, balance_col2, balance_col3 = st.columns(3)
    balance_col1.metric("Cash balance", format_idr(st.session_state.cash_balance))
    balance_col2.metric("Account balance", format_idr(st.session_state.account_balance))
    balance_col3.metric("Profile balance", format_idr(profile_balance))
    with st.form("profile_balances_form"):
        st.markdown("**Update balances**")
        balance_input_col1, balance_input_col2 = st.columns(2)
        with balance_input_col1:
            cash_balance_input = st.number_input("Cash balance (IDR)", min_value=0.0, value=float(st.session_state.cash_balance), step=1000.0, format="%.0f")
        with balance_input_col2:
            account_balance_input = st.number_input("Account balance (IDR)", min_value=0.0, value=float(st.session_state.account_balance), step=1000.0, format="%.0f")
        if st.form_submit_button("Save balances", width="stretch"):
            st.session_state.cash_balance = float(cash_balance_input)
            st.session_state.account_balance = float(account_balance_input)
            save_profile_balances(cash_balance_input, account_balance_input)
            st.rerun()

    with st.form("transfer_balance_form"):
        st.markdown("**Transfer between balances**")
        transfer_col1, transfer_col2, transfer_col3 = st.columns(3)
        with transfer_col1:
            transfer_from = st.selectbox("From", ["Cash balance", "Account balance"])
        with transfer_col2:
            transfer_to = st.selectbox("To", ["Account balance", "Cash balance"])
        with transfer_col3:
            transfer_amount = st.number_input("Amount (IDR)", min_value=0.0, step=1000.0, format="%.0f")
        if st.form_submit_button("Transfer", width="stretch"):
            transfer_success, transfer_message = transfer_balance(transfer_from, transfer_to, transfer_amount)
            if transfer_success:
                st.rerun()
            else:
                st.error(transfer_message)

    total_days = sum(monthrange(int(record["year"]), MONTH_INDEX[record["month"]] + 1)[1] for record in overview_records)
    average_daily_income = all_time_income / total_days if total_days else 0.0
    average_daily_expenses = all_time_expenses / total_days if total_days else 0.0
    daily_metric_col1, daily_metric_col2 = st.columns(2)
    daily_metric_col1.metric("Average daily income", format_idr(average_daily_income))
    daily_metric_col2.metric("Average daily expenses", format_idr(average_daily_expenses))

    monthly_summary = []
    for record in overview_records:
        record_income, record_expenses, _ = calculate_month_totals(record["income_items"], record["expense_items"])
        days_in_month = monthrange(int(record["year"]), MONTH_INDEX[record["month"]] + 1)[1]
        monthly_summary.append(
            {
                "month_key": month_sort_key(record["month"], record["year"]),
                "month": f"{record['month'][:3]} {record['year']}",
                "year": int(record["year"]),
                "Income": record_income,
                "Expenses": record_expenses,
                "Daily income": record_income / days_in_month,
                "Daily expenses": record_expenses / days_in_month,
            }
        )
    monthly_summary_df = pd.DataFrame(monthly_summary)

    if not monthly_summary_df.empty:
        monthly_chart_col1, monthly_chart_col2 = st.columns(2)
        with monthly_chart_col1:
            monthly_income_fig = px.line(
                monthly_summary_df,
                x="month",
                y="Income",
                markers=True,
                title="Monthly income",
                labels={"month": "Month", "Income": "Income (IDR)"},
            )
            monthly_income_fig.update_layout(height=300, margin=dict(t=55, b=35, l=45, r=20))
            st.plotly_chart(monthly_income_fig, width="stretch")
        with monthly_chart_col2:
            monthly_expenses_fig = px.line(
                monthly_summary_df,
                x="month",
                y="Expenses",
                markers=True,
                title="Monthly expenses",
                labels={"month": "Month", "Expenses": "Expenses (IDR)"},
            )
            monthly_expenses_fig.update_layout(height=300, margin=dict(t=55, b=35, l=45, r=20))
            st.plotly_chart(monthly_expenses_fig, width="stretch")

        daily_chart_col1, daily_chart_col2 = st.columns(2)
        with daily_chart_col1:
            daily_income_fig = px.line(
                monthly_summary_df,
                x="month",
                y="Daily income",
                markers=True,
                title="Daily income rate",
                labels={"month": "Month", "Daily income": "Income per day (IDR)"},
            )
            daily_income_fig.update_layout(height=300, margin=dict(t=55, b=35, l=45, r=20))
            st.plotly_chart(daily_income_fig, width="stretch")
        with daily_chart_col2:
            daily_expenses_fig = px.line(
                monthly_summary_df,
                x="month",
                y="Daily expenses",
                markers=True,
                title="Daily expenses rate",
                labels={"month": "Month", "Daily expenses": "Expenses per day (IDR)"},
            )
            daily_expenses_fig.update_layout(height=300, margin=dict(t=55, b=35, l=45, r=20))
            st.plotly_chart(daily_expenses_fig, width="stretch")

        yearly_summary_df = monthly_summary_df.groupby("year", as_index=False)[["Income", "Expenses"]].sum()
        yearly_chart_col1, yearly_chart_col2 = st.columns(2)
        with yearly_chart_col1:
            yearly_income_fig = px.line(
                yearly_summary_df,
                x="year",
                y="Income",
                markers=True,
                title="Yearly income",
                labels={"year": "Year", "Income": "Income (IDR)"},
            )
            st.plotly_chart(yearly_income_fig, width="stretch")
        with yearly_chart_col2:
            yearly_expenses_fig = px.line(
                yearly_summary_df,
                x="year",
                y="Expenses",
                markers=True,
                title="Yearly expenses",
                labels={"year": "Year", "Expenses": "Expenses (IDR)"},
            )
            st.plotly_chart(yearly_expenses_fig, width="stretch")

    st.markdown("**Daily transactions**")
    daily_transactions = list_daily_transactions()
    if daily_transactions:
        daily_table = pd.DataFrame(daily_transactions)
        daily_table["total"] = daily_table["income"] - daily_table["expenses"]
        daily_table = daily_table[["date", "name", "balance_type", "income", "expenses", "total"]]
        daily_table = daily_table.rename(
            columns={
                "date": "Date",
                "name": "Name",
                "balance_type": "Account type",
                "income": "Income",
                "expenses": "Expenses",
                "total": "Total",
            }
        )
        st.dataframe(daily_table, hide_index=True, height=360, width="stretch")
    else:
        st.info("No daily income or expenses have been added yet.")

    if overview_records:
        for record_index, record in enumerate(overview_records):
            st.markdown(f"### {record['month']} {record['year']}")
            overview_col1, overview_col2 = st.columns(2)
            with overview_col1:
                st.markdown("**Income**")
                if record["income_items"]:
                    income_table = pd.DataFrame(record["income_items"])
                    income_table["balance_type"] = income_table.get("balance_type", "Account balance")
                    income_table = income_table[["name", "amount", "balance_type"]]
                    income_table = income_table.rename(columns={"name": "Income", "amount": "Amount (IDR)", "balance_type": "Added to"})
                    st.dataframe(income_table, hide_index=True, width="stretch")
                else:
                    st.info("No income added.")
            with overview_col2:
                st.markdown("**Expenses**")
                if record["expense_items"]:
                    expense_table = pd.DataFrame(record["expense_items"])
                    expense_table["balance_type"] = expense_table.get("balance_type", "Account balance")
                    expense_table = expense_table[["name", "amount", "balance_type"]]
                    expense_table = expense_table.rename(columns={"name": "Expense", "amount": "Amount (IDR)", "balance_type": "Taken from"})
                    st.dataframe(expense_table, hide_index=True, width="stretch")
                else:
                    st.info("No expenses added.")

            chart_col1, chart_col2 = st.columns(2)
            with chart_col1:
                if record["income_items"]:
                    income_df = pd.DataFrame(record["income_items"])
                    income_fig = px.bar(income_df, x="name", y="amount", text_auto=True)
                    st.plotly_chart(income_fig, width="stretch")
            with chart_col2:
                if record["expense_items"]:
                    expense_df = pd.DataFrame(record["expense_items"])
                    expense_fig = px.pie(expense_df, names="name", values="amount", hole=0.5)
                    st.plotly_chart(expense_fig, width="stretch")

            if record_index < len(overview_records) - 1:
                st.divider()
    else:
        st.info("No monthly income or expenses have been added yet.")

elif page == "Monthly":
    st.subheader(f"Monthly Summary - {st.session_state.current_month} {st.session_state.current_year}")
    monthly_daily_transactions = [
        transaction for transaction in list_daily_transactions()
        if datetime.fromisoformat(transaction["date"]).month == MONTH_INDEX[st.session_state.current_month] + 1
        and datetime.fromisoformat(transaction["date"]).year == st.session_state.current_year
    ]
    monthly_income_items = [
        {"name": transaction["name"], "amount": transaction["income"], "balance_type": transaction["balance_type"]}
        for transaction in monthly_daily_transactions if transaction["income"] > 0
    ]
    monthly_expense_items = [
        {"name": transaction["name"], "amount": transaction["expenses"], "balance_type": transaction["balance_type"]}
        for transaction in monthly_daily_transactions if transaction["expenses"] > 0
    ]
    monthly_income_total = sum(item["amount"] for item in monthly_income_items)
    monthly_expense_total = sum(item["amount"] for item in monthly_expense_items)
    monthly_summary_col1, monthly_summary_col2, monthly_summary_col3 = st.columns(3)
    monthly_summary_col1.metric("Monthly income", format_idr(monthly_income_total))
    monthly_summary_col2.metric("Monthly expenses", format_idr(monthly_expense_total))
    monthly_summary_col3.metric("Monthly balance", format_idr(monthly_income_total - monthly_expense_total))

    st.markdown("---")
    monthly_chart_col1, monthly_chart_col2 = st.columns(2)
    with monthly_chart_col1:
        if monthly_income_items:
            monthly_income_df = pd.DataFrame(monthly_income_items)
            monthly_income_fig = px.bar(monthly_income_df, x="name", y="amount", text_auto=True, title="Monthly income")
            st.plotly_chart(monthly_income_fig, width="stretch")
        else:
            st.info("No income added for this month.")
    with monthly_chart_col2:
        if monthly_expense_items:
            monthly_expense_df = pd.DataFrame(monthly_expense_items)
            monthly_expense_fig = px.pie(monthly_expense_df, names="name", values="amount", hole=0.5, title="Monthly expenses")
            st.plotly_chart(monthly_expense_fig, width="stretch")
        else:
            st.info("No expenses added for this month.")

    st.markdown("---")
    st.markdown("**Monthly entries**")
    monthly_income_table, monthly_expense_table = st.columns(2)
    with monthly_income_table:
        if monthly_income_items:
            st.dataframe(
            pd.DataFrame(monthly_income_items)[["name", "amount", "balance_type"]].rename(
                    columns={"name": "Name", "amount": "Amount (IDR)", "balance_type": "Added to"}
                ),
                hide_index=True,
                width="stretch",
            )
        else:
            st.info("No income added.")
    with monthly_expense_table:
        if monthly_expense_items:
            st.dataframe(
            pd.DataFrame(monthly_expense_items)[["name", "amount", "balance_type"]].rename(
                    columns={"name": "Name", "amount": "Amount (IDR)", "balance_type": "Taken from"}
                ),
                hide_index=True,
                width="stretch",
            )
        else:
            st.info("No expenses added.")

elif page == "Daily":
    st.subheader("Daily")
    daily_transactions = list_daily_transactions()
    selected_daily_date = st.date_input("Date", value=wib_now().date(), key="daily_date_filter")
    selected_daily_transactions = [
        transaction for transaction in daily_transactions
        if transaction["date"] == selected_daily_date.isoformat()
    ]
    selected_daily_income = sum(transaction["income"] for transaction in selected_daily_transactions)
    selected_daily_expenses = sum(transaction["expenses"] for transaction in selected_daily_transactions)
    daily_summary_col1, daily_summary_col2, daily_summary_col3 = st.columns(3)
    daily_summary_col1.metric("Daily income", format_idr(selected_daily_income))
    daily_summary_col2.metric("Daily expenses", format_idr(selected_daily_expenses))
    daily_summary_col3.metric("Daily total", format_idr(selected_daily_income - selected_daily_expenses))

    with st.form("add_daily_transaction_form", clear_on_submit=True):
        st.markdown("**Add daily transaction**")
        daily_name = st.text_input("Name", placeholder="Salary, groceries, transport")
        daily_balance_type = st.selectbox("Account type", ["Account balance", "Cash balance"])
        daily_income = st.number_input("Income (IDR)", min_value=0.0, step=1000.0, format="%.0f")
        daily_expenses = st.number_input("Expenses (IDR)", min_value=0.0, step=1000.0, format="%.0f")
        if st.form_submit_button("Add transaction", width="stretch"):
            if daily_name and (daily_income > 0 or daily_expenses > 0):
                transaction = normalize_daily_transaction(
                    {
                        "date": selected_daily_date.isoformat(),
                        "name": daily_name,
                        "balance_type": daily_balance_type,
                        "income": daily_income,
                        "expenses": daily_expenses,
                    }
                )
                save_daily_transaction(transaction)
                adjust_balance(daily_balance_type, daily_income - daily_expenses)
                save_profile_balances(st.session_state.cash_balance, st.session_state.account_balance)
                st.rerun()
            else:
                st.error("Enter a name and an income or expense amount greater than zero.")

    st.markdown("---")
    st.markdown("**Daily history**")
    if daily_transactions:
        daily_history_table = pd.DataFrame(daily_transactions)
        daily_history_table["total"] = daily_history_table["income"] - daily_history_table["expenses"]
        st.dataframe(
            daily_history_table[["date", "name", "balance_type", "income", "expenses", "total"]].rename(
                columns={"date": "Date", "name": "Name", "balance_type": "Account type", "income": "Income", "expenses": "Expenses", "total": "Total"}
            ),
            hide_index=True,
            height=360,
            width="stretch",
        )
        daily_delete_choice = st.selectbox(
            "Delete transaction",
            options=[transaction["id"] for transaction in daily_transactions],
            format_func=lambda transaction_id: next(
                f"{transaction['date']} - {transaction['name']} ({format_idr(transaction['income'] - transaction['expenses'])})"
                for transaction in daily_transactions if transaction["id"] == transaction_id
            ),
        )
        if st.button("Delete transaction", width="stretch"):
            selected_transaction = next(transaction for transaction in daily_transactions if transaction["id"] == daily_delete_choice)
            adjust_balance(selected_transaction["balance_type"], selected_transaction["expenses"] - selected_transaction["income"])
            save_profile_balances(st.session_state.cash_balance, st.session_state.account_balance)
            delete_daily_transaction(daily_delete_choice)
            st.rerun()
    else:
        st.info("No daily transactions yet. Empty days count as IDR 0 income and IDR 0 expenses.")

elif page == "Legacy Monthly":
    st.subheader(f" Monthly Budget - {st.session_state.current_month} {st.session_state.current_year}")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Income")
        for item in st.session_state.current_income_items:
            st.write(f"{item['name']}: {format_idr(item.get('amount', 0))}")

        with st.form("income_form", clear_on_submit=True):
            income_name = st.text_input("Income name", placeholder="Salary, Freelance, Bonus")
            income_amount = st.number_input("Amount (IDR)", min_value=0, step=1000, format="%d")
            income_balance_type = st.selectbox("Add to", ["Account balance", "Cash balance"], key="income_balance_type")
            if st.form_submit_button("Add income", use_container_width=True):
                if income_name and income_amount > 0:
                    st.session_state.current_income_items.append({
                        "id": uuid.uuid4().hex,
                        "name": income_name,
                        "amount": float(income_amount),
                        "balance_type": income_balance_type,
                    })
                    adjust_balance(income_balance_type, income_amount)
                    save_profile_balances(st.session_state.cash_balance, st.session_state.account_balance)
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
                    selected_income = next(item for item in st.session_state.current_income_items if item.get("id") == income_choice)
                    remove_item_by_id(st.session_state.current_income_items, income_choice)
                    adjust_balance(selected_income.get("balance_type", "Account balance"), -selected_income.get("amount", 0))
                    save_profile_balances(st.session_state.cash_balance, st.session_state.account_balance)
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
            expense_balance_type = st.selectbox("Take from", ["Account balance", "Cash balance"], key="expense_balance_type")
            if st.form_submit_button("Add expense", use_container_width=True):
                if expense_name and expense_amount > 0:
                    st.session_state.current_expense_items.append({
                        "id": uuid.uuid4().hex,
                        "name": expense_name,
                        "amount": float(expense_amount),
                        "balance_type": expense_balance_type,
                    })
                    adjust_balance(expense_balance_type, -expense_amount)
                    save_profile_balances(st.session_state.cash_balance, st.session_state.account_balance)
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
                    selected_expense = next(item for item in st.session_state.current_expense_items if item.get("id") == expense_choice)
                    remove_item_by_id(st.session_state.current_expense_items, expense_choice)
                    adjust_balance(selected_expense.get("balance_type", "Account balance"), selected_expense.get("amount", 0))
                    save_profile_balances(st.session_state.cash_balance, st.session_state.account_balance)
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
                save_goals(st.session_state.goals)
                st.rerun()
            else:
                st.error("Please enter a goal name and target amount greater than zero.")

    st.markdown("---")
    if st.session_state.goals:
        for idx, goal in enumerate(st.session_state.goals):
            normalized_goal = normalize_goal(goal, fallback_monthly_savings=max(0.0, profile_balance))
            total_logged, average_monthly = goal_savings_summary(normalized_goal)
            total_saved = normalized_goal["current_savings"] + total_logged
            progress = min(total_saved / normalized_goal["target_amount"], 1.0) if normalized_goal["target_amount"] > 0 else 0
            amount_left = max(0.0, normalized_goal["target_amount"] - total_saved)
            days_left = (normalized_goal["deadline"] - wib_now().date()).days
            months_left = max(1, days_left // 30)
            ideal_monthly = amount_left / months_left if amount_left > 0 else 0.0
            projected_monthly = average_monthly
            projected_months = math.ceil(amount_left / projected_monthly) if projected_monthly > 0 and amount_left > 0 else None
            projected_date = wib_now().date() + timedelta(days=projected_months * 30) if projected_months else None
            ideal_projected_date = normalized_goal["deadline"] if ideal_monthly > 0 else None
            is_on_track = amount_left <= 0 or (projected_monthly > 0 and projected_monthly >= ideal_monthly)

            st.markdown(f"### {normalized_goal['name']}")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Target", format_idr(normalized_goal["target_amount"]))
            c2.metric("Total saved", format_idr(total_saved))
            c3.metric("Average / month", format_idr(average_monthly))
            c4.metric("Ideal savings / month", format_idr(ideal_monthly))
            st.progress(progress, text=f"{progress * 100:.1f}% complete")

            with st.form(f"goal_savings_form_{idx}", clear_on_submit=True):
                st.markdown("**Monthly savings**")
                history_col1, history_col2, history_col3 = st.columns(3)
                with history_col1:
                    logged_month = st.selectbox("Month", MONTHS, index=MONTH_INDEX[st.session_state.current_month], key=f"goal_saving_month_{idx}")
                with history_col2:
                    logged_year = st.number_input("Year", min_value=wib_now().year - 10, max_value=wib_now().year + 50, value=st.session_state.current_year, step=1, key=f"goal_saving_year_{idx}")
                with history_col3:
                    logged_amount = st.number_input("Amount (IDR)", min_value=0, step=1000, format="%d", key=f"goal_saving_amount_{idx}")
                if st.form_submit_button("Add monthly saving", width="stretch"):
                    normalized_goal["monthly_savings_history"] = [
                        entry for entry in normalized_goal["monthly_savings_history"]
                        if not (entry["month"] == logged_month and entry["year"] == int(logged_year))
                    ]
                    normalized_goal["monthly_savings_history"].append(
                        {"month": logged_month, "year": int(logged_year), "amount": float(logged_amount)}
                    )
                    st.session_state.goals[idx] = normalized_goal
                    save_goals(st.session_state.goals)
                    st.rerun()

            if normalized_goal["monthly_savings_history"]:
                st.caption(f"Logged savings: {format_idr(total_logged)} total | {format_idr(average_monthly)} average per month")
                st.markdown("**Savings history**")
                history_entries = sorted(
                    enumerate(normalized_goal["monthly_savings_history"]),
                    key=lambda item: (item[1]["year"], MONTH_INDEX.get(item[1]["month"], 0)),
                    reverse=True,
                )
                for history_index, entry in history_entries:
                    with st.form(f"edit_monthly_saving_form_{idx}_{history_index}"):
                        entry_col1, entry_col2, entry_col3, entry_col4 = st.columns([2, 1, 2, 1])
                        with entry_col1:
                            edited_month = st.selectbox(
                                "Month",
                                MONTHS,
                                index=MONTH_INDEX.get(entry["month"], 0),
                                key=f"history_month_{idx}_{history_index}",
                            )
                        with entry_col2:
                            edited_year = st.number_input(
                                "Year",
                                min_value=wib_now().year - 10,
                                max_value=wib_now().year + 50,
                                value=int(entry["year"]),
                                step=1,
                                key=f"history_year_{idx}_{history_index}",
                            )
                        with entry_col3:
                            edited_amount = st.number_input(
                                "Amount (IDR)",
                                min_value=0,
                                value=int(entry["amount"]),
                                step=1000,
                                format="%d",
                                key=f"history_amount_{idx}_{history_index}",
                            )
                        with entry_col4:
                            save_entry = st.form_submit_button("Save", width="stretch")
                            delete_entry = st.form_submit_button("Delete", width="stretch")

                        if save_entry:
                            normalized_goal["monthly_savings_history"][history_index] = {
                                "month": edited_month,
                                "year": int(edited_year),
                                "amount": float(edited_amount),
                            }
                            st.session_state.goals[idx] = normalized_goal
                            save_goals(st.session_state.goals)
                            st.rerun()
                        if delete_entry:
                            normalized_goal["monthly_savings_history"].pop(history_index)
                            st.session_state.goals[idx] = normalized_goal
                            save_goals(st.session_state.goals)
                            st.rerun()
            else:
                st.caption("No monthly savings logged yet.")
            if amount_left <= 0:
                st.success("Goal reached.")
            elif projected_date:
                track_label = "On track" if is_on_track else "Behind schedule"
                st.write(f"Estimated completion: {projected_date.strftime('%B %Y')} | {track_label}")
                st.caption(f"Projection uses your average logged saving of {format_idr(projected_monthly)} per month.")
            else:
                st.warning("Completion date unavailable until you log a monthly saving amount.")
            if ideal_projected_date:
                st.write(f"Ideal estimated completion: {ideal_projected_date.strftime('%B %Y')}")

            action_col1, action_col2 = st.columns(2)
            with action_col1:
                if st.button("Edit goal", key=f"edit_goal_{idx}", width="stretch"):
                    st.session_state.editing_goal = idx
                    st.rerun()
            with action_col2:
                if st.button("Delete goal", key=f"delete_goal_{idx}", width="stretch"):
                    st.session_state.goals.pop(idx)
                    save_goals(st.session_state.goals)
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
                            save_goals(st.session_state.goals)
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

    savings_history = []
    recurring_savings = list_recurring_savings()
    should_save_monthly = sum(goal_required_monthly(goal) for goal in st.session_state.goals)
    for record in list_monthly_data():
        record_month = record["month"]
        record_year = int(record["year"])
        actual_saved = sum(
            saving["amount"]
            for saving in recurring_savings
            if saving_months_applied(saving, record_month, record_year) > 0
        )
        savings_history.append(
            {
                "month_key": month_sort_key(record_month, record_year),
                "month": f"{record_month[:3]} {record_year}",
                "Saved": actual_saved,
                "Should save": should_save_monthly,
            }
        )
    savings_history.sort(key=lambda item: item["month_key"])

    st.markdown("---")
    st.markdown("**Saved vs. should save**")
    st.caption("Should save is the monthly amount needed to reach all savings goals by their deadlines.")
    savings_chart_df = pd.DataFrame(savings_history).melt(
        id_vars=["month_key", "month"],
        value_vars=["Saved", "Should save"],
        var_name="Measure",
        value_name="Amount",
    )
    savings_fig = px.line(
        savings_chart_df,
        x="month",
        y="Amount",
        color="Measure",
        markers=True,
        labels={"month": "Month", "Amount": "Amount (IDR)", "Measure": ""},
        color_discrete_map={"Saved": "#ef3340", "Should save": "#f4f4f5"},
    )
    savings_fig.update_layout(legend_title_text="", hovermode="x unified")
    st.plotly_chart(savings_fig, width="stretch")

    with st.form("add_saving_form", clear_on_submit=True):
        saving_name = st.text_input("Saving name", placeholder="Emergency fund, House deposit, Travel")
        saving_amount = st.number_input("Monthly amount (IDR)", min_value=0, step=1000, format="%d")
        if st.form_submit_button("Add saving", width="stretch"):
            if saving_name and saving_amount > 0:
                save_recurring_saving(
                    {
                        "name": saving_name,
                        "amount": float(saving_amount),
                        "start_month": st.session_state.current_month,
                        "start_year": st.session_state.current_year,
                    }
                )
                st.toast(f"Added {saving_name}")
                st.rerun()
            else:
                st.error("Please enter a saving name and an amount greater than zero.")

    st.markdown("---")
    st.markdown("**Recurring savings**")
    if recurring_savings:
        for saving in recurring_savings:
            savings_item_col1, savings_item_col2, savings_item_col3 = st.columns([2, 2, 1])
            with savings_item_col1:
                st.write(saving["name"])
            with savings_item_col2:
                st.write(f"{format_idr(saving['amount'])} per month")
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
