# Master-Prompt: Schnittprogramm fertigstellen

Diesen Text komplett in eine neue Claude-Code-Session kopieren (Repo `mirkanarslan/healbotics`,
Branch `claude/video-editing-jack-bloomfield-w0myzg`).

---

Du arbeitest im Repo `mirkanarslan/healbotics` auf dem Branch `claude/video-editing-jack-bloomfield-w0myzg`.
Dort liegt eine erste Version meiner Videoschnitt-Pipeline in `video-editing/` (`render.py`, `grades.json`,
`STYLE_GUIDE.md`, `projects/example/edit.json`, `references/analysis_jobs.tsv`). Lies zuerst `CLAUDE.md`
und alle Dateien in `video-editing/`.

## Ziel

Stelle das Schnittprogramm fertig, sodass ich danach nur noch Rohmaterial liefere und du daraus
eine fertige Vlog-Folge im Stil von Jack Bloomfield schneidest: gleiches Color Grading, gleiches
Storytelling, gleiche Schnittlogik, Orts-Einblendung (Stadt) bei jedem Standortwechsel, gelegentliche
Uhrzeit-Einblendungen und ein Building-in-Public-Aufbau mit Zwischenständen (Zahlen, Fortschritt,
Rückschläge). Stil übernehmen, Material nicht: keine Clips, Musik, Logos oder Grafiken aus den
Referenzvideos verwenden oder ins Repo committen.

## Regeln

- Subagents immer mit `model: "sonnet"` starten (Sonnet 5.5, siehe `CLAUDE.md`).
- Referenzvideos, Frames und Rohmaterial nur im Scratchpad bzw. in gitignorten Ordnern ablegen,
  nie committen. Ins Repo kommen nur Code, Presets (inkl. `.cube`-LUTs) und Dokumentation.
- Jede Aussage im Style Guide muss sich auf konkrete Beobachtungen aus den Referenzen stützen
  (Video-ID + Zeitstempel). Nichts erfinden. Was sich nicht messen lässt, als Schätzung kennzeichnen.
- Kleine, geprüfte Commits, am Ende pushen mit `git push -u origin claude/video-editing-jack-bloomfield-w0myzg`.

## Schritt 0: Umgebung prüfen

1. `pip install -q yt-dlp faster-whisper opencv-python-headless numpy` und `apt-get install -y ffmpeg`
   (braucht `drawtext`: `ffmpeg -filters | grep drawtext`).
2. YouTube-Zugriff testen:
   `python3 -m yt_dlp --skip-download --print "%(title)s" https://youtu.be/zt3F7kRB5ik`.
   Wenn das mit 403 vom Proxy scheitert: sofort abbrechen und mir sagen, welche Hosts
   (`youtube.com`, `*.youtube.com`, `youtu.be`, `*.googlevideo.com`, `*.ytimg.com`) in der
   Netzwerkeinstellung der Umgebung fehlen. Nicht mit Umwegen weitermachen.
3. Prüfen, ob die Higgsfield-Analysen aus `references/analysis_jobs.tsv` fertig sind
   (`video_analysis_status`). Wenn ja, als zusätzliche Quelle nutzen.

## Schritt 1: Referenzen laden

Für alle 21 URLs in `references/analysis_jobs.tsv` in den Scratchpad laden:
- Video in 720p (`-f "bv*[height<=720]+ba/b[height<=720]"`), Metadaten-JSON (`--write-info-json`),
  Untertitel/Auto-Untertitel (`--write-auto-subs --sub-langs "en.*,de.*" --convert-subs srt`).
- Kapitel, Titel, Beschreibung, Dauer, Upload-Datum festhalten.

## Schritt 2: Analyse (parallel mit Sonnet-Subagents, z. B. 4–5 Videos pro Agent)

Pro Video messen, nicht schätzen:

1. **Schnitt-Tempo**: Szenenwechsel mit `ffmpeg -vf "select='gt(scene,0.3)',showinfo"` oder
   PySceneDetect. Ergebnis: Anzahl Schnitte, mittlere und mediane Shot-Länge, getrennt für Hook
   (erste 60 s), Hauptteil und Ende.
2. **Farbe**: pro Szene 1 Frame extrahieren. Mit numpy/OpenCV messen: Schwarzwert (1. Perzentil Luma),
   Weißwert (99. Perzentil), mittlere Sättigung, Farbstich in Schatten/Mitten/Lichtern (Mittelwert
   a*/b* im Lab-Raum je Luma-Drittel), Korn, Vignette (Helligkeit Rand vs. Mitte), Seitenverhältnis
   bzw. Letterbox. Getrennt nach Tag außen, Nacht, Innenraum.
3. **Einblendungen**: Frames direkt nach Ortswechseln und in Übergängen ansehen (Bild lesen). Notieren:
   Position, Schriftart-Charakter (Serif/Sans/Mono, Gewicht, Groß-/Kleinschreibung), Größe relativ
   zur Bildhöhe, Farbe, Animation (Fade, Typewriter, Slide), Standdauer, Format der Uhrzeit,
   wie Ort + Land/Stadtteil dargestellt werden, ob Datum/Tag-Zähler vorkommen.
