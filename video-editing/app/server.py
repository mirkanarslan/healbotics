#!/usr/bin/env python3
"""Healbotics Cutter: local app server (standard library only).

Serves the UI on http://127.0.0.1:<port>, takes video uploads into a project
folder, installs the engine's dependencies once into a private virtualenv and
runs the cutting engine (vlog.job) as a subprocess, streaming its progress.
Nothing leaves the machine except the one-time package download.
"""
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
import unicodedata
import urllib.parse
import webbrowser
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

APP = "Healbotics Cutter"
VERSION = "1.0"
HERE = Path(__file__).resolve().parent
ENGINE = HERE / "engine" if (HERE / "engine" / "vlog").is_dir() else HERE.parent  # bundled app / repo checkout
MAC = sys.platform == "darwin"
SUPPORT = Path.home() / ("Library/Application Support" if MAC else ".local/share") / APP
PROJECTS = Path(os.environ.get("HEALBOTICS_PROJECTS") or Path.home() / ("Movies" if MAC else "Videos") / APP)
VENV = SUPPORT / "venv"
VPY = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
BASE_PACKAGES = ["pillow", "imageio-ffmpeg", "certifi"]
PORTS = range(8765, 8790)

state = {
    "setup": {"status": "pending", "log": []},
    "job": {"running": False, "progress": 0.0, "phase": "", "log": [], "result": None, "error": None},
}
lock = threading.Lock()


def log_to(section, line):
    with lock:
        buf = state[section]["log"] if section == "setup" else state["job"]["log"]
        buf.append(line.rstrip())
        del buf[:-400]


