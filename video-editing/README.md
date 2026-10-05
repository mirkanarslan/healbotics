# Healbotics Vlog-Cutter

Schneidet aus Rohmaterial eine Building-in-Public-Folge im Stil von Jack Bloomfield
(Regeln: `STYLE_GUIDE.md`).

```
raw/ ──ingest──▶ inventory.json ──rough──▶ edit.json + review.md ──render──▶ exports/<projekt>.mp4
                                                                              + _chapters.txt + .srt
```

## Einrichtung auf dem Mac (einmalig)

```bash
brew install ffmpeg python            # ffmpeg mit drawtext/zscale ist bei Homebrew dabei
pip3 install faster-whisper           # optional, aber empfohlen: Transkript, Untertitel, Hook-Auswahl
git clone https://github.com/mirkanarslan/healbotics.git && cd healbotics
git checkout claude/video-editing-jack-bloomfield-w0myzg
python3 video-editing/tests/test_pipeline.py   # Selbsttest, endet mit "ALLES OK"
```

Schriften kommen automatisch aus macOS (Arial, Courier New, Georgia). Eigene Schriften:
`video-editing/fonts/bold.ttf`, `regular.ttf`, `mono.ttf`, `serif.ttf` ablegen.

## Eine Folge schneiden

```bash
python3 video-editing/cut.py new "Erster Kunde"        # legt projects/<datum>-erster-kunde/ an
# iPhone-Clips nach .../raw/ kopieren (Original-Dateien, damit Zeit und GPS erhalten bleiben)
# eigene/lizenzfreie Musik nach .../music/track.mp3
# project.json ausfüllen (siehe unten)
python3 video-editing/cut.py ingest <projekt>          # sichten
python3 video-editing/cut.py rough <projekt>           # Rohschnitt, dann review.md lesen
python3 video-editing/cut.py render <projekt> --preview  # schnelle 540p-Vorschau
python3 video-editing/cut.py render <projekt>          # Final 1080p (oder --4k)
```

`<projekt>` ist der Ordnername unter `video-editing/projects/` oder ein Pfad.
`cut.py all <projekt> --preview` macht alle drei Schritte auf einmal.

**Wichtig beim Kopieren vom iPhone:** AirDrop oder Fotos-App „Unverändertes Original exportieren“.
Sonst fehlen Aufnahmezeit und GPS, und die Orts- und Zeitkarten bleiben leer.

## project.json

| Feld | Bedeutung |
|---|---|
| `title`, `episode` | Name der Folge |
| `language`, `timezone` | Sprache für Whisper (`de`/`en`/`null` = automatisch), Zeitzone für die Uhrzeit-Karten |
| `target_minutes` | Ziellänge. Der Rohschnitt kürzt Sprechpassagen, bis es passt (+15 %) |
| `resolution`, `fps` | `720p`/`1080p`/`4k`, Bildrate (iPhone meist 30) |
| `stats` | Building-in-Public-Zahlen, je Eintrag eine Karte nach der Montage (max. 2) |
| `hook` | Erster Satz der Folge fest vorgeben: `{"file": "raw/IMG_0420.MOV", "in": 12.3, "out": 18.9}`. Sonst automatisch: Transkript-Satz mit Zahl, Frage oder `hook_keywords` |
| `previously` | Clips der letzten Folge für den Schwarzweiß-Rückblick: `["../2026-09-28-x/raw/IMG_1.MOV", ...]` |
| `music` | `{"file": "music/track.mp3", "volume": 0.22}`. Startet mit der Montage, wird unter Sprache geduckt, blendet am Ende aus |
| `locations` | Ort pro Datei überschreiben: `{"IMG_0420.MOV": {"city": "Köln", "sub": "Ehrenfeld"}}` |
| `default_location` | Ort für Clips ohne GPS |
| `station_names` | Kapitelnamen der Stationen in Reihenfolge. Sonst „Stadt – Tageszeit“ |
| `grades` | Look pro Datei: `{"IMG_0420.MOV": "bloomfield_office"}` (Presets in `grades.json`) |
| `end_card` | Text der Endkarte |
| `burn_subtitles` | Untertitel ins Bild brennen (z. B. bei fremdsprachigen Gesprächen). Die `.srt`-Datei entsteht immer, wenn es ein Transkript gibt |

