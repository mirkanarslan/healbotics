# Style Guide: Healbotics-Vlogs im Stil von Jack Bloomfield

> **Status: Entwurf.** Die 21 Referenzvideos (siehe `references/analysis_jobs.tsv`) sind zur
> Szenen-Analyse eingereicht, die Ergebnisse stehen noch aus. Die Regeln unten beschreiben das
> Grundgerüst eines Building-in-Public-Vlogs und werden nach der Analyse konkretisiert
> (Schnittfrequenz, Farbwerte, Typografie, Kapitel-Aufbau). Alles, was noch nicht aus den Referenzen
> bestätigt ist, ist mit *(vorläufig)* markiert.

## 1. Story-Aufbau (Building in Public)

1. **Cold Open / Hook (0:00–0:30)**: stärkster Moment oder die zentrale Frage des Videos zuerst,
   danach Titel/Intro. *(vorläufig)*
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
