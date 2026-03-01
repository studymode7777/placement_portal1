import streamlit as st
import pandas as pd

st.set_page_config(page_title="Placement Portal", layout="centered")

st.title("🎓 College Placement Portal")
st.write("Welcome! Register your details for upcoming company drives.")

# Sidebar for Navigation
menu = ["Student Registration", "Admin Dashboard", "Company List"]
choice = st.sidebar.selectbox("Navigation", menu)

if choice == "Student Registration":
    st.subheader("Student Application Form")
    with st.form("reg_form"):
        name = st.text_input("Full Name")
        email = st.text_input("College Email")
        cgpa = st.number_input("Current CGPA", min_value=0.0, max_value=10.0, step=0.1)
        branch = st.selectbox("Branch", ["CSE", "IT", "ECE", "MECH"])
        
        submitted = st.form_submit_button("Submit Application")
        if submitted:
            st.success(f"Best of luck, {name}! Your data is saved.")

elif choice == "Company List":
    st.subheader("Hiring Companies")
    # Example data (In a real app, this comes from a database)
    data = {
        "Company": ["Google", "Microsoft", "TCS"],
        "Package": ["30 LPA", "25 LPA", "7 LPA"],
        "Criteria": ["8.5 CGPA", "8.0 CGPA", "No Backlogs"]
    }
    st.table(pd.DataFrame(data))