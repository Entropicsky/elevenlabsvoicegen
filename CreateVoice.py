import os
from pydub import AudioSegment
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Merge audio files with 2 seconds silence in between and return the path of the merged file
def merge_audio_files(files, target_file):
    combined = AudioSegment.empty()
    silence = AudioSegment.silent(duration=500)  # 0.5 seconds of silence
    max_size_bytes = 10 * 1024 * 1024  # 10MB
    num_files = 0

    for file in files:
        print(f"Processing file: {file}")  # Print the file being processed
        audio = AudioSegment.from_file(file)

        # Split large audio files into chunks of max size
        while len(audio) > 0:
            chunk = audio[:max_size_bytes]
            audio = audio[max_size_bytes:]
            
            temp = combined + chunk + silence
            temp.export(target_file, format='wav')
            
            if os.path.getsize(target_file) > max_size_bytes:
                if num_files == 0:  # If the first chunk is too big, skip it
                    num_files = 1
                else:
                    os.remove(target_file)  # Delete the oversized file
                break  # If adding this chunk would exceed the max size, stop here
            
            combined = temp
            num_files += 1

        if num_files > 0:  # Only export the file if at least one chunk was added
            combined.export(target_file, format='wav')
        else:
            target_file = None

    return target_file, num_files






def create_voice(directory_path, voice_name, voice_description, labels):
    url = "https://api.elevenlabs.io/v1/voices/add"
    api_key = os.getenv("ELEVENLABS_API_KEY")

    headers = {
        "Accept": "application/json",
        "xi-api-key": api_key
    }
    data = {
        'name': voice_name,
        'description': voice_description,
        'labels': labels
    }

    # Get all audio files in directory and sort them
    files = sorted([os.path.join(directory_path, f) for f in os.listdir(directory_path) if f.lower().endswith(('.mp3', '.wav'))])

    max_files = 25
    voice_files = []
    start = 0
    while start < len(files) and len(voice_files) < max_files:
        merged_file_path, num_files = merge_audio_files(files[start:], f'{directory_path}/merged_{len(voice_files)}.wav')
        if merged_file_path is not None:
            voice_files.append(('files', (os.path.basename(merged_file_path), open(merged_file_path, 'rb'), 'audio/mpeg')))
        start += num_files

    response = requests.post(url, headers=headers, data=data, files=voice_files)
    print(response.text)



if __name__ == "__main__":
    directory_path = "JoeMackenzie"  # Replace with your target directory
    voice_name = "JoeBro"
    voice_description = "A young American male with a killer marketing voice."
    labels = '{"accent": "American"}'

    create_voice(directory_path, voice_name, voice_description, labels)
