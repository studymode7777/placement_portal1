import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Placement Portal", layout="centered")

st.title("🎓 College Placement Portal")
st.write("Welcome! Register your details or view upcoming company drives.")

# helper for robust CSV reading
import pandas as _pd

def safe_read_csv(path, **kwargs):
    try:
        return _pd.read_csv(path, on_bad_lines='skip', **kwargs)
    except Exception as err:
        st.error(f"Error loading {path}: {err}")
        return _pd.DataFrame()

# columns ensuring for older files

def ensure_columns(df, cols):
    """Make sure dataframe contains at least the listed columns (fill empty where missing)."""
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    return df

# helpers to append rows with schema patching

def append_csv(path, row_dict, cols_order=None):
    """Append a row to csv; if file exists ensure columns include row keys and cols_order."""
    df_row = _pd.DataFrame([row_dict])
    if os.path.exists(path):
        existing = safe_read_csv(path)
        # unify columns
        for col in df_row.columns:
            if col not in existing.columns:
                existing[col] = ""
        for col in existing.columns:
            if col not in df_row.columns:
                df_row[col] = ""
        # re-order if requested
        if cols_order:
            existing = existing.reindex(columns=cols_order)
            df_row = df_row.reindex(columns=cols_order)
        # write back full file then append new row
        existing.to_csv(path, index=False)
        df_row.to_csv(path, mode='a', index=False, header=False)
    else:
        # write new file with row
        if cols_order:
            df_row = df_row.reindex(columns=cols_order)
        df_row.to_csv(path, index=False)

# alias the safe reader for convenience
pd_read = safe_read_csv

# We updated the menu to include the new features
menu = ["Student Registration", "Student Login", "Company Registration", "Company Login", "Job Board", "Admin Dashboard"]
choice = st.sidebar.selectbox("Navigation", menu)

