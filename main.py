import streamlit as st
import pandas as pd
import os
import time
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

st.set_page_config(page_title="College Placement Portal", layout="centered", page_icon="🎓")

# ==========================================
# HELPER FUNCTIONS & DB INITIALIZATION
# ==========================================

def init_db():
    """Create empty CSV files with correct headers if they don't exist."""
    # UPDATED: Added 'Boosted' column to database
    if not os.path.exists("database.csv"):
        pd.DataFrame(columns=["Name", "Email", "Password", "CGPA", "Branch", "Boosted"]).to_csv("database.csv", index=False)
    if not os.path.exists("companies.csv"):
        pd.DataFrame(columns=["Company", "Email", "Address", "Password", "Package", "Criteria"]).to_csv("companies.csv", index=False)
    if not os.path.exists("allocations.csv"):
        pd.DataFrame(columns=["Student_Email", "Company", "Package", "Date"]).to_csv("allocations.csv", index=False)
    if not os.path.exists("applications.csv"):
        pd.DataFrame(columns=["Student_Email", "Company_Name", "Status"]).to_csv("applications.csv", index=False)

init_db() # Run on startup

def safe_read_csv(path):
    try:
        df = pd.read_csv(path, on_bad_lines='skip')
        
        # --- ROBUST FIX: Automatically upgrade old CSV files ---
        if path == "applications.csv" and "Status" not in df.columns:
            df["Status"] = "Pending"
        if path == "database.csv" and "Boosted" not in df.columns:
            df["Boosted"] = "False"
            
        return df.fillna("")
    except Exception:
        return pd.DataFrame()

def append_csv(path, row_dict, cols_order):
    df = safe_read_csv(path)
    if "Password" in row_dict:
        row_dict["Password"] = str(row_dict["Password"]).strip()
    
    new_row = pd.DataFrame([row_dict])
    if not df.empty:
        df = pd.concat([df, new_row], ignore_index=True)
    else:
        df = new_row
    
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
                    if not df_students.empty and email in df_students["Email"].values:
                        st.error("Email already registered! Please login.")
                    else:
                        # Ensure new students start as not boosted
                        row = {"Name": name, "Email": email, "Password": password, "CGPA": cgpa, "Branch": branch, "Boosted": "False"}
                        append_csv("database.csv", row, ["Name","Email","Password","CGPA","Branch","Boosted"])
                        st.success(f"Best of luck, {name}! Your data has been saved.")

    with tab2:
        st.write("Fill in your details and download a formatted resume.")
        with st.form("resume_form"):
            r_name = st.text_input("Full Name")
            r_email = st.text_input("Email")
            r_phone = st.text_input("Phone Number")
            r_summary = st.text_area("Professional Summary")
            r_education = st.text_area("Education")
            r_skills = st.text_area("Skills (comma separated)")
            r_projects = st.text_area("Projects (one per line)")
            build = st.form_submit_button("Generate Resume")
            
        if build:
            if not REPORTLAB_AVAILABLE:
                st.error("Please install reportlab to generate PDFs: `pip install reportlab`")
            elif not r_name or not r_email:
                st.error("Name and Email are required.")
            else:
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
                st.download_button(label="📥 Download Resume (PDF)", data=pdf_bytes, file_name=f"{r_name.replace(' ', '_')}_Resume.pdf", mime="application/pdf")

