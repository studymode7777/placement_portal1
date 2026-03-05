import streamlit as st
import pandas as pd
import os
from io import BytesIO

# Try importing reportlab for PDF generation
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

st.set_page_config(page_title="Placement Portal", layout="centered", page_icon="🎓")

# ==========================================
# HELPER FUNCTIONS & DB INITIALIZATION
# ==========================================

def init_db():
    """Create empty CSV files with correct headers if they don't exist."""
    if not os.path.exists("database.csv"):
        pd.DataFrame(columns=["Name", "Email", "Password", "CGPA", "Branch"]).to_csv("database.csv", index=False)
    if not os.path.exists("companies.csv"):
        pd.DataFrame(columns=["Company", "Email", "Address", "Password", "Package", "Criteria"]).to_csv("companies.csv", index=False)
    if not os.path.exists("allocations.csv"):
        pd.DataFrame(columns=["Student_Email", "Company", "Package", "Date"]).to_csv("allocations.csv", index=False)

init_db() # Run on startup

def safe_read_csv(path):
    try:
        df = pd.read_csv(path, on_bad_lines='skip')
        return df.fillna("")
    except Exception as err:
        st.error(f"Error loading {path}: {err}")
        return pd.DataFrame()

def append_csv(path, row_dict, cols_order):
    df = safe_read_csv(path)
    # Ensure password is treated as a string
    if "Password" in row_dict:
        row_dict["Password"] = str(row_dict["Password"]).strip()
    
    new_row = pd.DataFrame([row_dict])
    df = pd.concat([df, new_row], ignore_index=True)
    
    # Fill any NaNs created by concatenation and reorder
    df = df.fillna("")
    for col in cols_order:
        if col not in df.columns:
            df[col] = ""
    df = df[cols_order]
    
    df.to_csv(path, index=False)

# Initialize Session States for Logins
if "student_logged_in" not in st.session_state:
    st.session_state.student_logged_in = False
    st.session_state.current_student = None

if "company_logged_in" not in st.session_state:
    st.session_state.company_logged_in = False
    st.session_state.current_company = None


# ==========================================
# NAVIGATION
# ==========================================
st.title("🎓 College Placement Portal")

menu = ["Student Registration", "Student Login", "Company Registration", "Company Login", "Job Board", "Admin Dashboard"]
choice = st.sidebar.selectbox("Navigation", menu)

