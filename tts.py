"""Step 2: synthesize every segment in script.json.

python tts.py [--backend studio|edge] [--size 1.7B|0.6B] [--only s01,s03] [--seed 7] [--force]

- studio (default): the OpenAI-compatible API of a local faster-qwen3-tts-studio (TTS_URL, default http://127.0.0.1:7860).
  Built-in speakers (e.g. Vivian) use the CustomVoice model; voices you cloned/saved in the Studio use the Base model.
  --size picks the model size (0.6B needs less VRAM); also TTS_SIZE.
- edge: Microsoft Edge online voices via `pip install edge-tts`; no GPU needed, but the text is sent to Microsoft's
  service and your own voice cannot be cloned. Voice: script.json "edge_voice" (default zh-CN-XiaoxiaoNeural).
- Backend can also be set with TTS_BACKEND. Run `python doctor.py` to see which one fits this machine.
- Writes audio/narr/<id>.wav; existing files are kept unless --force, so you can re-roll single lines.
Standard library only (edge also needs ffmpeg, like step 3).
"""
import argparse, io, json, os, subprocess, sys, tempfile, urllib.error, urllib.request, wave
from pathlib import Path

ROOT = Path(__file__).parent
URL = os.environ.get("TTS_URL", "http://127.0.0.1:7860")
ENDS = "。！？!?；;"
EDGE_VOICE = "zh-CN-XiaoxiaoNeural"


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


def studio_synth(script, size, seed):
    voice = script["voice"]
    try:
        voices = json.loads(http("/v1/audio/voices", timeout=10))["data"]
    except (urllib.error.URLError, OSError) as e:
        raise SystemExit(f"TTS server not reachable at {URL}: {e}\n"
                         "Run `python doctor.py` for setup steps, or use `--backend edge` (online, no GPU).")
    builtin = {v["id"] for v in voices if v.get("owned_by") == "qwen"}
    if voice not in {v["id"] for v in voices}:
        raise SystemExit(f"voice {voice!r} not found; available: {', '.join(v['id'] for v in voices)}")
    model = f"Qwen/Qwen3-TTS-12Hz-{size}-{'CustomVoice' if voice in builtin else 'Base'}"

    def synth(text):
        return http("/v1/audio/speech", {"model": model, "input": text, "voice": voice, "language": "Chinese",
                                         "response_format": "wav", "seed": seed})
    return synth


def edge_synth(script):
    voice = script.get("edge_voice", EDGE_VOICE)
    try:
        import edge_tts  # noqa: F401
    except ImportError:
        raise SystemExit("edge backend needs `pip install edge-tts`")

    def synth(text):
        with tempfile.TemporaryDirectory() as d:
            mp3, wav = Path(d, "a.mp3"), Path(d, "a.wav")
            r = subprocess.run([sys.executable, "-m", "edge_tts", "--voice", voice, "--text", text,
                                "--write-media", str(mp3)], capture_output=True, text=True)
            if r.returncode or not mp3.exists():
                raise SystemExit(f"edge-tts failed (needs internet access): {(r.stderr or r.stdout).strip()[-300:]}")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(mp3), "-ar", "24000", "-ac", "1", str(wav)], check=True)
            return wav.read_bytes()
    return synth


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=["studio", "edge"], default=os.environ.get("TTS_BACKEND", "studio"))
    ap.add_argument("--size", choices=["1.7B", "0.6B"], default=os.environ.get("TTS_SIZE", "1.7B"))
    ap.add_argument("--only", help="comma-separated segment ids")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    script = json.loads((ROOT / "script.json").read_text("utf-8"))
    synth = studio_synth(script, a.size, a.seed) if a.backend == "studio" else edge_synth(script)
    only = set(a.only.split(",")) if a.only else None
    out_dir = ROOT / "audio" / "narr"
    out_dir.mkdir(parents=True, exist_ok=True)
    for s in script["segments"]:
        out = out_dir / f"{s['id']}.wav"
        if (only and s["id"] not in only) or (out.exists() and not a.force and not only):
            continue
        out.write_bytes(join([synth(c) for c in chunks(s["text"])]))
        print("wrote", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
