"""Video generation: Runway ML (primary) with animated slideshow fallback."""

import os
import time
import httpx
import subprocess
from pathlib import Path

RUNWAY_API_URL = "https://api.dev.runwayml.com/v1"

STYLE_PREFIXES = {
    "medical_blue": "Professional 3D medical animation, deep blue and white color palette, cinematic lighting,",
    "dark_tech": "Futuristic 3D medical animation, dark background with neon blue highlights, cinematic,",
    "corporate_white": "Clean 3D medical animation, minimalist white and light blue, soft studio lighting,",
    "nature_green": "Organic 3D medical animation, natural green and white tones, soft lighting,",
}

# Gradient colors per style (for fallback slideshow)
STYLE_COLORS = {
    "medical_blue": [("#001f3f", "#0074D9"), ("#0074D9", "#7FDBFF"), ("#001f3f", "#004080")],
    "dark_tech": [("#0a0a1a", "#00ffcc"), ("#1a0a2e", "#6c63ff"), ("#0a0a1a", "#00b4d8")],
    "corporate_white": [("#e8f4f8", "#2c5f8a"), ("#f0f8ff", "#1a3a5c"), ("#dce8f0", "#2c5f8a")],
    "nature_green": [("#0d2b1e", "#27ae60"), ("#1a4a2e", "#2ecc71"), ("#0d2b1e", "#16a085")],
}


def generate_video_scenes(script: dict, output_path: Path) -> list:
    """Generate video clips for each scene. Uses Runway ML or slideshow fallback."""
    api_key = os.environ.get("RUNWAYML_API_KEY", "").strip()
    color_scheme = script.get('style', {}).get('color_scheme', 'medical_blue')

    if api_key:
        return _generate_runway(script, output_path, api_key, color_scheme)
    else:
        return _generate_slideshow(script, output_path, color_scheme)


# ── Runway ML path ──────────────────────────────────────────────────────────

def _generate_runway(script: dict, output_path: Path, api_key: str, color_scheme: str) -> list:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "X-Runway-Version": "2024-11-06",
        "Content-Type": "application/json"
    }
    style_prefix = STYLE_PREFIXES.get(color_scheme, STYLE_PREFIXES["medical_blue"])
    video_files = []

    for scene in script['scenes']:
        scene_id = scene['id']
        visual_prompt = scene.get('visual_prompt', '').strip()
        duration = scene.get('duration', 8)
        video_path = output_path / f"scene_{scene_id}_video.mp4"

        if not visual_prompt:
            video_files.append(None)
            continue

        enhanced_prompt = f"{style_prefix} {visual_prompt}, smooth camera movement, no text, no people"
        runway_duration = 10 if duration >= 7 else 5

        try:
            response = httpx.post(
                f"{RUNWAY_API_URL}/text_to_video",
                headers=headers,
                json={
                    "model": "gen4_turbo",
                    "promptText": enhanced_prompt,
                    "duration": runway_duration,
                    "ratio": "1280:720"
                },
                timeout=30
            )
            response.raise_for_status()
            task_id = response.json()["id"]

            video_url = _poll_runway_task(task_id, headers)

            video_response = httpx.get(video_url, timeout=180, follow_redirects=True)
            video_response.raise_for_status()
            with open(video_path, 'wb') as f:
                f.write(video_response.content)

            video_files.append(str(video_path))

        except Exception as e:
            # Scene-level fallback: generate a slideshow clip for this scene
            fallback = _make_single_slideshow_clip(
                scene, video_path, color_scheme, scene_id
            )
            video_files.append(fallback)

    return video_files


