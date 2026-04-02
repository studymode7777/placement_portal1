import streamlit as st
import pandas as pd
import os
import re
import time
from io import BytesIO
from werkzeug.security import generate_password_hash, check_password_hash

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

st.set_page_config(page_title="College Placement Portal", layout="centered", page_icon="🎓")

# ==========================================
# PASSWORD VALIDATION
# ==========================================

def validate_password(password: str) -> tuple:
    """Returns (is_valid, list_of_error_messages)."""
    errors = []
    if len(password) < 8:
        errors.append("Must be at least 8 characters long.")
    if not re.search(r'[A-Z]', password):
        errors.append("Must contain at least one uppercase letter (A–Z).")
    if not re.search(r'[a-z]', password):
        errors.append("Must contain at least one lowercase letter (a–z).")
    if not re.search(r'\d', password):
        errors.append("Must contain at least one number (0–9).")
    if not re.search(r'[!@#$%^&*(),.?\":{}|<>]', password):
        errors.append("Must contain at least one special character (!@#$%^&* etc.).")
    if ' ' in password:
        errors.append("Must not contain spaces.")
    return (len(errors) == 0, errors)


# ==========================================
# EMAIL VALIDATION
# ==========================================

def is_valid_email(email: str) -> bool:
    return bool(re.match(r"^[\w.+-]+@[\w-]+\.[a-z]{2,}$", email, re.IGNORECASE))


# ==========================================
# HELPER FUNCTIONS & DB INITIALIZATION
# ==========================================

def init_db():
    """Create empty CSV files with correct headers if they don't exist."""
    if not os.path.exists("database.csv"):
        pd.DataFrame(columns=["Name", "Email", "Password", "CGPA", "Branch", "Boosted"]).to_csv("database.csv", index=False)
    if not os.path.exists("companies.csv"):
        pd.DataFrame(columns=["Company", "Email", "Address", "Password", "Package", "MinCGPA", "Branches"]).to_csv("companies.csv", index=False)
    if not os.path.exists("allocations.csv"):
        pd.DataFrame(columns=["Student_Email", "Company", "Package", "Date"]).to_csv("allocations.csv", index=False)
    if not os.path.exists("applications.csv"):
        pd.DataFrame(columns=["Student_Email", "Company_Name", "Status"]).to_csv("applications.csv", index=False)

init_db()


def safe_read_csv(path):
    try:
        df = pd.read_csv(path, on_bad_lines='skip')
        if path == "applications.csv" and "Status" not in df.columns:
            df["Status"] = "Pending"
        if path == "database.csv" and "Boosted" not in df.columns:
            df["Boosted"] = "False"
        # Migrate old companies.csv that had single Criteria column
        if path == "companies.csv":
            if "MinCGPA" not in df.columns:
                df["MinCGPA"] = 0.0
            if "Branches" not in df.columns:
                df["Branches"] = "CSE,IT,ECE,MECH"
            if "Criteria" in df.columns:
                df = df.drop(columns=["Criteria"])
        return df.fillna("")
    except Exception:
        return pd.DataFrame()


def append_csv(path, row_dict, cols_order):
    df = safe_read_csv(path)
    new_row = pd.DataFrame([row_dict])
    df = pd.concat([df, new_row], ignore_index=True) if not df.empty else new_row
    df = df.fillna("")
    for col in cols_order:
        if col not in df.columns:
            df[col] = ""
    df = df[cols_order]
    df.to_csv(path, index=False)


def update_app_status(student_email, company_name, new_status):
    df_apps = safe_read_csv("applications.csv")
    if not df_apps.empty:
        mask = (df_apps["Student_Email"] == student_email) & (df_apps["Company_Name"] == company_name)
        df_apps.loc[mask, "Status"] = new_status
        df_apps.to_csv("applications.csv", index=False)


# ==========================================
# SESSION STATE INITIALIZATION
# ==========================================

if "student_logged_in" not in st.session_state:
    st.session_state.student_logged_in = False
    st.session_state.current_student = None

if "company_logged_in" not in st.session_state:
    st.session_state.company_logged_in = False
    st.session_state.current_company = None

