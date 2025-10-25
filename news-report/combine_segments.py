import requests
import json

# Your structured script from Step 1
script_data = { ... } 

ELEVENLABS_API_KEY = "your_api_key_here"
# Find Voice IDs on the ElevenLabs website
VOICE_ID_ADAM = "pNInz6obpgDQGcFmaJgB" 
VOICE_ID_RACHEL = "21m00Tcm4TlvDq8ikWAM"

audio_files = []

for segment in script_data["segments"]:
    if segment["type"] == "speech":
        print(f"Generating audio for: {segment['text'][:30]}...")
        
        voice_id = VOICE_ID_ADAM if segment['voice'] == 'Host_Adam' else VOICE_ID_RACHEL
        
        tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": ELEVENLABS_API_KEY
        }
        
        data = {
            "text": segment["text"],
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }
        
        response = requests.post(tts_url, json=data, headers=headers)
        
        # Save the audio file
        file_name = f"segment_{len(audio_files)}.mp3"
        with open(file_name, 'wb') as f:
            f.write(response.content)
        audio_files.append(file_name)
        
    elif segment["type"] == "intro_music":
        audio_files.append(segment["source"])
    # Add logic for outro music too

# Now you have a list of audio files (e.g., ['intro.mp3', 'segment_0.mp3', 'segment_1.mp3'])
# You can use a library like pydub to concatenate them into one final podcast file.
print("All audio segments generated! Next step: combine them.")