Feineinstellungen (Standardwert): `station_gap_minutes` (60), `max_talk_seconds` pro Clip (120),
`cover_every` (B-Roll über Sprache alle 9 s), `montage_shots` (16), `silence_db` (-32).

## Was der Rohschnitt automatisch macht

1. **Cold Open:** 3 Schwarzweiß-Blitzschnitte, dann der Hook-Satz in die Kamera.
2. **Previously** (wenn angegeben): Schwarzweiß-Rückblick mit Titel.
3. **Montage:** 16 Schnitte à 1 s, erst Schwarzweiß, dann Farbe. Hier setzt die Musik ein.
4. **Zahlen:** die `stats` als Karten.
5. **Stationen:** Eine neue Station beginnt bei Ortswechsel (GPS) oder nach mehr als 60 min Pause. Jede Station bekommt:
   - eine Totale mit Stadt-Karte (nur bei neuer Stadt) und Uhrzeit (bei neuer Tageszeit), mit Kapitelmarke;
   - Talking Heads mit herausgeschnittenen Pausen (Jump Cuts), alle ~9 s B-Roll der Station über die Stimme;
   - danach eine Musik-Brücke aus 3 B-Roll-Schnitten.
6. **Outro:** letzte B-Roll des Tages, dann die Endkarte „Thanks for watching“.

Automatisch gewählter Look: Schwarzweiß für Einstieg und Montage, nach 20 Uhr der Nacht-Look, sonst der warme Film-Look.
Hochkant-Clips bekommen einen unscharfen Hintergrund, iPhone-HDR wird auf SDR umgerechnet.

## edit.json von Hand oder mit Claude anpassen

`review.md` zeigt den Schnitt als Tabelle mit Zeitcodes. Änderungen macht man in `edit.json`.
Danach nur `render` neu laufen lassen, **nicht** `rough`, sonst wird `edit.json` überschrieben.

Ein Segment:
```json
{"file": "raw/IMG_0420.MOV", "in": 12.3, "out": 18.9, "grade": "bloomfield_warm_film",
 "volume": 1.0, "speed": 1.0, "chapter": "Köln – Morgen",
 "overlays": [{"type": "location", "text": "Köln", "sub": "Deutschland", "start": 0.4, "duration": 3},
              {"type": "time", "text": "08:12"},
              {"type": "stat", "text": "TAG 12 | 3 KUNDEN"},
              {"type": "caption", "text": "Schlüsselsatz"},
              {"type": "title", "text": "Previously"}],
 "cover": {"file": "raw/IMG_0425.MOV", "in": 3.0, "start": 1.0, "duration": 2.5},
 "subtitles": [[0.0, 2.1, "Text"]], "music_start": true}
```
Textkarte auf Schwarz: `{"card": {"text": "Thanks for watching", "sub": "..."}, "duration": 3.5}`.

## Grenzen

- Grafiken wie Lieferketten-Balken, Routenkarte und Bestellzähler (siehe Style Guide, Abschnitt 5) erzeugt das Tool nicht.
  Fertig gerendert als Clip in `raw/` legen und in `edit.json` einsetzen.
- Die Farb-Presets sind aus Beschreibungen abgeleitet, nicht aus gemessenen Referenz-Frames.
  Für den Abgleich `MASTER_PROMPT.md`, Schritt 2 (braucht YouTube-Zugriff).
- Der Rohschnitt ist ein Startpunkt. Story-Entscheidungen (welcher Moment ist der Konflikt, was ist der Cliffhanger)
  trifft man beim Review von `review.md`, am besten zusammen mit Claude.
