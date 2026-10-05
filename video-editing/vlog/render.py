"""Step 3: edit.json -> finished video + chapters.txt + subtitles.srt.

Each segment is rendered on its own (scale/crop or blurred fill for portrait
clips, HDR tonemapping, colour grade, B-roll cover, text overlays), then all
segments are concatenated and the music bed is mixed in with sidechain ducking
under speech, starting at the montage and fading out at the end.
"""
import json
import tempfile
from pathlib import Path

from .common import HERE, esc_text, ffmpeg, font_opt, has_filter, probe, run, srt_tc, tc

GRADES = json.loads((HERE / "grades.json").read_text())


def fade_alpha(start, dur, fade=0.35):
    end = start + dur
    return (f"if(lt(t,{start}),0,if(lt(t,{start + fade}),(t-{start})/{fade},"
            f"if(lt(t,{end - fade}),1,if(lt(t,{end}),({end}-t)/{fade},0))))")


def overlay_filters(ov, h):
    """drawtext filters for one overlay, timed relative to the segment."""
    start, dur = ov.get("start", 0.3), ov.get("duration", 3.0)
    size = int(h * ov.get("scale", 1.0) / 1080 * 64)
    common = f"fontcolor=white:alpha='{fade_alpha(start, dur)}':enable='between(t,{start},{start + dur})'"
    text = esc_text(ov["text"])
    kind = ov["type"]
    if kind == "location":  # city large bottom-left, country/district below
        out = [f"drawtext={font_opt('bold')}:text='{esc_text(ov['text'].upper())}':fontsize={size}:{common}:"
               f"x=w*0.06:y=h*0.78-th:shadowcolor=black@0.45:shadowx=2:shadowy=2"]
        if ov.get("sub"):
            out.append(f"drawtext={font_opt('regular')}:text='{esc_text(ov['sub'])}':fontsize={int(size * 0.42)}:"
                       f"{common}:x=w*0.06+4:y=h*0.78+{int(size * 0.2)}:shadowcolor=black@0.45:shadowx=1:shadowy=1")
        return out
    if kind == "time":  # small monospace clock top-left
        return [f"drawtext={font_opt('mono')}:text='{text}':fontsize={int(size * 0.55)}:{common}:"
                f"x=w*0.05:y=h*0.07:shadowcolor=black@0.5:shadowx=1:shadowy=1"]
    if kind == "stat":  # build-in-public numbers in a box
        return [f"drawtext={font_opt('bold')}:text='{text}':fontsize={int(size * 0.6)}:{common}:box=1:"
                f"boxcolor=black@0.55:boxborderw={int(size * 0.3)}:x=(w-tw)/2:y=h*0.12"]
    if kind == "caption":  # key sentence lower third
        return [f"drawtext={font_opt('bold')}:text='{text}':fontsize={int(size * 0.55)}:{common}:"
                f"x=(w-tw)/2:y=h*0.86:shadowcolor=black@0.7:shadowx=2:shadowy=2"]
    if kind == "title":  # e.g. "Previously" over the B&W recap
        return [f"drawtext={font_opt('serif')}:text='{text}':fontsize={int(size * 1.1)}:{common}:"
                f"x=(w-tw)/2:y=(h-th)/2:shadowcolor=black@0.6:shadowx=2:shadowy=2"]
    raise ValueError(f"Unbekannter Overlay-Typ: {kind}")


def subtitle_filters(subs, h):
    size = int(h / 1080 * 40)
    return [f"drawtext={font_opt('bold')}:text='{esc_text(t)}':fontsize={size}:fontcolor=white:"
            f"box=1:boxcolor=black@0.5:boxborderw={size // 3}:x=(w-tw)/2:y=h*0.9-th:"
            f"enable='between(t,{s},{e})'" for s, e, t in subs]


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


