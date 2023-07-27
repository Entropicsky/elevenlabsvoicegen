# ElevenLabs Voice Generation Project

This project is designed to generate voice lines for video games using the ElevenLabs API. The program also employs OpenAI's ChatGPT to choose the best voices based on a given casting note, and generates multiple variants of each line with different voice settings. The user can specify certain voices to always include in the selection.

## Setup & Usage

1. **Install Python 3.7 or later.**

2. **Clone this repository**
    ```
    git clone <repository_url>
    ```

3. **Go into the project directory**
    ```
    cd <project_dir>
    ```

4. **Install the required Python libraries**
    ```
    pip install -r requirements.txt
    ```

5. **Setup the Environment Variables**

   Copy the `.env.template` file and rename the copy to `.env`. Fill out the `.env` file with your ElevenLabs and ChatGPT API keys.

6. **Setup the configuration**
   
   Fill out the `settings.ini` file with your desired settings and save it.

7. **Run the program**
    ```
    python main.py
    ```

The program will generate audio files for each line, for each voice, and for each combination of voice settings. The generated audio files will be saved in the `voicefiles` directory.

## Configuration

The `settings.ini` file is used to configure the program. It includes the following settings:

- `casting_note`: A description of the desired voice.
- `specified_voice_names`: A list of specific voice names to include in the voice selection. Use lower case. Separate multiple names with commas.
- `stability_range`: A list of stability values to use when generating the voice lines. The stability value affects the consistency of the voice. Separate multiple values with commas.
- `similarity_boost_range`: A list of similarity boost values to use when generating the voice lines. The similarity boost value affects the clarity and similarity of the voice. Separate multiple values with commas.
- `variants`: The number of variants to generate for each line.
- `actors`: The number of actors to select from ChatGPT's suggestions in addition to the specified voices.
- `chunk_size`: The size of the chunks in which the audio data is received from the ElevenLabs API.

## Support

If you encounter any issues or need further assistance, please raise an issue on this repository.
