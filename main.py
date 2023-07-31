import pandas as pd
import requests
import openai
import json
import time
import re
import os
from dotenv import load_dotenv
import datetime
import csv
import itertools
import configparser
import wave
import elevenlabs
from elevenlabs import generate, save
import urllib.request
import ssl
ssl._create_default_https_context = ssl._create_unverified_context


# Load environment variables from .env to get teh API keys
load_dotenv()  # take environment variables from .env.

ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
CHATGPT_API_KEY = os.getenv('CHATGPT_API_KEY')

# read the settings.ini file to get key configuration
config = configparser.ConfigParser()
config.read('settings.ini')

# use a casting note to help select voices to use
casting_note = config.get('Voice', 'casting_note')

#Use or don't use the APIs based on Settings    
use_elevenlabs = config.getboolean('Voice', 'use_elevenlabs')
use_playht = config.getboolean('Voice', 'use_playht')

# Define your ranges here
stability_range = [float(value.strip()) for value in config.get('Settings', 'stability_range').split(",")]
similarity_boost_range = [float(value.strip()) for value in config.get('Settings', 'similarity_boost_range').split(",")]

settings_combinations = list(itertools.product(stability_range, similarity_boost_range))

VARIANTS = config.getint('Settings', 'variants')  # Number of variants per actor per line
elevenlabs_actors = config.getint('Settings', 'elevenlabs_actors')  # Number of actors to cast from ChatGPT's suggestions in addition to the specified_voice_names
playht_actors = config.getint('Settings', 'playht_actors')  # Number of actors to cast from ChatGPT's suggestions in addition to the specified_voice_names

CHUNK_SIZE = config.getint('System', 'chunk_size')

# Play.ht settings
PLAYHT_API_KEY = os.getenv('PLAYHT_API_KEY')
PLAYHT_USER_ID = os.getenv('PLAYHT_USER_ID')  # Get the user ID from the environment
PLAYHT_URL_GET_VOICES = config.get('PlayHT', 'url_get_voices')
PLAYHT_URL_CONVERT = config.get('PlayHT', 'url_convert')
PLAYHT_URL_STATUS = config.get('PlayHT', 'url_status')

# Get the current time at the start of the program and format as a string
start_time = datetime.datetime.now()
start_time_str = start_time.strftime("%Y%m%d%H%M")

# ElevenLabs API constants
ELEVENLABS_URL = config.get('ElevenLabs', 'url')
elevenlabs.set_api_key(ELEVENLABS_API_KEY)

# ChatGPT API constants  
CHATGPT_MODEL = config.get('ChatGPT', 'model')
CHATGPT_URL = config.get('ChatGPT', 'url')


def get_playht_voices():
    headers = {
        "Accept": "application/json",
        "Authorization": PLAYHT_API_KEY,
        "X-User-Id": PLAYHT_USER_ID
    }
    response = requests.get(PLAYHT_URL_GET_VOICES, headers=headers)
    
    # Print the entire response
    #print("Response: ", response.__dict__)
    
    # Check the status code of the response
    if response.status_code == 403:
        print("The provided API key's plan does not have access to the requested resource.")
        return []
    
    voices = response.json()["voices"]

    
    # Filter out non-English voices
    english_voices = [voice for voice in voices if 'English' in voice['language']]
    
    print(f"Fetched {len(english_voices)} English voices from Play.ht")
    return english_voices



def generate_audio_playht(text, voice):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": PLAYHT_API_KEY,
        "X-User-Id": PLAYHT_USER_ID
    }
    data = {
        "content": [text],
        "voice": voice
    }
    response = requests.post(PLAYHT_URL_CONVERT, headers=headers, json=data)
    
    response_data = response.json()
    
    # Print the response
    print(f"Response from generate_audio_playht: {response_data}")
    
    if "error" in response_data:
        print(f"Error: {response_data['error']} for voice {voice}. Skipping this voice.")
        return None
    
    return response_data["transcriptionId"]



def get_playht_audio_status(transcription_id):
    headers = {
        "Accept": "application/json",
        "Authorization": PLAYHT_API_KEY,
        "X-User-Id": PLAYHT_USER_ID
    }
    params = {
        "transcriptionId": transcription_id
    }
    response = requests.get(PLAYHT_URL_STATUS, headers=headers, params=params)
    response_data = response.json()
    
    # Print the status code and response data for debugging
    print(f"Status code: {response.status_code}")
    print(f"Response data: {response_data}")
    
    return response_data