# ==========================================
# 1. STUDENT REGISTRATION PAGE
# ==========================================
if choice == "Student Registration":
    st.subheader("📚 Student Portal")
    
    tab1, tab2 = st.tabs(["Register", "Build Resume"])
    
    # TAB 1: Registration Form
    with tab1:
        st.write("Complete your basic details for placement registration.")
        with st.form("reg_form"):
            name = st.text_input("Full Name")
            email = st.text_input("College Email")
            password = st.text_input("Set Password", type="password")
            cgpa = st.number_input("Current CGPA", min_value=0.0, max_value=10.0, step=0.1)
            branch = st.selectbox("Branch", ["CSE", "IT", "ECE", "MECH"])
            
            submitted = st.form_submit_button("Submit Application")
            
            if submitted:
                row = {"Name": name, "Email": email, "Password": password, "CGPA": cgpa, "Branch": branch}
                append_csv("database.csv", row, cols_order=["Name","Email","Password","CGPA","Branch"])
                
                st.success(f"Best of luck, {name}! Your data has been permanently saved.")
    
    # TAB 2: Resume Builder
    with tab2:
        st.write("Fill in your details and download a formatted resume.")
        
        with st.form("resume_form"):
            r_name = st.text_input("Full Name")
            r_email = st.text_input("Email")
            r_phone = st.text_input("Phone Number")
            r_summary = st.text_area("Professional Summary", height=100)
            r_education = st.text_area("Education (one entry per line, e.g. B.Tech CSE, 2023)", height=100)
            r_skills = st.text_area("Skills (comma separated)", height=100)
            r_projects = st.text_area("Projects (one per line)", height=100)
            build = st.form_submit_button("Build Resume")
        
        if build:
            errors = []
            if not r_name.strip():
                errors.append("Name cannot be empty.")
            if "@" not in r_email or not r_email.strip():
                errors.append("Please provide a valid email address.")
            if not r_phone.isdigit() or len(r_phone) < 10:
                errors.append("Phone number should be at least 10 digits and contain only numbers.")
            if not r_skills.strip():
                errors.append("Add at least one skill.")
            
            if errors:
                for err in errors:
                    st.error(err)
            else:
                # preview resume as markdown
                md = f"## {r_name}\n"
                md += f"**Email:** {r_email}  \\n"
                md += f"**Phone:** {r_phone}  \n\n"
                if r_summary.strip():
                    md += f"**Summary**\n{r_summary}\n\n"
                if r_education.strip():
                    md += "**Education**\n"
                    for line in r_education.strip().splitlines():
                        md += f"- {line}\n"
                    md += "\n"
                if r_skills.strip():
                    md += "**Skills**\n"
                    for skill in r_skills.split(","):
                        md += f"- {skill.strip()}\n"
                    md += "\n"
                if r_projects.strip():
                    md += "**Projects**\n"
                    for line in r_projects.strip().splitlines():
                        md += f"- {line}\n"
                    md += "\n"
                st.markdown(md)
                
                # generate PDF
                try:
                    from reportlab.lib.pagesizes import letter
                    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                    from reportlab.lib.units import inch
                    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
                    from reportlab.lib import colors
                    from io import BytesIO
                    
                    pdf_buffer = BytesIO()
                    doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
                    
                    story = []
                    styles = getSampleStyleSheet()
                    
                    # Title
                    title_style = ParagraphStyle(
                        'CustomTitle',
                        parent=styles['Heading1'],
                        fontSize=18,
                        textColor=colors.HexColor('#1f77b4'),
                        spaceAfter=6,
                        alignment=1
                    )
                    story.append(Paragraph(r_name, title_style))
                    
                    # Contact Info
                    contact_style = ParagraphStyle(
                        'Contact',
                        parent=styles['Normal'],
                        fontSize=10,
                        alignment=1
                    )
                    story.append(Paragraph(f"<b>Email:</b> {r_email} | <b>Phone:</b> {r_phone}", contact_style))
                    story.append(Spacer(1, 0.2*inch))
                    
                    # Summary
                    if r_summary.strip():
                        story.append(Paragraph("<b>Professional Summary</b>", styles['Heading2']))
                        story.append(Paragraph(r_summary, styles['Normal']))
                        story.append(Spacer(1, 0.15*inch))
                    
                    # Education
                    if r_education.strip():
                        story.append(Paragraph("<b>Education</b>", styles['Heading2']))
                        for line in r_education.strip().splitlines():
                            story.append(Paragraph(f"• {line}", styles['Normal']))
                        story.append(Spacer(1, 0.15*inch))
                    
                    # Skills
                    if r_skills.strip():
                        story.append(Paragraph("<b>Skills</b>", styles['Heading2']))
                        skills_list = ", ".join([s.strip() for s in r_skills.split(",")])
                        story.append(Paragraph(skills_list, styles['Normal']))
                        story.append(Spacer(1, 0.15*inch))
                    
                    # Projects
                    if r_projects.strip():
                        story.append(Paragraph("<b>Projects</b>", styles['Heading2']))
                        for line in r_projects.strip().splitlines():
                            story.append(Paragraph(f"• {line}", styles['Normal']))
                        story.append(Spacer(1, 0.15*inch))
                    
                    # Build PDF
                    doc.build(story)
                    pdf_bytes = pdf_buffer.getvalue()
                    st.download_button("📥 Download Resume (PDF)", data=pdf_bytes, file_name="resume.pdf", mime="application/pdf")
                except ImportError:
                    st.warning("PDF generation requires the 'reportlab' package. Install it from requirements.")

# ==========================================
# 3. COMPANY REGISTRATION PAGE (NEW)
# ==========================================
elif choice == "Company Registration":
    st.subheader("Post a Job Opening (For HR/Companies)")
    with st.form("company_form"):
        company_name = st.text_input("Company Name")
        company_email = st.text_input("Company Email")
        address = st.text_input("Company Address")
        password = st.text_input("Set Password", type="password")
        package = st.text_input("Salary Package (e.g., 10 LPA)")
        criteria = st.text_input("Eligibility Criteria (e.g., 8.0 CGPA, No Backlogs)")
        
        submitted_company = st.form_submit_button("Post Job Drive")
        
        if submitted_company:
            row = {"Company": company_name, "Email": company_email, "Address": address, "Password": password, "Package": package, "Criteria": criteria}
            append_csv("companies.csv", row, cols_order=["Company","Email","Address","Password","Package","Criteria"])
            
            st.success(f"Job drive for {company_name} has been posted successfully!")