def _poll_runway_task(task_id: str, headers: dict, max_wait: int = 600) -> str:
    start = time.time()
    while time.time() - start < max_wait:
        r = httpx.get(f"{RUNWAY_API_URL}/tasks/{task_id}", headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        status = data.get("status")
        if status == "SUCCEEDED":
            return data["output"][0]
        if status == "FAILED":
            raise RuntimeError(f"Runway-Task fehlgeschlagen: {data.get('failure', 'unknown')}")
        time.sleep(8)
    raise TimeoutError("Runway ML Timeout nach 10 Minuten")


# ── Slideshow fallback path ──────────────────────────────────────────────────

def _generate_slideshow(script: dict, output_path: Path, color_scheme: str) -> list:
    video_files = []
    colors = STYLE_COLORS.get(color_scheme, STYLE_COLORS["medical_blue"])

    for i, scene in enumerate(script['scenes']):
        scene_id = scene['id']
        video_path = output_path / f"scene_{scene_id}_video.mp4"
        color_pair = colors[i % len(colors)]
        clip = _make_single_slideshow_clip(scene, video_path, color_scheme, i, color_pair)
        video_files.append(clip)

    return video_files


def _make_single_slideshow_clip(scene: dict, video_path: Path, color_scheme: str,
                                  index: int, color_pair=None) -> str | None:
    """Create an animated gradient background clip with text overlay using FFmpeg + Pillow."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import numpy as np
    except ImportError:
        return _make_plain_ffmpeg_clip(scene, video_path)

    duration = scene.get('duration', 8)
    text = scene.get('text_overlay', '') or scene.get('title', '')
    scene_type = scene.get('type', 'content')
    colors = STYLE_COLORS.get(color_scheme, STYLE_COLORS["medical_blue"])

    if color_pair is None:
        color_pair = colors[index % len(colors)]

    c1 = _hex_to_rgb(color_pair[0])
    c2 = _hex_to_rgb(color_pair[1])

    fps = 25
    total_frames = duration * fps
    frames_dir = video_path.parent / f"frames_{scene['id']}"
    frames_dir.mkdir(exist_ok=True)

    for frame_idx in range(total_frames):
        t = frame_idx / total_frames
        # Animated gradient with slow shift
        shift = 0.5 + 0.5 * __import__('math').sin(t * __import__('math').pi * 2)
        img = _make_gradient_frame(c1, c2, shift, 1280, 720)

        draw = ImageDraw.Draw(img)

        # Scene type indicator
        type_labels = {
            "intro": "EINFÜHRUNG", "content": "INHALT",
            "highlight": "HIGHLIGHT", "comparison": "VERGLEICH",
            "summary": "ZUSAMMENFASSUNG", "outro": "ABSCHLUSS"
        }
        label = type_labels.get(scene_type, "")

        # Animated elements – floating circle
        radius = 60 + int(20 * __import__('math').sin(t * __import__('math').pi * 4))
        cx, cy = 640, 360
        accent = _lerp_color(c2, (255, 255, 255), 0.7)
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                     outline=accent, width=3)
        draw.ellipse([cx - radius//2, cy - radius//2, cx + radius//2, cy + radius//2],
                     outline=accent, width=2)

        # Text overlays
        if label:
            _draw_text_centered(draw, label, y=60, font_size=20, color=(200, 220, 255, 180))
        if text:
            _draw_text_centered(draw, text, y=620, font_size=36, color=(255, 255, 255, 230))

        # Progress bar at bottom
        bar_width = int(1280 * t)
        draw.rectangle([0, 710, bar_width, 720], fill=_lerp_color(c2, (255, 255, 255), 0.5))

        frame_path = frames_dir / f"frame_{frame_idx:05d}.png"
        img.save(frame_path)

    # Assemble frames to video
    cmd = [
        'ffmpeg', '-y',
        '-framerate', str(fps),
        '-i', str(frames_dir / 'frame_%05d.png'),
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
        '-crf', '23', '-preset', 'fast',
        str(video_path)
    ]
    result = subprocess.run(cmd, capture_output=True)

    # Cleanup frames
    for f in frames_dir.iterdir():
        f.unlink()
    frames_dir.rmdir()

    return str(video_path) if result.returncode == 0 else None


def _make_plain_ffmpeg_clip(scene: dict, video_path: Path) -> str | None:
    """Ultra-simple colored background clip using only FFmpeg."""
    duration = scene.get('duration', 8)
    cmd = [
        'ffmpeg', '-y',
        '-f', 'lavfi',
        '-i', f'color=c=0x001f3f:size=1280x720:duration={duration}:rate=25',
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
        str(video_path)
    ]
    result = subprocess.run(cmd, capture_output=True)
    return str(video_path) if result.returncode == 0 else None


# ── Helpers ─────────────────────────────────────────────────────────────────

def _hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _lerp_color(c1: tuple, c2: tuple, t: float) -> tuple:
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _make_gradient_frame(c1: tuple, c2: tuple, t: float, w: int, h: int):
    from PIL import Image
    img = Image.new('RGB', (w, h))
    pixels = img.load()
    for y in range(h):
        blend = y / h
        r = int(c1[0] + (c2[0] - c1[0]) * blend * (0.5 + 0.5 * t))
        g = int(c1[1] + (c2[1] - c1[1]) * blend * (0.5 + 0.5 * t))
        b = int(c1[2] + (c2[2] - c1[2]) * blend * (0.5 + 0.5 * t))
        for x in range(w):
            pixels[x, y] = (r, g, b)
    return img


def _draw_text_centered(draw, text: str, y: int, font_size: int, color: tuple):
    try:
        from PIL import ImageFont
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        x = (1280 - text_w) // 2
        # Drop shadow
        draw.text((x + 2, y + 2), text, fill=(0, 0, 0, 120), font=font)
        draw.text((x, y), text, fill=color[:3], font=font)
    except Exception:
        draw.text((640, y), text, fill=color[:3])
