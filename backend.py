import os
import whisper
import ffmpeg
import openai
from textblob import TextBlob
import concurrent.futures
import psycopg2
import yt_dlp as youtube_dl
from moviepy.editor import VideoFileClip
import re

# Set your API key for OpenAI
openai.api_key_path = "C:/Users/Lenovo/Desktop/PROJECT/api_key.env"

# Load Whisper model once for reuse
whisper_model = whisper.load_model("base")

# Database connection
def connect_db():
    return psycopg2.connect(
        host="localhost",
        database="registration",
        user="arya_nigam",
        password="123456"
    )

# Helper function to insert user into the database
def register_user(data):
    conn = connect_db()
    cur = conn.cursor()
    query = """
    INSERT INTO users_credentials (username, email, password, phone, dob, role, gender, profile_picture)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    cur.execute(query, data)
    conn.commit()
    conn.close()

# Helper function to insert user into the database
def register_user(data):
    conn = connect_db()
    cur = conn.cursor()
    query = """
    INSERT INTO users_credentials (username, email, password, phone, dob, role, gender, profile_picture)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    # Ensure binary data is passed correctly
    cur.execute(query, data)
    conn.commit()
    conn.close()


# User authentication function
def authenticate_user(email, password):
    conn = connect_db()
    cur = conn.cursor()
    query = "SELECT username, email, role FROM users_credentials WHERE email = %s AND password = %s"
    cur.execute(query, (email, password))
    user_data = cur.fetchone()
    conn.close()
    if user_data:
        return {"username": user_data[0], "email": user_data[1], "role": user_data[2]}
    return None

# Password validation function
def validate_password(password):
    password_regex = r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$'
    return bool(re.match(password_regex, password))

# Email validation function
def validate_email(email):
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(email_regex, email))

# Phone number validation function
def validate_phone(phone):
    phone_regex = r'^[9876]\d{9}$'
    return bool(re.match(phone_regex, phone))

# Step 1: Extract Audio from Video using FFmpeg
def extract_audio(video_path, output_audio_path):
    try:
        ffmpeg.input(video_path).output(output_audio_path).run(overwrite_output=True)
        print(f"Audio extracted successfully to {output_audio_path}")
    except Exception as e:
        print(f"Error extracting audio: {e}")

# Step 2: Transcribe Audio to Text with Segment-Level Timestamps using Whisper
def transcribe_audio_with_segment_timestamps(audio_path):
    result = whisper_model.transcribe(audio_path, verbose=True)

    transcription_with_timestamps = []
    full_text = []
    for segment in result['segments']:
        transcription_with_timestamps.append({
            'start': segment['start'],
            'end': segment['end'],
            'text': segment['text'].strip()
        })
        full_text.append(segment['text'].strip())

    return transcription_with_timestamps, " ".join(full_text)

# Step 3: Identify Video Genre
def identify_genre(transcription_segments):
    sample_text = " ".join([segment['text'] for segment in transcription_segments[:5]])

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "You are an AI trained to identify video genres."},
                  {"role": "user", "content": f"Identify the genre of this video based on the following text: '{sample_text}'"}],
        temperature=0.2
    )

    genre = response.choices[0].message['content'].strip().lower()
    return genre

# Step 4: Analyze Importance of the Full Transcribed Text
def analyze_importance_of_transcribed_text(transcribed_text, genre):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": f"You are selecting important moments for a {genre} video highlight reel."},
                  {"role": "user", "content": f"Analyze the transcript and extract as many important moments as possible, focusing on detailed, granular segments for a {genre} video. Text: '{transcribed_text}'"}
],
        max_tokens=500,
    )
    
    importance = response.choices[0].message['content'].strip().lower()
    return importance

# Step 5: Analyze Sentiment of Transcriptions
def analyze_sentiment(text):
    blob = TextBlob(text)
    return blob.sentiment.polarity  # Return only polarity for simplicity


# Step 6: Identify and Compile Important Segments
def identify_and_compile_important_segments(transcription_segments, genre, max_duration=100):
    transcribed_text = " ".join(segment['text'] for segment in transcription_segments)
    important_text = analyze_importance_of_transcribed_text(transcribed_text, genre)

    important_segments = []
    total_duration = 0

    # Lower the sentiment threshold to 0.1 to allow more segments to pass
    for segment in transcription_segments:
        segment_keywords = [keyword for keyword in important_text.split() if keyword in segment['text'].lower()]
        sentiment = analyze_sentiment(segment['text'])
        
        # Lower the sentiment threshold to 0.1
        if segment_keywords and sentiment > 0.1:
            segment_duration = segment['end'] - segment['start']
            if total_duration + segment_duration <= max_duration:
                important_segments.append(segment)
                total_duration += segment_duration
                print(f"Added important segment: {segment['text']}")

    print(f"Total important segments selected: {len(important_segments)}")
    return important_segments

