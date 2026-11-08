"""Step 2: synthesize every segment in script.json with a local Qwen3-TTS server.

python tts.py [--only s01,s03] [--seed 7] [--force]

- Talks to the OpenAI-compatible API of faster-qwen3-tts-studio (TTS_URL, default http://127.0.0.1:7860).
- Built-in speakers (e.g. Vivian) use the CustomVoice model; voices you cloned/saved in the Studio use the Base model.
- Writes audio/narr/<id>.wav; existing files are kept unless --force, so you can re-roll single lines.
Standard library only.
"""
import argparse, io, json, os, urllib.error, urllib.request, wave
from pathlib import Path

ROOT = Path(__file__).parent
URL = os.environ.get("TTS_URL", "http://127.0.0.1:7860")
CUSTOM = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
BASE = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
ENDS = "。！？!?；;"


def http(path, body=None, timeout=300):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(URL + path, data=data, headers={"Content-Type": "application/json; charset=utf-8"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def chunks(text, limit=100):
    """Long lines degrade, so split at sentence ends into pieces of <= limit characters."""
    out, cur = [], ""
    for ch in text:
        cur += ch
        if ch in ENDS or len(cur) >= limit:
            out.append(cur.strip())
            cur = ""
    if cur.strip():
        out.append(cur.strip())
    merged = []
    for c in out:
        if merged and len(merged[-1]) + len(c) <= limit:
            merged[-1] += c
        else:
            merged.append(c)
    return merged


def join(parts, gap_ms=200):
    frames, params = [], None
    for b in parts:
        with wave.open(io.BytesIO(b)) as w:
            params = params or w.getparams()
            frames.append(w.readframes(w.getnframes()))
    gap = b"\x00" * (int(params.framerate * gap_ms / 1000) * params.nchannels * params.sampwidth)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setparams(params)
        w.writeframes(gap.join(frames))
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated segment ids")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    script = json.loads((ROOT / "script.json").read_text("utf-8"))
    voice = script["voice"]
    try:
        voices = json.loads(http("/v1/audio/voices", timeout=10))["data"]
    except (urllib.error.URLError, OSError) as e:
        raise SystemExit(f"TTS server not reachable at {URL}: {e}")
    builtin = {v["id"] for v in voices if v.get("owned_by") == "qwen"}
    if voice not in {v["id"] for v in voices}:
        raise SystemExit(f"voice {voice!r} not found; available: {', '.join(v['id'] for v in voices)}")
    model = CUSTOM if voice in builtin else BASE
    only = set(a.only.split(",")) if a.only else None
    out_dir = ROOT / "audio" / "narr"
    out_dir.mkdir(parents=True, exist_ok=True)
    for s in script["segments"]:
        out = out_dir / f"{s['id']}.wav"
        if (only and s["id"] not in only) or (out.exists() and not a.force and not only):
            continue
        parts = [http("/v1/audio/speech", {"model": model, "input": c, "voice": voice, "language": "Chinese",
                                           "response_format": "wav", "seed": a.seed}) for c in chunks(s["text"])]
        out.write_bytes(join(parts))
        print("wrote", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
