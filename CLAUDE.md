# CLAUDE.md

## Subagents

- Alle Subagents (Agent-Tool, Workflows) laufen mit **Sonnet 5.5** (`claude-sonnet-5-5`).
  Beim Agent-Tool immer `model: "sonnet"` setzen. Zusätzlich erzwingt
  `.claude/settings.json` das über `CLAUDE_CODE_SUBAGENT_MODEL=claude-sonnet-5-5`.
- Die Hauptsession bleibt beim Modell, mit dem sie gestartet wurde.

## Repo-Inhalt

- `index.html`, `about.html`, `services.html`, `contact.html`, `assets/`, `healbotics_website/`: Healbotics-Website.
- `video-editing/`: Videoschnitt-Pipeline für die Healbotics-Vlogs (Building in Public).

## Videoschnitt

Stilreferenz: die Vlogs von Jack Bloomfield (YouTube). Referenzvideos und Analyse-Job-IDs stehen in
`video-editing/references/analysis_jobs.tsv`, die abgeleiteten Regeln in `video-editing/STYLE_GUIDE.md`.
Wir übernehmen den Schnittstil als Vorlage (Look, Tempo, Story-Aufbau, Einblendungen), aber mit
eigenem Material, eigener Musik und eigenen Grafiken. Keine Clips, Musik oder Grafiken aus den
Referenzvideos verwenden.

Werkzeug: `video-editing/cut.py` (Anleitung und alle Felder in `video-editing/README.md`).

Ablauf pro Folge:
1. `python3 video-editing/cut.py new "<titel>"`, Rohmaterial (iPhone-Originale mit Zeit und GPS) nach
   `projects/<datum>-<titel>/raw/`, Musik nach `music/`, Zahlen/Orte/Hook in `project.json`.
   Rohmaterial, Musik und Exporte sind gitignored.
2. `cut.py ingest <projekt>`: Zeit, GPS, Stadt, Sprechpausen, Transkript (faster-whisper, falls installiert).
3. `cut.py rough <projekt>`: Rohschnitt nach `STYLE_GUIDE.md` als `edit.json` plus `review.md`.
   `review.md` mit dem User durchgehen. Änderungen direkt in `edit.json` machen, danach nicht erneut `rough`
   laufen lassen (überschreibt `edit.json`).
4. `cut.py render <projekt> --preview`, Frames prüfen, dann `cut.py render <projekt>` (oder `--4k`).
   Ergebnis in `video-editing/exports/`: MP4, `_chapters.txt` für die YouTube-Beschreibung, `.srt`.

Vor Änderungen am Tool: `python3 video-editing/tests/test_pipeline.py` muss mit „ALLES OK“ enden.
Farb-Presets stehen in `video-editing/grades.json`. Neue Looks dort ergänzen, nicht im Code.