if "nav_override" not in st.session_state:
    st.session_state.nav_override = None

if "confirm_wipe_students" not in st.session_state:
    st.session_state.confirm_wipe_students = False

if "confirm_wipe_placements" not in st.session_state:
    st.session_state.confirm_wipe_placements = False


# ==========================================
# NAVIGATION
# ==========================================

st.title("🎓 College Placement Portal")

menu = ["Student Registration", "Student Login", "Company Registration", "Company Login", "Job Board", "Admin Dashboard"]

if st.session_state.nav_override in menu:
    default_idx = menu.index(st.session_state.nav_override)
    st.session_state.nav_override = None
else:
    default_idx = 0

choice = st.sidebar.selectbox("Navigation", menu, index=default_idx)


# ==========================================
# 1. STUDENT REGISTRATION & RESUME
# ==========================================

if choice == "Student Registration":
    st.subheader("📚 Student Portal")

    tab1, tab2 = st.tabs(["Register", "Build Resume"])

    with tab1:
        st.write("Complete your basic details for placement registration.")
        with st.form("reg_form"):
            name = st.text_input("Full Name", max_chars=100)
            email = st.text_input("College Email", max_chars=120).strip().lower()
            password = st.text_input("Set Password", type="password", max_chars=128,
                                     help="Min 8 chars · uppercase · lowercase · number · special character")
            confirm = st.text_input("Confirm Password", type="password", max_chars=128)
            cgpa = st.number_input("Current CGPA", min_value=0.0, max_value=10.0, step=0.1)
            branch = st.selectbox("Branch", ["CSE", "IT", "ECE", "MECH"])

            submitted = st.form_submit_button("Submit Application")

        if submitted:
            errors_found = False

            if not name or not email or not password:
                st.error("Please fill all mandatory fields.")
                errors_found = True

            if not errors_found and not is_valid_email(email):
                st.error("Please enter a valid email address.")
                errors_found = True

            if not errors_found:
                valid_pw, pw_errors = validate_password(password)
                if not valid_pw:
                    for err in pw_errors:
                        st.error(err)
                    errors_found = True

            if not errors_found and password != confirm:
                st.error("Passwords do not match.")
                errors_found = True

            if not errors_found:
                df_students = safe_read_csv("database.csv")
                if not df_students.empty and email in df_students["Email"].str.strip().str.lower().values:
                    st.error("Email already registered! Please login.")
                else:
                    hashed_pw = generate_password_hash(password)
                    row = {"Name": name, "Email": email, "Password": hashed_pw,
                           "CGPA": cgpa, "Branch": branch, "Boosted": "False"}
                    append_csv("database.csv", row, ["Name", "Email", "Password", "CGPA", "Branch", "Boosted"])
                    st.success(f"Best of luck, {name}! Your application has been saved.")

    with tab2:
        st.write("Fill in your details and download a formatted resume.")

        # Pre-fill from session if logged in
        prefill_name = ""
        prefill_email = ""
        if st.session_state.student_logged_in and st.session_state.current_student:
            prefill_name = st.session_state.current_student.get("Name", "")
            prefill_email = st.session_state.current_student.get("Email", "")

        with st.form("resume_form"):
            r_name = st.text_input("Full Name", value=prefill_name, max_chars=100)
            r_email = st.text_input("Email", value=prefill_email, max_chars=120)
            r_phone = st.text_input("Phone Number", max_chars=20)
            r_summary = st.text_area("Professional Summary", max_chars=1000)
            r_education = st.text_area("Education", max_chars=1000)
            r_skills = st.text_area("Skills (comma separated)", max_chars=500)
            r_projects = st.text_area("Projects (one per line)", max_chars=2000)
            build = st.form_submit_button("Generate Resume")

        if build:
            if not REPORTLAB_AVAILABLE:
                st.error("Please install reportlab: `pip install reportlab`")
            elif not r_name or not r_email:
                st.error("Name and Email are required.")
            else:
                pdf_buffer = BytesIO()
                doc = SimpleDocTemplate(pdf_buffer, pagesize=letter,
                                        topMargin=0.5 * inch, bottomMargin=0.5 * inch)
                story = []
                styles = getSampleStyleSheet()
                title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18,
                                             textColor=colors.HexColor('#1f77b4'),
                                             spaceAfter=6, alignment=1)
                story.append(Paragraph(r_name, title_style))
                story.append(Paragraph(f"<b>Email:</b> {r_email} | <b>Phone:</b> {r_phone}", styles['Normal']))
                story.append(Spacer(1, 0.2 * inch))
                if r_summary:
                    story.append(Paragraph("<b>Professional Summary</b>", styles['Heading2']))
                    story.append(Paragraph(r_summary, styles['Normal']))
                    story.append(Spacer(1, 0.1 * inch))
                if r_education:
                    story.append(Paragraph("<b>Education</b>", styles['Heading2']))
                    for line in r_education.strip().splitlines():
                        story.append(Paragraph(f"• {line}", styles['Normal']))
                    story.append(Spacer(1, 0.1 * inch))
                if r_skills:
                    story.append(Paragraph("<b>Skills</b>", styles['Heading2']))
                    story.append(Paragraph(r_skills, styles['Normal']))
                    story.append(Spacer(1, 0.1 * inch))
                if r_projects:
                    story.append(Paragraph("<b>Projects</b>", styles['Heading2']))
                    for line in r_projects.strip().splitlines():
                        story.append(Paragraph(f"• {line}", styles['Normal']))
                doc.build(story)
                pdf_bytes = pdf_buffer.getvalue()
                st.success("Resume generated successfully!")
                st.download_button(
                    label="📥 Download Resume (PDF)",
                    data=pdf_bytes,
                    file_name=f"{r_name.replace(' ', '_')}_Resume.pdf",
                    mime="application/pdf"
                )