# ==========================================
# 3.5 COMPANY LOGIN PAGE
# ==========================================
elif choice == "Company Login":
    st.subheader("🏢 Company Login")
    st.write("Login with email and password to view and connect with eligible students.")
    st.write("(After login you will see your posted salary package and eligibility criteria)")
    
    company_email = st.text_input("Enter your Company Email")
    pwd = st.text_input("Password", type="password")
    if st.button("Company Login"):
        if not company_email.strip() or not pwd:
            st.error("Please enter both email and password.")
        else:
            # Check if company exists
            if os.path.exists("companies.csv"):
                df_companies = pd_read("companies.csv")
                df_companies = ensure_columns(df_companies, ["Email","Password","Company","Address","Package","Criteria"])
                company = df_companies[(df_companies["Email"].str.strip().str.lower() == company_email.strip().lower()) & (df_companies["Password"] == pwd)]
                
                if company.empty:
                    st.error("❌ Invalid credentials. Make sure you registered and use correct password.")
                else:
                    company_name = company.iloc[0]['Company']
                    criteria = company.iloc[0]['Criteria']
                    package = company.iloc[0]['Package']
                    
                    st.success(f"✅ Welcome, {company_name}!")
                    
                    # Show company details (including package & criteria)
                    st.markdown("### Your Posting Details")
                    st.write(f"**Package:** {package}")
                    st.write(f"**Eligibility Criteria:** {criteria}")
                    st.write(f"**Address:** {company.iloc[0]['Address']}")
                    st.markdown("---")
                    
                    # Show eligible students
                    if os.path.exists("database.csv"):
                        df_students = pd_read("database.csv")
                        
                        st.write("### 👥 All Registered Students")
                        
                        # Display all students with their resumes
                        if not df_students.empty:
                            for idx, student in df_students.iterrows():
                                with st.expander(f"📄 {student['Name']} - {student['Branch']} (CGPA: {student['CGPA']})"):
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        st.write(f"**Email:** {student['Email']}")
                                        st.write(f"**CGPA:** {student['CGPA']}")
                                    with col2:
                                        st.write(f"**Branch:** {student['Branch']}")
                                    
                                    st.markdown("---")
                                    
                                    # Action buttons
                                    col_a, col_b = st.columns(2)
                                    with col_a:
                                        if st.button(f"✉️ Contact {student['Name']}", key=f"contact_{idx}"):
                                            st.info(f"Contact email: {student['Email']}")
                                            st.success(f"Message sent to {student['Name']}!")
                                    
                                    with col_b:
                                        if st.button(f"⭐ Shortlist {student['Name']}", key=f"shortlist_{idx}"):
                                            st.success(f"{student['Name']} has been shortlisted!")
                        else:
                            st.info("No students registered yet.")
                    else:
                        st.info("No students registered yet.")
            else:
                st.error("❌ No companies registered yet.")

# ==========================================
# 4. JOB BOARD PAGE (DYNAMIC)
# ==========================================
elif choice == "Job Board":
    st.subheader("Hiring Companies & Job Openings")
    
    # This now reads from the live file instead of hardcoded text
    if os.path.exists("companies.csv"):
        df_companies = pd_read("companies.csv")
        st.dataframe(df_companies, use_container_width=True)
    else:
        st.info("No companies have posted job drives yet. Check back later!")

# ==========================================
# 2. STUDENT LOGIN PAGE
# ==========================================
elif choice == "Student Login":
    st.subheader("🔐 Student Login")
    st.write("Login with your email and password to view your allocation status.")
    
    email = st.text_input("Enter your College Email")
    pwd = st.text_input("Password", type="password")
    if st.button("Login"):
        if not email.strip() or not pwd:
            st.error("Please enter both email and password.")
        else:
            # Check if student is registered
            if os.path.exists("database.csv"):
                df_students = pd_read("database.csv")
                df_students = ensure_columns(df_students, ["Email","Password","Name","Branch","CGPA"])
                student = df_students[(df_students["Email"].str.strip() == email.strip()) & (df_students["Password"] == pwd)]
                
                if student.empty:
                    st.error("❌ Invalid credentials. Make sure you registered and use correct password.")
                else:
                    st.success(f"✅ Welcome, {student.iloc[0]['Name']}!")
                    
                    # Show student profile
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Name:** {student.iloc[0]['Name']}")
                        st.write(f"**Branch:** {student.iloc[0]['Branch']}")
                    with col2:
                        st.write(f"**Email:** {student.iloc[0]['Email']}")
                        st.write(f"**CGPA:** {student.iloc[0]['CGPA']}")
                    
                    st.markdown("---")
                    
                    # Check allocation
                    if os.path.exists("allocations.csv"):
                        df_alloc = pd_read("allocations.csv")
                        allocation = df_alloc[df_alloc["Student_Email"].str.strip() == email.strip()]
                        
                        if not allocation.empty:
                            st.success("🎉 **Allocation Status: SELECTED**")
                            st.write(f"**Company:** {allocation.iloc[0]['Company']}")
                            st.write(f"**Package:** {allocation.iloc[0]['Package']}")
                            st.write(f"**Date:** {allocation.iloc[0]['Date']}")
                        else:
                            st.info("⏳ No allocation yet. Results are pending...")
                    else:
                        st.info("⏳ No allocation yet. Results are pending...")
            else:
                st.error("❌ No students registered yet.")