def render_card(clip, out, cfg):
    w, h, fps = cfg["width"], cfg["height"], cfg["fps"]
    card, dur = clip["card"], clip.get("duration", 3.0)
    size = int(h / 1080 * card.get("size", 72))
    lines = [card["text"]] + ([card["sub"]] if card.get("sub") else [])
    vf = []
    for i, line in enumerate(lines):
        fs = size if i == 0 else int(size * 0.45)
        y = "(h-th)/2" if len(lines) == 1 else (f"(h-th)/2-{int(size * 0.4)}" if i == 0 else f"(h/2)+{int(size * 0.5)}")
        color = card.get("color", "#D4AF37") if i == 0 else "white@0.85"
        vf.append(f"drawtext={font_opt('serif' if card.get('serif', True) else 'bold')}:text='{esc_text(line)}':"
                  f"fontsize={fs}:fontcolor={color}:alpha='{fade_alpha(0.2, dur - 0.4, 0.5)}':x=(w-tw)/2:y={y}")
    run([ffmpeg(), "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=black:s={w}x{h}:r={fps}:d={dur}",
         "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-vf", ",".join(vf) + ",setsar=1",
         "-t", str(dur), *encode_args(cfg), str(out)])
    return dur


def render_segment(clip, out, cfg):
    if "card" in clip:
        return render_card(clip, out, cfg)
    w, h, fps = cfg["width"], cfg["height"], cfg["fps"]
    meta = probe(clip["file"])
    speed = clip.get("speed", 1.0)
    start, end = clip.get("in", 0), clip.get("out", meta["duration"])
    dur = (end - start) / speed

    inputs = ["-ss", str(start), "-to", str(end), "-i", clip["file"]]
    graph = [f"[0:v]{prep_chain(meta, w, h, fps)}" + (f",setpts=PTS/{speed}" if speed != 1 else "")
             + f",{GRADES[clip.get('grade', cfg['grade'])]['filter']}[base]"]
    last = "base"

    cover = clip.get("cover")
    if cover:  # B-roll over the voice: video from another clip, audio stays
        cmeta = probe(cover["file"])
        inputs += ["-ss", str(cover.get("in", 0)), "-t", str(cover["duration"]), "-i", cover["file"]]
        cs = cover.get("start", 0)
        graph.append(f"[1:v]{prep_chain(cmeta, w, h, fps)},{GRADES[cover.get('grade', cfg['grade'])]['filter']},"
                     f"setpts=PTS-STARTPTS+{cs}/TB[cov]")
        graph.append(f"[{last}][cov]overlay=eof_action=pass:enable='between(t,{cs},{cs + cover['duration']})'[cvd]")
        last = "cvd"

    texts = [f for ov in clip.get("overlays", []) for f in overlay_filters(ov, h)]
    if cfg.get("burn_subtitles") and clip.get("subtitles"):
        texts += subtitle_filters(clip["subtitles"], h)
    if cfg.get("letterbox"):
        bar = int(h * cfg["letterbox"])
        texts.append(f"drawbox=x=0:y=0:w=iw:h={bar}:color=black:t=fill,drawbox=x=0:y=ih-{bar}:w=iw:h={bar}:color=black:t=fill")
    graph.append(f"[{last}]" + (",".join(texts) if texts else "null") + "[v]")

    vol = clip.get("volume", 1.0)
    if meta["has_audio"] and vol > 0:
        atempo = f"atempo={speed}," if speed != 1 else ""
        graph.append(f"[0:a]{atempo}aresample=48000,aformat=channel_layouts=stereo,volume={vol},apad[a]")
        amap = "[a]"
    else:
        inputs += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
        amap = f"{len([x for x in inputs if x == '-i']) - 1}:a"
    run([ffmpeg(), "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(graph),
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


def run_render(edl_path, preview=False, uhd=False):
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
            print(f"\r  Segment {i + 1}/{len(edl['clips'])}", end="", flush=True)
            out = tmp / f"seg_{i:04d}.mp4"
            durs.append(render_segment(clip, out, cfg))
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