# ==========================================
# 2. STUDENT LOGIN (WITH PROFILE BOOST FEATURE)
# ==========================================
elif choice == "Student Login":
    st.subheader("🔐 Student Login")
    
    if not st.session_state.student_logged_in:
        email = st.text_input("College Email").strip().lower()
        pwd = st.text_input("Password", type="password").strip()
        
        if st.button("Login"):
            df_students = safe_read_csv("database.csv")
            if not df_students.empty:
                df_students["Password"] = df_students["Password"].astype(str).str.strip()
                match = df_students[(df_students["Email"].str.lower() == email) & (df_students["Password"] == pwd)]
                
                if not match.empty:
                    st.session_state.student_logged_in = True
                    st.session_state.current_student = match.iloc[0].to_dict()
                    st.rerun()
                else:
                    st.error("❌ Invalid Email or Password.")
            else:
                st.error("❌ No students registered yet.")
    else:
        # Refresh student data from DB to get accurate Boost status
        df_students = safe_read_csv("database.csv")
        student_email = st.session_state.current_student["Email"]
        student = df_students[df_students["Email"] == student_email].iloc[0].to_dict()
        
        st.success(f"✅ Welcome back, {student['Name']}!")
        
        with st.container(border=True):
            col1, col2 = st.columns(2)
            col1.write(f"**Branch:** {student['Branch']}")
            col1.write(f"**CGPA:** {student['CGPA']}")
            col2.write(f"**Email:** {student['Email']}")
        
        # --- NEW FEATURE: PROFILE BOOST ---
        st.markdown("### 🚀 Premium Features")
        if student.get("Boosted") == "True":
            st.success("🔥 Your profile is BOOSTED! Companies will see your applications at the top of their lists.")
        else:
            st.info("Want to stand out? Boost your profile to appear at the top of recruiter pipelines!")
            if st.button("💳 Pay ₹499 to Boost Profile"):
                with st.spinner("Processing secure payment..."):
                    time.sleep(1.5) # Simulate payment delay
                    
                    # Update DB
                    df_students.loc[df_students["Email"] == student["Email"], "Boosted"] = "True"
                    df_students.to_csv("database.csv", index=False)
                    
                    st.success("Payment Successful! Your profile is now prioritized.")
                    st.rerun()
                    
        st.divider()
        
        st.markdown("### 📋 My Job Applications")
        df_apps = safe_read_csv("applications.csv")
        
        if not df_apps.empty:
            my_apps = df_apps[df_apps["Student_Email"].str.lower() == student["Email"].lower()]
            if not my_apps.empty:
                for idx, app in my_apps.iterrows():
                    status = app['Status']
                    if status == "Accepted":
                        st.success(f"🎉 **{app['Company_Name']}** - Status: **{status}**")
                    elif status == "Rejected":
                        st.error(f"❌ **{app['Company_Name']}** - Status: **{status}**")
                    elif status == "Shortlisted":
                        st.warning(f"⭐ **{app['Company_Name']}** - Status: **{status}**")
                    else:
                        st.info(f"⏳ **{app['Company_Name']}** - Status: **{status}**")
            else:
                st.write("You haven't applied to any jobs yet. Check the Job Board!")
        else:
            st.write("You haven't applied to any jobs yet. Check the Job Board!")
            
        st.markdown("---")
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
                if not df_comps.empty and company_email in df_comps["Email"].values:
                    st.error("Company Email already registered!")
                else:
                    row = {"Company": company_name, "Email": company_email, "Address": address, 
                           "Password": password, "Package": package, "Criteria": criteria}
                    append_csv("companies.csv", row, ["Company","Email","Address","Password","Package","Criteria"])
                    st.success(f"Job drive for {company_name} posted successfully!")

# ==========================================
# 4. COMPANY LOGIN (SORTS BOOSTED STUDENTS FIRST)
# ==========================================
elif choice == "Company Login":
    st.subheader("🏢 Company Dashboard")
    
    if not st.session_state.company_logged_in:
        email = st.text_input("Company Email").strip().lower()
        pwd = st.text_input("Password", type="password").strip()
        
        if st.button("Login"):
            df_comps = safe_read_csv("companies.csv")
            if not df_comps.empty:
                df_comps["Password"] = df_comps["Password"].astype(str).str.strip()
                match = df_comps[(df_comps["Email"].str.lower() == email) & (df_comps["Password"] == pwd)]
                
                if not match.empty:
                    st.session_state.company_logged_in = True
                    st.session_state.current_company = match.iloc[0].to_dict()
                    st.rerun()
                else:
                    st.error("❌ Invalid Email or Password.")
            else:
                st.error("❌ No companies registered yet.")
    else:
        comp = st.session_state.current_company
        company_name = comp['Company']
        st.success(f"✅ Dashboard: {company_name}")
        
        with st.container(border=True):
            st.write(f"**Active Posting Package:** {comp['Package']}")
            st.write(f"**Criteria:** {comp['Criteria']}")
        
        st.markdown("### 📥 Candidate Pipeline")
        df_students = safe_read_csv("database.csv")
        df_apps = safe_read_csv("applications.csv")
        
        if not df_apps.empty and not df_students.empty:
            my_apps = df_apps[df_apps["Company_Name"] == company_name]
            
            if not my_apps.empty:
                # Merge applications with student database to easily sort and filter
                merged_data = pd.merge(my_apps, df_students, left_on="Student_Email", right_on="Email")
                # SORTING: Ensure Boosted=="True" comes first!
                merged_data = merged_data.sort_values(by="Boosted", ascending=False)
                
                col_pending, col_shortlist = st.columns(2)
                
                # --- LEFT COLUMN: NEW APPLICATIONS ---
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

                # --- RIGHT COLUMN: SHORTLISTED ---
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
                
                # --- BOTTOM: PROCESSED HISTORY ---
                st.divider()
                st.markdown("#### 🗄️ Processed Candidates")
                processed_apps = merged_data[merged_data["Status"].isin(["Accepted", "Rejected"])]
                
                if not processed_apps.empty:
                    for idx, row in processed_apps.iterrows():
                        status_icon = "✅" if row["Status"] == "Accepted" else "❌"
                        st.write(f"{status_icon} **{row['Name']}** - {row['Status']}")
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
            st.rerun()