def pip(*packages, section="setup"):
    proc = subprocess.Popen([str(VPY), "-m", "pip", "install", "--disable-pip-version-check", "-q", *packages],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in proc.stdout:
        log_to(section, line)
    return proc.wait() == 0


def setup():
    """Create the private venv and install engine packages (first launch only)."""
    marker = SUPPORT / f"setup-{VERSION}.ok"
    try:
        if marker.exists() and VPY.exists():
            state["setup"]["status"] = "ready"
            return
        state["setup"]["status"] = "installing"
        SUPPORT.mkdir(parents=True, exist_ok=True)
        if not VPY.exists():
            log_to("setup", "Lege Python-Umgebung an …")
            subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
        log_to("setup", "Lade Bausteine (Bildbearbeitung, ffmpeg) … das dauert beim ersten Mal 1–3 Minuten.")
        if not pip(*BASE_PACKAGES):
            raise RuntimeError("Installation fehlgeschlagen. Internetverbindung prüfen und App neu starten.")
        marker.write_text(time.ctime())
        state["setup"]["status"] = "ready"
        log_to("setup", "Einrichtung fertig.")
    except Exception as e:
        state["setup"]["status"] = "error"
        log_to("setup", f"Fehler: {e}")


def has_whisper():
    return subprocess.run([str(VPY), "-c", "import faster_whisper"], capture_output=True).returncode == 0


def slug(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "folge"


def project_dir(pid):
    p = (PROJECTS / pid).resolve()
    if PROJECTS.resolve() not in p.parents or not p.is_dir():
        raise ValueError("Unbekanntes Projekt")
    return p


def new_project(title):
    base = f"{date.today().isoformat()}-{slug(title)}"
    pid, n = base, 2
    while (PROJECTS / pid).exists():
        pid, n = f"{base}-{n}", n + 1
    (PROJECTS / pid / "raw").mkdir(parents=True)
    (PROJECTS / pid / "music").mkdir()
    return pid


def local_timezone():
    try:
        return os.path.realpath("/etc/localtime").split("zoneinfo/")[1]
    except IndexError:
        return "Europe/Berlin"


def write_project_json(p, opts):
    music = next((m for m in sorted((p / "music").glob("*")) if m.is_file() and not m.name.startswith(".")), None)
    cfg = {
        "title": opts.get("title") or p.name,
        "language": "de",
        "timezone": local_timezone(),
        "target_minutes": float(opts.get("target_minutes") or 10),
        "resolution": "1080p",
        "fps": 30,
        "stats": [s for s in [opts.get("stats", "").strip()] if s],
        "output_dir": "export",
        "end_card": {"text": opts.get("end_text") or "Thanks for watching",
                     "sub": opts.get("end_sub") or "Neue Folge jede Woche"},
        "burn_subtitles": bool(opts.get("burn_subtitles")),
    }
    if opts.get("city"):
        cfg["default_location"] = {"city": opts["city"].strip(), "sub": (opts.get("sub") or "").strip()}
        if opts.get("city_override"):
            cfg["locations"] = {f.name: cfg["default_location"] for f in (p / "raw").iterdir()}
    if music:
        cfg["music"] = {"file": f"music/{music.name}", "volume": float(opts.get("music_volume") or 0.22)}
    (p / "project.json").write_text(json.dumps(cfg, indent=2, ensure_ascii=False))


def run_job(p, opts):
    job = state["job"]
    try:
        if opts.get("whisper") and not has_whisper():
            job["phase"] = "Lade Transkriptions-Modul (einmalig, ca. 500 MB) …"
            if not pip("faster-whisper", section="job"):
                raise RuntimeError("faster-whisper konnte nicht installiert werden.")
        write_project_json(p, opts)
        cmd = [str(VPY), "-u", "-m", "vlog.job", str(p), "--quality", opts.get("quality", "preview")]
        if opts.get("whisper"):
            cmd.append("--whisper")
        proc = subprocess.Popen(cmd, cwd=str(ENGINE), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                env={**os.environ, "PYTHONPATH": str(ENGINE)})
        for line in proc.stdout:
            if line.startswith("@@PROGRESS"):
                _, frac, *phase = line.split(" ", 2)
                job["progress"], job["phase"] = float(frac), " ".join(phase).strip()
            elif line.startswith("@@DONE"):
                job["result"] = json.loads(line[7:])
            elif line.startswith("@@ERROR"):
                job["error"] = line[8:].strip()
            else:
                log_to("job", line)
        proc.wait()
        if proc.returncode and not job["error"]:
            job["error"] = "Der Schnitt ist abgebrochen. Details im Protokoll."
        if job["result"]:
            job["progress"], job["phase"] = 1.0, "Fertig"
    except Exception as e:
        job["error"] = str(e)
    finally:
        job["running"] = False


def reveal(path):
    if MAC:
        subprocess.run(["open", "-R", path])
    elif os.name == "nt":
        subprocess.run(["explorer", "/select,", path])
    else:
        subprocess.run(["xdg-open", str(Path(path).parent)])


class Handler(BaseHTTPRequestHandler):
    server_version = f"HealboticsCutter/{VERSION}"

    def log_message(self, *args):
        pass

    def send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def query(self):
        return {k: v[0] for k, v in urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).items()}

    def do_GET(self):
        route = urllib.parse.urlparse(self.path).path
        if route == "/":
            body = (HERE / "ui.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif route == "/api/ping":
            self.send_json({"app": APP, "version": VERSION})
        elif route == "/api/state":
            with lock:
                self.send_json({**state, "projects_root": str(PROJECTS), "mac": MAC})
        elif route == "/api/projects":
            items = []
            for p in sorted(PROJECTS.glob("*/raw"), reverse=True):
                proj = p.parent
                items.append({"id": proj.name, "clips": sorted(f.name for f in p.iterdir() if not f.name.startswith(".")),
                              "music": sorted(f.name for f in (proj / "music").glob("*") if not f.name.startswith("."))})
            self.send_json(items)
        elif route == "/media":
            self.send_media(self.query().get("path", ""))
        else:
            self.send_error(404)

    def send_media(self, path):
        f = Path(path).resolve()
        if PROJECTS.resolve() not in f.parents or not f.is_file():
            return self.send_error(404)
        size = f.stat().st_size
        start, end = 0, size - 1
        rng = re.match(r"bytes=(\d*)-(\d*)", self.headers.get("Range", ""))
        if rng:
            start = int(rng.group(1) or 0)
            end = int(rng.group(2)) if rng.group(2) else size - 1
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", "video/mp4" if f.suffix == ".mp4" else "application/octet-stream")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        with f.open("rb") as fh:
            fh.seek(start)
            left = end - start + 1
            try:
                while left > 0:
                    chunk = fh.read(min(1 << 20, left))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    left -= len(chunk)
            except (BrokenPipeError, ConnectionResetError):
                pass  # the video element often aborts range requests

    def do_PUT(self):
        if urllib.parse.urlparse(self.path).path != "/api/upload":
            return self.send_error(404)
        q = self.query()
        try:
            p = project_dir(q["project"])
        except (KeyError, ValueError) as e:
            return self.send_json({"error": str(e)}, 400)
        kind = "music" if q.get("kind") == "music" else "raw"
        name = Path(q.get("name", "clip.mp4")).name
        if kind == "music":  # one music bed per project
            for old in (p / "music").glob("*"):
                old.unlink()
        dest = p / kind / name
        left = int(self.headers.get("Content-Length") or 0)
        with dest.open("wb") as fh:
            while left > 0:
                chunk = self.rfile.read(min(1 << 20, left))
                if not chunk:
                    break
                fh.write(chunk)
                left -= len(chunk)
        if left:
            dest.unlink(missing_ok=True)
            return self.send_json({"error": "Upload abgebrochen"}, 400)
        self.send_json({"ok": True, "name": name})

    def do_POST(self):
        route = urllib.parse.urlparse(self.path).path
        data = self.read_json()
        if route == "/api/new":
            self.send_json({"id": new_project(data.get("title") or "Testlauf")})
        elif route == "/api/delete-clip":
            try:
                (project_dir(data["project"]) / ("music" if data.get("kind") == "music" else "raw")
                 / Path(data["name"]).name).unlink(missing_ok=True)
                self.send_json({"ok": True})
            except (KeyError, ValueError) as e:
                self.send_json({"error": str(e)}, 400)
        elif route == "/api/run":
            if state["setup"]["status"] != "ready":
                return self.send_json({"error": "Einrichtung läuft noch."}, 409)
            if state["job"]["running"]:
                return self.send_json({"error": "Es läuft schon ein Schnitt."}, 409)
            try:
                p = project_dir(data["project"])
            except (KeyError, ValueError) as e:
                return self.send_json({"error": str(e)}, 400)
            if not any(f.is_file() and not f.name.startswith(".") for f in (p / "raw").iterdir()):
                return self.send_json({"error": "Noch keine Videos im Projekt."}, 400)
            state["job"] = {"running": True, "progress": 0.0, "phase": "Start", "log": [], "result": None,
                            "error": None, "project": p.name, "quality": data.get("quality", "preview")}
            threading.Thread(target=run_job, args=(p, data), daemon=True).start()
            self.send_json({"ok": True})
        elif route == "/api/reveal":
            reveal(data.get("path", str(PROJECTS)))
            self.send_json({"ok": True})
        elif route == "/api/quit":
            self.send_json({"ok": True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
        else:
            self.send_error(404)


def already_running():
    for port in PORTS:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.3) as s:
                s.sendall(b"GET /api/ping HTTP/1.0\r\n\r\n")
                if APP.encode() in s.recv(4096):
                    return port
        except OSError:
            continue
    return None


def main():
    PROJECTS.mkdir(parents=True, exist_ok=True)
    port = already_running()
    if port:  # second launch: just show the window again
        webbrowser.open(f"http://127.0.0.1:{port}/")
        return
    for port in PORTS:
        try:
            httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            break
        except OSError:
            continue
    else:
        sys.exit("Kein freier Port gefunden.")
    threading.Thread(target=setup, daemon=True).start()
    url = f"http://127.0.0.1:{port}/"
    print(f"{APP} läuft auf {url}", flush=True)
    if not os.environ.get("HEALBOTICS_NO_BROWSER"):
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    httpd.serve_forever()


if __name__ == "__main__":
    main()
