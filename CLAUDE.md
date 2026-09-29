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

Ablauf pro Video:
1. Rohmaterial nach `video-editing/projects/<datum>-<titel>/raw/` legen (gitignored, zu groß für Git).
   Große Dateien am besten per Google-Drive-Link teilen.
2. Material sichten (Transkript, Orte, Uhrzeiten aus den Metadaten `creation_time`), dann eine
   Story nach `STYLE_GUIDE.md` bauen: Hook, Kontext, Stationen mit Orts- und Zeitkarten, Stand/Zahlen,
   Cliffhanger/Ausblick.
3. Den Schnitt als `edit.json` (EDL) im Projektordner festhalten, Format siehe `video-editing/projects/example/edit.json`.
4. Rendern: `python3 video-editing/render.py video-editing/projects/<name>/edit.json`
   (braucht ein ffmpeg mit `drawtext`, z. B. `apt-get install ffmpeg`).
5. Export liegt in `video-editing/exports/` (gitignored). Stichproben-Frames prüfen, bevor er rausgeht.

Farb-Presets stehen in `video-editing/grades.json`. Neue Looks dort ergänzen, nicht im Skript.