# Step 6: Create and Compile Highlight Reels
def create_segment(video_path, segment, output_dir="segments"):
    try:
        segment_duration = segment['end'] - segment['start']
        segment_file = os.path.join(output_dir, f"segment_{segment['start']:.2f}_{segment['end']:.2f}.mp4")
        ffmpeg.input(video_path, ss=segment['start'], to=segment['end']).output(segment_file, c='copy').run(overwrite_output=True)
        return segment_file
    except Exception as e:
        print(f"Error creating segment file: {e}")
        return None

def create_highlight_reels(video_path, important_segments, min_reels=3, max_reel_duration=30):
    segment_files = []
    reels = []
    output_dir = "segments"
    os.makedirs(output_dir, exist_ok=True)

    # Parallelize segment extraction
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_segment = {executor.submit(create_segment, video_path, segment): segment for segment in important_segments}
        for future in concurrent.futures.as_completed(future_to_segment):
            segment = future_to_segment[future]
            segment_file = future.result()
            if segment_file:
                segment_files.append(segment_file)

    # Distribute segments into reels
    reels = [segment_files[i::min_reels] for i in range(min_reels)]

    reel_paths = []
    for i, reel_segments in enumerate(reels):
        reel_list_file = create_reel_list_file(reel_segments, i + 1)
        reel_path = f"highlight_reel_{i + 1}.mp4"
        try:
            ffmpeg.input(reel_list_file, format='concat', safe=0).output(reel_path, c='copy').run(overwrite_output=True)
            reel_paths.append(reel_path)
        except Exception as e:
            print(f"Error creating reel {i + 1}: {e}")
    return reel_paths

def create_reel_list_file(reel_segments, reel_index):
    reel_list_file = f"reel_{reel_index}_list.txt"
    with open(reel_list_file, "w") as f:
        for segment in reel_segments:
            f.write(f"file '{os.path.abspath(segment)}'\n")
    return reel_list_file

# Step 7: Add Subtitles to Video
def add_subtitles_to_video(video_path, subtitle_segments, output_video_path):
    subtitle_file = "subtitles.srt"
    
    # Create SRT file
    with open(subtitle_file, "w") as f:
        for idx, segment in enumerate(subtitle_segments):
            start_time = segment['start']
            end_time = segment['end']
            text = segment['text']
            f.write(f"{idx+1}\n")
            f.write(f"{format_time(start_time)} --> {format_time(end_time)}\n")
            f.write(f"{text}\n\n")
    
    # Use ffmpeg to add subtitles
    ffmpeg.input(video_path).output(output_video_path, vf=f"subtitles={subtitle_file}").run(overwrite_output=True)

# Convert seconds to HH:MM:SS,MS format for SRT file
def format_time(seconds):
    mins, sec = divmod(seconds, 60)
    hour, mins = divmod(mins, 60)
    return f"{int(hour):02}:{int(mins):02}:{int(sec):02},{int((sec % 1) * 1000):03}"

# Full Process: Extract audio, transcribe, identify important segments, and add subtitles
def process_video_to_reels(video_path):
    audio_path = 'output_audio.wav'
    extract_audio(video_path, audio_path)

    transcription_segments, full_text = transcribe_audio_with_segment_timestamps(audio_path)
    genre = identify_genre(transcription_segments)

    important_segments = identify_and_compile_important_segments(transcription_segments, genre)

    reel_paths = create_highlight_reels(video_path, important_segments)

    output_video_path = "highlight_video_with_subtitles.mp4"
    add_subtitles_to_video(video_path, important_segments, output_video_path)

    # Save transcription to file
    transcription_file_path = "transcription.txt"
    with open(transcription_file_path, "w") as file:
        file.write(full_text)

    return reel_paths, output_video_path, transcription_file_path

# Function to download video from YouTube
def download_video_from_youtube(youtube_url, output_dir="downloaded_videos"):
    try:
        # Set up the download options
        ydl_opts = {
            'format': 'best',
            'outtmpl': f'{output_dir}/%(title)s.%(ext)s',
            'quiet': True,
        }
        os.makedirs(output_dir, exist_ok=True)
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            video_path = os.path.join(output_dir, f"{info['title']}.{info['ext']}")
            return video_path
    except Exception as e:
        print(f"Error downloading video: {e}")
        return None

def get_user_data(email):
    conn = connect_db()
    cur = conn.cursor()
    query = "SELECT username, email, dob, role, gender, profile_picture FROM users_credentials WHERE email = %s"
    cur.execute(query, (email,))
    user_data = cur.fetchone()
    conn.close()
    return user_data
