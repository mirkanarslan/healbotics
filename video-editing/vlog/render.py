"""Step 3: edit.json -> finished video + chapters.txt + subtitles.srt.

Each segment is rendered on its own (scale/crop or blurred fill for portrait
clips, HDR tonemapping, colour grade, B-roll cover, text overlays), then all
segments are concatenated and the music bed is mixed in with sidechain ducking
under speech, starting at the montage and fading out at the end.
"""
import json
import tempfile
from pathlib import Path

from .common import HERE, ffmpeg, has_filter, probe, run, srt_tc, tc
from .text import overlay_png

GRADES = json.loads((HERE / "grades.json").read_text())


def prep_chain(meta, w, h, fps):
    """Bring any source to the target frame: HDR -> SDR, portrait -> blurred fill."""
    chain = []
    if meta.get("transfer") in ("arib-std-b67", "smpte2084"):
        if has_filter("zscale") and has_filter("tonemap"):
            tin = "arib-std-b67" if meta["transfer"] == "arib-std-b67" else "smpte2084"
            chain.append(f"zscale=tin={tin}:min=bt2020nc:pin=bt2020:t=linear:npl=203,format=gbrpf32le,"
                         f"zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p")
        else:
            print("  Warnung: HDR-Clip, aber ffmpeg ohne zscale/tonemap. Farben können flau aussehen.")
    portrait_in_landscape = meta["height"] > meta["width"] and w > h
    if portrait_in_landscape:
        chain.append(f"split[pa][pb];[pa]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
                     f"boxblur=30:2,eq=brightness=-0.08[pbg];[pb]scale=-2:{h}[pfg];[pbg][pfg]overlay=(W-w)/2:0")
    else:
        chain.append(f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}")
    chain.append(f"fps={fps},setsar=1")
    return ",".join(chain)


