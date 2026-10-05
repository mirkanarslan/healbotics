"""Step 1: scan raw/, collect per-clip facts into inventory.json.

Per clip: duration, orientation, HDR, local recording time, GPS + city,
speech intervals (whisper word timestamps if installed, else ffmpeg
silencedetect) and the transcript. Results are cached by file size+mtime,
so re-running only processes new or changed clips.
"""
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from . import places
from .common import VIDEO_EXT, ffmpeg, load_json, probe, save_json


def recorded_at(meta, path, tz):
    tags = meta["tags"]
    raw = tags.get("com.apple.quicktime.creationdate")  # local time with offset, iPhone
    if raw:
        try:
            return datetime.strptime(raw[:24], "%Y-%m-%dT%H:%M:%S%z").astimezone(tz)
        except ValueError:
            pass
    raw = tags.get("creation_time")  # UTC
    if raw:
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(tz)
        except ValueError:
            pass
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).astimezone(tz)


def silence_speech(path, duration, noise_db=-32, min_silence=0.6):
    """Speech = everything that is not silence, per ffmpeg silencedetect."""
    err = subprocess.run([ffmpeg(), "-hide_banner", "-nostats", "-i", str(path), "-vn",
                          "-af", f"silencedetect=noise={noise_db}dB:d={min_silence}", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    speech, cursor = [], 0.0
    for i, s in enumerate(starts):
        if s > cursor:
            speech.append([cursor, s])
        cursor = ends[i] if i < len(ends) else duration
    if cursor < duration:
        speech.append([cursor, duration])
    return clean_intervals(speech)


def clean_intervals(iv, merge_gap=0.35, min_len=0.4):
    out = []
    for s, e in sorted(iv):
        if out and s - out[-1][1] <= merge_gap:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return [[round(s, 3), round(e, 3)] for s, e in out if e - s >= min_len]


_MODEL = {}


def transcribe(path, model_name, language):
    """Return transcript segments with word timestamps, or None if no whisper is installed."""
    try:
        from faster_whisper import WhisperModel
        if model_name not in _MODEL:
            _MODEL[model_name] = WhisperModel(model_name, compute_type="int8")
        segs, _ = _MODEL[model_name].transcribe(str(path), language=language, word_timestamps=True,
                                                vad_filter=True)
        return [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip(),
                 "words": [[round(w.start, 2), round(w.end, 2), w.word.strip()] for w in (s.words or [])]}
                for s in segs]
    except ImportError:
        pass
    try:
        import whisper
        if model_name not in _MODEL:
            _MODEL[model_name] = whisper.load_model(model_name)
        res = _MODEL[model_name].transcribe(str(path), language=language, word_timestamps=True)
        return [{"start": round(s["start"], 2), "end": round(s["end"], 2), "text": s["text"].strip(),
                 "words": [[round(w["start"], 2), round(w["end"], 2), w["word"].strip()]
                           for w in s.get("words", [])]}
                for s in res["segments"]]
    except ImportError:
        return None


def words_speech(transcript, gap=0.6):
    iv = [[w[0], w[1]] for seg in transcript for w in seg["words"]] or \
         [[seg["start"], seg["end"]] for seg in transcript]
    return clean_intervals(iv, merge_gap=gap, min_len=0.3)


def classify(speech, duration):
    talk = sum(e - s for s, e in speech)
    return "talk" if talk >= 3 and talk / max(duration, 0.1) >= 0.35 else "broll"


def run(project_dir, model="small", whisper=True, online=True):
    project_dir = Path(project_dir).resolve()
    cfg = load_json(project_dir / "project.json", {})
    tz = ZoneInfo(cfg.get("timezone", "Europe/Berlin"))
    language = cfg.get("language")
    old = {c["file"]: c for c in load_json(project_dir / "inventory.json", {}).get("clips", [])}
    files = sorted(p for p in (project_dir / "raw").rglob("*")
                   if p.suffix.lower() in VIDEO_EXT and not p.name.startswith("."))
    if not files:
        raise SystemExit(f"Keine Videos in {project_dir / 'raw'} gefunden.")

    clips, no_whisper = [], False
    for path in files:
        rel = str(path.relative_to(project_dir))
        stat = path.stat()
        prev = old.get(rel)
        if prev and prev.get("size") == stat.st_size and prev.get("mtime") == int(stat.st_mtime) \
                and (prev.get("transcript") is not None or not whisper):
            clips.append(prev)
            continue
        meta = probe(path)
        if not meta["has_video"]:
            continue
        print(f"  {rel} ({meta['duration']:.1f}s)", flush=True)
        when = recorded_at(meta, path, tz)
        gps = places.gps_from_tags(meta["tags"])
        place = places.lookup(gps, project_dir / "geocache.json", cfg.get("language", "de"), online) \
            if gps else None

        transcript = transcribe(path, model, language) if whisper and meta["has_audio"] else None
        if whisper and meta["has_audio"] and transcript is None:
            no_whisper = True
        if transcript:
            speech = words_speech(transcript)
        elif meta["has_audio"]:
            speech = silence_speech(path, meta["duration"], cfg.get("silence_db", -32))
        else:
            speech = []

        clips.append({
            "file": rel, "size": stat.st_size, "mtime": int(stat.st_mtime),
            "duration": round(meta["duration"], 3), "width": meta["width"], "height": meta["height"],
            "portrait": meta["height"] > meta["width"], "fps": meta.get("fps"),
            "hdr": meta.get("transfer") in ("arib-std-b67", "smpte2084"),
            "transfer": meta.get("transfer"), "has_audio": meta["has_audio"],
            "recorded": when.isoformat(timespec="seconds"),
            "gps": list(gps) if gps else None, "place": place,
            "speech": speech, "kind": classify(speech, meta["duration"]),
            "transcript": transcript,
        })

    clips.sort(key=lambda c: (c["recorded"], c["file"]))
    save_json(project_dir / "inventory.json", {"project": project_dir.name, "clips": clips})

    print(f"\n{len(clips)} Clips -> {project_dir / 'inventory.json'}")
    for c in clips:
        where = (c.get("place") or {}).get("city", "-")
        talk = sum(e - s for s, e in c["speech"])
        print(f"  {c['recorded'][11:16]}  {c['kind']:5}  {where:18.18}  {c['duration']:6.1f}s  "
              f"Sprache {talk:5.1f}s  {c['file']}")
    if no_whisper:
        print("\nHinweis: Kein Whisper installiert, Sprache nur per Pausenerkennung. Für Transkripte, "
              "Untertitel und bessere Hook-Auswahl: `pip install faster-whisper`.")
    return clips