# ==========================================
# 2. STUDENT LOGIN
# ==========================================

elif choice == "Student Login":
    st.subheader("🔐 Student Login")

    if not st.session_state.student_logged_in:
        email = st.text_input("College Email", max_chars=120).strip().lower()
        pwd = st.text_input("Password", type="password", max_chars=128)

        if st.button("Login"):
            df_students = safe_read_csv("database.csv")
            if not df_students.empty:
                df_students["Email_clean"] = df_students["Email"].astype(str).str.strip().str.lower()
                match = df_students[df_students["Email_clean"] == email]

                if not match.empty:
                    stored_hash = str(match.iloc[0]["Password"]).strip()
                    if check_password_hash(stored_hash, pwd):
                        st.session_state.student_logged_in = True
                        st.session_state.current_student = match.iloc[0].to_dict()
                        st.rerun()
                    else:
                        st.error("❌ Invalid Email or Password.")
                else:
                    st.error("❌ Invalid Email or Password.")
            else:
                st.error("❌ No students registered yet.")
    else:
        df_students = safe_read_csv("database.csv")
        student_email = str(st.session_state.current_student["Email"]).strip().lower()
        df_students["Email_clean"] = df_students["Email"].astype(str).str.strip().str.lower()
        student_match = df_students[df_students["Email_clean"] == student_email]

        if student_match.empty:
            st.session_state.student_logged_in = False
            st.session_state.current_student = None
            st.warning("⚠️ Session expired. Please log in again.")
            time.sleep(1.5)
            st.rerun()
        else:
            student = student_match.iloc[0].to_dict()

            st.success(f"✅ Welcome back, {student['Name']}!")

            with st.container(border=True):
                col1, col2 = st.columns(2)
                col1.write(f"**Branch:** {student['Branch']}")
                col1.write(f"**CGPA:** {student['CGPA']}")
                col2.write(f"**Email:** {student['Email']}")

            # --- PROFILE BOOST ---
            st.markdown("### 🚀 Premium Features")
            is_boosted = str(student.get("Boosted", "False")).strip()

            if is_boosted == "True":
                st.success("🔥 Your profile is BOOSTED! Companies see your applications first.")
            else:
                st.info("Boost your profile to appear at the top of recruiter pipelines.")
                st.caption("⚠️ Demo only — no real payment is processed.")

                if st.button("💳 Pay ₹300 to Boost Profile (Demo)"):
                    status_box = st.empty()
                    with status_box.container():
                        with st.spinner("Processing payment (simulation)..."):
                            time.sleep(1.5)
                            target_email = str(student["Email"]).strip().lower()
                            df_students["Email_clean2"] = df_students["Email"].astype(str).str.strip().str.lower()
                            df_students.loc[df_students["Email_clean2"] == target_email, "Boosted"] = "True"
                            df_students = df_students.drop(columns=["Email_clean", "Email_clean2"], errors="ignore")
                            df_students.to_csv("database.csv", index=False)
                            st.session_state.current_student["Boosted"] = "True"
                    status_box.success("🎉 Profile boosted! (Demo — integrate Razorpay for real payments.)")
                    time.sleep(1.5)
                    st.rerun()

            st.divider()

            # --- MY APPLICATIONS ---
            st.markdown("### 📋 My Job Applications")
            df_apps = safe_read_csv("applications.csv")

            if not df_apps.empty:
                df_apps["Student_Email"] = df_apps["Student_Email"].astype(str).str.strip()
                my_apps = df_apps[df_apps["Student_Email"].str.lower() == str(student["Email"]).lower()]

                if not my_apps.empty:
                    for _, app in my_apps.iterrows():
                        status = app['Status']
                        if status == "Accepted":
                            st.success(f"🎉 **{app['Company_Name']}** — {status}")
                        elif status == "Rejected":
                            st.error(f"❌ **{app['Company_Name']}** — {status}")
                        elif status == "Shortlisted":
                            st.warning(f"⭐ **{app['Company_Name']}** — {status}")
                        else:
                            st.info(f"⏳ **{app['Company_Name']}** — {status}")
                else:
                    st.write("You haven't applied to any jobs yet. Check the Job Board!")
            else:
                st.write("You haven't applied to any jobs yet. Check the Job Board!")

            st.markdown("---")
            if st.button("Logout", type="primary"):
                st.session_state.student_logged_in = False
                st.session_state.current_student = None
                st.session_state.nav_override = "Job Board"
                st.rerun()


