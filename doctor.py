"""Step 0: check this machine and say what is missing, which TTS backend fits, and what to run next.

python doctor.py [--json]

Read-only: it never installs anything. `next_steps` are commands for the user to approve and run.
Standard library only.
"""
import argparse, json, os, platform, re, shutil, subprocess, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
URL = os.environ.get("TTS_URL", "http://127.0.0.1:7860")
OS = {"Windows": "win", "Darwin": "mac"}.get(platform.system(), "linux")
BROWSERS = [
    os.environ.get("BROWSER"),
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
]
INSTALL = {
    "ffmpeg": {"win": "winget install Gyan.FFmpeg", "mac": "brew install ffmpeg", "linux": "sudo apt install ffmpeg"},
    "node": {"win": "winget install OpenJS.NodeJS", "mac": "brew install node", "linux": "install Node.js 22+ from https://nodejs.org"},
    "docker": {"win": "install Docker Desktop (WSL2 backend) from https://www.docker.com", "mac": "", "linux": "install Docker Engine + NVIDIA Container Toolkit"},
}
STUDIO_RUN = ("docker run -d --name faster-qwen3-tts-studio --restart unless-stopped --gpus all -p 127.0.0.1:7860:7860 "
              "-v faster_qwen3_tts_studio_data:/app/persistent hangrylabs/faster-qwen3-tts-studio:v1.0")


def run(*cmd, timeout=10):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() if r.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def gpu():
    out = run("nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits")
    if not out:
        return None
    name, mem = out.splitlines()[0].rsplit(",", 1)
    return {"name": name.strip(), "vram_mb": int(mem)}


def studio_up():
    try:
        with urllib.request.urlopen(URL + "/v1/audio/voices", timeout=3) as r:
            return r.status == 200
    except OSError:
        return False


def importable(mod):
    return subprocess.run([sys.executable, "-c", f"import {mod}"], capture_output=True).returncode == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    checks, steps = [], []

    def check(id, ok, detail, fix="", required=True):
        checks.append({"id": id, "ok": bool(ok), "required": required, "detail": detail})
        if not ok and fix:
            steps.append(fix)

    check("python", sys.version_info >= (3, 10), platform.python_version(), "install Python 3.10+")
    check("ffmpeg", shutil.which("ffmpeg"), shutil.which("ffmpeg") or "not on PATH", INSTALL["ffmpeg"][OS])
    node = run("node", "--version")
    node_ok = bool(node) and int(re.match(r"v(\d+)", node).group(1)) >= 22
    check("node", node_ok, node or "not found (need 22+)", INSTALL["node"][OS])
    browser = next((p for p in BROWSERS if p and Path(p).exists()), None)
    check("browser", browser, browser or "no Chromium browser found", "install Edge or Chrome, or set BROWSER=/path/to/chrome")
    check("remotion deps", (ROOT / "remotion" / "node_modules").exists(), "remotion/node_modules", "cd remotion && npm install")

    g = gpu()
    docker = bool(shutil.which("docker")) and run("docker", "info", timeout=15) is not None
    up = studio_up()
    edge = importable("edge_tts")
    vram = g["vram_mb"] if g else 0

    if up:
        tts = {"backend": "studio", "size": "1.7B", "note": f"TTS server already running at {URL}; own-voice cloning available"}
    elif g and vram >= 12000 and docker:
        tts = {"backend": "studio", "size": "1.7B", "note": "local Qwen3-TTS fits; own-voice cloning available"}
        steps.append(STUDIO_RUN + "   # then open http://127.0.0.1:7860")
    elif g and vram >= 6000 and docker:
        tts = {"backend": "studio", "size": "0.6B", "note": "limited VRAM (heuristic threshold): use the 0.6B model, "
               "e.g. `python tts.py --size 0.6B`"}
        steps.append(STUDIO_RUN + "   # then open http://127.0.0.1:7860")
    else:
        why = "no NVIDIA GPU (Studio supports NVIDIA only)" if not g else ("not enough VRAM" if vram < 6000 else "Docker not available")
        tts = {"backend": "edge", "size": None, "note": f"local Qwen3-TTS not usable: {why}. Fallback: Edge online voices "
               "(free; the script text is sent to Microsoft; no own-voice cloning) - ask the user before using it"}
        if g and vram >= 6000 and not docker:
            steps.append(INSTALL["docker"][OS] + "   # needed for local Qwen3-TTS; or use the edge fallback")
        if not edge:
            steps.append("pip install edge-tts   # only after the user agrees to the online fallback")
    check("tts", up or (tts["backend"] == "edge" and edge), f"{tts['backend']}: {tts['note']}", required=False)
    check("asr model (optional)", Path(os.environ.get("KOUBO_ASR_MODEL", "~/.cache/koubo/sherpa-onnx-fire-red-asr2-ctc-zh_en-int8-2026-02-25")).expanduser().exists(),
          "only for `build_audio.py --check`; see README", required=False)

    ready = all(c["ok"] for c in checks if c["required"]) and any(c["id"] == "tts" and c["ok"] for c in checks)
    report = {"os": OS, "gpu": g, "ready": ready, "tts": tts, "checks": checks, "next_steps": steps,
              "tts_command": "python tts.py" + (f" --backend {tts['backend']}" if tts["backend"] != "studio" else "")
              + (f" --size {tts['size']}" if tts["size"] == "0.6B" else "")}
    if a.json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
        return
    print(f"OS: {OS}   GPU: {g['name'] + ' ' + str(g['vram_mb']) + ' MiB' if g else 'none'}")
    for c in checks:
        print(f"  [{'ok' if c['ok'] else ('--' if not c['required'] else 'MISSING')}] {c['id']}: {c['detail']}")
    print(f"TTS: {tts['backend']}" + (f" ({tts['size']})" if tts["size"] else "") + f" - {tts['note']}")
    print("ready" if ready else "not ready")
    if steps:
        print("next steps (run only after the user agrees):")
        for s in steps:
            print("  " + s)
    print("then: " + report["tts_command"])


if __name__ == "__main__":
    main()
