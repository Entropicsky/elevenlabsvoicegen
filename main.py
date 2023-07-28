import pandas as pd
import requests
import openai
import json
import re
import os
from dotenv import load_dotenv
import datetime
import csv
import itertools
import configparser
import elevenlabs
from elevenlabs import generate, save

# read the settings.ini file to get key configuration
config = configparser.ConfigParser()
config.read('settings.ini')

# use a casting note to help select voices to use
casting_note = config.get('Voice', 'casting_note')

# Specify any voices that you know you want to use, if any. USE LOWER CASE.
specified_voice_names = [name.strip() for name in config.get('Voice', 'specified_voices').split(",")]

# Define your ranges here
stability_range = [float(value.strip()) for value in config.get('Settings', 'stability_range').split(",")]
similarity_boost_range = [float(value.strip()) for value in config.get('Settings', 'similarity_boost_range').split(",")]

settings_combinations = list(itertools.product(stability_range, similarity_boost_range))

VARIANTS = config.getint('Settings', 'variants')  # Number of variants per actor per line
ACTORS = config.getint('Settings', 'actors')  # Number of actors to cast from ChatGPT's suggestions in addition to the specified_voice_names

CHUNK_SIZE = config.getint('System', 'chunk_size')

# Load environment variables from .env to get teh API keys
load_dotenv()  # take environment variables from .env.

ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
CHATGPT_API_KEY = os.getenv('CHATGPT_API_KEY')


# Load the voice lines from the CSV file
lines_file = config.get('Settings', 'lines_file')
df = pd.read_csv(lines_file)
lines = list(df[['id', 'text']].itertuples(index=False, name=None))



# Get the current time at the start of the program
start_time = datetime.datetime.now()

# Format the time as a string
start_time_str = start_time.strftime("%Y%m%d%H%M")


# ElevenLabs API constants

ELEVENLABS_URL = 'https://api.elevenlabs.io/v1/voices'

# Set the API key for ElevenLabs
elevenlabs.set_api_key(ELEVENLABS_API_KEY)


# ChatGPT API constants  

CHATGPT_MODEL = 'gpt-3.5-turbo-16k'
CHATGPT_URL = 'https://api.openai.com/v1/chat/completions'



def generate_audio(text, voice_id, stability, similarity_boost):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    headers = {
      "Accept": "audio/mpeg",
      "Content-Type": "application/json",
      "xi-api-key": ELEVENLABS_API_KEY
    }

    data = {
      "text": text,
      "model_id": "eleven_monolingual_v1",
      "voice_settings": {
        "stability": stability,
        "similarity_boost": similarity_boost
      }
    }

    response = requests.post(url, json=data, headers=headers)
    audio_data = b""
    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
        if chunk:
            audio_data += chunk
    return audio_data


def get_elevenlabs_voices():
    headers = {
        "Accept": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }

    # API call 
    response = requests.get(ELEVENLABS_URL, headers=headers)

    # Get voices list
    data = response.json()
    voices = data["voices"]

    print(f"Fetched {len(voices)} voices from ElevenLabs")
    
    return voices

# Updated function to include gender and accent


def pick_best_voices(voices, casting_note, num_suggestions):
    openai.api_key = CHATGPT_API_KEY

    # transform voice data into a string format
    voices_string = ', '.join([f"{voice['name']} (gender: {voice['labels'].get('gender', 'N/A')}, language: {voice['labels'].get('language', 'N/A')}, accent: {voice['labels'].get('accent', 'N/A')})" for voice in voices])

    # prepare the message
    user_message = {
        "role": "user",
        "content": f"We need a {casting_note}. Please rank the following voice options: {voices_string}. Return the top {num_suggestions} choice(s) for the best actors to handle the role in a numbered list."
    }
    system_message = {
        "role": "system",
        "content": "You are a casting director assistant that helps in selecting the best voice actors for a given role based on provided voice options and casting notes."
    }
    messages = [system_message, user_message]
    
    # call the model
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-16k",
        messages=messages
    )
    
    # extract the message from the response
    response_message = response['choices'][0]['message']['content']

    print(response_message)

    # Get the ordered list of voice names from the model's output
    voice_names_in_response = [match.group(1).lower() for match in re.finditer(r"\d+\. ([\w\s]+?)\s\(", response_message)]  # updated regular expression

    # filter original voices list to get top voices with all information
    top_voices = [voice for voice in voices if voice['name'].lower() in voice_names_in_response][:num_suggestions]


    return top_voices




def add_specified_voices(voices, specified_voice_names, all_voices):
    """
    Adds specified voices to the list of voices if not already present.
    """
    specified_voices = [voice for voice in all_voices if voice['name'].lower() in specified_voice_names]

    # Check for duplicates and only add specified voices that are not in the list
    for voice in specified_voices:
        if voice not in voices:
            voices.append(voice)

    return voices




# Example usage:
# Example usage:


all_voices = get_elevenlabs_voices()

print("All voices:")
for voice in all_voices:
    print(voice['name'])

# First, add specified voices
specified_voices = add_specified_voices([], specified_voice_names, all_voices)

print("Specified voices:")
for voice in specified_voices:
    print(voice['name'])


# Remaining voices are those not manually specified
remaining_voices = [voice for voice in all_voices if voice not in specified_voices]

# Then, get suggestions from ChatGPT for the remaining voices
top_voices = []
if ACTORS > 0:
    top_voices = pick_best_voices(remaining_voices, casting_note, num_suggestions=ACTORS)

# Combine manually specified voices and top voices
final_voices = specified_voices + top_voices



print("Final voice picks:")
for i, voice in enumerate(final_voices):
  print(f"{i+1}. Name: {voice['name']}, Gender: {voice['labels'].get('gender', 'N/A')}, Accent: {voice['labels'].get('accent', 'N/A')}, Voice ID: {voice['voice_id']}, Preview URL: {voice['preview_url']}, Description: {voice['labels'].get('description', 'N/A')}, Use Case: {voice['labels'].get('use case', 'N/A')}")

# Define your directory name
#dir_name = f"voicefiles_{start_time_str}"
dir_name = config.get('System', 'directory_name')


# Ensure the directory exists
os.makedirs(dir_name, exist_ok=True)


for voice_info in final_voices:
    voice_name = voice_info['name']
    voice_id = voice_info['voice_id']
    for line in lines:
        line_id, line_text = line
        for variant, (stability, similarity_boost) in enumerate(settings_combinations):
            filename = f"{dir_name}/{voice_name}_{line_id}_variant_{variant+1}_stability_{stability}_similarity_{similarity_boost}.wav"
            # Check if file exists
            if os.path.exists(filename):
                print(f"File {filename} already exists, skipping...")
                continue
            try:
                print(f"Generating line: {line_text} with stability: {stability} and similarity boost: {similarity_boost}")  # Log the line being processed
                # Generate the audio
                audio = generate_audio(text=line_text, voice_id=voice_id, stability=stability, similarity_boost=similarity_boost)
                # Save the audio file
                with open(filename, 'wb') as f:
                    f.write(audio)
            except Exception as e:
                print(f"Failed to generate audio for line: {line_text}. Error: {str(e)}")
