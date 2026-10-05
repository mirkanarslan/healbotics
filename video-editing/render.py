#!/usr/bin/env python3
"""Kompatibilität: python3 video-editing/render.py <edit.json> [--preview|--4k]. Neu: cut.py render."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vlog.render import run_render  # noqa: E402

if __name__ == "__main__":
    run_render(sys.argv[1], "--preview" in sys.argv, "--4k" in sys.argv)
