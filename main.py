import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Placement Portal", layout="centered")

st.title("🎓 College Placement Portal")
st.write("Welcome! Register your details or view upcoming company drives.")

# We updated the menu to include the new features
menu = ["Student Registration", "Company Registration", "Job Board", "Admin Dashboard"]
choice = st.sidebar.selectbox("Navigation", menu)

# ==========================================
# 1. STUDENT REGISTRATION PAGE
# ==========================================
if choice == "Student Registration":
    st.subheader("Student Application Form")
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

# ==========================================
# 2. COMPANY REGISTRATION PAGE (NEW)
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
# 3. JOB BOARD PAGE (DYNAMIC)
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
# 4. ADMIN DASHBOARD PAGE
# ==========================================
elif choice == "Admin Dashboard":
    st.subheader("Admin Access: Portal Data")
    
    password = st.text_input("Enter Admin Password", type="password")
    
    if password == "college123":
        st.write("### Registered Students")
        if os.path.exists("database.csv"):
            df_students = pd.read_csv("database.csv")
            st.dataframe(df_students)
            csv_students = df_students.to_csv(index=False).encode('utf-8')
            st.download_button("Download Student List (CSV)", data=csv_students, file_name="students.csv")
        else:
            st.warning("No students registered yet.")
            
        st.write("### Registered Companies")
        if os.path.exists("companies.csv"):
            df_comps = pd.read_csv("companies.csv")
            st.dataframe(df_comps)
            csv_comps = df_comps.to_csv(index=False).encode('utf-8')
            st.download_button("Download Company List (CSV)", data=csv_comps, file_name="companies.csv")
        else:
            st.warning("No companies registered yet.")
            
    elif password: 
        st.error("Incorrect Password.")