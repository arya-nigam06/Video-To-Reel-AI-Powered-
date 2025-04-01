import whisper
import ffmpeg
import openai
import os
from dotenv import load_dotenv

# Load OpenAI API key
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

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

    transcription_with_timestamps = []
    for segment in result['segments']:
        transcription_with_timestamps.append({
            'start': segment['start'],
            'end': segment['end'],
            'text': segment['text'].strip()
        })

    print("Transcription Segments:", transcription_with_timestamps)
    return transcription_with_timestamps

# Step 3: Analyze Segment Importance
def analyze_segment_importance(segments):
    important_segments = []
    buffer_time = 0.5
    importance_threshold = 0.5

    for segment in segments:
        text = segment['text']
        start_time = max(0, segment['start'] - buffer_time)
        end_time = segment['end'] + buffer_time

        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant selecting meaningful moments for a video highlight reel."},
                    {"role": "user", "content": f"Does the following segment contain a memorable or significant moment for a highlight reel? Consider expressions of joy, excitement, or important information. If it’s a potential highlight, respond with 'important'; if not, respond with 'not important'. Segment: '{text}'"}
                ],
                max_tokens=10
            )

            importance = response.choices[0].message['content'].strip().lower()
            if importance == "important":
                importance_score = segment['end'] - segment['start']  # Example: score based on duration
                if importance_score > importance_threshold:
                    important_segments.append({
                        'text': text,
                        'start_time': start_time,
                        'end_time': end_time,
                        'importance_score': importance_score
                    })

        except Exception as e:
            print(f"Error during OpenAI API call: {e}")

    # Save important segments to a file
    with open("important_segments.txt", "w") as file:
        for segment in important_segments:
            file.write(f"Text: {segment['text']}\n")
            file.write(f"Start Time: {segment['start_time']}s\n")
            file.write(f"End Time: {segment['end_time']}s\n")
            file.write(f"Importance Score: {segment['importance_score']}\n")
            file.write("=" * 40 + "\n")  # Separator for readability

    return important_segments

# Step 4: Extract Video Segments Based on Timestamps
def extract_video_segment(video_path, start_time, end_time, output_path):
    try:
        duration = end_time - start_time
        ffmpeg.input(video_path, ss=start_time, t=duration).output(output_path).run()
        print(f"Segment extracted: {output_path}")
    except Exception as e:
        print(f"Error extracting video segment: {e}")

# Step 5: Compile Extracted Segments into 30-Second Reels
def compile_video_segments(segment_paths, output_video_path):
    with open('file_list.txt', 'w') as f:
        for segment in segment_paths:
            f.write(f"file '{segment}'\n")

    try:
        ffmpeg.input('file_list.txt', format='concat', safe=0).output(output_video_path, c='copy').run()
        print(f"Compiled reel created: {output_video_path}")
    except Exception as e:
        print(f"Error compiling videos: {e}")

# Full Process: Generate Multiple Reels from Important Segments
def generate_reels_from_important_segments(video_path, audio_path, top_n=5):
    extract_audio(video_path, audio_path)
    transcription_segments = transcribe_audio_with_segment_timestamps(audio_path)
    print("Transcription and timestamp extraction completed.")

    important_segments = analyze_segment_importance(transcription_segments)
    important_segments.sort(key=lambda x: x['importance_score'], reverse=True)

    compiled_video_paths = []  # List to store compiled video paths
    for reel_index in range(3):  # Limit to 3 reels
        top_segments = important_segments[reel_index * top_n:(reel_index + 1) * top_n]
        top_segments.sort(key=lambda x: x['start_time'])

        segment_paths = []
        for i, segment in enumerate(top_segments):
            start_time = segment['start_time']
            end_time = segment['end_time']
            output_path = f'reel_{reel_index + 1}_segment_{i + 1}.mp4'
            extract_video_segment(video_path, start_time, end_time, output_path)
            segment_paths.append(output_path)

        compiled_video_path = f'reel_{reel_index + 1}.mp4'
        compile_video_segments(segment_paths, compiled_video_path)
        compiled_video_paths.append(compiled_video_path)  # Add compiled path to the list

    return compiled_video_paths  # Return only compiled video paths

# Step 6: Save timestamps to a text file
def save_timestamps_to_file(segments, output_file):
    with open(output_file, 'w') as f:
        for segment in segments:
            f.write(f"Start: {segment['start_time']:.2f}, End: {segment['end_time']:.2f}\n")
    print(f"Timestamps saved to {output_file}")

# Example Usage
def process_video_to_reels(video_path):
    audio_path = 'output_audio.wav'
    compiled_reels = generate_reels_from_important_segments(video_path, audio_path)

    print(f"Reels created: {compiled_reels}")

video_path = "video 1.mp4"  
process_video_to_reels(video_path)
