from elevenlabs.client import ElevenLabs
from elevenlabs.play import play
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Union, Optional

load_dotenv(".local.env", override=True)

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

elevenlabs = ElevenLabs(api_key=ELEVENLABS_API_KEY)


def synthesize_elevenlab(
  text: str,
  output_path: Union[str, Path, None] = None,
  voice_id: str = "UgBBYS2sOqTuMpoF3BR0",
  model_id: str = "eleven_multilingual_v2",
  output_format: str = "mp3_44100_128",
  play_audio: bool = False,
) -> Path:
  """Synthesize `text` using ElevenLabs, save to `output_path`, and return the Path.

  - If `output_path` is None the file is saved to `backend/voice/audio-data/latest-news.mp3`.
  - `play_audio=True` will play the generated audio after saving.
  """
  if output_path is None:
    output_path = Path(__file__).parent / "audio-data" / "latest-news.mp3"
  else:
    output_path = Path(output_path)

  # Ensure directory exists
  output_path.parent.mkdir(parents=True, exist_ok=True)

  # Get streaming audio bytes from SDK
  audio_stream = elevenlabs.text_to_speech.convert(
    text=text,
    voice_id=voice_id,
    model_id=model_id,
    output_format=output_format,
  )

  # Write stream to file (streaming iterable of bytes/chunks)
  with output_path.open("wb") as f:
    for chunk in audio_stream:
      f.write(chunk)

  if play_audio:
    # Play the saved file by reading its bytes (SDK play accepts bytes)
    with output_path.open("rb") as f:
      play(f.read())

  return output_path


if __name__ == "__main__":
  # Quick local demo when running the module directly
  demo_text = "The first move is what sets everything in motion."
  out = synthesize_elevenlab(demo_text, play_audio=False)
  print(f"Audio saved to {out}")