import streamlit as st
import pandas as pd
import sqlite3
import os
import re
import time
import json
import shutil
from io import BytesIO
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Optional imports (PyPDF2, docx, stripe, reportlab) remain the same...
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

st.set_page_config(page_title="College Placement Portal", layout="wide", page_icon="🎓")

ADMIN_PASSWORD = "admin123"

# ==========================================
# DATABASE CONNECTION HELPER
# ==========================================
def get_db_connection():
    # check_same_thread=False is required for Streamlit
    conn = sqlite3.connect('placement_portal.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row # Allows dictionary-like access to rows
    return conn

def execute_query(query, params=(), commit=False):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        if commit:
            conn.commit()
            return True
        return cursor.fetchall()
    except sqlite3.Error as e:
        st.error(f"Database Error: {e}")
        return False
    finally:
        conn.close()

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def validate_password(password: str) -> tuple:
    errors = []
    if len(password) < 8: errors.append("At least 8 characters")
    if not re.search(r'[A-Z]', password): errors.append("One uppercase letter")
    if not re.search(r'[a-z]', password): errors.append("One lowercase letter")
    if not re.search(r'\d', password): errors.append("One number")
    if not re.search(r'[!@#$%^&*(),.?\":{}|<>]', password): errors.append("One special character")
    return (len(errors) == 0, errors)

def is_valid_email(email: str) -> bool:
    return bool(re.match(r"^[\w.+-]+@[\w-]+\.[a-z]{2,}$", email, re.IGNORECASE))

def log_admin_action(action):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    execute_query(
        "INSERT INTO audit_logs (admin_email, action, timestamp) VALUES (?, ?, ?)", 
        ("admin", action, timestamp), 
        commit=True
    )

# ==========================================
# SESSION STATE
# ==========================================
if "student_logged_in" not in st.session_state:
    st.session_state.student_logged_in = False
    st.session_state.current_student = None
    st.session_state.company_logged_in = False
    st.session_state.current_company = None
    st.session_state.nav_override = None

# ==========================================
# NAVIGATION
# ==========================================
st.title("🎓 College Placement Portal")

menu = ["Student Registration", "Student Login", "Company Registration", "Company Login", "Job Board", "Admin Dashboard"]
default_idx = menu.index(st.session_state.nav_override) if st.session_state.nav_override in menu else 0
choice = st.sidebar.selectbox("Navigation", menu, index=default_idx)

# ==========================================
# 1. STUDENT REGISTRATION
# ==========================================
if choice == "Student Registration":
    st.subheader("📚 Student Registration")
    with st.form("reg_form"):
        name = st.text_input("Full Name")
        email = st.text_input("College Email").strip().lower()
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm Password", type="password")
        cgpa = st.number_input("CGPA", 0.0, 10.0, step=0.1)
        branch = st.selectbox("Branch", ["CSE","IT","ECE","MECH"])
        submitted = st.form_submit_button("Register")

    if submitted:
        errors = False
        if not all([name, email, password]):
            st.error("All fields required")
            errors = True
        if not is_valid_email(email):
            st.error("Invalid email")
            errors = True
        valid_pw, pw_err = validate_password(password)
        if not valid_pw:
            for e in pw_err: st.error(e)
            errors = True
        if password != confirm:
            st.error("Passwords mismatch")
            errors = True

        if not errors:
            hashed_pw = generate_password_hash(password)
            # Database Insert
            success = execute_query(
                "INSERT INTO students (email, name, password, cgpa, branch, boosted, verified) VALUES (?, ?, ?, ?, ?, 'False', 'True')",
                (email, name, hashed_pw, cgpa, branch),
                commit=True
            )
            if success:
                st.success("Registration successful! You can now log in.")

# ==========================================
# 2. STUDENT LOGIN & DASHBOARD
# ==========================================
elif choice == "Student Login":
    if not st.session_state.student_logged_in:
        st.subheader("🔐 Student Login")
        email = st.text_input("Email").strip().lower()
        pwd = st.text_input("Password", type="password")
        if st.button("Login"):
            conn = get_db_connection()
            user = conn.execute("SELECT * FROM students WHERE email = ?", (email,)).fetchone()
            conn.close()

            if user and check_password_hash(user["password"], pwd):
                st.session_state.student_logged_in = True
                st.session_state.current_student = dict(user)
                st.rerun()
            else:
                st.error("Invalid credentials or Email not found")
    else:
        student = st.session_state.current_student
        st.success(f"✅ Welcome back, {student['name']}!")
        
        with st.container(border=True):
            col1, col2 = st.columns(2)
            col1.write(f"**Branch:** {student['branch']} | **CGPA:** {student['cgpa']}")
            col2.write(f"**Email:** {student['email']}")

        st.divider()

        st.markdown("### 📋 My Job Applications")
        conn = get_db_connection()
        # Use pandas to easily render the SQL query as a table
        df_apps = pd.read_sql_query("SELECT company_name, status, test_score FROM applications WHERE student_email = ?", conn, params=(student['email'],))
        conn.close()

        if not df_apps.empty:
            st.dataframe(df_apps, use_container_width=True)
        else:
            st.write("No applications yet.")

        st.divider()
        if st.button("Logout", type="primary"):
            st.session_state.student_logged_in = False
            st.session_state.current_student = None
            st.rerun()

# ==========================================
# 3. JOB BOARD (Applying SQL logic)
# ==========================================
elif choice == "Job Board":
    st.subheader("📢 Job Openings")
    
    conn = get_db_connection()
    df_comps = pd.read_sql_query("SELECT * FROM companies", conn)
    
    if df_comps.empty:
        st.info("No companies have posted jobs yet.")
    else:
        search = st.text_input("Search by company or location")
        if search:
            df_comps = df_comps[df_comps["company_name"].str.contains(search, case=False) | df_comps["address"].str.contains(search, case=False)]
        
        for idx, job in df_comps.iterrows():
            with st.container(border=True):
                st.markdown(f"### {job['company_name']}")
                st.write(f"💰 Package: {job['package']}  |  🎓 Min CGPA: {job['min_cgpa']}  |  🌿 Branches: {job['branches']}")
                
                if st.session_state.student_logged_in:
                    student = st.session_state.current_student
                    
                    # Check if already applied using SQL
                    app_exists = conn.execute(
                        "SELECT id FROM applications WHERE student_email = ? AND company_name = ?", 
                        (student['email'], job['company_name'])
                    ).fetchone()

                    if app_exists:
                        st.success("✅ Application Submitted")
                    elif float(student['cgpa']) < float(job['min_cgpa']):
                        st.warning("CGPA too low for this role.")
                    else:
                        if st.button(f"Apply to {job['company_name']}", key=f"apply_{job['company_name']}"):
                            execute_query(
                                "INSERT INTO applications (student_email, company_name, status) VALUES (?, ?, 'Pending')",
                                (student['email'], job['company_name']),
                                commit=True
                            )
                            st.success("Application submitted!")
                            st.rerun()
                else:
                    st.info("Login as student to apply")
    conn.close()