4. **Storytelling**: aus Transkript + Kapiteln den Aufbau rekonstruieren: Hook-Typ, wann der Titel
   kommt, wie Zahlen/Fortschritt präsentiert werden, Voice-over vs. Talking Head vs. Vlog-Kamera,
   wie Konflikte eingebaut sind, wie das Video endet (Cliffhanger, CTA).
5. **Ton**: Musikanteil, Musik unter Dialog (geduckt?), Sound-Design bei Einblendungen,
   Lautheit (`ffmpeg -af ebur128`).

Jeder Subagent liefert ein JSON pro Video in `video-editing/references/analysis/<video_id>.json`
(nur Messwerte und Beobachtungen mit Zeitstempeln, keine Frames). Danach fasst du alles zu einer
Gesamtauswertung zusammen: was ist in allen bzw. den meisten Videos gleich (= Stilregel), was variiert.

## Schritt 3: Style Guide und Looks fertigstellen

1. `STYLE_GUIDE.md` komplett neu aus den Messungen schreiben, alle *(vorläufig)*-Markierungen
   auflösen. Konkrete Zahlen: Shot-Längen, Einblendungsdauer, Positionen in % der Bildgröße,
   Story-Struktur als Vorlage mit Minutenangaben.
2. Grading: für jede Lichtsituation einen `.cube`-3D-LUT erzeugen (`video-editing/luts/`), der die
   gemessenen Werte trifft, und in `grades.json` über `lut3d` einbinden, plus Korn/Vignette als Filter.
   Validieren: neutrale Testbilder und eigene Beispielframes graden und die Messwerte mit den
   Referenzwerten vergleichen (Abweichung dokumentieren).
3. Overlays in `render.py` an die beobachtete Typografie und Animation anpassen. Eine frei nutzbare
   Schrift mit ähnlichem Charakter verwenden (z. B. aus Google Fonts, Lizenz prüfen) und unter
   `video-editing/fonts/` ablegen.

## Schritt 4: Schnittprogramm fertig bauen

`render.py` bleibt der Renderer. Dazu kommt ein Assistent-Workflow, der aus Rohmaterial eine `edit.json` baut:

1. `ingest.py <projektordner>`: listet alle Dateien in `raw/`, liest Aufnahmezeit
   (`creation_time`, bei iPhone auch `com.apple.quicktime.creationdate`) und GPS
   (`com.apple.quicktime.location.ISO6709`), macht daraus Orts- und Uhrzeit-Vorschläge
   (Stadt per Reverse-Geocoding nur, wenn der Host erreichbar ist, sonst nachfragen), transkribiert
   mit faster-whisper (Sprache automatisch, DE/EN) und schreibt `inventory.json`.
   Falls das Whisper-Modell nicht geladen werden kann: sagen, welcher Host fehlt.
2. `rough_cut.py`: entfernt Stille und Versprecher aus Talking-Head-Clips (Wortzeitstempel), schlägt
   B-Roll-Stellen vor, erzeugt eine erste `edit.json` nach der Story-Vorlage aus dem Style Guide,
   mit Ortskarte bei jedem Ortswechsel und Uhrzeit an Tagesabschnitten.
3. `render.py` erweitern um: Überblendungen und J/L-Cuts wo der Style Guide sie vorsieht,
   Musik-Ducking (existiert), Kapitelmarken als Textdatei für die YouTube-Beschreibung, optional
   Untertitel (SRT), Export 1080p und 4K, Vorschau-Render in niedriger Qualität (`--preview`).
4. Build-in-Public-Elemente: `stat`-Karten mit Werten aus einer `project.json` (Tag-Nummer,
   Kunden, Umsatz, Meilensteine), damit ich sie pro Folge nur aktualisiere.

## Schritt 5: Testen

- Ein Testprojekt mit synthetischen Clips (ffmpeg `testsrc2`, Sprachaufnahme per TTS oder Sinuston,
  gesetzte `creation_time`- und GPS-Metadaten) komplett durch `ingest.py` → `rough_cut.py` → `render.py`.
- Frames an den Einblendungen extrahieren und ansehen. Dauer, Tonspur (48 kHz, -14 LUFS) und
  Auflösung prüfen.
- Ein kurzes Vorher/Nachher (Referenz-Frame vs. unser Grade auf ähnlichem Motiv) als Bildvergleich
  erzeugen und mir zeigen.

## Schritt 6: Abschluss

- `CLAUDE.md` um den finalen Workflow ergänzen („Rohmaterial in `projects/<datum>-<titel>/raw/`,
  dann `ingest` → `rough_cut` → Review mit mir → `render`“).
- Committen und pushen. Mir dann kurz auf Deutsch berichten: was die Analyse ergeben hat
  (die 5–10 wichtigsten Stilregeln), was gebaut und getestet wurde, was noch offen ist, und was ich
  für die erste Folge an Rohmaterial liefern soll (Dateiformat, Upload-Weg per Google Drive,
  welche Infos zu Orten/Zahlen).