# ==========================================
# 1. STUDENT REGISTRATION & RESUME
# ==========================================
if choice == "Student Registration":
    st.subheader("📚 Student Portal")
    
    tab1, tab2 = st.tabs(["Register", "Build Resume"])
    
    # TAB 1: Registration Form
    with tab1:
        st.write("Complete your basic details for placement registration.")
        with st.form("reg_form"):
            name = st.text_input("Full Name")
            email = st.text_input("College Email").strip().lower()
            password = st.text_input("Set Password", type="password")
            confirm = st.text_input("Confirm Password", type="password")
            cgpa = st.number_input("Current CGPA", min_value=0.0, max_value=10.0, step=0.1)
            branch = st.selectbox("Branch", ["CSE", "IT", "ECE", "MECH"])
            
            if st.form_submit_button("Submit Application"):
                if not name or not email or not password:
                    st.error("Please fill all mandatory fields.")
                elif password != confirm:
                    st.error("Passwords do not match.")
                else:
                    df_students = safe_read_csv("database.csv")
                    if email in df_students["Email"].values:
                        st.error("Email already registered! Please login.")
                    else:
                        row = {"Name": name, "Email": email, "Password": password, "CGPA": cgpa, "Branch": branch}
                        append_csv("database.csv", row, ["Name","Email","Password","CGPA","Branch"])
                        st.success(f"Best of luck, {name}! Your data has been saved.")

    # TAB 2: Resume Builder
    with tab2:
        st.write("Fill in your details and download a formatted resume.")
        with st.form("resume_form"):
            r_name = st.text_input("Full Name")
            r_email = st.text_input("Email")
            r_phone = st.text_input("Phone Number")
            r_summary = st.text_area("Professional Summary")
            r_education = st.text_area("Education (one entry per line)")
            r_skills = st.text_area("Skills (comma separated)")
            r_projects = st.text_area("Projects (one per line)")
            build = st.form_submit_button("Generate Resume")
            
        if build:
            if not REPORTLAB_AVAILABLE:
                st.error("Please install reportlab to generate PDFs: `pip install reportlab`")
            elif not r_name or not r_email:
                st.error("Name and Email are required.")
            else:
                # PDF Generation Logic
                pdf_buffer = BytesIO()
                doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
                story = []
                styles = getSampleStyleSheet()
                
                title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor('#1f77b4'), spaceAfter=6, alignment=1)
                story.append(Paragraph(r_name, title_style))
                story.append(Paragraph(f"<b>Email:</b> {r_email} | <b>Phone:</b> {r_phone}", styles['Normal']))
                story.append(Spacer(1, 0.2*inch))
                
                if r_summary:
                    story.append(Paragraph("<b>Professional Summary</b>", styles['Heading2']))
                    story.append(Paragraph(r_summary, styles['Normal']))
                    story.append(Spacer(1, 0.1*inch))
                
                if r_education:
                    story.append(Paragraph("<b>Education</b>", styles['Heading2']))
                    for line in r_education.strip().splitlines():
                        story.append(Paragraph(f"• {line}", styles['Normal']))
                    story.append(Spacer(1, 0.1*inch))
                    
                if r_skills:
                    story.append(Paragraph("<b>Skills</b>", styles['Heading2']))
                    story.append(Paragraph(r_skills, styles['Normal']))
                    story.append(Spacer(1, 0.1*inch))
                    
                if r_projects:
                    story.append(Paragraph("<b>Projects</b>", styles['Heading2']))
                    for line in r_projects.strip().splitlines():
                        story.append(Paragraph(f"• {line}", styles['Normal']))
                
                doc.build(story)
                pdf_bytes = pdf_buffer.getvalue()
                
                st.success("Resume Generated Successfully!")
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
        email = st.text_input("College Email").strip().lower()
        pwd = st.text_input("Password", type="password").strip()
        
        if st.button("Login"):
            df_students = safe_read_csv("database.csv")
            df_students["Password"] = df_students["Password"].astype(str).str.strip()
            
            match = df_students[(df_students["Email"].str.lower() == email) & (df_students["Password"] == pwd)]
            
            if not match.empty:
                st.session_state.student_logged_in = True
                st.session_state.current_student = match.iloc[0].to_dict()
                st.rerun()
            else:
                st.error("❌ Invalid Email or Password.")
    else:
        student = st.session_state.current_student
        st.success(f"✅ Welcome back, {student['Name']}!")
        
        with st.container(border=True):
            col1, col2 = st.columns(2)
            col1.write(f"**Branch:** {student['Branch']}")
            col1.write(f"**CGPA:** {student['CGPA']}")
            col2.write(f"**Email:** {student['Email']}")
        
        st.markdown("### 🏆 Allocation Status")
        df_alloc = safe_read_csv("allocations.csv")
        my_alloc = df_alloc[df_alloc["Student_Email"].str.lower() == student["Email"].lower()]
        
        if not my_alloc.empty:
            alloc_data = my_alloc.iloc[0]
            st.success("🎉 **Status: PLACED**")
            st.write(f"**Company:** {alloc_data['Company']}")
            st.write(f"**Package:** {alloc_data['Package']}")
            st.write(f"**Joining Date:** {alloc_data['Date']}")
        else:
            st.info("⏳ Status: Pending. Keep applying and checking back!")
            
        if st.button("Logout", type="primary"):
            st.session_state.student_logged_in = False
            st.session_state.current_student = None
            st.rerun()

# ==========================================
# 3. COMPANY REGISTRATION
# ==========================================
elif choice == "Company Registration":
    st.subheader("🏢 Post a Job Opening")
    with st.form("company_form"):
        company_name = st.text_input("Company Name")
        company_email = st.text_input("Company Email").strip().lower()
        address = st.text_input("Company Address")
        password = st.text_input("Set Password", type="password")
        package = st.text_input("Salary Package (e.g., 10 LPA)")
        criteria = st.text_input("Eligibility Criteria (e.g., 8.0 CGPA)")
        
        if st.form_submit_button("Register Company"):
            if not company_name or not company_email or not password:
                st.error("Name, Email, and Password are required.")
            else:
                df_comps = safe_read_csv("companies.csv")
                if company_email in df_comps["Email"].values:
                    st.error("Company Email already registered!")
                else:
                    row = {"Company": company_name, "Email": company_email, "Address": address, 
                           "Password": password, "Package": package, "Criteria": criteria}
                    append_csv("companies.csv", row, ["Company","Email","Address","Password","Package","Criteria"])
                    st.success(f"Job drive for {company_name} posted successfully!")

