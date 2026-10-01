"""Asset providers. Written against public REST docs and NOT exercised in this repo's tests (no network/keys in CI);
verify against current docs before relying on them. Add a Higgsfield/video adapter the same way."""
import base64
import json
import os
import urllib.error
import urllib.request

from .llm import LLMError


def _post(url: str, headers: dict, payload: dict, timeout: int = 120) -> bytes:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        raise LLMError(f"HTTP {e.code}: {e.read().decode(errors='replace')[:200]}")
    except (urllib.error.URLError, TimeoutError) as e:
        raise LLMError(f"network error: {e}")


def elevenlabs_tts(text: str, out_path: str, voice_id: str | None = None,
                   model_id: str = "eleven_multilingual_v2") -> None:
    key, voice = os.getenv("ELEVENLABS_API_KEY"), voice_id or os.getenv("ELEVENLABS_VOICE_ID")
    if not key or not voice:
        raise LLMError("set ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID")
    audio = _post(f"https://api.elevenlabs.io/v1/text-to-speech/{voice}",
                  {"xi-api-key": key, "Accept": "audio/mpeg"}, {"text": text, "model_id": model_id})
    with open(out_path, "wb") as f:
        f.write(audio)


def openai_image(prompt: str, out_path: str, model: str = "gpt-image-1", size: str = "1024x1536") -> None:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise LLMError("OPENAI_API_KEY is not set")
    data = json.loads(_post("https://api.openai.com/v1/images/generations",
                            {"Authorization": f"Bearer {key}"},
                            {"model": model, "prompt": prompt, "size": size, "n": 1}))
    with open(out_path, "wb") as f:
        f.write(base64.b64decode(data["data"][0]["b64_json"]))
