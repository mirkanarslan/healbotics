"""Entry point for the desktop app: one full run with machine-readable progress.

    python -m vlog.job <project_dir> [--quality preview|final|4k] [--whisper]

Prints normal log lines plus `@@PROGRESS <0..1> <phase>` and, at the end,
`@@DONE <json>` or `@@ERROR <message>`.
"""
import argparse
import json
import os
import sys
import traceback
from pathlib import Path

try:  # python.org builds on macOS ship without CA certificates
    import certifi
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
except ImportError:
    pass

from . import ingest, render, roughcut  # noqa: E402


def emit(frac, phase):
    print(f"@@PROGRESS {frac:.3f} {phase}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--quality", choices=["preview", "final", "4k"], default="preview")
    ap.add_argument("--whisper", action="store_true")
    a = ap.parse_args()
    p = Path(a.project).resolve()
    try:
        emit(0.0, "Clips werden gesichtet")
        ingest.run(p, whisper=a.whisper, progress=lambda i, n: emit(0.15 * i / n, f"Sichten {i + 1}/{n}"))
        emit(0.15, "Rohschnitt wird gebaut")
        roughcut.run(p)
        emit(0.2, "Rendern")
        out, total = render.run_render(p / "edit.json", preview=a.quality == "preview", uhd=a.quality == "4k",
                                       progress=lambda i, n: emit(0.2 + 0.78 * i / n, f"Rendern {i + 1}/{n}"))
        chap = out.with_name(out.stem + "_chapters.txt")
        srt = out.with_suffix(".srt")
        print("@@DONE " + json.dumps({
            "output": str(out.resolve()), "duration": total,
            "chapters": chap.read_text() if chap.exists() else "",
            "srt": str(srt.resolve()) if srt.exists() else None,
            "review": (p / "review.md").read_text() if (p / "review.md").exists() else "",
        }, ensure_ascii=False), flush=True)
    except SystemExit as e:
        print(f"@@ERROR {e}", flush=True)
        sys.exit(1)
    except Exception as e:  # report anything else to the app instead of dying silently
        traceback.print_exc()
        print(f"@@ERROR {type(e).__name__}: {e}", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
