# AI Voice Acting Generator

This project generates voice lines for video games using AI voice actors from multiple APIs. It was created to allow game developers to quickly generate high quality voice samples to prototype dialog in their games.

## Features

- Generates voice lines using [ElevenLabs](https://elevenlabs.io/) and [Play.ht](https://play.ht/) text-to-speech APIs
- Employs [OpenAI's ChatGPT](https://openai.com/blog/chatgpt/) to select the best voices based on a provided casting note  
- Creates multiple variants of each line by varying voice parameters like stability and similarity
- Allows manually specifying certain voices to always include
- Saves generated audio lines as .wav or .mp3 files

## Usage

The main workflow is:

1. Configure settings in `settings.ini`
    - API keys, voices to use, lines file, output folder, etc.
2. Run `python main.py`
3. Audio files are saved to the configured output folder

Some key configuration options:

- `casting_note` - The casting note used to select voices, like "An authoritative voice for a fantasy RPG villain"
- `specified_voices_*` - Voices to always include from each API
- `lines_file` - CSV file with line IDs and text
- `directory_name` - Output folder for saving audio files  
- `variants` - Number of variants to generate per voice/line

See below for a detailed explanation of each setting.

The program will:

- Fetch available voices from ElevenLabs and Play.ht
- Pick top voices for the casting note using ChatGPT   
- Add any specified voices
- Generate audio for each line using selected voices  
- Create configured number of variants by varying voice parameters
- Save audio files to the output folder

## Settings and Installation

The `settings.ini` file contains all the configuration options for the program.

```ini

directory_name - Output folder name for saving audio files.
chunk_size - Size of audio chunks when saving files.

use_elevenlabs - Whether to use ElevenLabs API.
use_playht - Whether to use Play.ht API.
casting_note - The note used to select voices with ChatGPT.
specified_voices_* - Specific voices to always include.

lines_file - CSV file with lines to generate audio for.
stability_range - Range of stability values to use.
similarity_boost_range - Range of similarity boost values to use.
variants - Number of variants to generate per voice/line.
*_actors - Number of voices to select from each API.

## Installation

Clone the repository:
git clone https://github.com/Entropicsky/elevenlabsvoicegen.git


Install dependencies:
pip install -r requirements.txt


This will install required packages like OpenAI, ElevenLabs SDK, etc. 

Create a `.env` file and add your API keys:
ELEVENLABS_API_KEY=...
CHATGPT_API_KEY=...
PLAYHT_API_KEY=...
PLAYHT_USER_ID=...


Now you can run the program:
python main.py


Generated audio files will be saved to the `directory_name` in `settings.ini`.
