import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Placement Portal", layout="centered")

st.title("🎓 College Placement Portal")
st.write("Welcome! Register your details or view upcoming company drives.")

# We updated the menu to include the new features
menu = ["Student Registration", "Student Login", "Company Registration", "Job Board", "Admin Dashboard"]
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
            cgpa = st.number_input("Current CGPA", min_value=0.0, max_value=10.0, step=0.1)
            branch = st.selectbox("Branch", ["CSE", "IT", "ECE", "MECH"])
            
            submitted = st.form_submit_button("Submit Application")
            
            if submitted:
                new_data = {"Name": [name], "Email": [email], "CGPA": [cgpa], "Branch": [branch]}
                new_df = pd.DataFrame(new_data)
                
                if os.path.exists("database.csv"):
                    new_df.to_csv("database.csv", mode='a', index=False, header=False)
                else:
                    new_df.to_csv("database.csv", index=False)
                
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
                    from fpdf import FPDF
                    import io
                    
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", 'B', 16)
                    pdf.cell(0, 10, r_name, ln=True, align='C')
                    pdf.set_font("Arial", size=12)
                    pdf.ln(4)
                    pdf.cell(0, 8, f"Email: {r_email}", ln=True)
                    pdf.cell(0, 8, f"Phone: {r_phone}", ln=True)
                    pdf.ln(4)
                    if r_summary.strip():
                        pdf.set_font("Arial", 'B', 14)
                        pdf.cell(0, 8, "Summary", ln=True)
                        pdf.set_font("Arial", size=12)
                        pdf.multi_cell(0, 6, r_summary)
                        pdf.ln(2)
                    if r_education.strip():
                        pdf.set_font("Arial", 'B', 14)
                        pdf.cell(0, 8, "Education", ln=True)
                        pdf.set_font("Arial", size=12)
                        for line in r_education.strip().splitlines():
                            pdf.cell(0, 6, f"- {line}", ln=True)
                        pdf.ln(2)
                    if r_skills.strip():
                        pdf.set_font("Arial", 'B', 14)
                        pdf.cell(0, 8, "Skills", ln=True)
                        pdf.set_font("Arial", size=12)
                        for skill in r_skills.split(","):
                            pdf.cell(0, 6, f"- {skill.strip()}", ln=True)
                        pdf.ln(2)
                    if r_projects.strip():
                        pdf.set_font("Arial", 'B', 14)
                        pdf.cell(0, 8, "Projects", ln=True)
                        pdf.set_font("Arial", size=12)
                        for line in r_projects.strip().splitlines():
                            pdf.cell(0, 6, f"- {line}", ln=True)
                        pdf.ln(2)
                    
                    pdf_bytes = pdf.output(dest='S').encode('latin-1')
                    st.download_button("Download Resume (PDF)", data=pdf_bytes, file_name="resume.pdf", mime="application/pdf")
                except ImportError:
                    st.warning("PDF generation requires the 'fpdf' package. Add it to requirements and rebuild the environment.")

# ==========================================
# 3. COMPANY REGISTRATION PAGE (NEW)
# ==========================================
elif choice == "Company Registration":
    st.subheader("Post a Job Opening (For HR/Companies)")
    with st.form("company_form"):
        company_name = st.text_input("Company Name")
        package = st.text_input("Salary Package (e.g., 10 LPA)")
        criteria = st.text_input("Eligibility Criteria (e.g., 8.0 CGPA, No Backlogs)")
        
        submitted_company = st.form_submit_button("Post Job Drive")
        
        if submitted_company:
            company_data = {"Company": [company_name], "Package": [package], "Criteria": [criteria]}
            company_df = pd.DataFrame(company_data)
            
            # Save to a separate companies.csv file
            if os.path.exists("companies.csv"):
                company_df.to_csv("companies.csv", mode='a', index=False, header=False)
            else:
                company_df.to_csv("companies.csv", index=False)
            
            st.success(f"Job drive for {company_name} has been posted successfully!")

# ==========================================
# 4. JOB BOARD PAGE (DYNAMIC)
# ==========================================
elif choice == "Job Board":
    st.subheader("Hiring Companies & Job Openings")
    
    # This now reads from the live file instead of hardcoded text
    if os.path.exists("companies.csv"):
        df_companies = pd.read_csv("companies.csv")
        st.dataframe(df_companies, use_container_width=True)
    else:
        st.info("No companies have posted job drives yet. Check back later!")

# ==========================================
# 2. STUDENT LOGIN PAGE
# ==========================================
elif choice == "Student Login":
    st.subheader("🔐 Student Login")
    st.write("Login with your email to view your allocation status.")
    
    email = st.text_input("Enter your College Email")
    if st.button("Login"):
        if not email.strip():
            st.error("Please enter your email.")
        else:
            # Check if student is registered
            if os.path.exists("database.csv"):
                df_students = pd.read_csv("database.csv")
                student = df_students[df_students["Email"].str.strip() == email.strip()]
                
                if student.empty:
                    st.error("❌ Email not found. Please register first in Student Registration.")
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
                        df_alloc = pd.read_csv("allocations.csv")
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
                df_students = pd.read_csv("database.csv")
                st.dataframe(df_students, use_container_width=True)
                csv_students = df_students.to_csv(index=False).encode('utf-8')
                st.download_button("Download Student List (CSV)", data=csv_students, file_name="students.csv")
            else:
                st.warning("No students registered yet.")
        
        # TAB 2: Companies
        with tab_companies:
            st.write("### Registered Companies")
            if os.path.exists("companies.csv"):
                df_comps = pd.read_csv("companies.csv")
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
                df_allocations = pd.read_csv("allocations.csv")
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