# ==========================================
# 5. ADMIN DASHBOARD PAGE
# ==========================================
elif choice == "Admin Dashboard":
    st.subheader("Admin Access: Portal Data")
    
    password = st.text_input("Enter Admin Password", type="password")
    
    if password == "college123":
        tab_students, tab_companies, tab_allocate, tab_danger = st.tabs(["Students", "Companies", "Allocations", "Danger Zone"])
        
        # TAB 1: Students
        with tab_students:
            st.write("### Registered Students")
            if os.path.exists("database.csv"):
                df_students = pd_read("database.csv")
                st.dataframe(df_students, use_container_width=True)
                csv_students = df_students.to_csv(index=False).encode('utf-8')
                st.download_button("Download Student List (CSV)", data=csv_students, file_name="students.csv")
            else:
                st.warning("No students registered yet.")
        
        # TAB 2: Companies
        with tab_companies:
            st.write("### Registered Companies")
            if os.path.exists("companies.csv"):
                df_comps = pd_read("companies.csv")
                df_comps = ensure_columns(df_comps, ["Company","Email","Address","Password","Package","Criteria"])
                st.dataframe(df_comps, use_container_width=True)
                csv_comps = df_comps.to_csv(index=False).encode('utf-8')
                st.download_button("Download Company List (CSV)", data=csv_comps, file_name="companies.csv")
            else:
                st.warning("No companies registered yet.")
        
        # TAB 3: Allocations
        with tab_allocate:
            st.write("### Manage Student Allocations")
            with st.form("allocation_form"):
                st.write("Assign a company to a student")
                
                col1, col2 = st.columns(2)
                with col1:
                    student_email = st.text_input("Student Email")
                with col2:
                    company_name = st.text_input("Company Name")
                
                package = st.text_input("Package")
                date = st.text_input("Interview Date (e.g., 2026-03-15)")
                
                submit_alloc = st.form_submit_button("Allocate Student")
            
            if submit_alloc:
                if student_email and company_name and package and date:
                    alloc_data = {"Student_Email": [student_email], "Company": [company_name], "Package": [package], "Date": [date]}
                    alloc_df = pd.DataFrame(alloc_data)
                    
                    if os.path.exists("allocations.csv"):
                        alloc_df.to_csv("allocations.csv", mode='a', index=False, header=False)
                    else:
                        alloc_df.to_csv("allocations.csv", index=False)
                    
                    st.success(f"✅ {student_email} allocated to {company_name}!")
                else:
                    st.error("Please fill all fields.")
            
            # View all allocations
            if os.path.exists("allocations.csv"):
                st.write("### Current Allocations")
                df_allocations = pd_read("allocations.csv")
                st.dataframe(df_allocations, use_container_width=True)
                csv_alloc = df_allocations.to_csv(index=False).encode('utf-8')
                st.download_button("Download Allocations (CSV)", data=csv_alloc, file_name="allocations.csv")
        
        # TAB 4: Danger Zone
        with tab_danger:
            st.write("### ⚠️ Danger Zone")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("Wipe Student Data"):
                    if os.path.exists("database.csv"):
                        os.remove("database.csv")
                        st.success("Student database cleared.")
                        st.rerun()
                    else:
                        st.info("Student database is already empty.")

            with col2:
                if st.button("Wipe Company Data"):
                    if os.path.exists("companies.csv"):
                        os.remove("companies.csv")
                        st.success("Company database cleared.")
                        st.rerun()
                    else:
                        st.info("Company database is already empty.")
            
            with col3:
                if st.button("Wipe Allocation Data"):
                    if os.path.exists("allocations.csv"):
                        os.remove("allocations.csv")
                        st.success("Allocation database cleared.")
                        st.rerun()
                    else:
                        st.info("Allocation database is already empty.")
            
    elif password: 
        st.error("Incorrect Password.")