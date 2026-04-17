"""TTS generation using ElevenLabs API (German voices)."""

import os
import requests
from pathlib import Path

ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1/text-to-speech"

# German/multilingual professional voices
VOICE_IDS = {
    "professional_male": "onwK4e9ZLuTAKqWW03F9",   # Daniel
    "professional_female": "XB0fDUnXU5powFXDhCwa",  # Charlotte (multilingual)
    "narrator": "pNInz6obpgDQGcFmaJgB",              # Adam
}

DEFAULT_VOICE = "professional_male"


def generate_tts(script: dict, output_path: Path) -> list:
    """Generate TTS audio for all scene narrations. Returns list of file paths (None if skipped)."""
    api_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    audio_files = []

    for scene in script['scenes']:
        narration = scene.get('narration', '').strip()
        scene_id = scene['id']
        audio_path = output_path / f"scene_{scene_id}_audio.mp3"

        if not narration:
            audio_files.append(None)
            continue

        if not api_key:
            # No API key – create silent placeholder using FFmpeg
            _create_silent_audio(audio_path, scene.get('duration', 8))
            audio_files.append(str(audio_path))
            continue

        voice_id = VOICE_IDS[DEFAULT_VOICE]
        response = requests.post(
            f"{ELEVENLABS_BASE_URL}/{voice_id}",
            headers={
                "xi-api-key": api_key,
                "Content-Type": "application/json"
            },
            json={
                "text": narration,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.55,
                    "similarity_boost": 0.80,
                    "style": 0.10,
                    "use_speaker_boost": True
                }
            },
            timeout=90
        )
        response.raise_for_status()

        with open(audio_path, 'wb') as f:
            f.write(response.content)

        audio_files.append(str(audio_path))

    return audio_files


def _create_silent_audio(path: Path, duration: int):
    """Create a silent MP3 placeholder using FFmpeg."""
    import subprocess
    cmd = [
        'ffmpeg', '-y', '-f', 'lavfi',
        '-i', f'anullsrc=channel_layout=stereo:sample_rate=44100',
        '-t', str(duration),
        '-q:a', '9', '-acodec', 'libmp3lame',
        str(path)
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        # Fallback: create empty file
        path.touch()
