#!/usr/bin/env python3
"""End-to-end test with synthetic footage: ingest -> rough -> render --preview.

    python3 video-editing/tests/test_pipeline.py [--keep]

Builds a fake shooting day (Berlin morning, Hamburg afternoon/night) with GPS and
creation-time metadata, a portrait clip, an HLG-tagged clip, talking clips with
pauses and a music track, then checks inventory, edit list and the rendered file.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vlog import ingest, render, roughcut  # noqa: E402
from vlog.common import probe  # noqa: E402

BERLIN, HAMBURG = "+52.5163+013.3777/", "+53.5503+009.9930/"
# name, source, seconds, UTC time, gps, speech?, extra args
CLIPS = [
    ("A001.mp4", "testsrc2=s=1920x1080:r=30", 6, "2026-10-05T06:05:00Z", BERLIN, False, []),
    ("A002.mp4", "smptebars=s=1920x1080:r=30", 22, "2026-10-05T06:10:00Z", BERLIN, True, []),
    ("A003.mp4", "testsrc=s=1080x1920:r=30", 6, "2026-10-05T06:30:00Z", BERLIN, False, []),
    ("A004.mp4", "mandelbrot=s=1920x1080:r=30", 6, "2026-10-05T11:00:00Z", HAMBURG, False, []),
    ("A005.mp4", "rgbtestsrc=s=1920x1080:r=30", 24, "2026-10-05T11:05:00Z", HAMBURG, True,
     ["-color_primaries", "bt2020", "-color_trc", "arib-std-b67", "-colorspace", "bt2020nc"]),
    ("A006.mp4", "life=s=1920x1080:r=30:mold=10:ratio=0.1", 6, "2026-10-05T19:00:00Z", HAMBURG, False, []),
]


def ff(*args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


def make_project(root):
    raw = root / "raw"
    raw.mkdir(parents=True)
    (root / "music").mkdir()
    for name, src, dur, utc, gps, speech, extra in CLIPS:
        # "speech": 5 s tone, 1.2 s silence, repeating; b-roll: quiet ambience
        expr = "0.4*sin(2*PI*220*t)*lt(mod(t\\,6.2)\\,5)" if speech else "0.002*sin(2*PI*80*t)"
        ff("-f", "lavfi", "-i", src, "-f", "lavfi", "-i", f"aevalsrc={expr}:s=48000", "-t", str(dur),
           "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", *extra, "-c:a", "aac",
           "-metadata", f"creation_time={utc}", "-metadata", f"location={gps}", "-movflags", "+use_metadata_tags",
           str(raw / name))
    ff("-f", "lavfi", "-i", "sine=f=330:d=20", "-f", "lavfi", "-i", "sine=f=440:d=20",
       "-filter_complex", "amix=inputs=2", str(root / "music" / "track.mp3"))
    (root / "project.json").write_text(json.dumps({
        "title": "Testfolge", "timezone": "Europe/Berlin", "target_minutes": 2, "fps": 30,
        "stats": ["TAG 12 | 3 KUNDEN | 4.200 EUR, 18% MARGE"],
        "music": {"file": "music/track.mp3", "volume": 0.2},
    }, ensure_ascii=False))


def check(cond, msg):
    print(("  ok    " if cond else "  FEHLER ") + msg)
    if not cond:
        check.failed = True


check.failed = False


def main():
    keep = "--keep" in sys.argv
    tmp = Path(tempfile.mkdtemp(prefix="vlogtest-"))
    proj = tmp / "projects" / "2026-10-05-test"
    try:
        make_project(proj)
        print("== ingest")
        clips = {Path(c["file"]).name: c for c in ingest.run(proj, whisper=False, online=False)}
        check(len(clips) == 6, "6 Clips erkannt")
        check(clips["A002.mp4"]["kind"] == "talk" and clips["A005.mp4"]["kind"] == "talk", "Talk-Clips erkannt")
        check(clips["A001.mp4"]["kind"] == "broll", "B-Roll erkannt")
        check(clips["A001.mp4"]["place"]["city"] == "Berlin", "GPS -> Berlin")
        check(clips["A004.mp4"]["place"]["city"] == "Hamburg", "GPS -> Hamburg")
        check(clips["A001.mp4"]["recorded"].startswith("2026-10-05T08:05"), "UTC -> Ortszeit 08:05")
        check(clips["A003.mp4"]["portrait"], "Hochkant erkannt")
        check(clips["A005.mp4"]["hdr"], "HDR (HLG) erkannt")
        check(len(clips["A002.mp4"]["speech"]) >= 3, "Sprechpausen gefunden")

        print("== rough")
        edl = roughcut.run(proj)["clips"]
        ovs = [o for c in edl for o in c.get("overlays", [])]
        check({"Berlin", "Hamburg"} <= {o["text"] for o in ovs if o["type"] == "location"}, "Ortskarten Berlin + Hamburg")
        check(any(o["type"] == "time" for o in ovs), "Uhrzeit-Einblendung")
        check(any(o["type"] == "stat" for o in ovs), "Zahlen-Karte")
        check(any(c.get("music_start") for c in edl), "Musikstart an der Montage")
        check(any(c.get("grade") == "bloomfield_bw_recap" for c in edl), "Schwarzweiß im Cold Open")
        check(any(c.get("cover") for c in edl), "B-Roll über Sprache")
        check("card" in edl[-1], "Endkarte am Schluss")
        check(sum(1 for c in edl if c.get("chapter")) >= 3, "mind. 3 Kapitel")
        check(any(c.get("grade") == "bloomfield_night" for c in edl), "Nacht-Look für 21:00")

        print("== render --preview")
        out, total = render.run_render(proj / "edit.json", preview=True)
        meta = probe(out)
        expected = roughcut.length(edl)
        check(abs(meta["duration"] - expected) < 1.0, f"Länge {meta['duration']:.1f}s ≈ Schnittliste {expected:.1f}s")
        check(meta["width"] == 960 and meta["has_audio"], "540p-Vorschau mit Ton")
        chap = out.with_name(out.stem + "_chapters.txt").read_text().splitlines()
        check(len(chap) >= 3 and chap[0].startswith("0:00"), f"Kapiteldatei: {chap}")
        # frame of the first establishing shot, for a visual check
        t, frame_at = 0.0, None
        for c in edl:
            if any(o["type"] == "location" for o in c.get("overlays", [])):
                frame_at = t + 1.5
                break
            t += c.get("duration", 0) if "card" in c else c["out"] - c["in"]
        if frame_at is not None:
            ff("-ss", str(frame_at), "-i", str(out), "-frames:v", "1", str(tmp / "location_frame.png"))
            print(f"  Frame Ortskarte: {tmp / 'location_frame.png'}")
    finally:
        if not keep and not check.failed:
            shutil.rmtree(tmp, ignore_errors=True)
        else:
            print(f"Testdaten behalten: {tmp}")
    print("\nALLES OK" if not check.failed else "\nTEST FEHLGESCHLAGEN")
    sys.exit(1 if check.failed else 0)


if __name__ == "__main__":
    main()
