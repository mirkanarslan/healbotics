"""Step 2: inventory.json + project.json -> edit.json (+ review.md).

Builds the episode structure from STYLE_GUIDE.md:
  B&W flash -> hook line to camera -> ("Previously") -> B&W->colour montage with
  music -> stat cards -> stations (establishing shot with city + time card,
  talking-head jump cuts with B-roll cutaways over the voice, music bridge)
  -> outro shot -> end card.
The result is a plain JSON edit list: review it, tweak it, then render.
"""
import re
from datetime import datetime
from pathlib import Path

from .common import load_json, save_json, tc

DEFAULTS = {
    "fps": 30, "resolution": "1080p", "target_minutes": 12, "station_gap_minutes": 60,
    "max_talk_seconds": 120, "cover_every": 9, "montage_shots": 16, "montage_shot_len": 1.0,
    "time_format": "%H:%M",
    "hook_keywords": ["problem", "geld", "euro", "kunden", "risiko", "alles", "nie", "heute",
                      "erste", "million", "fehler", "warum"],
    "end_card": {"text": "Thanks for watching", "sub": "Neue Folge jede Woche"},
}
RES = {"720p": (1280, 720), "1080p": (1920, 1080), "4k": (3840, 2160)}


def daypart(dt):
    h = dt.hour
    return ("Morgen" if 5 <= h < 11 else "Mittag" if h < 14 else "Nachmittag" if h < 18
            else "Abend" if h < 22 else "Nacht") if h >= 5 else "Nacht"


def grade_for(clip, cfg):
    over = cfg.get("grades", {})
    name = Path(clip["file"]).name
    if name in over or clip["file"] in over:
        return over.get(name, over.get(clip["file"]))
    h = datetime.fromisoformat(clip["recorded"]).hour
    return "bloomfield_night" if h >= 20 or h < 6 else cfg.get("grade_default", "bloomfield_warm_film")


def place_for(clip, cfg):
    over = cfg.get("locations", {})
    name = Path(clip["file"]).name
    return over.get(name) or over.get(clip["file"]) or clip.get("place") or cfg.get("default_location")


class BrollPool:
    """Hands out non-overlapping B-roll windows, walking through each clip."""

    def __init__(self, clips):
        self.clips = [c for c in clips if c["duration"] >= 1.2]
        self.cursor = {c["file"]: min(0.5, c["duration"] * 0.1) for c in self.clips}
        self.i = 0

    def take(self, length, prefer_last=False):
        if not self.clips:
            return None
        order = list(reversed(self.clips)) if prefer_last else \
            self.clips[self.i % len(self.clips):] + self.clips[:self.i % len(self.clips)]
        for c in order:
            start = self.cursor[c["file"]]
            if start + length <= c["duration"] - 0.2:
                self.cursor[c["file"]] = start + length + 0.3
                self.i += 1
                return c, round(start, 3), round(start + length, 3)
        c = order[0]  # everything used once: loop from the start again
        self.cursor = {k: 0.2 for k in self.cursor}
        length = min(length, c["duration"] - 0.4)
        return (c, 0.2, round(0.2 + length, 3)) if length > 0.3 else None


def pad_speech(speech, duration, before=0.12, after=0.2):
    out = []
    for s, e in speech:
        s, e = max(0, s - before), min(duration, e + after)
        if out and s - out[-1][1] < 0.25:
            out[-1][1] = e
        else:
            out.append([s, e])
    return out


def subs_for(clip, start, end):
    """Transcript lines inside [start, end], re-timed to the segment."""
    out = []
    for seg in clip.get("transcript") or []:
        if seg["end"] <= start or seg["start"] >= end:
            continue
        out.append([round(max(seg["start"], start) - start, 2), round(min(seg["end"], end) - start, 2),
                    seg["text"]])
    return out