# ==========================================
# 3. COMPANY REGISTRATION
# ==========================================

elif choice == "Company Registration":
    st.subheader("🏢 Post a Job Opening")
    with st.form("company_form"):
        company_name = st.text_input("Company Name", max_chars=100)
        company_email = st.text_input("Company Email", max_chars=120).strip().lower()
        address = st.text_input("Company Address / Location", max_chars=200)
        password = st.text_input("Set Password", type="password", max_chars=128,
                                 help="Min 8 chars · uppercase · lowercase · number · special character")
        package = st.text_input("Salary Package (e.g., 10 LPA)", max_chars=50)
        min_cgpa = st.number_input("Minimum CGPA Required", min_value=0.0, max_value=10.0, step=0.1, value=6.0)
        branches = st.multiselect("Eligible Branches", ["CSE", "IT", "ECE", "MECH"],
                                  default=["CSE", "IT", "ECE", "MECH"])

        submitted = st.form_submit_button("Register Company")

    if submitted:
        errors_found = False
        if not company_name or not company_email or not password:
            st.error("Company name, email, and password are required.")
            errors_found = True

        if not errors_found and not is_valid_email(company_email):
            st.error("Please enter a valid company email address.")
            errors_found = True

        if not errors_found:
            valid_pw, pw_errors = validate_password(password)
            if not valid_pw:
                for err in pw_errors:
                    st.error(err)
                errors_found = True

        if not errors_found and not branches:
            st.error("Please select at least one eligible branch.")
            errors_found = True

        if not errors_found:
            df_comps = safe_read_csv("companies.csv")
            if not df_comps.empty and company_email in df_comps["Email"].str.strip().str.lower().values:
                st.error("Company email already registered!")
            else:
                hashed_pw = generate_password_hash(password)
                row = {
                    "Company": company_name,
                    "Email": company_email,
                    "Address": address,
                    "Password": hashed_pw,
                    "Package": package,
                    "MinCGPA": min_cgpa,
                    "Branches": ",".join(branches)
                }
                append_csv("companies.csv", row,
                           ["Company", "Email", "Address", "Password", "Package", "MinCGPA", "Branches"])
                st.success(f"Job drive for {company_name} posted successfully!")


