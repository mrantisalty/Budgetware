import json
import os
import sqlite3
import tempfile
import uuid
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Budgetware",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS for sticky navbar
st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    padding-top: 0;
}
.navbar-container {
    position: sticky;
    top: 0;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 1rem;
    border-radius: 0 0 15px 15px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    z-index: 999;
    margin-bottom: 2rem;
}
.navbar-content {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
}
.navbar-brand {
    font-size: 1.5rem;
    font-weight: bold;
    color: white;
}
.navbar-nav {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
}
.nav-button {
    background: rgba(255,255,255,0.2);
    color: white;
    border: 2px solid white;
    padding: 0.5rem 1rem;
    border-radius: 25px;
    cursor: pointer;
    transition: all 0.3s ease;
    font-weight: 500;
}
.nav-button:hover {
    background: white;
    color: #667eea;
}
.nav-button.active {
    background: white;
    color: #667eea;
}
.hamburger-btn {
    background: rgba(255,255,255,0.2);
    color: white;
    border: 2px solid white;
    padding: 0.5rem 1rem;
    border-radius: 25px;
    cursor: pointer;
    font-size: 1.2rem;
    transition: all 0.3s ease;
}
.hamburger-btn:hover {
    background: white;
    color: #667eea;
}
</style>
""", unsafe_allow_html=True)

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
MONTH_INDEX = {name: idx for idx, name in enumerate(MONTHS)}
DB_PATH = "budgetware_data.db"
SAVES_FOLDER = "saves"


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
        normalized["deadline"] = datetime.now().date() + timedelta(days=365)
    return normalized


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
    return running_balance


def ensure_saves_folder():
    if not os.path.exists(SAVES_FOLDER):
        os.makedirs(SAVES_FOLDER)


def export_data(filename=None):
    ensure_saves_folder()
    if file_name := filename:
        filepath = os.path.join(SAVES_FOLDER, file_name)
    else:
        filepath = os.path.join(SAVES_FOLDER, f"budget_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT month, year, income_items, expense_items FROM monthly_data ORDER BY year, month")
    rows = cursor.fetchall()
    conn.close()

    payload = {"exported_at": datetime.now().isoformat(), "monthly_data": []}
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

        return True, "Data imported successfully."
    except Exception as exc:
        return False, f"Error importing data: {exc}"


init_database()

if "current_month" not in st.session_state:
    st.session_state.current_month = MONTHS[0]
if "current_year" not in st.session_state:
    st.session_state.current_year = datetime.now().year
if "goals" not in st.session_state:
    st.session_state.goals = []
if "current_page" not in st.session_state:
    st.session_state.current_page = "Monthly"

# STICKY NAVBAR
navbar_col1, navbar_col2, navbar_col3 = st.columns([1, 4, 1])

with navbar_col1:
    st.markdown("<div class='navbar-brand'>💼 Budgetware</div>", unsafe_allow_html=True)

with navbar_col2:
    st.markdown("<div class='navbar-nav'>", unsafe_allow_html=True)
    nav_col1, nav_col2, nav_col3, nav_col4 = st.columns(4)
    
    pages = ["Monthly", "Yearly", "Lifetime", "Savings Goals"]
    
    with nav_col1:
        if st.button("📊 Monthly", key="nav_monthly", use_container_width=True):
            st.session_state.current_page = "Monthly"
    with nav_col2:
        if st.button("📈 Yearly", key="nav_yearly", use_container_width=True):
            st.session_state.current_page = "Yearly"
    with nav_col3:
        if st.button("🌍 Lifetime", key="nav_lifetime", use_container_width=True):
            st.session_state.current_page = "Lifetime"
    with nav_col4:
        if st.button("🎯 Goals", key="nav_goals", use_container_width=True):
            st.session_state.current_page = "Savings Goals"
    
    st.markdown("</div>", unsafe_allow_html=True)

with navbar_col3:
    if st.button("☰ Menu", key="hamburger_btn", use_container_width=True):
        st.session_state.show_menu = not st.session_state.get("show_menu", False)

# HAMBURGER MENU
if st.session_state.get("show_menu", False):
    st.markdown("---")
    st.subheader("⚙️ Settings")
    
    menu_col1, menu_col2 = st.columns(2)
    
    with menu_col1:
        st.markdown("**📅 Month**")
        previous_month = st.session_state.current_month
        previous_year = st.session_state.current_year
        selected_month = st.selectbox(
            "Select Month",
            MONTHS,
            index=MONTH_INDEX[st.session_state.current_month],
            key="month_select",
        )
    
    with menu_col2:
        st.markdown("**📆 Year**")
        year_options = [datetime.now().year - 1, datetime.now().year, datetime.now().year + 1]
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
    st.markdown("**💾 Backup**")
    
    backup_col1, backup_col2 = st.columns(2)
    
    with backup_col1:
        if st.button("💾 Save Backup", use_container_width=True):
            save_monthly_data(
                st.session_state.current_month,
                st.session_state.current_year,
                st.session_state.get("current_income_items", []),
                st.session_state.get("current_expense_items", []),
            )
            filepath = export_data()
            st.success(f"✅ Saved: {os.path.basename(filepath)}")
    
    with backup_col2:
        uploaded_file = st.file_uploader("📂 Import Backup", type="json", key="import_backup")
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
        st.markdown("**📥 Download**")
        backup_choice = st.selectbox("Backup file", backups, key="backup_choice")
        if st.button("⬇️ Download JSON", use_container_width=True):
            filepath = os.path.join(SAVES_FOLDER, backup_choice)
            with open(filepath, "rb") as f:
                st.download_button(
                    label="📥 Download",
                    data=f.read(),
                    file_name=backup_choice,
                    mime="application/json",
                    use_container_width=True,
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

save_monthly_data(
    st.session_state.current_month,
    st.session_state.current_year,
    st.session_state.current_income_items,
    st.session_state.current_expense_items,
)

# PAGE CONTENT
page = st.session_state.current_page

if page == "Monthly":
    st.subheader(f"📊 Monthly Budget - {st.session_state.current_month} {st.session_state.current_year}")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📥 Income")
        for item in st.session_state.current_income_items:
            st.write(f"- {item['name']}: {format_idr(item.get('amount', 0))}")

        with st.form("income_form", clear_on_submit=True):
            income_name = st.text_input("Income name", placeholder="Salary, Freelance, Bonus")
            income_amount = st.number_input("Amount (IDR)", min_value=0, step=1000, format="%d")
            if st.form_submit_button("➕ Add Income", use_container_width=True):
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
                if st.form_submit_button("🗑️ Delete Income", use_container_width=True):
                    remove_item_by_id(st.session_state.current_income_items, income_choice)
                    save_monthly_data(
                        st.session_state.current_month,
                        st.session_state.current_year,
                        st.session_state.current_income_items,
                        st.session_state.current_expense_items,
                    )
                    st.rerun()

    with col2:
        st.markdown("### 📤 Expenses")
        for item in st.session_state.current_expense_items:
            st.write(f"- {item['name']}: {format_idr(item.get('amount', 0))}")

        with st.form("expense_form", clear_on_submit=True):
            expense_name = st.text_input("Expense name", placeholder="Rent, Groceries, Bills")
            expense_amount = st.number_input("Amount (IDR)", min_value=0, step=1000, format="%d", key="expense_amount_input")
            if st.form_submit_button("➕ Add Expense", use_container_width=True):
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
                if st.form_submit_button("🗑️ Delete Expense", use_container_width=True):
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
    metrics_col3.metric("Monthly Balance", format_idr(monthly_balance), delta=f"{monthly_balance:,.0f}")
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
    st.subheader(f"📈 Yearly Summary - {st.session_state.current_year}")
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
    st.subheader("🌍 Lifetime Summary")
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

else:
    st.subheader("🎯 Savings Goals")
    with st.form("add_goal_form", clear_on_submit=True):
        goal_name = st.text_input("Goal name", placeholder="Vacation, Emergency Fund, Car")
        goal_target = st.number_input("Target amount (IDR)", min_value=0, step=1000, format="%d")
        goal_saved = st.number_input("Current saved amount (IDR)", min_value=0, step=1000, format="%d")
        goal_deadline = st.date_input("Target deadline", value=datetime.now().date() + timedelta(days=365))
        goal_monthly = st.number_input("Monthly savings rate (IDR)", min_value=0, step=1000, format="%d")
        if st.form_submit_button("➕ Add Goal", use_container_width=True):
            if goal_name and goal_target > 0:
                st.session_state.goals.append(
                    normalize_goal(
                        {
                            "name": goal_name,
                            "target_amount": float(goal_target),
                            "current_savings": float(goal_saved),
                            "balance": float(goal_saved),
                            "deadline": goal_deadline,
                            "monthly_savings": float(goal_monthly),
                        },
                        fallback_monthly_savings=max(0.0, profile_balance),
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
            days_left = (normalized_goal["deadline"] - datetime.now().date()).days
            months_left = max(1, days_left // 30)
            required_per_month = amount_left / months_left if amount_left > 0 else 0

            st.markdown(f"### {normalized_goal['name']}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Target", format_idr(normalized_goal["target_amount"]))
            c2.metric("Saved", format_idr(normalized_goal["current_savings"]))
            c3.metric("Needed / month", format_idr(required_per_month))
            st.progress(progress, text=f"{progress * 100:.1f}% complete")

            editor1, editor2, editor3 = st.columns([1.2, 1.2, 0.6])
            with editor1:
                updated_saved = st.number_input(
                    "Saved amount",
                    min_value=0.0,
                    value=float(normalized_goal["current_savings"]),
                    step=1000.0,
                    key=f"saved_{idx}",
                    format="%.0f",
                )
            with editor2:
                updated_monthly = st.number_input(
                    "Monthly savings",
                    min_value=0.0,
                    value=float(normalized_goal["monthly_savings"]),
                    step=1000.0,
                    key=f"monthly_{idx}",
                    format="%.0f",
                )
            with editor3:
                if st.button("🗑️", key=f"delete_goal_{idx}"):
                    st.session_state.goals.pop(idx)
                    st.rerun()

            if updated_saved != normalized_goal["current_savings"] or updated_monthly != normalized_goal["monthly_savings"]:
                st.session_state.goals[idx] = normalize_goal(
                    {
                        **normalized_goal,
                        "current_savings": float(updated_saved),
                        "balance": float(updated_saved),
                        "monthly_savings": float(updated_monthly),
                    },
                    fallback_monthly_savings=max(0.0, profile_balance),
                )
                st.rerun()

            st.divider()
    else:
        st.info("No savings goals yet.")

save_monthly_data(
    st.session_state.current_month,
    st.session_state.current_year,
    st.session_state.current_income_items,
    st.session_state.current_expense_items,
)
