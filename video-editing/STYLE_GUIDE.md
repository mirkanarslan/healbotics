# Style Guide: Healbotics-Vlogs im Stil von Jack Bloomfield

> **Status: Entwurf.** Von den 21 Referenzvideos (siehe `references/analysis_jobs.tsv`) liegen erst
> zwei verwertbare Szenen-Analysen vor (`ZCKbMiJ6OR4`, `X6ZsjEAEh8k`, Abschnitt 0). Die übrigen
> stehen aus oder sind bei Higgsfield fehlgeschlagen. Die Regeln unten beschreiben das
> Grundgerüst eines Building-in-Public-Vlogs und werden nach der Analyse konkretisiert
> (Schnittfrequenz, Farbwerte, Typografie, Kapitel-Aufbau). Alles, was noch nicht aus den Referenzen
> bestätigt ist, ist mit *(vorläufig)* markiert.

## 0. Belegte Beobachtungen aus den Referenzen

Quelle: Higgsfield-Szenenanalyse (Beschreibungstext, keine Pixelmessung). Zeitstempel = Referenzvideo.

- **Serien-Format mit „Previously“-Rückblick**: schnelle Schwarzweiß-Montage der letzten Folge mit
  eingeblendetem „Previously“ (ZCKbMiJ6OR4, 0:21–0:25).
- **Cold Open in Schwarzweiß mit Zoom-Blur-Schnitten** und treibender elektronischer Musik,
  Kamera-Auslöser-Sounds (ZCKbMiJ6OR4, 0:00–0:02).
- **Mission in einem Satz direkt in die Kamera, dann sofort die Fallhöhe**: „I've moved my entire
  life to Hong Kong …“, „everything is on the line“ (ZCKbMiJ6OR4, 0:02–0:25; X6ZsjEAEh8k, 0:23–0:27).
- **Einladung an den Zuschauer**: „Come with me, I'm going to show you …“ vor dem Titel-/Montageteil
  (ZCKbMiJ6OR4, 0:25–0:43).
- **Cinematic-Montage nach dem Intro**: Drohnen-Totale der Stadt, Nacht-Laptop-Arbeit im Apartment,
  Showroom, Übergänge von Schwarzweiß zu Farbe, orchestrale Musik mit hartem Beat (ZCKbMiJ6OR4, 0:43–1:01).
- **Ort wird gesagt und gezeigt**: „on our way to our first supply meeting here in Guangzhou“, Auto-Talking-Head
  auf dem Rücksitz, Handy-POV aus dem Autofenster auf die Fabrik (ZCKbMiJ6OR4, 0:15–0:17, 1:01–1:45).
- **Zahlen physisch zeigen**: ausgedruckte Folien mit Preisvergleich (Fabrikpreis / eigener Preis /
  Einzelhandel), Finger zeigt auf die Zahlen, Schnitt zwischen Gesicht und Papier (ZCKbMiJ6OR4, 1:45–2:10).
- **Pitch-Trailer-Rhythmus**: 14 Szenen in 64 s, also rund 4–5 s pro Szene. Jeder Satz der Erzählung
  liegt auf einem neuen Ort oder Bild (Lager, Showroom, Straße, Skyline, Büro) (X6ZsjEAEh8k, 0:00–1:04).
- **Look (Beschreibung)**: natürliches, helles Licht, gedämpfte Industrietöne mit einzelnen kräftigen
  Farbakzenten (Tor, Container) (X6ZsjEAEh8k). Noch nicht per Pixelmessung bestätigt.

## 1. Story-Aufbau (Building in Public)

1. **Cold Open / Hook (0:00–0:45)**: Schwarzweiß-Schnellschnitt, „Previously“-Rückblick, Mission in
   einem Satz, was auf dem Spiel steht, „Kommt mit“. Danach Cinematic-Montage mit Musik (belegt, Abschnitt 0).
2. **Stand der Dinge**: wo steht Healbotics gerade? Zahlen als Statuskarte
   (`stat`-Overlay, z. B. „TAG 12 | 3 KUNDEN | 4.200 EUR MRR“).
3. **Stationen des Tages / der Woche**: jeder Ortswechsel bekommt eine Ortskarte
   (`location`: Stadt groß, Land/Ort klein), wichtige Momente eine Uhrzeit (`time`).
4. **Konflikt / Problem**: was läuft nicht, welche Entscheidung steht an. Ehrlich zeigen.
5. **Auflösung oder Cliffhanger**: Ergebnis, neue Zahlen, Ausblick auf die nächste Folge.

## 2. Schnitt

- Ortswechsel: harter Schnitt auf eine Establishing-Shot-Sequenz (Außenaufnahme, Straße, Gebäude),
  darauf die Ortskarte, 3 s mit 0,35 s Ein- und Ausblendung.
- Uhrzeit-Einblendungen an Tagesabschnitten (Morgen, Meeting, Abend), nicht bei jedem Schnitt.
- Talking-Head-Passagen straff: Pausen und Versprecher raus, Jump-Cuts erlaubt. *(vorläufig)*
- B-Roll über Erzählung legen, damit Talking Heads nie lange stehen. *(vorläufig)*
- Musik unter Dialog automatisch geduckt (Sidechain in `render.py`), Lautheit -14 LUFS für YouTube.

## 3. Farbe

Presets in `grades.json`: `bloomfield_warm_film` (Hauptlook), `bloomfield_night`, `bloomfield_office`.
Warm, leicht angehobene Schwarzwerte, etwas entsättigt, feines Korn, dezente Vignette.
*(vorläufig, Werte werden an Referenz-Frames angeglichen)*

## 4. Typografie der Einblendungen

- Ort: fett, Großbuchstaben, unten links, weiche Schattenkante.
- Uhrzeit: Monospace, klein, oben links.
- Statuskarte: fett, zentriert oben, halbtransparente Box.
*(vorläufig, Schrift und Positionen werden an die Referenzen angepasst)*

## 5. Was wir nicht übernehmen

Keine Musik, Clips, Logos oder Grafik-Assets aus den Referenzvideos. Wir kopieren den Stil,
nicht das Material.