# ==========================================
# 4. COMPANY LOGIN
# ==========================================

elif choice == "Company Login":
    st.subheader("🏢 Company Dashboard")

    if not st.session_state.company_logged_in:
        email = st.text_input("Company Email", max_chars=120).strip().lower()
        pwd = st.text_input("Password", type="password", max_chars=128)

        if st.button("Login"):
            df_comps = safe_read_csv("companies.csv")
            if not df_comps.empty:
                df_comps["Email_clean"] = df_comps["Email"].astype(str).str.strip().str.lower()
                match = df_comps[df_comps["Email_clean"] == email]

                if not match.empty:
                    stored_hash = str(match.iloc[0]["Password"]).strip()
                    if check_password_hash(stored_hash, pwd):
                        st.session_state.company_logged_in = True
                        st.session_state.current_company = match.iloc[0].to_dict()
                        st.rerun()
                    else:
                        st.error("❌ Invalid Email or Password.")
                else:
                    st.error("❌ Invalid Email or Password.")
            else:
                st.error("❌ No companies registered yet.")
    else:
        comp = st.session_state.current_company
        company_name = comp['Company']
        st.success(f"✅ Dashboard: {company_name}")

        with st.container(border=True):
            st.write(f"**Package:** {comp['Package']}")
            st.write(f"**Min CGPA:** {comp.get('MinCGPA', 'N/A')}  |  **Eligible Branches:** {comp.get('Branches', 'All')}")

        st.markdown("### 📥 Candidate Pipeline")
        df_students = safe_read_csv("database.csv")
        df_apps = safe_read_csv("applications.csv")

        if not df_apps.empty and not df_students.empty:
            my_apps = df_apps[df_apps["Company_Name"] == company_name]

            if not my_apps.empty:
                merged_data = pd.merge(my_apps, df_students, left_on="Student_Email", right_on="Email")
                merged_data = merged_data.sort_values(by="Boosted", ascending=False)

                col_pending, col_shortlist = st.columns(2)

                with col_pending:
                    st.markdown("#### 🆕 Pending Review")
                    pending_apps = merged_data[merged_data["Status"] == "Pending"]

                    if not pending_apps.empty:
                        for idx, row in pending_apps.iterrows():
                            boost_badge = "🔥 **Premium**" if str(row.get("Boosted")) == "True" else ""
                            with st.container(border=True):
                                st.write(f"**{row['Name']}** {boost_badge}")
                                st.write(f"🎓 {row['Branch']} | CGPA: {row['CGPA']}")
                                c1, c2, c3 = st.columns(3)
                                if c1.button("⭐ Short", key=f"shortlist_{idx}"):
                                    update_app_status(row["Email"], company_name, "Shortlisted")
                                    st.rerun()
                                if c2.button("✅ Acc", key=f"acc_p_{idx}"):
                                    update_app_status(row["Email"], company_name, "Accepted")
                                    st.rerun()
                                if c3.button("❌ Rej", key=f"rej_p_{idx}"):
                                    update_app_status(row["Email"], company_name, "Rejected")
                                    st.rerun()
                    else:
                        st.info("No new pending applications.")

                with col_shortlist:
                    st.markdown("#### ⭐ Shortlisted")
                    shortlisted_apps = merged_data[merged_data["Status"] == "Shortlisted"]

                    if not shortlisted_apps.empty:
                        for idx, row in shortlisted_apps.iterrows():
                            boost_badge = "🔥 **Premium**" if str(row.get("Boosted")) == "True" else ""
                            with st.container(border=True):
                                st.write(f"**{row['Name']}** {boost_badge}")
                                st.write(f"🎓 {row['Branch']} | CGPA: {row['CGPA']}")
                                c1, c2 = st.columns(2)
                                if c1.button("✅ Accept", key=f"acc_s_{idx}"):
                                    update_app_status(row["Email"], company_name, "Accepted")
                                    st.rerun()
                                if c2.button("❌ Reject", key=f"rej_s_{idx}"):
                                    update_app_status(row["Email"], company_name, "Rejected")
                                    st.rerun()
                    else:
                        st.info("No candidates shortlisted yet.")

                st.divider()
                st.markdown("#### 🗄️ Processed Candidates")
                processed_apps = merged_data[merged_data["Status"].isin(["Accepted", "Rejected"])]

                if not processed_apps.empty:
                    for _, row in processed_apps.iterrows():
                        icon = "✅" if row["Status"] == "Accepted" else "❌"
                        st.write(f"{icon} **{row['Name']}** — {row['Status']}")
                else:
                    st.write("No candidates have been accepted or rejected yet.")
            else:
                st.info("No applications received yet.")
        else:
            st.info("No applications received yet.")

        st.markdown("---")
        if st.button("Logout", type="primary"):
            st.session_state.company_logged_in = False
            st.session_state.current_company = None
            st.session_state.nav_override = "Job Board"
            st.rerun()


