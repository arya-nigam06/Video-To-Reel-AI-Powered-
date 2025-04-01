import bcrypt
import streamlit as st
import psycopg2
from PIL import Image
import io
import re

# Connect to PostgreSQL
def connect_to_db():
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="registration",
            user="adityabhatt",
            password="123567"
        )
        return conn
    except psycopg2.OperationalError:
        st.error("Unable to connect to the database. Please check your database credentials or connection.")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
    return None

def insert_user_data(username, email, password, phone, dob, role, gender, profile_picture):
    conn = connect_to_db()
    if not conn:
        return
    cursor = conn.cursor()
   
    # Hash the password
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
   
    insert_query = """
    INSERT INTO users (username, email, password, phone, dob, role, gender, profile_picture)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    profile_picture_bytes = profile_picture.read() if profile_picture else None
    cursor.execute(insert_query, (username, email, hashed_password, phone, dob, role, gender, profile_picture_bytes))
    conn.commit()
    cursor.close()
    conn.close()

def login_user(username, password):
    conn = connect_to_db()
    if not conn:
        return "Database connection error."
   
    cursor = conn.cursor()
    query = "SELECT username, email, phone, dob, role, gender, profile_picture, password FROM users WHERE username = %s"
    cursor.execute(query, (username,))
    user_data = cursor.fetchone()
    cursor.close()
    conn.close()
   
    if user_data:
        # Extract the stored hashed password
        stored_password = user_data[-1]  # This should be a string
       
        # Verify the password
        if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):  # Ensure it's compared correctly
            return user_data[:-1]  # Return all fields except the hashed password
        else:
            return "Incorrect password."
    else:
        return "User not registered."

# Profile page
def show_profile_page():
    st.title('User Profile')
    if st.sidebar.button("Logout"):
        st.session_state.is_logged_in = False
        st.session_state.user_data = None
        st.session_state.page = 'login'
        st.experimental_rerun()
    user_data = st.session_state.user_data
    username, email, phone, dob, role, gender, profile_picture_bytes = user_data
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("User Details")
        st.write(f"*Username:* {username}")
        st.write(f"*Email:* {email}")
        st.write(f"*Phone:* {phone}")
        st.write(f"*Date of Birth:* {dob}")
        st.write(f"*Role:* {role}")
        st.write(f"*Gender:* {gender}")
    with col2:
        if profile_picture_bytes:
            image = Image.open(io.BytesIO(profile_picture_bytes))
            st.image(image.resize((320, 320)), caption='Profile Picture')

# Registration validation functions
def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def is_valid_phone(phone):
    return phone.isdigit() and len(phone) >= 10

def is_valid_password(password):
    return (
        len(password) >= 8 and
        re.search(r"[A-Z]", password) and
        re.search(r"[a-z]", password) and
        re.search(r"[0-9]", password) and
        re.search(r"[@$!%*?&#]", password)
    )

def show_registration_page():
    st.title('User Registration')
    with st.form("registration_form", clear_on_submit=True):
        username = st.text_input("Username")
        email = st.text_input("Email")
        password = st.text_input("Password", type='password')
        phone = st.text_input("Phone Number")
        dob = st.date_input("Date of Birth")
        role = st.text_input("Profession/Role")
        gender = st.selectbox("Gender", ("Male", "Female", "Other"))
        profile_picture = st.file_uploader("Upload Profile Picture", type=["jpg", "jpeg", "png"])
        submit_button = st.form_submit_button("Register")

        # Validation
        if submit_button:
            if not username:
                st.warning("Username is required.")
            if not email or not is_valid_email(email):
                st.warning("Invalid email format.")
            if not password or not is_valid_password(password):
                st.warning("Password must be at least 8 characters long, with a number, an uppercase letter, a lowercase letter, and a special character.")
            if not phone:
                st.warning("Phone number is required.")
            elif not is_valid_phone(phone):
                st.warning("Phone number must start with 6, 7, 8, or 9 and be at least 10 digits long.")
            if not all([username, email, password, phone, dob, role, gender]):
                st.warning("All fields must be filled out.")
            elif username and email and is_valid_email(email) and password and is_valid_password(password) and phone and is_valid_phone(phone):
                insert_user_data(username, email, password, phone, dob, role, gender, profile_picture)
                st.success("User registered successfully! Please proceed to login.")
            else:
                st.error("Registration failed. Please correct the errors above.")

    if st.button("Already have an account? Login here"):
        st.session_state.page = 'login'
        st.experimental_rerun()

# Login page
def show_login_page():
    st.title('User Login')
    username = st.text_input("Username")
    password = st.text_input("Password", type='password')
   
    if st.button("Login"):
        if username and password:
            login_response = login_user(username, password)
            if isinstance(login_response, str):
                st.error(login_response)  # Display the specific error message (e.g., "Invalid password" or "User not registered")
            else:
                st.session_state.is_logged_in = True
                st.session_state.user_data = login_response
                st.session_state.page = 'profile'
                st.experimental_rerun()
        else:
            st.warning("Both username and password are required.")

    if st.button("Don't have an account? Register here"):
        st.session_state.page = 'register'
        st.experimental_rerun()

# Page Flow Control
if 'is_logged_in' not in st.session_state:
    st.session_state.is_logged_in = False
if 'page' not in st.session_state:
    st.session_state.page = 'login'
if st.session_state.is_logged_in and st.session_state.user_data:
    show_profile_page()
else:
    if st.session_state.page == 'login':
        show_login_page()
    elif st.session_state.page == 'register':
        show_registration_page()