def pick_hook(clips, cfg):
    if cfg.get("hook"):
        h = cfg["hook"]
        clip = next((c for c in clips if c["file"] == h["file"] or Path(c["file"]).name == Path(h["file"]).name), None)
        if not clip:
            raise SystemExit(f"Hook-Datei {h['file']} aus project.json ist nicht in raw/.")
        return clip, h["in"], h["out"], "aus project.json"
    keys = [k.lower() for k in cfg["hook_keywords"]]
    best = None
    for idx, c in enumerate(clips):
        for seg in c.get("transcript") or []:
            d = seg["end"] - seg["start"]
            if not 2.5 <= d <= 12:
                continue
            t = seg["text"].lower()
            score = 3 * bool(re.search(r"\d", t)) + 2 * ("?" in t) + ("!" in t) \
                + 2 * sum(k in t for k in keys) + (idx > 0) - abs(d - 6) / 6
            if not best or score > best[0]:
                best = (score, c, seg["start"], seg["end"], f"Transkript: „{seg['text']}“")
    if best:
        return best[1:]
    talk = [c for c in clips if c["kind"] == "talk"]
    if not talk:
        return None
    mid = talk[len(talk) // 2]
    s, e = min(mid["speech"], key=lambda iv: abs((iv[1] - iv[0]) - 6))
    if e - s > 10:
        e = s + 8
    return mid, s, e, "längste passende Sprechpassage (kein Transkript)"


def stations_of(clips, cfg):
    stations, last_city, last_time = [], None, None
    for c in clips:
        place = place_for(c, cfg)
        city = (place or {}).get("city")
        t = datetime.fromisoformat(c["recorded"])
        gap = (t - last_time).total_seconds() / 60 if last_time else 0
        if not stations or (city and last_city and city != last_city) or gap > cfg["station_gap_minutes"]:
            stations.append({"clips": [], "place": place, "start": t})
        stations[-1]["clips"].append(c)
        if city:
            last_city = city
            stations[-1]["place"] = stations[-1]["place"] or place
        last_time = t
    return stations


def seg(clip, s, e, cfg, **extra):
    return {"file": clip["file"], "in": round(s, 3), "out": round(e, 3), "grade": grade_for(clip, cfg), **extra}


def build(clips, cfg, max_talk):
    pool_all = BrollPool([c for c in clips if c["kind"] == "broll"] or clips)
    edl = []

    # 1. Cold open: B&W flash, hook line, optional "Previously" recap.
    hook = pick_hook(clips, cfg)
    for _ in range(3):
        b = pool_all.take(0.4)
        if b:
            edl.append(seg(b[0], b[1], b[2], cfg, grade="bloomfield_bw_recap", volume=0,
                           chapter="Intro" if not edl else None, note="Cold Open Flash"))
    if hook:
        hc, hs, he, why = hook
        edl.append(seg(hc, max(0, hs - 0.1), min(hc["duration"], he + 0.15), cfg,
                       subtitles=subs_for(hc, hs - 0.1, he + 0.15), note=f"Hook ({why})",
                       chapter=None if edl else "Intro"))
    prev = cfg.get("previously") or []
    for i, item in enumerate(prev[:6]):
        f, s = (item, 0.5) if isinstance(item, str) else (item["file"], item.get("in", 0.5))
        edl.append({"file": f, "in": s, "out": s + 1.0, "grade": "bloomfield_bw_recap", "volume": 0,
                    "overlays": [{"type": "title", "text": "Previously", "start": 0.1, "duration": 0.9}] if i == 0 else [],
                    "note": "Previously"})

    # 2. Montage: music starts, ~1 s cuts, black & white turning to colour halfway.
    n = cfg["montage_shots"]
    for i in range(n):
        b = pool_all.take(cfg["montage_shot_len"])
        if not b:
            break
        edl.append(seg(b[0], b[1], b[2], cfg, volume=0, music_start=(i == 0) or None,
                       grade="bloomfield_bw_recap" if i < n // 2 else grade_for(b[0], cfg),
                       note="Montage"))

    # 3. Build-in-public numbers.
    for text in (cfg.get("stats") or [])[:2]:
        b = pool_all.take(3.0)
        if b:
            edl.append(seg(b[0], b[1], b[2], cfg, volume=0.2, note="Zahlen",
                           overlays=[{"type": "stat", "text": text, "start": 0.3, "duration": 2.5}]))

    # 4. Stations.
    stations = stations_of(clips, cfg)
    names = cfg.get("station_names") or []
    shown_city, shown_part = None, None
    for si, st in enumerate(stations):
        pool = BrollPool([c for c in st["clips"] if c["kind"] == "broll"] or st["clips"])
        place = st["place"] or {}
        city = place.get("city")
        part = daypart(st["start"])
        title = names[si] if si < len(names) else (f"{city} – {part}" if city else f"Station {si + 1} – {part}")
        overlays = []
        if city and city != shown_city:
            overlays.append({"type": "location", "text": city, "sub": place.get("sub") or "",
                             "start": 0.4, "duration": 3.0})
            shown_city = city
        if part != shown_part:
            overlays.append({"type": "time", "text": st["start"].strftime(cfg["time_format"]),
                             "start": 0.4, "duration": 3.0})
            shown_part = part
        est = pool.take(3.6)
        if est:
            edl.append(seg(est[0], est[1], est[2], cfg, volume=0.5, overlays=overlays, chapter=title,
                           note="Establishing Shot"))
        elif overlays:
            st["pending_overlays"] = overlays

        since_cover, chapter_set = 0.0, bool(est)
        for c in [c for c in st["clips"] if c["kind"] == "talk"]:
            used = 0.0
            for s, e in pad_speech(c["speech"], c["duration"]):
                if used >= max_talk:
                    break
                e = min(e, s + (max_talk - used))
                item = seg(c, s, e, cfg, subtitles=subs_for(c, s, e), note="Talk")
                if st.get("pending_overlays"):
                    item["overlays"] = st.pop("pending_overlays")
                if not chapter_set:
                    item["chapter"], chapter_set = title, True
                since_cover += e - s
                if since_cover >= cfg["cover_every"] and e - s >= 4:
                    b = pool.take(min(3.0, e - s - 1.2))
                    if b and b[0]["file"] != c["file"]:
                        item["cover"] = {"file": b[0]["file"], "in": b[1], "start": 0.6,
                                         "duration": round(b[2] - b[1], 3), "grade": grade_for(b[0], cfg)}
                        since_cover = 0.0
                edl.append(item)
                used += e - s

        if si < len(stations) - 1:  # music bridge to the next station
            for _ in range(3):
                b = pool.take(2.2)
                if b:
                    edl.append(seg(b[0], b[1], b[2], cfg, volume=0.25, note="Brücke"))

    # 5. Outro shot and end card.
    last = BrollPool([c for c in stations[-1]["clips"] if c["kind"] == "broll"] or clips).take(4.0, prefer_last=True)
    if last:
        edl.append(seg(last[0], last[1], last[2], cfg, volume=0.3, note="Outro"))
    edl.append({"card": cfg["end_card"], "duration": 3.5, "note": "Endkarte"})

    for item in edl:  # drop empty keys for a readable edit.json
        for k in [k for k, v in item.items() if v is None or v == [] or v == {}]:
            del item[k]
    return edl


def length(edl):
    return sum(c.get("duration", 0) if "card" in c else c["out"] - c["in"] for c in edl)


def write_review(path, edl, cfg, project):
    rows, t = [], 0.0
    for c in edl:
        d = c.get("duration", 0) if "card" in c else c["out"] - c["in"]
        what = c["card"]["text"] if "card" in c else f"{c['file']} {c['in']:.1f}–{c['out']:.1f}"
        extra = []
        if c.get("chapter"):
            extra.append(f"**Kapitel: {c['chapter']}**")
        for ov in c.get("overlays", []):
            extra.append(f"{ov['type']}: {ov['text']}")
        if c.get("cover"):
            extra.append(f"B-Roll drüber: {c['cover']['file']}")
        if c.get("subtitles"):
            extra.append("„" + " ".join(s[2] for s in c["subtitles"])[:90] + "“")
        rows.append(f"| {tc(t)} | {c.get('note', '')} | {what} | {d:.1f}s | {'; '.join(extra)} |")
        t += d
    Path(path).write_text(
        f"# Rohschnitt: {cfg.get('title', project)}\n\nLänge: {tc(t)} (Ziel {cfg['target_minutes']} min), "
        f"{len(edl)} Segmente.\n\n| Zeit | Teil | Quelle | Dauer | Details |\n|---|---|---|---|---|\n"
        + "\n".join(rows) + "\n")


def run(project_dir):
    project_dir = Path(project_dir).resolve()
    cfg = {**DEFAULTS, **load_json(project_dir / "project.json", {})}
    inv = load_json(project_dir / "inventory.json")
    if not inv:
        raise SystemExit("inventory.json fehlt. Erst `cut.py ingest` ausführen.")
    clips = inv["clips"]

    max_talk = cfg["max_talk_seconds"]
    edl = build(clips, cfg, max_talk)
    target = cfg["target_minutes"] * 60 * 1.15
    while length(edl) > target and max_talk > 20:  # trim talk per clip until it fits
        max_talk = int(max_talk * 0.8)
        edl = build(clips, cfg, max_talk)

    w, h = RES[cfg["resolution"]]
    out = {
        "output": f"../../exports/{project_dir.name}.mp4",
        "settings": {"width": w, "height": h, "fps": cfg["fps"], "grade": cfg.get("grade_default", "bloomfield_warm_film"),
                     "burn_subtitles": cfg.get("burn_subtitles", False)},
        "clips": edl,
    }
    if cfg.get("music"):
        out["music"] = cfg["music"]
    save_json(project_dir / "edit.json", out)
    write_review(project_dir / "review.md", edl, cfg, project_dir.name)
    print(f"Rohschnitt: {len(edl)} Segmente, Länge {tc(length(edl))} "
          f"(Ziel {cfg['target_minutes']} min, Talk-Limit pro Clip {max_talk}s)")
    print(f"  {project_dir / 'edit.json'}\n  {project_dir / 'review.md'}")
    return out
