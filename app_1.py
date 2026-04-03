import streamlit as st
import pandas as pd
import os
import re
import time
import json
import shutil
from io import BytesIO
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Optional imports
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

try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

st.set_page_config(page_title="College Placement Portal", layout="wide", page_icon="🎓")

# ==========================================
# CONFIGURATION (from secrets or env)
# ==========================================
try:
    ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "admin123")
    STRIPE_PUBLIC_KEY = st.secrets.get("STRIPE_PUBLIC_KEY", "")
    STRIPE_SECRET_KEY = st.secrets.get("STRIPE_SECRET_KEY", "")
    if STRIPE_SECRET_KEY:
        stripe.api_key = STRIPE_SECRET_KEY
except:
    ADMIN_PASSWORD = "admin123"

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def validate_password(password: str) -> tuple:
    errors = []
    if len(password) < 8:
        errors.append("At least 8 characters")
    if not re.search(r'[A-Z]', password):
        errors.append("One uppercase letter")
    if not re.search(r'[a-z]', password):
        errors.append("One lowercase letter")
    if not re.search(r'\d', password):
        errors.append("One number")
    if not re.search(r'[!@#$%^&*(),.?\":{}|<>]', password):
        errors.append("One special character")
    return (len(errors) == 0, errors)

def is_valid_email(email: str) -> bool:
    return bool(re.match(r"^[\w.+-]+@[\w-]+\.[a-z]{2,}$", email, re.IGNORECASE))