# ==========================================
# 5. JOB BOARD
# ==========================================

elif choice == "Job Board":
    st.subheader("📢 Hiring Companies & Job Openings")
    df_comps = safe_read_csv("companies.csv")

    if not df_comps.empty:
        with st.expander("🔍 Filter & Search Jobs", expanded=True):
            search_query = st.text_input("Search by company name or location").lower()

        display_df = df_comps.copy()
        if search_query:
            mask = (
                display_df['Company'].astype(str).str.lower().str.contains(search_query) |
                display_df['Address'].astype(str).str.lower().str.contains(search_query)
            )
            display_df = display_df[mask]

        if not display_df.empty:
            for _, row in display_df.iterrows():
                with st.container(border=True):
                    st.markdown(f"### {row['Company']}")
                    st.write(f"**💰 Package:** {row['Package']}  |  **🎓 Min CGPA:** {row['MinCGPA']}  |  **🌿 Branches:** {row['Branches']}")
                    st.write(f"📍 **Location:** {row['Address']}")

                    if st.session_state.student_logged_in:
                        student = st.session_state.current_student
                        student_email = student["Email"]
                        company_name = row['Company']

                        # --- ELIGIBILITY CHECK ---
                        try:
                            student_cgpa = float(student.get("CGPA", 0))
                            min_cgpa = float(row.get("MinCGPA", 0))
                        except (ValueError, TypeError):
                            student_cgpa = 0
                            min_cgpa = 0

                        eligible_branches = [b.strip() for b in str(row.get("Branches", "")).split(",")]
                        student_branch = str(student.get("Branch", ""))
                        cgpa_ok = student_cgpa >= min_cgpa
                        branch_ok = student_branch in eligible_branches or eligible_branches == [""]

                        df_apps = safe_read_csv("applications.csv")
                        already_applied = False
                        if not df_apps.empty:
                            already_applied = not df_apps[
                                (df_apps["Student_Email"].astype(str) == str(student_email)) &
                                (df_apps["Company_Name"].astype(str) == str(company_name))
                            ].empty

                        if already_applied:
                            st.success("✅ Application Submitted")
                        elif not cgpa_ok:
                            st.warning(f"⚠️ Not eligible — your CGPA ({student_cgpa}) is below the requirement ({min_cgpa}).")
                        elif not branch_ok:
                            st.warning(f"⚠️ Not eligible — your branch ({student_branch}) is not in the eligible list.")
                        else:
                            if st.button(f"Apply to {company_name}", key=f"apply_{company_name}"):
                                new_app = {"Student_Email": student_email,
                                           "Company_Name": company_name, "Status": "Pending"}
                                append_csv("applications.csv", new_app,
                                           ["Student_Email", "Company_Name", "Status"])
                                st.success(f"Successfully applied to {company_name}!")
                                st.rerun()

                    elif not st.session_state.company_logged_in:
                        st.info("Log in as a student to apply.")
        else:
            st.warning("No jobs found matching your search.")
    else:
        st.info("No companies have posted job drives yet.")


# ==========================================
# 6. ADMIN DASHBOARD
# ==========================================

