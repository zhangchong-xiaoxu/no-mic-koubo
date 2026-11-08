"""Step 3: trim, speed up, normalize, ASR-check and assemble the voice track.

python build_audio.py [--tempo 1.2] [--check]

- every audio/narr/<id>.wav: cut leading/trailing silence, atempo (pitch kept), loudnorm to -16 LUFS
- --check: transcribe each clip with FireRed ASR (sherpa-onnx) and compare with the script
- writes remotion/public/narration.wav and remotion/src/segments.json [{id, text, title, image, start, end}]
Needs ffmpeg on PATH; --check also needs `pip install sherpa-onnx soundfile numpy` and the model (see README).
"""
import argparse, difflib, json, os, re, subprocess, wave
from pathlib import Path

ROOT = Path(__file__).parent
TMP = ROOT / "audio" / "_trim"
GAP = 0.12   # silence between lines
LEAD = 0.25  # silence before the first line
TAIL = 0.8   # silence after the last line
SR = 24000
ASR_MODEL = os.environ.get("KOUBO_ASR_MODEL", os.path.expanduser("~/.cache/koubo/sherpa-onnx-fire-red-asr2-ctc-zh_en-int8-2026-02-25"))


def ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *map(str, args)], check=True)


def trim(src, dst, tempo):
    af = ("silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.06,"
          "areverse,silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.1,areverse")
    if tempo != 1.0:
        af += f",atempo={tempo}"
    af += ",loudnorm=I=-16:TP=-1.5:LRA=11"
    ff("-i", src, "-af", af, "-ar", SR, "-ac", 1, dst)


def dur(p):
    with wave.open(str(p)) as w:
        return w.getnframes() / w.getframerate()


def check(items):
    import sherpa_onnx, soundfile as sf
    rec = sherpa_onnx.OfflineRecognizer.from_fire_red_asr_ctc(
        model=f"{ASR_MODEL}/model.int8.onnx", tokens=f"{ASR_MODEL}/tokens.txt", num_threads=4)
    norm = lambda t: re.sub(r"[\W_]", "", t).lower()
    bad = 0
    for s, f in items:
        tmp = TMP / "_16k.wav"
        ff("-i", f, "-af", "adelay=300", "-ar", 16000, tmp)  # lead-in silence, otherwise the first syllable gets dropped
        x, sr = sf.read(tmp, dtype="float32")
        st = rec.create_stream(); st.accept_waveform(sr, x); rec.decode_stream(st)
        score = difflib.SequenceMatcher(None, norm(st.result.text), norm(s["text"])).ratio()
        flag = "ok" if score >= 0.85 else "CHECK"
        bad += flag != "ok"
        print(f"{flag:5} {score:.2f} {s['id']:>5} | heard: {st.result.text} | script: {s['text']}")
    print(f"{bad} line(s) to listen to" if bad else "all lines match")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tempo", type=float, help="narration speed; defaults to script.json 'tempo' or 1.0")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    script = json.loads((ROOT / "script.json").read_text("utf-8"))
    tempo = a.tempo or script.get("tempo", 1.0)
    TMP.mkdir(parents=True, exist_ok=True)
    items = []
    for s in script["segments"]:
        src = ROOT / "audio" / "narr" / f"{s['id']}.wav"
        if not src.exists():
            raise SystemExit(f"missing {src.relative_to(ROOT)}; run tts.py first")
        dst = TMP / f"{s['id']}.wav"
        trim(src, dst, s.get("tempo", tempo))
        items.append((s, dst))
    if a.check:
        check(items)

    segs, lines, cur = [], [], LEAD
    for i, (s, f) in enumerate(items):
        gap = GAP if i + 1 < len(items) else TAIL
        silence = TMP / f"sil_{i}.wav"
        ff("-f", "lavfi", "-i", f"anullsrc=r={SR}:cl=mono:d={gap:.3f}", "-c:a", "pcm_s16le", silence)
        d = dur(f)
        segs.append({k: s[k] for k in ("id", "text", "title", "image") if k in s} | {"start": round(cur, 3), "end": round(cur + d, 3)})
        lines += [f"file '{f.as_posix()}'", f"file '{silence.as_posix()}'"]
        cur += d + gap
    lead = TMP / "lead.wav"
    ff("-f", "lavfi", "-i", f"anullsrc=r={SR}:cl=mono:d={LEAD:.3f}", "-c:a", "pcm_s16le", lead)
    lst = TMP / "concat.txt"
    lst.write_text("\n".join([f"file '{lead.as_posix()}'"] + lines), "utf-8")
    out = ROOT / "remotion" / "public" / "narration.wav"
    out.parent.mkdir(parents=True, exist_ok=True)
    ff("-f", "concat", "-safe", 0, "-i", lst, "-ar", SR, "-ac", 1, "-c:a", "pcm_s16le", out)
    total = dur(out)
    (ROOT / "remotion" / "src" / "segments.json").write_text(json.dumps(
        {"total": round(total, 3), "display": script.get("display", {}), "segments": segs}, ensure_ascii=False, indent=1), "utf-8")
    print(f"total {total:.2f}s, {len(segs)} lines -> remotion/public/narration.wav, remotion/src/segments.json")


if __name__ == "__main__":
    main()
