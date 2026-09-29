#!/usr/bin/env python3
"""Render a vlog from an edit decision list (EDL) in the reference style.

Usage:
    python3 video-editing/render.py video-editing/projects/<name>/edit.json

The EDL describes the cut: which raw clips, in/out points, the color grade,
and the overlays (location/city card, timestamp, build-in-public stat cards).
See video-editing/projects/example/edit.json for the format.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
GRADES = json.loads((HERE / "grades.json").read_text())
FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
FONT_SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FONT_MONO = "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"


def ffmpeg_bin():
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    import imageio_ffmpeg  # pip install imageio-ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def probe(ff, path):
    """Return (duration_seconds, has_audio) for a media file."""
    info = subprocess.run([ff, "-hide_banner", "-i", path], capture_output=True, text=True).stderr
    hms = re.search(r"Duration: (\d+):(\d+):([\d.]+)", info).groups()
    return int(hms[0]) * 3600 + int(hms[1]) * 60 + float(hms[2]), "Audio:" in info


def esc(text):
    # drawtext needs ':' '\'' and '%' escaped
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace("%", "\\%")


def fade_alpha(start, dur, fade=0.35):
    end = start + dur
    return (f"if(lt(t,{start}),0,if(lt(t,{start + fade}),(t-{start})/{fade},"
            f"if(lt(t,{end - fade}),1,if(lt(t,{end}),({end}-t)/{fade},0))))")


def overlay_filters(ov, h):
    """Build drawtext filters for one overlay, timed relative to the clip."""
    start = ov.get("start", 0.3)
    dur = ov.get("duration", 3.0)
    alpha = fade_alpha(start, dur)
    enable = f"between(t,{start},{start + dur})"
    size = int(h * ov.get("scale", 1.0) / 1080 * 64)
    common = f"fontcolor=white:alpha='{alpha}':enable='{enable}'"
    kind = ov["type"]

    if kind == "location":
        # Large city name bottom-left with a smaller country/sub line.
        filters = [f"drawtext=fontfile={FONT_BOLD}:text='{esc(ov['text'].upper())}':"
                   f"fontsize={size}:{common}:x=w*0.06:y=h*0.78-th:"
                   f"shadowcolor=black@0.45:shadowx=2:shadowy=2"]
        if ov.get("sub"):
            filters.append(f"drawtext=fontfile={FONT_REG}:text='{esc(ov['sub'])}':"
                           f"fontsize={int(size * 0.42)}:{common}:x=w*0.06+4:"
                           f"y=h*0.78+{int(size * 0.2)}:shadowcolor=black@0.45:shadowx=1:shadowy=1")
        return filters
    if kind == "time":
        # Small monospace clock top-left, camcorder-timestamp style.
        return [f"drawtext=fontfile={FONT_MONO}:text='{esc(ov['text'])}':"
                f"fontsize={int(size * 0.55)}:{common}:x=w*0.05:y=h*0.07:"
                f"shadowcolor=black@0.5:shadowx=1:shadowy=1"]
    if kind == "stat":
        # Build-in-public stat card, e.g. "Tag 12 | 3 Kunden | 4.200 EUR MRR".
        return [f"drawtext=fontfile={FONT_BOLD}:text='{esc(ov['text'])}':"
                f"fontsize={int(size * 0.6)}:{common}:box=1:boxcolor=black@0.55:"
                f"boxborderw={int(size * 0.3)}:x=(w-tw)/2:y=h*0.12"]
    if kind == "caption":
        # Lower-third line for narration / key sentence.
        return [f"drawtext=fontfile={FONT_BOLD}:text='{esc(ov['text'])}':"
                f"fontsize={int(size * 0.55)}:{common}:x=(w-tw)/2:y=h*0.86:"
                f"shadowcolor=black@0.7:shadowx=2:shadowy=2"]
    raise ValueError(f"unknown overlay type: {kind}")


def render_card(ff, clip, idx, cfg, tmp):
    """Text on black, e.g. end card "Thanks for watching" or a chapter card."""
    w, h, fps = cfg["width"], cfg["height"], cfg["fps"]
    card, dur = clip["card"], clip.get("duration", 3.0)
    font = FONT_SERIF if card.get("serif", True) else FONT_BOLD
    size = int(h / 1080 * card.get("size", 72))
    lines = [card["text"]] + ([card["sub"]] if card.get("sub") else [])
    vf = []
    for i, line in enumerate(lines):
        fs = size if i == 0 else int(size * 0.45)
        y = f"(h-th)/2-{int(size * 0.4)}" if len(lines) > 1 and i == 0 else (
            f"(h/2)+{int(size * 0.5)}" if i else "(h-th)/2")
        vf.append(f"drawtext=fontfile={font}:text='{esc(line)}':fontsize={fs}:"
                  f"fontcolor={card.get('color', '#D4AF37') if i == 0 else 'white@0.85'}:"
                  f"alpha='{fade_alpha(0.2, dur - 0.4, 0.5)}':x=(w-tw)/2:y={y}")
    out = tmp / f"seg_{idx:03d}.mp4"
    subprocess.run([ff, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    f"color=black:s={w}x{h}:r={fps}:d={dur}", "-f", "lavfi", "-i",
                    "anullsrc=r=48000:cl=stereo", "-vf", ",".join(vf) + ",setsar=1",
                    "-t", str(dur), "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    str(out)], check=True)
    return out


def render_segment(ff, clip, idx, cfg, tmp):
    if "card" in clip:
        return render_card(ff, clip, idx, cfg, tmp)
    w, h, fps = cfg["width"], cfg["height"], cfg["fps"]
    grade = GRADES[clip.get("grade", cfg["grade"])]
    speed = clip.get("speed", 1.0)
    vf = [f"scale={w}:{h}:force_original_aspect_ratio=increase", f"crop={w}:{h}",
          f"fps={fps}", "setsar=1"]
    if speed != 1.0:
        vf.append(f"setpts=PTS/{speed}")
    vf.append(grade["filter"])
    for ov in clip.get("overlays", []):
        vf += overlay_filters(ov, h)
    if cfg["letterbox"]:
        bar = int(h * cfg["letterbox"])
        vf.append(f"drawbox=x=0:y=0:w=iw:h={bar}:color=black:t=fill,"
                  f"drawbox=x=0:y=ih-{bar}:w=iw:h={bar}:color=black:t=fill")

    af = [f"atempo={speed}"] if speed != 1.0 else []
    af.append(f"volume={clip.get('volume', 1.0)}")

    src_dur, src_audio = probe(ff, clip["file"])
    seg_dur = (clip.get("out", src_dur) - clip.get("in", 0)) / speed

    out = tmp / f"seg_{idx:03d}.mp4"
    cmd = [ff, "-y", "-loglevel", "error"]
    if "in" in clip:
        cmd += ["-ss", str(clip["in"])]
    if "out" in clip:
        cmd += ["-to", str(clip["out"])]
    cmd += ["-i", clip["file"], "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
    if src_audio:
        audio = f"[0:a]{','.join(af)}[a0];[a0][1:a]amix=inputs=2:duration=first[a]"
    else:
        audio = "[1:a]anull[a]"
    cmd += ["-filter_complex", f"[0:v]{','.join(vf)}[v];{audio}",
            "-map", "[v]", "-map", "[a]", "-t", f"{seg_dur:.3f}", "-c:v", "libx264", "-preset", "medium",
            "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            str(out)]
    subprocess.run(cmd, check=True)
    return out


def main():
    edl_path = Path(sys.argv[1]).resolve()
    edl = json.loads(edl_path.read_text())
    os.chdir(edl_path.parent)
    cfg = {"width": 1920, "height": 1080, "fps": 25, "letterbox": 0,
           "grade": "bloomfield_warm_film", **edl.get("settings", {})}
    ff = ffmpeg_bin()

    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        segs = [render_segment(ff, c, i, cfg, tmp) for i, c in enumerate(edl["clips"])]
        listfile = tmp / "list.txt"
        listfile.write_text("".join(f"file '{s}'\n" for s in segs))
        joined = tmp / "joined.mp4"
        subprocess.run([ff, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                        "-i", str(listfile), "-c", "copy", str(joined)], check=True)

        output = Path(edl.get("output", "export.mp4"))
        output.parent.mkdir(parents=True, exist_ok=True)
        music = edl.get("music")
        if music:
            # Duck the music under dialogue with sidechain compression.
            audio = (f"[1:a]volume={music.get('volume', 0.25)}[m];"
                     "[m][0:a]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[md];"
                     "[0:a][md]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1[a]")
            cmd = [ff, "-y", "-loglevel", "error", "-i", str(joined),
                   "-stream_loop", "-1", "-i", music["file"], "-filter_complex", audio,
                   "-map", "0:v", "-map", "[a]"]
        else:
            cmd = [ff, "-y", "-loglevel", "error", "-i", str(joined),
                   "-af", "loudnorm=I=-14:TP=-1"]
        subprocess.run(cmd + ["-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", str(output)],
                       check=True)
    print(f"rendered {output}")


if __name__ == "__main__":
    main()
