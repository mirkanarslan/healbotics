#!/usr/bin/env python3
"""Healbotics vlog cutter.

  python3 video-editing/cut.py new <titel>            # Projektordner + project.json anlegen
  python3 video-editing/cut.py ingest <projekt>       # Clips sichten (Zeit, GPS, Sprache, Transkript)
  python3 video-editing/cut.py rough <projekt>        # Rohschnitt -> edit.json + review.md
  python3 video-editing/cut.py render <projekt> [--preview | --4k]
  python3 video-editing/cut.py all <projekt> [--preview]   # alles hintereinander

<projekt> ist ein Ordner unter video-editing/projects/ (Name oder Pfad).
"""
import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from vlog import ingest, render, roughcut  # noqa: E402
from vlog.common import HERE, load_json, save_json  # noqa: E402

TEMPLATE = {
    "title": "",
    "episode": 1,
    "language": "de",
    "timezone": "Europe/Berlin",
    "target_minutes": 12,
    "resolution": "1080p",
    "fps": 30,
    "stats": ["TAG 1 | 0 KUNDEN | 0 EUR UMSATZ"],
    "hook": None,
    "hook_keywords": [],
    "previously": [],
    "music": {"file": "music/track.mp3", "volume": 0.22},
    "locations": {},
    "default_location": None,
    "station_names": [],
    "grades": {},
    "end_card": {"text": "Thanks for watching", "sub": "Neue Folge jede Woche"},
    "burn_subtitles": False,
}


def project_path(name):
    p = Path(name)
    if p.is_dir():
        return p.resolve()
    p = HERE / "projects" / name
    if not p.is_dir():
        raise SystemExit(f"Projekt nicht gefunden: {name}")
    return p


def cmd_new(a):
    slug = "-".join(a.title.lower().split())
    p = HERE / "projects" / f"{date.today().isoformat()}-{slug}"
    (p / "raw").mkdir(parents=True, exist_ok=True)
    (p / "music").mkdir(exist_ok=True)
    if not (p / "project.json").exists():
        save_json(p / "project.json", {**TEMPLATE, "title": a.title})
    print(f"Projekt angelegt: {p}\n  Rohmaterial nach {p / 'raw'}\n  Musik nach {p / 'music'} "
          f"(eigene/lizenzfreie Tracks)\n  Zahlen, Orte, Hook in {p / 'project.json'}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("new"); s.add_argument("title")
    for name in ("ingest", "rough", "render", "all"):
        s = sub.add_parser(name); s.add_argument("project")
        if name in ("ingest", "all"):
            s.add_argument("--model", default="small", help="Whisper-Modell (tiny/base/small/medium/large-v3)")
            s.add_argument("--no-whisper", action="store_true", help="ohne Transkription, nur Pausenerkennung")
            s.add_argument("--offline", action="store_true", help="Orte nur aus der eingebauten Städteliste")
        if name in ("render", "all"):
            s.add_argument("--preview", action="store_true", help="schnelle 540p-Vorschau")
            s.add_argument("--4k", dest="uhd", action="store_true", help="Export in 3840x2160")
    a = ap.parse_args()

    if a.cmd == "new":
        return cmd_new(a)
    p = project_path(a.project)
    if a.cmd in ("ingest", "all"):
        print("== Sichten"); ingest.run(p, a.model, not a.no_whisper, not a.offline)
    if a.cmd in ("rough", "all"):
        print("== Rohschnitt"); roughcut.run(p)
    if a.cmd in ("render", "all"):
        if not (p / "edit.json").exists():
            raise SystemExit("edit.json fehlt. Erst `cut.py rough` ausführen.")
        print("== Rendern"); render.run_render(p / "edit.json", a.preview, a.uhd)


if __name__ == "__main__":
    main()
