import whisper
import ffmpeg
import os

# Step 1: Extract Audio from Video using FFmpeg
def extract_audio(video_path, output_audio_path):
    try:
        ffmpeg.input(video_path).output(output_audio_path).run()
        print(f"Audio extracted successfully to {output_audio_path}")
    except Exception as e:
        print(f"Error extracting audio: {e}")

# Step 2: Transcribe Audio to Text with Segment-Level Timestamps using Whisper
def transcribe_audio_with_segment_timestamps(audio_path):
    model = whisper.load_model("base")
    result = model.transcribe(audio_path, verbose=True)
    
    # Prepare transcription with segment-level timestamps
    transcription_with_timestamps = []                                                                                             
    for segment in result['segments']:
        # Get segment start time and end time
        start_time = segment['start']
        end_time = segment['end']
        text = segment['text'].strip()

        # Format the timestamp
        formatted_time = f"[{int(start_time // 60):02d}:{int(start_time % 60):02d}] - [{int(end_time // 60):02d}:{int(end_time % 60):02d}]"
        transcription_with_timestamps.append(f"{formatted_time} {text}")
    
    return '\n'.join(transcription_with_timestamps)

# Full Process: Video to Audio, Audio to Text with Segment Timestamps
def process_video_to_text_with_segment_timestamps(video_path):
    # Step 1: Extract audio from video
    audio_path = 'output_audio.wav'
    extract_audio(video_path, audio_path)

    # Step 2: Transcribe audio to text with segment-level timestamps
    transcribed_text_with_segment_timestamps = transcribe_audio_with_segment_timestamps(audio_path)
    print("Transcription with segment-level timestamps completed.")
    
    # Ensure the transcription is saved in the same directory as the video
    video_dir = os.path.dirname(os.path.abspath(video_path))  # Ensure absolute path
    transcription_file_path = os.path.join(video_dir, 'transcription_with_segment_timestamps.txt')
    
    # Save transcription to the correct path
    try:
        with open(transcription_file_path, 'w') as f:
            f.write(transcribed_text_with_segment_timestamps)
        print(f"Transcription with segment-level timestamps saved to {transcription_file_path}")
    except Exception as e:
        print(f"Error saving transcription: {e}")

# Example Usage
video_path = 'test.mp4'
process_video_to_text_with_segment_timestamps(video_path)