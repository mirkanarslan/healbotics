"""Shared helpers: ffmpeg discovery, fonts, media probing, time formatting."""
import json
import os
import re
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent  # video-editing/
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".mts", ".mxf"}

# First existing file wins. Override with VLOG_FONT_<KIND>=/path/to/font.ttf
# or drop fonts into video-editing/fonts/ named <kind>.ttf (e.g. bold.ttf).
FONT_CANDIDATES = {
    "bold": [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
    "regular": [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ],
    "mono": [
        "/System/Library/Fonts/Supplemental/Courier New.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ],
    "serif": [
        "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
        "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    ],
}


@lru_cache(None)
def font(kind):
    env = os.environ.get(f"VLOG_FONT_{kind.upper()}")
    for cand in [env, str(HERE / "fonts" / f"{kind}.ttf"), *FONT_CANDIDATES[kind]]:
        if cand and Path(cand).exists():
            return cand
    raise SystemExit(f"Keine Schrift für '{kind}' gefunden. Setze VLOG_FONT_{kind.upper()} "
                     f"oder lege video-editing/fonts/{kind}.ttf ab.")


def font_opt(kind):
    """fontfile=... option for drawtext, quoted so paths with spaces work."""
    return "expansion=none:fontfile='" + font(kind).replace("'", r"\'").replace(":", r"\:") + "'"


@lru_cache(None)
def ffmpeg():
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    raise SystemExit("ffmpeg fehlt. Mac: `brew install ffmpeg`, Linux: `apt-get install ffmpeg`.")


@lru_cache(None)
def ffprobe():
    return shutil.which("ffprobe")


@lru_cache(None)
def has_filter(name):
    out = subprocess.run([ffmpeg(), "-hide_banner", "-filters"], capture_output=True, text=True).stdout
    return re.search(rf"^\s*\S+\s+{re.escape(name)}\s", out, re.M) is not None


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


@lru_cache(None)
def probe(path):
    """Media facts for one file: duration, size, rotation-corrected orientation,
    audio presence, HDR transfer, creation time and GPS tags."""
    path = str(path)
    if not ffprobe():
        info = subprocess.run([ffmpeg(), "-hide_banner", "-i", path],
                              capture_output=True, text=True).stderr
        hms = re.search(r"Duration: (\d+):(\d+):([\d.]+)", info).groups()
        size = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", info)
        return {"duration": int(hms[0]) * 3600 + int(hms[1]) * 60 + float(hms[2]),
                "width": int(size.group(1)) if size else 0,
                "height": int(size.group(2)) if size else 0,
                "has_audio": "Audio:" in info, "has_video": "Video:" in info,
                "transfer": None, "tags": {}}
    data = json.loads(subprocess.run(
        [ffprobe(), "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
        capture_output=True, text=True, check=True).stdout)
    v = next((s for s in data["streams"] if s.get("codec_type") == "video"), {})
    w, h = v.get("width", 0), v.get("height", 0)
    rot = int(v.get("tags", {}).get("rotate", 0) or 0)
    for sd in v.get("side_data_list", []):
        if "rotation" in sd:
            rot = int(sd["rotation"])
    if abs(rot) % 180 == 90:
        w, h = h, w
    tags = {k.lower(): val for k, val in data["format"].get("tags", {}).items()}
    tags.update({k.lower(): val for k, val in v.get("tags", {}).items() if k.lower() not in tags})
    return {
        "duration": float(data["format"].get("duration") or v.get("duration") or 0),
        "width": w, "height": h,
        "has_audio": any(s.get("codec_type") == "audio" for s in data["streams"]),
        "has_video": bool(v),
        "transfer": v.get("color_transfer"),
        "primaries": v.get("color_primaries"),
        "fps": _fps(v.get("avg_frame_rate", "0/1")),
        "tags": tags,
    }


def _fps(rate):
    num, _, den = rate.partition("/")
    try:
        return round(float(num) / float(den or 1), 3)
    except (ValueError, ZeroDivisionError):
        return 0


def tc(seconds):
    """Seconds -> M:SS or H:MM:SS (YouTube chapter format)."""
    s = int(round(seconds))
    h, m, s = s // 3600, s % 3600 // 60, s % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def srt_tc(seconds):
    ms = int(round(seconds * 1000))
    return f"{ms // 3600000:02d}:{ms % 3600000 // 60000:02d}:{ms % 60000 // 1000:02d},{ms % 1000:03d}"


def load_json(path, default=None):
    p = Path(path)
    return json.loads(p.read_text()) if p.exists() else default


def save_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def esc_text(text):
    """Escape text for a single-quoted drawtext value."""
    return (str(text).replace("\\", "\\\\").replace(":", "\\:").replace("'", "’")
            .replace(",", "\\,"))