def encode_args(cfg):
    return ["-c:v", "libx264", "-preset", cfg["preset"], "-crf", str(cfg["crf"]), "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]


class Inputs:
    """Collects ffmpeg inputs and hands out their stream index."""

    def __init__(self):
        self.args, self.n = [], 0

    def add(self, *args):
        self.args += [*args]
        self.n += 1
        return self.n - 1


def add_overlay(graph, inputs, last, ov, w, h, fps, seg_dur, cache, tag, fade=0.35):
    """Overlay one text PNG on stream `last`, return the new stream label."""
    start = ov.get("start", 0.3)
    dur = min(ov.get("duration", 3.0), max(0.1, seg_dur - start))
    end = start + dur
    png = overlay_png(ov, w, h, cache)
    k = inputs.add("-loop", "1", "-framerate", str(fps), "-t", f"{seg_dur:.3f}", "-i", str(png))
    chain = "format=rgba"
    if fade:
        f = min(fade, dur / 3)
        chain += f",fade=t=in:st={start}:d={f}:alpha=1,fade=t=out:st={end - f}:d={f}:alpha=1"
    graph.append(f"[{k}:v]{chain}[o{tag}]")
    graph.append(f"[{last}][o{tag}]overlay=eof_action=pass:enable='between(t,{start},{end})'[l{tag}]")
    return f"l{tag}"


def render_card(clip, out, cfg, cache):
    w, h, fps = cfg["width"], cfg["height"], cfg["fps"]
    dur = clip.get("duration", 3.0)
    inputs, graph = Inputs(), []
    inputs.add("-f", "lavfi", "-i", f"color=black:s={w}x{h}:r={fps}:d={dur}")
    a = inputs.add("-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo")
    ov = {"type": "card", **clip["card"], "start": 0.2, "duration": dur - 0.4}
    last = add_overlay(graph, inputs, "0:v", ov, w, h, fps, dur, cache, "c", fade=0.5)
    graph.append(f"[{last}]setsar=1[v]")
    run([ffmpeg(), "-y", "-loglevel", "error", *inputs.args, "-filter_complex", ";".join(graph),
         "-map", "[v]", "-map", f"{a}:a", "-t", str(dur), *encode_args(cfg), str(out)])
    return dur


def render_segment(clip, out, cfg, cache):
    if "card" in clip:
        return render_card(clip, out, cfg, cache)
    w, h, fps = cfg["width"], cfg["height"], cfg["fps"]
    meta = probe(clip["file"])
    speed = clip.get("speed", 1.0)
    start, end = clip.get("in", 0), clip.get("out", meta["duration"])
    dur = (end - start) / speed

    inputs, graph = Inputs(), []
    inputs.add("-ss", str(start), "-to", str(end), "-i", clip["file"])
    graph.append(f"[0:v]{prep_chain(meta, w, h, fps)}" + (f",setpts=PTS/{speed}" if speed != 1 else "")
                 + f",{GRADES[clip.get('grade', cfg['grade'])]['filter']}[base]")
    last = "base"

    cover = clip.get("cover")
    if cover:  # B-roll over the voice: picture from another clip, sound stays
        cmeta = probe(cover["file"])
        k = inputs.add("-ss", str(cover.get("in", 0)), "-t", str(cover["duration"]), "-i", cover["file"])
        cs = cover.get("start", 0)
        graph.append(f"[{k}:v]{prep_chain(cmeta, w, h, fps)},{GRADES[cover.get('grade', cfg['grade'])]['filter']},"
                     f"setpts=PTS-STARTPTS+{cs}/TB[cov]")
        graph.append(f"[{last}][cov]overlay=eof_action=pass:enable='between(t,{cs},{cs + cover['duration']})'[cvd]")
        last = "cvd"

    for i, ov in enumerate(clip.get("overlays", [])):
        last = add_overlay(graph, inputs, last, ov, w, h, fps, dur, cache, f"t{i}")
    if cfg.get("burn_subtitles"):
        for i, (s0, e0, text) in enumerate(clip.get("subtitles", [])):
            ov = {"type": "subtitle", "text": text, "start": s0, "duration": e0 - s0}
            last = add_overlay(graph, inputs, last, ov, w, h, fps, dur, cache, f"s{i}", fade=0)
    if cfg.get("letterbox"):
        bar = int(h * cfg["letterbox"])
        graph.append(f"[{last}]drawbox=x=0:y=0:w=iw:h={bar}:color=black:t=fill,"
                     f"drawbox=x=0:y=ih-{bar}:w=iw:h={bar}:color=black:t=fill[lb]")
        last = "lb"
    graph.append(f"[{last}]null[v]")

    vol = clip.get("volume", 1.0)
    if meta["has_audio"] and vol > 0:
        atempo = f"atempo={speed}," if speed != 1 else ""
        graph.append(f"[0:a]{atempo}aresample=48000,aformat=channel_layouts=stereo,volume={vol},apad[a]")
        amap = "[a]"
    else:
        amap = f"{inputs.add('-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo')}:a"
    run([ffmpeg(), "-y", "-loglevel", "error", *inputs.args, "-filter_complex", ";".join(graph),
         "-map", "[v]", "-map", amap, "-t", f"{dur:.3f}", *encode_args(cfg), str(out)])
    return dur


def chapters(edl, durations):
    """YouTube chapters: first at 0:00, each at least 10 s, at least three."""
    marks, t = [], 0.0
    for clip, d in zip(edl, durations):
        if clip.get("chapter"):
            if not marks or t - marks[-1][0] >= 10:  # shorter than 10 s: fold into previous
                marks.append((t, clip["chapter"]))
        t += d
    if marks:
        marks[0] = (0.0, marks[0][1])
    return marks


def subtitles(edl, durations):
    lines, t = [], 0.0
    for clip, d in zip(edl, durations):
        for s, e, text in clip.get("subtitles", []):
            lines.append((t + s, t + min(e, d), text))
        t += d
    return lines


def run_render(edl_path, preview=False, uhd=False, progress=None):
    import os
    edl_path = Path(edl_path).resolve()
    edl = json.loads(edl_path.read_text())
    os.chdir(edl_path.parent)
    cfg = {"width": 1920, "height": 1080, "fps": 30, "letterbox": 0, "grade": "bloomfield_warm_film",
           "preset": "medium", "crf": 18, **edl.get("settings", {})}
    if preview:
        cfg.update(width=960, height=540, preset="ultrafast", crf=28)
    elif uhd:
        cfg.update(width=3840, height=2160, crf=20)

    output = Path(edl.get("output", "export.mp4"))
    if preview:
        output = output.with_name(output.stem + "_preview" + output.suffix)
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        segs, durs = [], []
        for i, clip in enumerate(edl["clips"]):
            if progress:
                progress(i, len(edl["clips"]))
            else:
                print(f"\r  Segment {i + 1}/{len(edl['clips'])}", end="", flush=True)
            out = tmp / f"seg_{i:04d}.mp4"
            durs.append(render_segment(clip, out, cfg, tmp))
            segs.append(out)
        print()
        (tmp / "list.txt").write_text("".join(f"file '{s}'\n" for s in segs))
        joined = tmp / "joined.mp4"
        run([ffmpeg(), "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"),
             "-c", "copy", str(joined)])

        total = sum(durs)
        music = edl.get("music")
        if music and Path(music["file"]).exists():
            offset = 0.0
            for clip, d in zip(edl["clips"], durs):
                if clip.get("music_start"):
                    break
                offset += d
            else:
                offset = 0.0
            ms = int(offset * 1000)
            fade_at = max(0, total - 3)
            audio = (f"[1:a]aresample=48000,aformat=channel_layouts=stereo,volume={music.get('volume', 0.22)},"
                     f"adelay={ms}|{ms},afade=t=out:st={fade_at}:d=3[m];"
                     "[m][0:a]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[md];"
                     "[0:a][md]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1[a]")
            cmd = [ffmpeg(), "-y", "-loglevel", "error", "-i", str(joined), "-stream_loop", "-1",
                   "-i", music["file"], "-filter_complex", audio, "-map", "0:v", "-map", "[a]"]
        else:
            if music:
                print(f"  Warnung: Musikdatei {music['file']} nicht gefunden, Export ohne Musik.")
            cmd = [ffmpeg(), "-y", "-loglevel", "error", "-i", str(joined), "-af", "loudnorm=I=-14:TP=-1"]
        run(cmd + ["-t", f"{total:.3f}", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                   "-movflags", "+faststart", str(output)])

    marks = chapters(edl["clips"], durs)
    chap_file = output.with_name(output.stem + "_chapters.txt")
    chap_file.write_text("".join(f"{tc(t)} {name}\n" for t, name in marks))
    if len(marks) < 3:
        print("  Hinweis: weniger als 3 Kapitel, YouTube zeigt dann keine Kapitel an.")
    subs = subtitles(edl["clips"], durs)
    if subs:
        output.with_name(output.stem + ".srt").write_text("".join(
            f"{i}\n{srt_tc(s)} --> {srt_tc(e)}\n{text}\n\n" for i, (s, e, text) in enumerate(subs, 1)))
    print(f"Fertig: {output.resolve()} ({tc(total)})")
    print(f"  Kapitel: {chap_file.resolve()}" + (f"\n  Untertitel: {output.with_suffix('.srt').resolve()}" if subs else ""))
    return output, total