def log_admin_action(action):
    row = {"Admin_Email": "admin", "Action": action, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    append_csv("audit_logs.csv", row)

def parse_resume(file_bytes, filename):
    if not (PDF_AVAILABLE or DOCX_AVAILABLE):
        return None
    text = ""
    if filename.endswith('.pdf') and PDF_AVAILABLE:
        pdf_reader = PyPDF2.PdfReader(BytesIO(file_bytes))
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
    elif filename.endswith('.docx') and DOCX_AVAILABLE:
        doc = docx.Document(BytesIO(file_bytes))
        text = "\n".join([para.text for para in doc.paragraphs])
    else:
        return None
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    email = email_match.group(0) if email_match else ""
    name_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', text)
    name = name_match.group(0) if name_match else ""
    return {"name": name, "email": email, "raw_text": text[:500]}

# ==========================================
# DATABASE INITIALIZATION (CSV files)
# ==========================================

def init_db():
    files = {
        "database.csv": ["Name","Email","Password","CGPA","Branch","Boosted","Verified"],
        "companies.csv": ["Company","Email","Address","Password","Package","MinCGPA","Branches","CustomQuestions"],
        "allocations.csv": ["Student_Email","Company","Package","Date","Rating"],
        "applications.csv": ["Student_Email","Company_Name","Status","Answers","TestScore"],
        "documents.csv": ["Student_Email","Document_Name","File_Path","Upload_Date"],
        "interviews.csv": ["Company","Slot_Time","Duration","Mode","Booked_By","Booking_Date"],
        "ratings.csv": ["Student_Email","Company","Rating","Review","Date"],
        "audit_logs.csv": ["Admin_Email","Action","Timestamp"],
        "skill_tests.csv": ["Company","Job_Title","Questions","Answers","Passing_Score"],
        "test_results.csv": ["Student_Email","Company","Score","Passed","Date"]
    }
    for fname, cols in files.items():
        if not os.path.exists(fname):
            pd.DataFrame(columns=cols).to_csv(fname, index=False)
    os.makedirs("uploads", exist_ok=True)

init_db()

# Migration: ensure Verified column exists and set to True for all existing students
def migrate_existing_students():
    if os.path.exists("database.csv"):
        df = pd.read_csv("database.csv")
        if "Verified" not in df.columns:
            df["Verified"] = "True"
        else:
            df["Verified"] = df["Verified"].fillna("True")
            df["Verified"] = df["Verified"].replace("False", "True")  # force all to True
        df.to_csv("database.csv", index=False)

migrate_existing_students()

def safe_read_csv(path):
    try:
        df = pd.read_csv(path, on_bad_lines='skip')
        required_columns = {
            "database.csv": ["Name","Email","Password","CGPA","Branch","Boosted","Verified"],
            "companies.csv": ["Company","Email","Address","Password","Package","MinCGPA","Branches","CustomQuestions"],
            "applications.csv": ["Student_Email","Company_Name","Status","Answers","TestScore"],
            "allocations.csv": ["Student_Email","Company","Package","Date","Rating"],
            "documents.csv": ["Student_Email","Document_Name","File_Path","Upload_Date"],
            "interviews.csv": ["Company","Slot_Time","Duration","Mode","Booked_By","Booking_Date"],
            "ratings.csv": ["Student_Email","Company","Rating","Review","Date"],
            "audit_logs.csv": ["Admin_Email","Action","Timestamp"],
            "skill_tests.csv": ["Company","Job_Title","Questions","Answers","Passing_Score"],
            "test_results.csv": ["Student_Email","Company","Score","Passed","Date"]
        }
        if path in required_columns:
            for col in required_columns[path]:
                if col not in df.columns:
                    df[col] = ""
        return df.fillna("")
    except Exception:
        return pd.DataFrame()

def append_csv(path, row_dict):
    df = safe_read_csv(path)
    new_row = pd.DataFrame([row_dict])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(path, index=False)

def update_csv(path, condition_func, update_dict):
    df = safe_read_csv(path)
    for idx, row in df.iterrows():
        if condition_func(row):
            for k, v in update_dict.items():
                df.at[idx, k] = v
    df.to_csv(path, index=False)

def save_uploaded_file(uploaded_file, student_email):
    base_name = os.path.splitext(uploaded_file.name)[0]
    ext = os.path.splitext(uploaded_file.name)[1]
    timestamp = int(time.time())
    safe_email = student_email.replace('@', '_at_').replace('.', '_')
    safe_filename = f"{safe_email}_{base_name}_{timestamp}{ext}"
    safe_filename = re.sub(r'[^\w\-_.]', '_', safe_filename)
    file_path = os.path.join("uploads", safe_filename)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path

def get_student_documents(student_email):
    df_docs = safe_read_csv("documents.csv")
    if df_docs.empty:
        return pd.DataFrame()
    df_docs["Student_Email"] = df_docs["Student_Email"].astype(str).str.strip().str.lower()
    return df_docs[df_docs["Student_Email"] == student_email.lower()]

def delete_document(file_path, student_email, doc_name):
    if os.path.exists(file_path):
        os.remove(file_path)
    df_docs = safe_read_csv("documents.csv")
    df_docs["Student_Email"] = df_docs["Student_Email"].astype(str).str.strip().str.lower()
    df_docs = df_docs[~((df_docs["Student_Email"] == student_email.lower()) & (df_docs["Document_Name"] == doc_name))]
    df_docs.to_csv("documents.csv", index=False)

def update_app_status(student_email, company_name, new_status):
    df_apps = safe_read_csv("applications.csv")
    if not df_apps.empty:
        mask = (df_apps["Student_Email"] == student_email) & (df_apps["Company_Name"] == company_name)
        df_apps.loc[mask, "Status"] = new_status
        df_apps.to_csv("applications.csv", index=False)

# ==========================================
# SESSION STATE
# ==========================================

if "student_logged_in" not in st.session_state:
    st.session_state.student_logged_in = False
    st.session_state.current_student = None
    st.session_state.company_logged_in = False
    st.session_state.current_company = None
    st.session_state.nav_override = None
    st.session_state.current_test = None
    st.session_state.test_company = None

# ==========================================
# NAVIGATION
# ==========================================

st.title("🎓 College Placement Portal")

menu = ["Student Registration", "Student Login", "Company Registration", "Company Login", "Job Board", "Placement Stats", "Admin Dashboard"]
if st.session_state.nav_override:
    default_idx = menu.index(st.session_state.nav_override) if st.session_state.nav_override in menu else 0
    st.session_state.nav_override = None
else:
    default_idx = 0

choice = st.sidebar.selectbox("Navigation", menu, index=default_idx)

# ==========================================
# 1. STUDENT REGISTRATION (no OTP)
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
        resume_file = st.file_uploader("Upload Resume (PDF/DOCX) for auto-fill (optional)", type=["pdf","docx"])
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
        df = safe_read_csv("database.csv")
        if not df.empty and email in df["Email"].str.lower().values:
            st.error("Email already registered")
            errors = True

        if not errors:
            if resume_file:
                parsed = parse_resume(resume_file.read(), resume_file.name)
                if parsed and parsed["name"]:
                    st.info(f"Parsed: {parsed['name']} – {parsed['email']}")
            hashed_pw = generate_password_hash(password)
            row = {"Name": name, "Email": email, "Password": hashed_pw, "CGPA": cgpa,
                   "Branch": branch, "Boosted": "False", "Verified": "True"}
            append_csv("database.csv", row)
            st.success("Registration successful! You can now log in.")

# ==========================================
# 2. STUDENT LOGIN (no verification required)
# ==========================================

elif choice == "Student Login":
    st.subheader("🔐 Student Login")
    if not st.session_state.student_logged_in:
        email = st.text_input("Email").strip().lower()
        pwd = st.text_input("Password", type="password")
        if st.button("Login"):
            df = safe_read_csv("database.csv")
            df["Email_clean"] = df["Email"].str.lower()
            match = df[df["Email_clean"] == email]
            if not match.empty:
                if check_password_hash(match.iloc[0]["Password"], pwd):
                    st.session_state.student_logged_in = True
                    st.session_state.current_student = match.iloc[0].to_dict()
                    st.rerun()
                else:
                    st.error("Invalid credentials")
            else:
                st.error("Email not found")
    else:
        # STUDENT DASHBOARD
        student = st.session_state.current_student
        student_email = student["Email"]
        st.success(f"✅ Welcome back, {student['Name']}!")

        with st.container(border=True):
            col1, col2 = st.columns(2)
            col1.write(f"**Branch:** {student['Branch']}")
            col1.write(f"**CGPA:** {student['CGPA']}")
            col2.write(f"**Email:** {student['Email']}")

        # Profile Boost (Stripe or demo)
        st.markdown("### 🚀 Premium Features")
        if student.get("Boosted") == "True":
            st.success("🔥 Your profile is BOOSTED! Companies see your applications first.")
        else:
            st.info("Boost your profile to appear at the top of recruiter pipelines.")
            if STRIPE_PUBLIC_KEY and STRIPE_SECRET_KEY:
                if st.button("💳 Pay ₹300 to Boost Profile (Stripe)"):
                    try:
                        checkout_session = stripe.checkout.Session.create(
                            payment_method_types=['card'],
                            line_items=[{
                                'price_data': {
                                    'currency': 'inr',
                                    'unit_amount': 30000,
                                    'product_data': {'name': 'Profile Boost'},
                                },
                                'quantity': 1,
                            }],
                            mode='payment',
                            success_url=st.secrets.get("APP_URL", "http://localhost:8501") + "?boost=success",
                            cancel_url=st.secrets.get("APP_URL", "http://localhost:8501") + "?boost=cancel",
                        )
                        st.write(f"<script>window.location.href = '{checkout_session.url}';</script>", unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"Stripe error: {e}")
            else:
                if st.button("💳 Simulate Boost (Demo)"):
                    update_csv("database.csv", lambda r: r["Email"] == student_email, {"Boosted": "True"})
                    st.session_state.current_student["Boosted"] = "True"
                    st.success("Profile boosted! (Demo)")

        st.divider()

        # Placement Statistics for Student
        st.markdown("### 📊 Placement Statistics")
        df_allocs = safe_read_csv("allocations.csv")
        df_students_all = safe_read_csv("database.csv")
        if not df_allocs.empty and not df_students_all.empty:
            merged = df_allocs.merge(df_students_all, left_on="Student_Email", right_on="Email")
            branch_data = merged[merged["Branch"] == student["Branch"]]
            if not branch_data.empty:
                pkg_nums = branch_data["Package"].str.extract(r'(\d+\.?\d*)').astype(float)
                avg_pkg = pkg_nums.mean().iloc[0] if not pkg_nums.empty else 0
                st.metric(f"Average Package for {student['Branch']}", f"{avg_pkg:.1f} LPA")
                st.bar_chart(branch_data["Company"].value_counts())
            else:
                st.info("No placement data for your branch yet.")
        else:
            st.info("No placement data available.")

        st.divider()

        # Document Upload
        st.markdown("### 📄 My Documents")
        with st.expander("➕ Upload New Document"):
            uploaded_file = st.file_uploader("Choose a file (PDF, DOCX, JPG, PNG)", type=['pdf','docx','jpg','jpeg','png'])
            doc_name = st.text_input("Document Title")
            if uploaded_file and doc_name:
                if st.button("Upload"):
                    file_path = save_uploaded_file(uploaded_file, student_email)
                    row = {"Student_Email": student_email, "Document_Name": doc_name,
                           "File_Path": file_path, "Upload_Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                    append_csv("documents.csv", row)
                    st.success("Uploaded!")
                    st.rerun()
        docs_df = get_student_documents(student_email)
        if not docs_df.empty:
            for idx, row in docs_df.iterrows():
                col1, col2 = st.columns([4,1])
                with col1:
                    st.write(f"📎 **{row['Document_Name']}** (Uploaded: {row['Upload_Date']})")
                with col2:
                    with open(row['File_Path'], "rb") as f:
                        st.download_button("📥", f, file_name=os.path.basename(row['File_Path']), key=f"dl_{idx}")
                    if st.button("🗑️", key=f"del_{idx}"):
                        delete_document(row['File_Path'], student_email, row['Document_Name'])
                        st.rerun()
        else:
            st.info("No documents uploaded.")

        st.divider()

        # My Applications
        st.markdown("### 📋 My Job Applications")
        df_apps = safe_read_csv("applications.csv")
        if not df_apps.empty:
            my_apps = df_apps[df_apps["Student_Email"].str.lower() == student_email.lower()]
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
            st.write("No applications yet.")

        st.divider()

        # Interview Slots Booking
        st.markdown("### 🗓️ Upcoming Interviews")
        df_slots = safe_read_csv("interviews.csv")
        applied_companies = df_apps[df_apps["Student_Email"].str.lower() == student_email.lower()]["Company_Name"].unique()
        available_slots = df_slots[(df_slots["Booked_By"] == "") & (df_slots["Company"].isin(applied_companies))]
        if not available_slots.empty:
            for _, slot in available_slots.iterrows():
                with st.container(border=True):
                    st.write(f"**{slot['Company']}** – {slot['Slot_Time']} ({slot['Duration']} min, {slot['Mode']})")
                    if st.button(f"Book Slot", key=f"book_{slot.name}"):
                        update_csv("interviews.csv", lambda r: r.name == slot.name, {"Booked_By": student_email, "Booking_Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
                        st.success("Slot booked!")
                        st.rerun()
        else:
            st.info("No available interview slots for companies you applied to.")

        st.divider()
        if st.button("Logout", type="primary"):
            st.session_state.student_logged_in = False
            st.session_state.current_student = None
            st.session_state.nav_override = "Job Board"
            st.rerun()

# ==========================================
# 3. COMPANY REGISTRATION
# ==========================================

elif choice == "Company Registration":
    st.subheader("🏢 Register Company")
    with st.form("comp_reg"):
        name = st.text_input("Company Name")
        email = st.text_input("Company Email").strip().lower()
        address = st.text_input("Address")
        password = st.text_input("Password", type="password")
        package = st.text_input("Package (e.g., 12 LPA)")
        min_cgpa = st.number_input("Min CGPA", 0.0, 10.0, 6.0)
        branches = st.multiselect("Eligible Branches", ["CSE","IT","ECE","MECH"])
        custom_qs = st.text_area("Custom Questions for Students (one per line)", placeholder="Why do you want to join us?\nGitHub profile link")
        submitted = st.form_submit_button("Register")
    if submitted:
        if not all([name, email, password]):
            st.error("Missing required fields")
        else:
            hashed = generate_password_hash(password)
            row = {"Company": name, "Email": email, "Address": address, "Password": hashed,
                   "Package": package, "MinCGPA": min_cgpa, "Branches": ",".join(branches),
                   "CustomQuestions": custom_qs}
            append_csv("companies.csv", row)
            st.success("Company registered!")

# ==========================================
# 4. COMPANY LOGIN (full dashboard)
# ==========================================

elif choice == "Company Login":
    if not st.session_state.company_logged_in:
        email = st.text_input("Company Email")
        pwd = st.text_input("Password", type="password")
        if st.button("Login"):
            df = safe_read_csv("companies.csv")
            match = df[df["Email"] == email]
            if not match.empty and check_password_hash(match.iloc[0]["Password"], pwd):
                st.session_state.company_logged_in = True
                st.session_state.current_company = match.iloc[0].to_dict()
                st.rerun()
            else:
                st.error("Invalid")
    else:
        comp = st.session_state.current_company
        company_name = comp["Company"]
        st.success(f"✅ Dashboard: {company_name}")
        tab1, tab2, tab3, tab4 = st.tabs(["📥 Applications", "🗓️ Interview Slots", "📝 Skill Tests", "⭐ Ratings"])

        # Tab 1: Applications
        with tab1:
            st.markdown("### Candidate Pipeline")
            df_students = safe_read_csv("database.csv")
            df_apps = safe_read_csv("applications.csv")
            df_docs = safe_read_csv("documents.csv")
            df_tests = safe_read_csv("test_results.csv")
            if not df_apps.empty:
                my_apps = df_apps[df_apps["Company_Name"] == company_name]
                if not my_apps.empty:
                    merged = my_apps.merge(df_students, left_on="Student_Email", right_on="Email")
                    merged = merged.sort_values(by="Boosted", ascending=False)
                    for status in ["Pending", "Shortlisted", "Accepted", "Rejected"]:
                        st.markdown(f"#### {status}")
                        subset = merged[merged["Status"] == status]
                        for _, row in subset.iterrows():
                            with st.container(border=True):
                                st.write(f"**{row['Name']}** (CGPA: {row['CGPA']}, Branch: {row['Branch']})")
                                test_res = df_tests[(df_tests["Student_Email"] == row["Email"]) & (df_tests["Company"] == company_name)]
                                if not test_res.empty:
                                    st.write(f"📊 Skill Test Score: {test_res.iloc[0]['Score']}% – {'Passed' if test_res.iloc[0]['Passed']=='True' else 'Failed'}")
                                if row.get("Answers"):
                                    try:
                                        answers = json.loads(row["Answers"])
                                        with st.expander("View Custom Answers"):
                                            for q, a in answers.items():
                                                st.write(f"**{q}**\n{a}")
                                    except:
                                        pass
                                student_docs = df_docs[df_docs["Student_Email"].str.lower() == row["Email"].lower()]
                                if not student_docs.empty:
                                    with st.expander("📎 Student Documents"):
                                        for _, doc in student_docs.iterrows():
                                            if os.path.exists(doc["File_Path"]):
                                                with open(doc["File_Path"], "rb") as f:
                                                    st.download_button(doc["Document_Name"], f, file_name=os.path.basename(doc["File_Path"]))
                                            else:
                                                st.warning(f"{doc['Document_Name']} (missing)")
                                if status == "Pending":
                                    col1, col2, col3 = st.columns(3)
                                    if col1.button("⭐ Shortlist", key=f"short_{row.name}"):
                                        update_app_status(row["Email"], company_name, "Shortlisted")
                                        st.rerun()
                                    if col2.button("✅ Accept", key=f"acc_{row.name}"):
                                        update_app_status(row["Email"], company_name, "Accepted")
                                        st.rerun()
                                    if col3.button("❌ Reject", key=f"rej_{row.name}"):
                                        update_app_status(row["Email"], company_name, "Rejected")
                                        st.rerun()
                                elif status == "Shortlisted":
                                    col1, col2 = st.columns(2)
                                    if col1.button("✅ Accept", key=f"acc2_{row.name}"):
                                        update_app_status(row["Email"], company_name, "Accepted")
                                        st.rerun()
                                    if col2.button("❌ Reject", key=f"rej2_{row.name}"):
                                        update_app_status(row["Email"], company_name, "Rejected")
                                        st.rerun()
                else:
                    st.info("No applications yet.")
            else:
                st.info("No applications.")

        # Tab 2: Interview Slots
        with tab2:
            st.write("### Create Interview Slot")
            slot_time = st.datetime_input("Slot Time")
            duration = st.number_input("Duration (minutes)", 15, 120, 30)
            mode = st.selectbox("Mode", ["Online", "Offline"])
            if st.button("Add Slot"):
                row = {"Company": company_name, "Slot_Time": slot_time.strftime("%Y-%m-%d %H:%M:%S"), "Duration": duration, "Mode": mode, "Booked_By": "", "Booking_Date": ""}
                append_csv("interviews.csv", row)
                st.success("Slot added")
            st.write("### Existing Slots")
            df_slots = safe_read_csv("interviews.csv")
            slots = df_slots[df_slots["Company"] == company_name]
            for _, slot in slots.iterrows():
                st.write(f"{slot['Slot_Time']} ({slot['Duration']} min, {slot['Mode']}) – Booked: {slot['Booked_By'] if slot['Booked_By'] else 'Available'}")

        # Tab 3: Skill Tests
        with tab3:
            st.write("### Create Skill Test for a Job")
            job_title = st.text_input("Job Title (e.g., SDE Intern)")
            questions = st.text_area("Questions (one per line)")
            answers = st.text_area("Answers (one per line, matching order)")
            passing_score = st.number_input("Passing Score (%)", 0, 100, 60)
            if st.button("Save Test"):
                row = {"Company": company_name, "Job_Title": job_title, "Questions": questions, "Answers": answers, "Passing_Score": passing_score}
                append_csv("skill_tests.csv", row)
                st.success("Test added")
            st.write("### Existing Tests")
            df_tests = safe_read_csv("skill_tests.csv")
            tests = df_tests[df_tests["Company"] == company_name]
            st.dataframe(tests[["Job_Title","Passing_Score"]])

        # Tab 4: Ratings
        with tab4:
            st.write("### Ratings Received")
            df_ratings = safe_read_csv("ratings.csv")
            my_ratings = df_ratings[df_ratings["Company"] == company_name]
            if not my_ratings.empty:
                st.dataframe(my_ratings[["Student_Email","Rating","Review","Date"]])
                avg = my_ratings["Rating"].astype(float).mean()
                st.metric("Average Rating", f"{avg:.2f} / 5")
            else:
                st.info("No ratings yet.")

        st.divider()
        if st.button("Logout", type="primary"):
            st.session_state.company_logged_in = False
            st.session_state.current_company = None
            st.session_state.nav_override = "Job Board"
            st.rerun()

# ==========================================
# 5. JOB BOARD
# ==========================================
elif choice == "Job Board":
    st.subheader("📢 Job Openings")
    df_comps = safe_read_csv("companies.csv")
    if df_comps.empty:
        st.info("No companies have posted jobs yet.")
    else:
        search = st.text_input("Search by company or location")
        if search:
            df_comps = df_comps[df_comps["Company"].str.contains(search, case=False) | df_comps["Address"].str.contains(search, case=False)]
        for idx, job in df_comps.iterrows():          # use idx for unique keys
            with st.container(border=True):
                st.markdown(f"### {job['Company']}")
                st.write(f"💰 Package: {job['Package']}  |  🎓 Min CGPA: {job['MinCGPA']}  |  🌿 Branches: {job['Branches']}")
                st.write(f"📍 {job['Address']}")

                if st.session_state.student_logged_in:
                    student = st.session_state.current_student
                    student_email = student["Email"]
                    try:
                        student_cgpa = float(student.get("CGPA",0))
                        min_cgpa = float(job.get("MinCGPA",0))
                    except:
                        student_cgpa = 0
                        min_cgpa = 0
                    eligible_branches = [b.strip() for b in str(job.get("Branches","")).split(",")]
                    cgpa_ok = student_cgpa >= min_cgpa
                    branch_ok = student["Branch"] in eligible_branches or eligible_branches == [""]
                    df_apps = safe_read_csv("applications.csv")
                    already_applied = not df_apps[(df_apps["Student_Email"]==student_email) & (df_apps["Company_Name"]==job["Company"])].empty

                    if already_applied:
                        st.success("✅ Application Submitted")
                    elif not cgpa_ok or not branch_ok:
                        if not cgpa_ok:
                            st.warning(f"CGPA too low ({student_cgpa} < {min_cgpa})")
                        if not branch_ok:
                            st.warning(f"Branch {student['Branch']} not eligible")
                    else:
                        # Check if skill test exists
                        df_tests = safe_read_csv("skill_tests.csv")
                        test = df_tests[df_tests["Company"] == job["Company"]]
                        # Check if student already passed the test
                        df_test_results = safe_read_csv("test_results.csv")
                        test_passed = False
                        if not df_test_results.empty:
                            student_result = df_test_results[(df_test_results["Student_Email"] == student_email) & 
                                                              (df_test_results["Company"] == job["Company"])]
                            if not student_result.empty and student_result.iloc[0]["Passed"] == "True":
                                test_passed = True

                        # If test exists and not yet passed, show test
                        if not test.empty and not test_passed:
                            st.warning("This job requires a skill test. Click below to take the test.")
                            # UNIQUE KEY: use idx
                            if st.button(f"📝 Take Test for {job['Company']}", key=f"test_{job['Company']}_{idx}"):
                                st.session_state.current_test = test.iloc[0].to_dict()
                                st.session_state.test_company = job["Company"]
                                st.rerun()
                            if st.session_state.get("test_company") == job["Company"] and st.session_state.get("current_test"):
                                test_data = st.session_state.current_test
                                st.write("### Skill Test")
                                user_answers = []
                                q_list = test_data["Questions"].split("\n")
                                for i, q in enumerate(q_list):
                                    if q.strip():
                                        # UNIQUE KEY: include idx and i
                                        ans = st.text_input(f"Q{i+1}: {q}", key=f"test_q_{idx}_{i}_{job['Company']}")
                                        user_answers.append(ans)
                                if st.button("Submit Test", key=f"submit_test_{idx}_{job['Company']}"):
                                    correct_answers = test_data["Answers"].split("\n")
                                    total = len([q for q in q_list if q.strip()])
                                    score = 0
                                    for u, c in zip(user_answers, correct_answers):
                                        if u.strip().lower() == c.strip().lower():
                                            score += 1
                                    score_percent = (score / total) * 100 if total > 0 else 0
                                    passed = score_percent >= float(test_data["Passing_Score"])
                                    res_row = {"Student_Email": student_email, "Company": job["Company"], 
                                               "Score": score_percent, "Passed": str(passed), 
                                               "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                                    append_csv("test_results.csv", res_row)
                                    if passed:
                                        st.success(f"You scored {score_percent:.1f}%. Test passed! You can now apply.")
                                    else:
                                        st.error(f"You scored {score_percent:.1f}%. Test failed. Cannot apply.")
                                    st.session_state.current_test = None
                                    st.session_state.test_company = None
                                    st.rerun()

                        # If test passed (or no test required), show application form
                        elif test.empty or test_passed:
                            custom_qs = job.get("CustomQuestions", "")
                            if custom_qs:
                                with st.form(key=f"apply_form_{job['Company']}_{idx}"):
                                    st.write("### Please answer the following questions")
                                    answers = {}
                                    for i, q in enumerate(custom_qs.split("\n")):
                                        if q.strip():
                                            ans = st.text_input(q, key=f"cq_{idx}_{i}_{job['Company']}")
                                            answers[q] = ans
                                    submitted_app = st.form_submit_button("Submit Application")
                                    if submitted_app:
                                        app_row = {"Student_Email": student_email, "Company_Name": job["Company"], 
                                                   "Status": "Pending", "Answers": json.dumps(answers), "TestScore": ""}
                                        append_csv("applications.csv", app_row)
                                        st.success("Application submitted!")
                                        st.rerun()
                            else:
                                if st.button(f"Apply to {job['Company']}", key=f"apply_{job['Company']}_{idx}"):
                                    app_row = {"Student_Email": student_email, "Company_Name": job["Company"], 
                                               "Status": "Pending", "Answers": "", "TestScore": ""}
                                    append_csv("applications.csv", app_row)
                                    st.success("Application submitted!")
                                    st.rerun()
                else:
                    st.info("Login as student to apply")

# ==========================================
# 6. PLACEMENT STATS (global)
# ==========================================

elif choice == "Placement Stats":
    st.subheader("📊 Placement Analytics")
    df_allocs = safe_read_csv("allocations.csv")
    df_students = safe_read_csv("database.csv")
    if not df_allocs.empty and not df_students.empty:
        merged = df_allocs.merge(df_students, left_on="Student_Email", right_on="Email")
        st.write("### Branch-wise Average Package")
        branch_pkg = merged.groupby("Branch")["Package"].apply(lambda x: x.str.extract(r'(\d+\.?\d*)').astype(float).mean())
        st.bar_chart(branch_pkg)
        st.write("### Top Recruiters")
        st.bar_chart(merged["Company"].value_counts().head(5))
        st.write("### Placement Over Time")
        merged["Date"] = pd.to_datetime(merged["Date"], errors='coerce')
        placements_by_month = merged.groupby(merged["Date"].dt.to_period("M")).size()
        st.line_chart(placements_by_month)
    else:
        st.info("No placement data available")

# ==========================================
# 7. ADMIN DASHBOARD
# ==========================================

elif choice == "Admin Dashboard":
    st.subheader("⚙️ Admin Panel")
    pwd = st.text_input("Admin Password", type="password")
    if pwd == ADMIN_PASSWORD:
        st.success("Logged in as Admin")
        log_admin_action("Admin login")
        t1, t2, t3, t4, t5 = st.tabs(["Export Data", "Bulk Import", "Audit Logs", "Ratings & Reviews", "Danger Zone"])
        with t1:
            st.write("Download CSV files")
            files = ["database.csv","companies.csv","applications.csv","allocations.csv","documents.csv","interviews.csv","ratings.csv","skill_tests.csv","test_results.csv","audit_logs.csv"]
            for f in files:
                if os.path.exists(f):
                    with open(f, "rb") as file:
                        st.download_button(f"Download {f}", file, file_name=f)
        with t2:
            st.write("Bulk Import Students (CSV)")
            uploaded = st.file_uploader("Upload CSV with columns: Name,Email,Password,CGPA,Branch", type="csv")
            if uploaded:
                df_new = pd.read_csv(uploaded)
                required = ["Name","Email","Password","CGPA","Branch"]
                if all(col in df_new.columns for col in required):
                    for col in ["Boosted","Verified"]:
                        if col not in df_new.columns:
                            df_new[col] = ""
                    df_existing = safe_read_csv("database.csv")
                    df_combined = pd.concat([df_existing, df_new], ignore_index=True)
                    df_combined.to_csv("database.csv", index=False)
                    st.success(f"Added {len(df_new)} students")
                    log_admin_action(f"Bulk imported {len(df_new)} students")
                else:
                    st.error("CSV missing required columns")
        with t3:
            st.write("Audit Logs")
            logs = safe_read_csv("audit_logs.csv")
            st.dataframe(logs)
        with t4:
            st.write("Ratings & Reviews")
            df_ratings = safe_read_csv("ratings.csv")
            if not df_ratings.empty:
                st.dataframe(df_ratings)
                rating_to_delete = st.selectbox("Select rating to delete (by Student_Email, Company)", df_ratings.apply(lambda r: f"{r['Student_Email']} - {r['Company']}", axis=1).unique())
                if st.button("Delete Selected Rating"):
                    df_ratings = df_ratings[~((df_ratings["Student_Email"] + " - " + df_ratings["Company"]) == rating_to_delete)]
                    df_ratings.to_csv("ratings.csv", index=False)
                    st.success("Deleted")
                    log_admin_action(f"Deleted rating: {rating_to_delete}")
                    st.rerun()
            else:
                st.info("No ratings yet.")
        with t5:
            st.error("⚠️ Danger Zone")
            if st.button("Wipe ALL Data (Students, Companies, Applications, etc.)"):
                for f in os.listdir("."):
                    if f.endswith(".csv"):
                        os.remove(f)
                if os.path.exists("uploads"):
                    shutil.rmtree("uploads")
                init_db()
                migrate_existing_students()
                st.success("All data wiped")
                log_admin_action("Wiped entire database")
                st.rerun()
    else:
        if pwd:
            st.error("Wrong password")

# ==========================================
# END OF APP
# ==========================================