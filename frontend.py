import streamlit as st
import os
from backend import register_user, authenticate_user, get_user_data, process_video_to_reels, download_video_from_youtube
import yt_dlp

# Function to set the background image for the whole screen
def set_background_image(image_path):
    # Custom CSS to set the background image
    st.markdown(
        f"""
        <style>
        body {{
            background-image: url({image_path});
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            height: 100vh;
        }}
        </style>
        """, 
        unsafe_allow_html=True
    )




# Helper function for saving uploaded files locally
def save_uploaded_file(uploaded_file, directory="uploaded_videos"):
    os.makedirs(directory, exist_ok=True)
    file_path = os.path.join(directory, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path

# Function to download video from YouTube using yt_dlp
def download_video_from_youtube(youtube_url):
    try:
        # Set download directory (ensure the directory exists)
        download_dir = os.path.join(os.getcwd(), 'downloaded_videos')
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)

        # Set the download options for yt_dlp
        ydl_opts = {
            'format': 'best',  # Download the best quality video
            'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),  # Save with video title as the filename
            'noplaylist': True,  # Avoid downloading playlists
        }

        # Download the video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(youtube_url, download=True)
            video_file_path = os.path.join(download_dir, f"{info_dict['title']}.mp4")

        return video_file_path
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None

# Video Processing and Reel Generation Page
def video_processing_page():
    st.title("🎥 Video Processing and Reel Generation")

    # User can input a YouTube URL or upload a video file
    youtube_url = st.text_input("Enter YouTube URL")
    video_file = st.file_uploader("Or upload your video file", type=["mp4", "mov", "avi"])
    video_path = None

    if youtube_url:
        # Download video from YouTube
        with st.spinner("Downloading video from YouTube..."):
            video_path = download_video_from_youtube(youtube_url)
        if video_path:
            st.success(f"Video downloaded successfully: {video_path}")
        else:
            st.error("Error downloading YouTube video. Please check the URL.")
    
    elif video_file:
        # Save the uploaded video file locally
        with st.spinner("Saving uploaded video..."):
            video_path = save_uploaded_file(video_file)
        if video_path:
            st.success(f"Video uploaded successfully: {video_path}")
        else:
            st.error("Error uploading the video.")

    # Show video preview if a video is available
    if video_path:
        st.video(video_path)

        # Process video to generate reels
        if st.button("Generate Reels"):
            with st.spinner("Processing video..."):
                try:
                    reel_paths, highlight_video_path, transcription_file_path = process_video_to_reels(video_path)

                    # Display generated reels and download options
                    if reel_paths:
                        st.success("Reels generated successfully!")
                        for idx, reel in enumerate(reel_paths):
                            st.video(reel)
                            with open(reel, "rb") as file:
                                st.download_button(f"Download Reel {idx + 1}", file, file_name=os.path.basename(reel))
                        st.download_button("Download Full Highlight Video", open(highlight_video_path, "rb"), file_name="highlight_video.mp4")
                        st.download_button("Download Transcription", open(transcription_file_path, "rb"), file_name="transcription.txt")
                    else:
                        st.error("Error generating reels.")
                except Exception as e:
                    st.error(f"An error occurred: {e}")

# Registration page
def registration_page():
    st.title("📝 Registration")
    username = st.text_input("Username")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    phone = st.text_input("Phone Number")
    dob = st.date_input("Date of Birth")
    role = st.selectbox("Role", ["Admin", "User"])
    gender = st.selectbox("Gender", ["Male", "Female", "Other"])
    profile_picture = st.file_uploader("Upload Profile Picture", type=["jpg", "png", "jpeg"])

    if st.button("Register"):
        if username and email and password and phone and dob and role and gender:
            profile_picture_data = profile_picture.read() if profile_picture else None
            try:
                register_user((username, email, password, phone, dob, role, gender, profile_picture_data))
                st.success("Registration successful! Please log in.")
            except Exception as e:
                st.error(f"Error during registration: {e}")
        else:
            st.warning("Please fill all fields.")

# Login page
def login_page():
    st.title("🔒 Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if email and password:
            try:
                user_data = authenticate_user(email, password)
                if user_data:
                    st.session_state["user_email"] = email
                    st.success("Login successful!")
                    profile_page()  # Redirect to profile page after successful login
                else:
                    st.error("Invalid email or password.")
            except Exception as e:
                st.error(f"Error during login: {e}")
        else:
            st.warning("Please enter both email and password.")

# Profile Page
def profile_page():
    if 'user_email' in st.session_state:
        user_data = get_user_data(st.session_state.user_email)
        
        if user_data:
            username, email, dob, role, gender, profile_picture = user_data
            
            st.title(f"Welcome, {username}!")
            
            # Check and display the profile picture
            if profile_picture:
                try:
                    # Convert memoryview to bytes
                    profile_picture_bytes = bytes(profile_picture)
                    st.image(profile_picture_bytes, caption="Profile Picture", use_column_width=True)
                except Exception as e:
                    st.warning(f"Error displaying profile picture: {e}")
            else:
                st.write("No profile picture available.")
            
            # Display user information
            st.write(f"**Email:** {email}")
            st.write(f"**Date of Birth:** {dob}")
            st.write(f"**Role:** {role}")
            st.write(f"**Gender:** {gender}")
        else:
            st.warning("Unable to fetch user data. Please try again later.")
    else:
        st.warning("Please log in to view your profile.")

# Main function to handle navigation
def main():
    st.sidebar.title("📌 Navigation")
    page = st.sidebar.radio("Select a page", ["Login", "Registration", "Profile", "Video Processing"])

    if page == "Login":
        login_page()
    elif page == "Registration":
        registration_page()
    elif page == "Profile":
        profile_page()
    elif page == "Video Processing":
        video_processing_page()

if __name__ == "__main__":
    if "user_email" not in st.session_state:
        st.session_state["user_email"] = None
    main()