def generate_audio_elevenlabs(text, voice_id, stability, similarity_boost):
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


def pick_best_voices_elevenlabs(voices, casting_note, num_suggestions):
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
    # In this modified regular expression, (\s*[-:\(]|$) matches either a space followed by a dash, colon, or opening parenthesis, or the end of the string. This should allow the script to correctly extract the names whether they are followed by a space and a dash, a colon and a space, a space and an opening parenthesis, or nothing at all. 
    voice_names_in_response = [match.group(1).lower() for match in re.finditer(r"\d+\. ([\w\s]+?)(\s*[-:\(]|$)", response_message)]
    # filter original voices list to get top voices with all information
    top_voices = [voice for voice in voices if voice['name'].lower() in voice_names_in_response][:num_suggestions]


    return top_voices


def pick_best_voices_playht(voices, casting_note, num_suggestions):
    openai.api_key = CHATGPT_API_KEY

    # transform voice data into a string format
    voices_string = ', '.join([f"{voice['name']} (gender: {voice['gender']}, language: {voice['language']})" for voice in voices])

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

    # Get the ordered list of voice names from the model's output. Handle various ways that ChatGPT may format the list of voice names.
    voice_names_in_response = [match.group(1).lower() for match in re.finditer(r"\d+\. ([\w\s]+?)(\s*[-:\(]|$)", response_message)]


    # filter original voices list to get top voices with all information, preserving the order of ranking
    top_voices = [next(voice for voice in voices if voice['name'].lower() == name) for name in voice_names_in_response][:num_suggestions]

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


def download_and_save_file(url, filename):
    # Download the file
    response = requests.get(url)
    
    # Check the file format from the URL
    base_url = url.split('?')[0]  # Split the URL at the first '?'
    file_format = base_url.split('.')[-1]  # Get the file extension from the base URL

    if file_format == 'mp3':
        filename = filename.replace('.wav', '.mp3')  # Change the filename to .mp3
    elif file_format != 'wav':
        raise ValueError(f"Unsupported file format: {file_format}")
    
    with open(filename, 'wb') as f:
        f.write(response.content)


def generate_voices_for_elevenlabs(final_voices, lines, settings_combinations, dir_name):
    # Generate voices for the platform
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
                    print(f"Generating line: {voice_name}_{line_text} with stability: {stability} and similarity boost: {similarity_boost}")  # Log the line being processed
                    # Generate the audio
                    audio = generate_audio_elevenlabs(text=line_text, voice_id=voice_id, stability=stability, similarity_boost=similarity_boost)
                    # Save the audio file
                    with open(filename, 'wb') as f:
                        f.write(audio)
                except Exception as e:
                    print(f"Failed to generate audio for line: {line_text}. Error: {str(e)}")

def generate_voices_for_playht(final_voices, lines, dir_name, max_attempts=10):
    # Generate voice lines for the selected voices
    for voice_info in final_voices:
        voice_name = voice_info["name"]
        for line in lines:
            line_id, line_text = line
            filename = f"{dir_name}/playht_{voice_name}_{line_id}.mp3"
            # Check if file exists
            if os.path.exists(filename):
                print(f"File {filename} already exists, skipping...")
                continue
            transcription_id = generate_audio_playht(text=line_text, voice=voice_name)
            if transcription_id is None:
                print(f"Skipping voice {voice_name} for line {line_id} due to error in audio generation.")
                continue
            attempt = 0
            while True:
                attempt += 1
                audio_status = get_playht_audio_status(transcription_id)
                print(f"Attempt #{attempt}: Audio status for voice {voice_name}, line {line_id}: {audio_status}")  # print the audio status for debugging
                audio_ready = False
                if 'converted' in audio_status:
                    audio_ready = audio_status["converted"]
                elif 'transcriped' in audio_status:
                    audio_ready = audio_status["transcriped"]
                if audio_ready and 'audioUrl' in audio_status:
                    audio_urls = audio_status["audioUrl"]
                    if isinstance(audio_urls, str):
                        # Play.ht API gives a string
                        audio_urls = [audio_urls]
                    download_successful = False
                    for audio_url in audio_urls:
                        try:
                            # Try to download the file
                            download_and_save_file(audio_url, filename)
                            print(f'Saved audio file for voice {voice_name} line {line_id} at {filename}')
                            download_successful = True
                            break  # exit the 'for' loop once the audio has been saved
                        except Exception as e:
                            print(f'Error while downloading file: {e}')
                    if download_successful:
                        break  # exit the 'while' loop if a download was successful
                    else:
                        print(f'Waiting for audio to be ready for voice {voice_name} line {line_id}...')
                else:
                    print(f'Waiting for audio to be ready for voice {voice_name} line {line_id}...')
                if attempt >= max_attempts:
                    print(f'Stopped waiting for voice {voice_name} line {line_id} after {max_attempts} attempts.')
                    break
                time.sleep(5)


