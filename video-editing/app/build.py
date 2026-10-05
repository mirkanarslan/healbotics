#!/usr/bin/env python3
"""Build the macOS app and the ZIP to hand out:  python3 video-editing/app/build.py

Output: video-editing/dist/MirkoMagic.app and video-editing/dist/MirkoMagic-Mac.zip
"""
import shutil
import stat
import time
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw

APP_SRC = Path(__file__).resolve().parent
ROOT = APP_SRC.parent  # video-editing/
DIST = ROOT / "dist"
APP = DIST / "MirkoMagic.app"
ZIP = DIST / "MirkoMagic-Mac.zip"


def icon(path):
    """Simple app icon: red rounded square with a white play/cut mark, as .icns."""
    imgs = []
    for size in (16, 32, 64, 128, 256, 512, 1024):
        im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        r = size * 0.22
        d.rounded_rectangle((size * 0.06, size * 0.06, size * 0.94, size * 0.94), r, fill=(200, 16, 46, 255))
        d.polygon([(size * 0.38, size * 0.3), (size * 0.38, size * 0.7), (size * 0.72, size * 0.5)], fill="white")
        d.rectangle((size * 0.24, size * 0.3, size * 0.3, size * 0.7), fill=(255, 255, 255, 220))
        imgs.append(im)
    imgs[-1].save(path, format="ICNS", append_images=imgs[:-1])


def main():
    shutil.rmtree(APP, ignore_errors=True)
    res = APP / "Contents" / "Resources"
    macos = APP / "Contents" / "MacOS"
    (res / "engine").mkdir(parents=True)
    macos.mkdir(parents=True)
    shutil.copy(APP_SRC / "macos" / "Info.plist", APP / "Contents" / "Info.plist")
    exe = macos / "MirkoMagic"
    shutil.copy(APP_SRC / "macos" / "launcher.sh", exe)
    exe.chmod(exe.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    for f in ("server.py", "ui.html"):
        shutil.copy(APP_SRC / f, res / f)
    shutil.copytree(ROOT / "vlog", res / "engine" / "vlog", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(ROOT / "grades.json", res / "engine" / "grades.json")
    icon(res / "AppIcon.icns")

    ZIP.unlink(missing_ok=True)
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(DIST.rglob("*")):
            if APP not in f.parents and f != APP:
                continue
            arc = f.relative_to(DIST)
            info = zipfile.ZipInfo(str(arc) + ("/" if f.is_dir() else ""))
            mode = f.stat().st_mode
            info.date_time = time.localtime()[:6]
            info.external_attr = (mode & 0xFFFF) << 16 | (0x10 if f.is_dir() else 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, b"" if f.is_dir() else f.read_bytes())
        readme = zipfile.ZipInfo("LIES MICH.txt", time.localtime()[:6])
        readme.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(readme, (APP_SRC / "LIES_MICH.txt").read_text())
    print(f"{APP}\n{ZIP} ({ZIP.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
