"""Text overlays as transparent full-frame PNGs (Pillow), so any ffmpeg build works
(no drawtext/freetype needed). Layouts match the style guide: city card bottom-left,
clock top-left, stat box, caption, centred title, subtitles, end card."""
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .common import font

_FONTS = {}


def _font(kind, size):
    key = (kind, size)
    if key not in _FONTS:
        _FONTS[key] = ImageFont.truetype(font(kind), max(8, int(size)))
    return _FONTS[key]


def _rgba(color, alpha=1.0):
    if color.startswith("#"):
        c = color.lstrip("#")
        return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), int(255 * alpha))
    return {"white": (255, 255, 255, int(255 * alpha)), "black": (0, 0, 0, int(255 * alpha))}[color]


def _text(draw, xy, text, fnt, fill, shadow=None, anchor="la"):
    if shadow:
        off, alpha = shadow
        draw.text((xy[0] + off, xy[1] + off), text, font=fnt, fill=(0, 0, 0, int(255 * alpha)), anchor=anchor)
    draw.text(xy, text, font=fnt, fill=fill, anchor=anchor)


def _wrap(draw, text, fnt, max_w):
    words, lines, line = text.split(), [], ""
    for wd in words:
        test = f"{line} {wd}".strip()
        if draw.textlength(test, font=fnt) <= max_w or not line:
            line = test
        else:
            lines.append(line)
            line = wd
    return lines + ([line] if line else [])


def draw_overlay(ov, w, h):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    unit = h / 1080 * 64 * ov.get("scale", 1.0)
    sh = max(1, round(h / 540))
    kind, text = ov["type"], str(ov.get("text", ""))
    white = _rgba("white")

    if kind == "location":
        f = _font("bold", unit)
        _text(d, (w * 0.06, h * 0.78), text.upper(), f, white, (sh, 0.45), anchor="ls")
        if ov.get("sub"):
            _text(d, (w * 0.06 + 4 * h / 1080, h * 0.78 + unit * 0.2), ov["sub"], _font("regular", unit * 0.42),
                  _rgba("white", 0.92), (max(1, sh // 2), 0.45), anchor="lt")
    elif kind == "time":
        _text(d, (w * 0.05, h * 0.07), text, _font("mono", unit * 0.55), white, (max(1, sh // 2), 0.5))
    elif kind == "stat":
        f, pad = _font("bold", unit * 0.6), unit * 0.3
        x0, y0, x1, y1 = d.textbbox((w / 2, h * 0.12), text, font=f, anchor="mt")
        d.rectangle((x0 - pad, y0 - pad, x1 + pad, y1 + pad), fill=(0, 0, 0, 140))
        d.text((w / 2, h * 0.12), text, font=f, fill=white, anchor="mt")
    elif kind == "caption":
        _text(d, (w / 2, h * 0.86), text, _font("bold", unit * 0.55), white, (sh, 0.7), anchor="mm")
    elif kind == "title":
        _text(d, (w / 2, h / 2), text, _font("serif", unit * 1.1), white, (sh, 0.6), anchor="mm")
    elif kind == "subtitle":
        f = _font("bold", h / 1080 * 40)
        lines = _wrap(d, text, f, w * 0.8)[:2]
        lh, pad = f.size * 1.25, f.size / 3
        y = h * 0.9 - lh * len(lines)
        for line in lines:
            x0, y0, x1, y1 = d.textbbox((w / 2, y), line, font=f, anchor="mt")
            d.rectangle((x0 - pad, y0 - pad / 2, x1 + pad, y1 + pad / 2), fill=(0, 0, 0, 128))
            d.text((w / 2, y), line, font=f, fill=white, anchor="mt")
            y += lh
    elif kind == "card":
        size = h / 1080 * ov.get("size", 72)
        main = _font("serif" if ov.get("serif", True) else "bold", size)
        color = _rgba(ov.get("color", "#D4AF37"))
        if ov.get("sub"):
            d.text((w / 2, h / 2 - size * 0.1), text, font=main, fill=color, anchor="md")
            d.text((w / 2, h / 2 + size * 0.5), ov["sub"], font=_font("serif", size * 0.45),
                   fill=_rgba("white", 0.85), anchor="mt")
        else:
            d.text((w / 2, h / 2), text, font=main, fill=color, anchor="mm")
    else:
        raise ValueError(f"Unbekannter Overlay-Typ: {kind}")
    return img


def overlay_png(ov, w, h, cache_dir):
    """Render once per distinct overlay+size, return the PNG path."""
    key = hashlib.sha1(json.dumps([ov, w, h], sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
    path = Path(cache_dir) / f"ov_{key}.png"
    if not path.exists():
        draw_overlay(ov, w, h).save(path)
    return path