# ==========================================
# 5. JOB BOARD (WITH SMART FILTERS)
# ==========================================
elif choice == "Job Board":
    st.subheader("📢 Hiring Companies & Job Openings")
    df_comps = safe_read_csv("companies.csv")
    
    if not df_comps.empty:
        # --- NEW FEATURE: SMART FILTERS ---
        with st.expander("🔍 Filter & Search Jobs", expanded=True):
            search_query = st.text_input("Search by Company Name, Role, or Location").lower()
            
        # Apply the filter logic
        display_df = df_comps.copy()
        if search_query:
            # Check if the search query is in the Company, Address, or Criteria column
            mask = (
                display_df['Company'].astype(str).str.lower().str.contains(search_query) |
                display_df['Address'].astype(str).str.lower().str.contains(search_query) |
                display_df['Criteria'].astype(str).str.lower().str.contains(search_query)
            )
            display_df = display_df[mask]

        # Display the filtered jobs
        if not display_df.empty:
            for idx, row in display_df.iterrows():
                with st.container(border=True):
                    st.markdown(f"### {row['Company']}")
                    st.write(f"**💰 Package:** {row['Package']} | **🎯 Eligibility:** {row['Criteria']}")
                    st.write(f"📍 **Location:** {row['Address']}")
                    
                    if st.session_state.student_logged_in:
                        student_email = st.session_state.current_student["Email"]
                        company_name = row['Company']
                        
                        df_apps = safe_read_csv("applications.csv")
                        already_applied = False
                        if not df_apps.empty:
                            already_applied = not df_apps[(df_apps["Student_Email"] == student_email) & (df_apps["Company_Name"] == company_name)].empty
                        
                        if already_applied:
                            st.success("✅ Application Submitted")
                        else:
                            if st.button(f"Apply to {company_name}", key=f"apply_{company_name}"):
                                new_app = {"Student_Email": student_email, "Company_Name": company_name, "Status": "Pending"}
                                append_csv("applications.csv", new_app, ["Student_Email", "Company_Name", "Status"])
                                st.success(f"Successfully applied to {company_name}!")
                                st.rerun()
                    elif not st.session_state.company_logged_in:
                        st.info("Log in as a student to apply.")
        else:
            st.warning("No jobs found matching your search criteria.")
    else:
        st.info("No companies have posted job drives yet.")

# ==========================================
# 6. ADMIN DASHBOARD
# ==========================================
elif choice == "Admin Dashboard":
    st.subheader("⚙️ Admin Access & Recovery")
    
    pwd = st.text_input("Admin Password", type="password")
    
    if pwd == "admin123":
        df_students = safe_read_csv("database.csv")
        df_comps = safe_read_csv("companies.csv")
        df_allocs = safe_read_csv("allocations.csv")
        df_apps = safe_read_csv("applications.csv")
        
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
                branch_counts = df_students["Branch"].value_counts()
                st.bar_chart(branch_counts, color="#1f77b4")
            else:
                st.info("Not enough student data to generate chart.")
                
        with chart_col2:
            st.write("**Applications per Company**")
            if not df_apps.empty and "Company_Name" in df_apps.columns:
                app_counts = df_apps["Company_Name"].value_counts()
                st.bar_chart(app_counts, color="#ff7f0e")
            else:
                st.info("Not enough application data to generate chart.")
                
        st.divider()
        st.warning("🔒 **Admin View Active:** Account passwords are now visible for recovery purposes.")
        
        t1, t2, t3, t4 = st.tabs(["Students", "Companies", "Allocations", "Danger Zone"])
        
        with t1:
            if not df_students.empty:
                st.dataframe(df_students, use_container_width=True)
            else:
                st.info("No students registered.")
            
        with t2:
            if not df_comps.empty:
                st.dataframe(df_comps, use_container_width=True)
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
            st.error("⚠️ Danger Zone: Actions cannot be undone.")
            if st.button("Wipe All Student Data"):
                if os.path.exists("database.csv"): os.remove("database.csv")
                if os.path.exists("applications.csv"): os.remove("applications.csv")
                init_db()
                st.success("Student database and applications cleared.")
                st.rerun()
            if st.button("Wipe All Placements"):
                if os.path.exists("allocations.csv"): os.remove("allocations.csv")
                init_db()
                st.success("Allocations cleared.")
                st.rerun()
                
    elif pwd:
        st.error("Incorrect Admin Password.")