# Load the voice lines from the CSV file
lines_file = config.get('Settings', 'lines_file')
df = pd.read_csv(lines_file)
lines = list(df[['id', 'text']].itertuples(index=False, name=None))

# Define your directory name
dir_name = config.get('System', 'directory_name')

# Ensure the directory exists
os.makedirs(dir_name, exist_ok=True)

if use_elevenlabs:
    # Fetch voices from ElevenLabs API
    all_voices_elevenlabs = get_elevenlabs_voices()

    # Specify any voices that you know you want to use for ElevenLabs, if any. USE LOWER CASE. This is pulled from settings.ini
    specified_voice_names_elevenlabs = [name.strip() for name in config.get('Voice', 'specified_voices_elevenlabs').split(",")]

    # Remove any specified voices that are not in the all_voices list (i.e, invalid voice names)
    specified_voices_elevenlabs = add_specified_voices([], specified_voice_names_elevenlabs, all_voices_elevenlabs)

    # Fetch remaining voices that have not been specified for ElevenLabs
    remaining_voices_elevenlabs = [voice for voice in all_voices_elevenlabs if voice not in specified_voices_elevenlabs]

    # Get ChatGPT to choose the Top X best voices based on casting notes for ElevenLabs. X determined by the _actors variables in settings.ini
    top_voices_elevenlabs = []
    if elevenlabs_actors > 0:
        top_voices_elevenlabs = pick_best_voices_elevenlabs(remaining_voices_elevenlabs, casting_note, num_suggestions=elevenlabs_actors)

    # Combine manually specified voices and top voices for ElevenLabs
    final_voices_elevenlabs = specified_voices_elevenlabs + top_voices_elevenlabs

    # Print final voice picks for ElevenLabs
    print("Final voice picks for ElevenLabs:")
    for i, voice in enumerate(final_voices_elevenlabs):
        print(f"{i+1}. Name: {voice['name']}, Gender: {voice['labels'].get('gender', 'N/A')}, Accent: {voice['labels'].get('accent', 'N/A')}, Voice ID: {voice['voice_id']}, Preview URL: {voice['preview_url']}, Description: {voice['labels'].get('description', 'N/A')}, Use Case: {voice['labels'].get('use case', 'N/A')}")

    # Generate voices for ElevenLabs
    generate_voices_for_elevenlabs(final_voices_elevenlabs, lines, settings_combinations, dir_name)

if use_playht:
    # Fetch voices from Play.ht API
    all_voices_playht = get_playht_voices()

    # Specify any voices that you know you want to use for Play.ht. USE LOWER CASE. This is pulled from settings.ini
    specified_voice_names_playht = [name.strip() for name in config.get('Voice', 'specified_voices_playht').split(",")]

    # Remove any specified voices that are not in the all_voices list (i.e, invalid voice names
    specified_voices_playht = add_specified_voices([], specified_voice_names_playht, all_voices_playht)

    # Fetch remaining voices that have not been specified for Play.ht
    remaining_voices_playht = [voice for voice in all_voices_playht if voice not in specified_voices_playht]

    # Get ChatGPT to choose the Top X best voices based on casting notes for Play.ht. X determined by the _actors variables in settings.ini
    top_voices_playht = []
    if playht_actors > 0:
        top_voices_playht = pick_best_voices_playht(remaining_voices_playht, casting_note, num_suggestions=playht_actors)

    # Combine manually specified voices and top voices for Play.ht
    final_voices_playht = specified_voices_playht + top_voices_playht

    # Print final voice picks for Play.ht
    print("Final voice picks for Play.ht:")
    for i, voice in enumerate(final_voices_playht):
        print(f"{i+1}. Name: {voice['name']}, Gender: {voice['gender']}, Language: {voice['language']}")

    # Generate voice lines for the selected Play.ht voices
    generate_voices_for_playht(final_voices_playht, lines, dir_name, 10)
