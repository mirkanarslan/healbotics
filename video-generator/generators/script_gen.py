"""Script generation using Anthropic Claude API."""

import os
import json
import anthropic

SYSTEM_PROMPT = """Du bist ein professioneller Videoskript-Autor für medizinische Bildungsvideos (Arzt-Bildungsträger).
Du erstellst strukturierte Skripte für 3D-animierte Erklärvideos im Stil von Lemon Studios und ähnlichen Produktionsfirmen.

Deine Videos sind:
- Wissenschaftlich präzise und professionell
- Visuell ansprechend mit detaillierten 3D-Animationsanweisungen
- In flüssigem, medizinisch korrektem Deutsch
- Strukturiert mit klaren Szenenübergängen
- Optimiert für die angegebene Zielgruppe

Erstelle das Skript als JSON-Objekt mit dieser exakten Struktur:
{
  "title": "Prägnanter Videotitel",
  "duration_estimate": "1:30",
  "target_audience": "Beschreibung der Zielgruppe",
  "key_message": "Die wichtigste Botschaft des Videos in einem Satz",
  "scenes": [
    {
      "id": 1,
      "duration": 8,
      "type": "intro",
      "narration": "Der gesprochene Text für dieses Segment – präzise, klar, professionell",
      "visual_prompt": "3D medical animation, [Hauptobjekt detailliert beschreiben], floating in dark blue void, soft volumetric lighting, slow camera orbit, cinematic depth of field, photorealistic render, no text, no humans, Blender-style 3D visualization",
      "text_overlay": "Kurzer Einblendungstext (max. 5 Wörter, optional)",
      "camera_movement": "slow_orbit"
    }
  ],
  "style": {
    "color_scheme": "medical_blue",
    "mood": "professional"
  }
}

Szenen-Typen: intro, content, highlight, comparison, summary, outro

Für visual_prompt gilt: Beschreibe die Animation OHNE Text, OHNE Menschen, reine 3D-Objekte/Moleküle/Organe/Diagramme.
Verwende spezifische medizinische Visualisierungen: Molekülstrukturen, Organe, Zellmechanismen, Blutfluss, neuronale Netze etc.

Erstelle 5-8 Szenen je nach Komplexität.
Antworte NUR mit dem JSON-Objekt, kein weiterer Text."""


def generate_script(prompt: str, options: dict = None) -> dict:
    """Generate a structured video script from a user prompt using Claude."""
    if options is None:
        options = {}

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    audience_map = {
        "general_practitioners": "Allgemeinmediziner",
        "specialists": "Fachärzte",
        "medical_students": "Medizinstudenten",
        "nursing_staff": "Pflegepersonal",
        "patients": "Patienten (Laien)"
    }

    audience = audience_map.get(options.get('audience', ''), "Medizinisches Bildungspersonal")
    duration = options.get('duration', 90)
    style = options.get('style', {})
    color_scheme = style.get('color_scheme', 'medical_blue') if isinstance(style, dict) else 'medical_blue'

    user_message = f"""Erstelle ein professionelles 3D-Erklärvideo-Skript für folgendes Thema:

{prompt}

Rahmenbedingungen:
- Zielgruppe: {audience}
- Gewünschte Dauer: ca. {duration} Sekunden
- Visueller Stil: {color_scheme}
- Sprache: Deutsch (medizinisch präzise)

Erstelle 5-8 Szenen mit detaillierten visuellen Anweisungen für 3D-Animationen.
Beginne mit einer packenden Intro-Szene und ende mit einer klaren Summary/Call-to-Action."""

    message = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    )

    response_text = message.content[0].text.strip()

    # Strip markdown code fences if present
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        response_text = "\n".join(lines).strip()

    script = json.loads(response_text)

    if "scenes" not in script or not script["scenes"]:
        raise ValueError("Generiertes Skript enthält keine Szenen")

    # Ensure each scene has required fields
    for i, scene in enumerate(script["scenes"]):
        scene.setdefault("id", i + 1)
        scene.setdefault("duration", 8)
        scene.setdefault("type", "content")
        scene.setdefault("narration", "")
        scene.setdefault("visual_prompt", "")
        scene.setdefault("text_overlay", "")
        scene.setdefault("camera_movement", "slow_zoom_in")

    return script