# ==========================================
# 4. COMPANY LOGIN
# ==========================================
elif choice == "Company Login":
    st.subheader("🏢 Company Dashboard")
    
    if not st.session_state.company_logged_in:
        email = st.text_input("Company Email").strip().lower()
        pwd = st.text_input("Password", type="password").strip()
        
        if st.button("Login"):
            df_comps = safe_read_csv("companies.csv")
            df_comps["Password"] = df_comps["Password"].astype(str).str.strip()
            
            match = df_comps[(df_comps["Email"].str.lower() == email) & (df_comps["Password"] == pwd)]
            
            if not match.empty:
                st.session_state.company_logged_in = True
                st.session_state.current_company = match.iloc[0].to_dict()
                st.rerun()
            else:
                st.error("❌ Invalid Email or Password.")
    else:
        comp = st.session_state.current_company
        st.success(f"✅ Dashboard: {comp['Company']}")
        
        with st.container(border=True):
            st.write(f"**Active Posting Package:** {comp['Package']}")
            st.write(f"**Criteria:** {comp['Criteria']}")
        
        st.markdown("### 👥 Student Pool")
        df_students = safe_read_csv("database.csv")
        
        if not df_students.empty:
            for idx, student in df_students.iterrows():
                with st.expander(f"📄 {student['Name']} - {student['Branch']} (CGPA: {student['CGPA']})"):
                    st.write(f"**Email:** {student['Email']}")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"✉️ Contact", key=f"contact_{idx}"):
                            st.success(f"Notification sent to {student['Name']}!")
                    with col2:
                        if st.button(f"⭐ Shortlist", key=f"shortlist_{idx}"):
                            st.info(f"{student['Name']} added to shortlist.")
        else:
            st.info("No students registered yet.")
            
        if st.button("Logout", type="primary"):
            st.session_state.company_logged_in = False
            st.session_state.current_company = None
            st.rerun()

# ==========================================
# 5. JOB BOARD
# ==========================================
elif choice == "Job Board":
    st.subheader("📢 Hiring Companies & Job Openings")
    df_comps = safe_read_csv("companies.csv")
    
    if not df_comps.empty:
        for idx, row in df_comps.iterrows():
            with st.container(border=True):
                st.markdown(f"#### {row['Company']}")
                st.write(f"**💰 Package:** {row['Package']} | **🎯 Eligibility:** {row['Criteria']}")
                st.write(f"📍 **Location:** {row['Address']}")
    else:
        st.info("No companies have posted job drives yet.")

# ==========================================
# 6. ADMIN DASHBOARD
# ==========================================
elif choice == "Admin Dashboard":
    st.subheader("⚙️ Admin Access")
    
    pwd = st.text_input("Admin Password", type="password")
    
    if pwd == "admin123": # Changed from college123 to standard admin123
        df_students = safe_read_csv("database.csv")
        df_comps = safe_read_csv("companies.csv")
        df_allocs = safe_read_csv("allocations.csv")
        
        st.write("### 📊 Portal Analytics")
        c1, c2, c3 = st.columns(3)
        c1.metric("Registered Students", len(df_students))
        c2.metric("Partner Companies", len(df_comps))
        c3.metric("Successful Placements", len(df_allocs))
        
        st.divider()
        
        t1, t2, t3, t4 = st.tabs(["Students", "Companies", "Allocations", "Danger Zone"])
        
        with t1:
            st.dataframe(df_students.drop(columns=["Password"], errors='ignore'), use_container_width=True)
            
        with t2:
            st.dataframe(df_comps.drop(columns=["Password"], errors='ignore'), use_container_width=True)
            
        with t3:
            st.write("### Assign Student to Company")
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
            st.dataframe(df_allocs, use_container_width=True)
            
        with t4:
            st.error("⚠️ Danger Zone: Actions cannot be undone.")
            if st.button("Wipe All Student Data"):
                os.remove("database.csv")
                init_db()
                st.success("Student database cleared.")
                st.rerun()
            if st.button("Wipe All Placements"):
                os.remove("allocations.csv")
                init_db()
                st.success("Allocations cleared.")
                st.rerun()
                
    elif pwd:
        st.error("Incorrect Admin Password.")