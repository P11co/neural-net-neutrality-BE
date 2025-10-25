from fish_audio_sdk import Session, TTSRequest
from dotenv import load_dotenv
import os
from pathlib import Path
from typing import Union, Optional

load_dotenv(".local.env", override=True)

def synthesize_fish(
  script: str,
  output_path: Union[str, Path, None] = None,
  backend: str = "s1",
  api_key: Optional[str] = None,
) -> Path:
  """Synthesize `script` using the Fish TTS SDK and save to `output_path`.

  - If `api_key` is not provided, reads `FISH_API_KEY` from the environment.
  - If `output_path` is None the file is saved to `backend/voice/audio-data/latest-news.mp3`.
  - Returns the Path to the saved file.
  """
  if api_key is None:
    api_key = os.getenv("FISH_API_KEY")

  if api_key is None:
    raise RuntimeError("No Fish API key provided and FISH_API_KEY not found in environment")

  session = Session(api_key)

  if output_path is None:
    output_path = Path(__file__).parent / "audio-data" / "latest-news.mp3"
  else:
    output_path = Path(output_path)

  output_path.parent.mkdir(parents=True, exist_ok=True)

  with output_path.open("wb") as f:
    for chunk in session.tts(TTSRequest(text=script), backend=backend):
      f.write(chunk)

  return output_path


if __name__ == "__main__":
  demo_script = "Hello — this is a quick test of the Fish TTS synthesize_fish function."
  out = synthesize_fish(demo_script, output_path=Path(__file__).parent / "audio-data" / "fish-demo.mp3")
  print(f"✓ Audio saved to {out}")