elif choice == "Admin Dashboard":
    st.subheader("⚙️ Admin Access")

    ADMIN_PASSWORD = "admin123"
    if not ADMIN_PASSWORD:
        st.warning("⚠️ Admin password not set. Set the `ADMIN_PASSWORD` environment variable to enable access.")

    pwd = st.text_input("Admin Password", type="password")

    if ADMIN_PASSWORD and pwd == ADMIN_PASSWORD:
        df_students = safe_read_csv("database.csv")
        df_comps = safe_read_csv("companies.csv")
        df_allocs = safe_read_csv("allocations.csv")
        df_apps = safe_read_csv("applications.csv")

        # --- ANALYTICS ---
        st.write("### 📊 Portal Analytics")
        c1, c2, c3 = st.columns(3)
        c1.metric("Registered Students", len(df_students) if not df_students.empty else 0)
        c2.metric("Partner Companies", len(df_comps) if not df_comps.empty else 0)
        c3.metric("Total Applications", len(df_apps) if not df_apps.empty else 0)

        st.divider()

        st.write("### 📈 Visual Insights")
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            st.write("**Students by Branch**")
            if not df_students.empty and "Branch" in df_students.columns:
                st.bar_chart(df_students["Branch"].value_counts(), color="#1f77b4")
            else:
                st.info("No student data yet.")
        with chart_col2:
            st.write("**Applications per Company**")
            if not df_apps.empty and "Company_Name" in df_apps.columns:
                st.bar_chart(df_apps["Company_Name"].value_counts(), color="#ff7f0e")
            else:
                st.info("No application data yet.")

        st.divider()

        t1, t2, t3, t4 = st.tabs(["Students", "Companies", "Allocations", "Danger Zone"])

        with t1:
            st.write("### Registered Students")
            if not df_students.empty:
                # Never show passwords
                display_students = df_students.drop(columns=["Password"], errors="ignore")
                st.dataframe(display_students, use_container_width=True)
            else:
                st.info("No students registered.")

        with t2:
            st.write("### Registered Companies")
            if not df_comps.empty:
                display_comps = df_comps.drop(columns=["Password"], errors="ignore")
                st.dataframe(display_comps, use_container_width=True)
            else:
                st.info("No companies registered.")

        with t3:
            st.write("### Assign Student to Company (Manual Override)")
            with st.form("alloc_form"):
                s_email = st.text_input("Student Email")
                c_name = st.text_input("Company Name")
                pkg = st.text_input("Final Package")
                date = st.date_input("Offer Date")
                if st.form_submit_button("Confirm Allocation"):
                    row = {"Student_Email": s_email, "Company": c_name, "Package": pkg, "Date": date}
                    append_csv("allocations.csv", row, ["Student_Email", "Company", "Package", "Date"])
                    st.success(f"Allocated {s_email} to {c_name}!")

            st.write("### Current Placements")
            if not df_allocs.empty:
                st.dataframe(df_allocs, use_container_width=True)
            else:
                st.info("No placements recorded yet.")

        with t4:
            st.error("⚠️ Danger Zone — these actions cannot be undone.")

            st.write("#### Wipe All Student Data")
            wipe_confirm = st.text_input('Type "DELETE" to enable the wipe button', key="wipe_students_input")
            if wipe_confirm == "DELETE":
                if st.button("🗑️ Wipe All Student Data & Applications", type="primary"):
                    for f in ["database.csv", "applications.csv"]:
                        if os.path.exists(f):
                            os.remove(f)
                    init_db()
                    st.success("Student database and applications cleared.")
                    st.rerun()
            else:
                st.button("🗑️ Wipe All Student Data & Applications", disabled=True)

            st.write("#### Wipe All Placements")
            wipe_confirm2 = st.text_input('Type "DELETE" to enable the wipe button', key="wipe_placements_input")
            if wipe_confirm2 == "DELETE":
                if st.button("🗑️ Wipe All Placements", type="primary"):
                    if os.path.exists("allocations.csv"):
                        os.remove("allocations.csv")
                    init_db()
                    st.success("Allocations cleared.")
                    st.rerun()
            else:
                st.button("🗑️ Wipe All Placements", disabled=True)

    elif pwd:
        st.error("Incorrect admin password.")
